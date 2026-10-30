# backend/app/services/exchange_service.py
import time
import requests
import ccxt

BINANCE_FAPI = "https://fapi.binance.com"
BINANCE_SPOT_API = "https://api.binance.com"
_cache = {
    "pairs": None,
    "limits": {},
    "time": 0,
}
_spot_cache = {
    "pairs": None,
    "limits": {},
    "time": 0,
}
CACHE_SECONDS = 600  # 10 分钟缓存
_pair_limits_cache = {}
_pair_limits_cache_ts = 0
_PAIR_LIMITS_TTL = 60
_balance_cache = {}
_BALANCE_CACHE_TTL = 10

class ExchangeService:

    @staticmethod
    def get_account_balance(exchange: str, api_key: str, api_secret: str,
                             passphrase: str = "", trading_mode: str = "futures"):
        exchange_name = {"gate": "gateio", "huobi": "htx"}.get(exchange, exchange)
        exchange_class = getattr(ccxt, exchange_name, None)
        if exchange_class is None:
            raise ValueError(f"不支持的交易所: {exchange}")
        if not api_key or not api_secret:
            raise ValueError("实盘账户缺少 API 凭证")

        balance_type = "spot" if trading_mode == "spot" else "future"
        cache_key = (exchange_name, api_key, api_secret, passphrase, balance_type)
        now = time.time()
        cached = _balance_cache.get(cache_key)
        if cached and now - cached["time"] < _BALANCE_CACHE_TTL:
            return cached["data"]

        config = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "timeout": 10000,
        }
        config["options"] = {"defaultType": balance_type}
        if passphrase:
            config["password"] = passphrase
        client = exchange_class(config)
        data = client.fetch_balance({"type": balance_type})
        result = {
            "total": float((data.get("total") or {}).get("USDT") or 0),
            "free": float((data.get("free") or {}).get("USDT") or 0),
            "used": float((data.get("used") or {}).get("USDT") or 0),
        }
        _balance_cache[cache_key] = {"time": now, "data": result}
        return result

    @staticmethod
    def get_account_wallets(exchange: str, api_key: str, api_secret: str,
                            passphrase: str = ""):
        wallets = {}
        errors = []
        for wallet_type in ("futures", "spot"):
            try:
                wallets[wallet_type] = ExchangeService.get_account_balance(
                    exchange, api_key, api_secret, passphrase, wallet_type
                )
            except Exception as exc:
                errors.append(f"{wallet_type}: {exc}")
        if not wallets:
            raise RuntimeError("; ".join(errors))
        return wallets

    @staticmethod
    def get_binance_usdt_futures_pair_limits(pair: str):
        global _pair_limits_cache, _pair_limits_cache_ts
        now = time.time()
        if now - _pair_limits_cache_ts >= _PAIR_LIMITS_TTL or not _pair_limits_cache:
            try:
                resp = requests.get(
                    f"{BINANCE_FAPI}/fapi/v1/exchangeInfo",
                    timeout=5,
                )
                resp.raise_for_status()
                data = resp.json()
                new_cache = {}
                for sym in data.get("symbols", []):
                    name = sym.get("symbol", "")
                    if (
                        not name.endswith("USDT")
                        or sym.get("quoteAsset") != "USDT"
                        or sym.get("contractType") != "PERPETUAL"
                        or sym.get("status") != "TRADING"
                    ):
                        continue
                    # 转换成 Freqtrade 格式：BTC/USDT:USDT
                    ft_pair = f"{name[:-4]}/USDT:USDT"
                    filters = sym.get("filters", [])
                    min_qty = None
                    min_notional = None
                    for f in filters:
                        if f.get("filterType") in ("LOT_SIZE", "MARKET_LOT_SIZE"):
                            try:
                                value = float(f.get("minQty", 0.001))
                                min_qty = value if min_qty is None else max(min_qty, value)
                            except (TypeError, ValueError):
                                continue
                        elif f.get("filterType") in ("MIN_NOTIONAL", "NOTIONAL"):
                            try:
                                value = f.get("notional") or f.get("minNotional")
                                value = float(value)
                                min_notional = (
                                    value if min_notional is None
                                    else max(min_notional, value)
                                )
                            except (TypeError, ValueError):
                                continue
                    new_cache[ft_pair] = {
                        "symbol": name,
                        "min_qty": min_qty or 0.001,
                        "min_notional": min_notional or 10.0,
                    }
                _pair_limits_cache = new_cache
                _pair_limits_cache_ts = now
            except (requests.RequestException, ValueError) as e:
                print(f"[ExchangeService] fetch pair limits failed: {e}")
                return None

        result = _pair_limits_cache.get(pair)
        if not result:
            return None

        try:
            ticker = requests.get(
                f"{BINANCE_FAPI}/fapi/v1/ticker/price",
                params={"symbol": result["symbol"]},
                timeout=5,
            )
            ticker.raise_for_status()
            price = float(ticker.json()["price"])
        except (requests.RequestException, KeyError, TypeError, ValueError) as e:
            print(f"[ExchangeService] fetch pair price failed: {e}")
            return result

        # Binance checks both the minimum notional and the minimum quantity.
        # The effective minimum is therefore the larger of the two values.
        effective_notional = max(
            result["min_notional"],
            result["min_qty"] * price,
        )
        return {
            "min_qty": result["min_qty"],
            "min_notional": effective_notional,
            "price": price,
        }

    @staticmethod
    def get_binance_usdt_futures_pairs(force=False):
        now = time.time()

        # 1. 检查缓存（如果没有要求强制刷新，且缓存未过期，直接返回）
        if (
                not force
                and _cache["pairs"]
                and now - _cache["time"] < CACHE_SECONDS
        ):
            return _cache["pairs"]

        url = f"{BINANCE_FAPI}/fapi/v1/exchangeInfo"

        # ★ 关键修改 1：加入 User-Agent，防止被交易所防火墙拦截
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            # 发起请求，设置超时
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            pairs = []
            limits = {}
            for s in data.get("symbols", []):
                # 只保留 USDT 本位、状态 TRADING 的永续
                if s.get("quoteAsset") != "USDT":
                    continue
                if s.get("contractType") != "PERPETUAL":
                    continue
                if s.get("status") != "TRADING":
                    continue
                symbol = s.get("symbol")
                if not symbol:
                    continue
                # 与你现有 freqtrade 命名一致：BTC/USDT:USDT
                pairs.append({
                    "symbol": symbol,  # BTCUSDT
                    "name": f"{s['baseAsset']}/USDT:USDT",  # BTC/USDT:USDT
                    "base": s["baseAsset"],
                })

                min_qty = None
                min_notional = None
                for item in s.get("filters", []):
                    if item.get("filterType") == "LOT_SIZE":
                        min_qty = item.get("minQty")
                    elif item.get("filterType") in ("MIN_NOTIONAL", "NOTIONAL"):
                        min_notional = item.get("notional") or item.get("minNotional")
                limits[pairs[-1]["name"]] = {
                    "min_qty": float(min_qty) if min_qty else 0.001,
                    "min_notional": float(min_notional) if min_notional else 10.0,
                }

            pairs.sort(key=lambda x: x["name"])

            # 请求成功，更新缓存
            _cache["pairs"] = pairs
            _cache["limits"] = limits
            _cache["time"] = now
            return pairs

        except requests.exceptions.HTTPError as e:
            # ★ 关键修改 2：专门捕获 418/429 限频错误
            status_code = e.response.status_code if e.response is not None else "Unknown"
            print(f"[ExchangeService] 请求币安失败，状态码: {status_code}")

            # 如果内存里有旧数据，直接兜底返回旧数据
            if _cache["pairs"]:
                print("[ExchangeService] 正在使用缓存的旧数据进行兜底")
                return _cache["pairs"]

            # 如果没有旧数据，只能抛出异常
            raise e

        except requests.exceptions.RequestException as e:
            # 处理网络超时、断网等其他问题
            print(f"[ExchangeService] 网络请求异常: {e}")

            if _cache["pairs"]:
                print("[ExchangeService] 正在使用缓存的旧数据进行兜底")
                return _cache["pairs"]

            raise e

    # ★ 新增：获取币安现货交易对
    @staticmethod
    def get_binance_usdt_spot_pairs(force=False):
        now = time.time()
        if not force and _spot_cache["pairs"] and now - _spot_cache["time"] < CACHE_SECONDS:
            return _spot_cache["pairs"]

        url = f"{BINANCE_SPOT_API}/api/v3/exchangeInfo"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            pairs = []
            for s in data.get("symbols", []):
                # 只保留 USDT 本位、状态 TRADING 的现货
                if s.get("quoteAsset") != "USDT":
                    continue
                if s.get("status") != "TRADING":
                    continue

                symbol = s.get("symbol")  # BTCUSDT
                # 现货不需要加后缀
                ft_pair = f"{s['baseAsset']}/USDT"

                pairs.append({
                    "symbol": symbol,
                    "name": ft_pair,  # BTC/USDT
                    "base": s["baseAsset"],
                })

            pairs.sort(key=lambda x: x["name"])
            _spot_cache["pairs"] = pairs
            _spot_cache["time"] = now
            return pairs

        except Exception as e:
            print(f"[ExchangeService] 获取现货交易对失败: {e}")
            if _spot_cache["pairs"]:
                return _spot_cache["pairs"]
            raise e