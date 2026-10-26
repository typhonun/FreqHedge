# backend/app/services/exchange_service.py
import time
import requests

BINANCE_FAPI = "https://fapi.binance.com"

_cache = {
    "pairs": None,
    "time": 0,
}
CACHE_SECONDS = 600  # 10 分钟缓存


class ExchangeService:

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

            pairs.sort(key=lambda x: x["name"])

            # 请求成功，更新缓存
            _cache["pairs"] = pairs
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