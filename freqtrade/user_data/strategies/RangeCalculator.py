# freqtrade/user_data/strategies/RangeCalculator.py
"""
价格区间计算器（用于网格上下沿）

功能：
1. 从 config 读取白名单交易对（支持 pair_whitelist / dynamic whitelist 文件）
2. 通过 CCXT 获取日线 OHLCV，计算 7/30/90 天内的最高价、最低价
3. 输出可直接用于网格的 lower_price / upper_price（默认放宽 1%）
4. 支持单 pair 查询、批量计算、JSON 输出、CLI 调用
5. 带内存缓存（避免同一进程内重复请求）

用法（CLI）：
    python user_data/strategies/RangeCalculator.py --config user_data/bots/14/config_bot14_long.json --days 30
    python user_data/strategies/RangeCalculator.py --config ... --days 7 --pair AAOI/USDT:USDT --json

用法（策略内）：
    from RangeCalculator import RangeCalculator
    calc = RangeCalculator(exchange=self.dp.exchange)
    bounds = calc.get_pair_bounds("AAOI/USDT:USDT", days=30)
    # -> {'pair': ..., 'days': 30, 'high': ..., 'low': ..., 'lower': ..., 'upper': ...}
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

# ---------------- 常量 ----------------
DEFAULT_DAYS = 30
SUPPORTED_DAYS = (7, 30, 90)
PADDING_RATIO = 0.01          # 上下沿各放宽 1%，防止一开盘就破网
CACHE_TTL_SECONDS = 300       # 同一 pair+days 缓存 5 分钟
DAILY_TIMEFRAME = "1d"
FETCH_LIMIT_EXTRA = 5         # 多取几根日线，防止最新一根未收盘导致极值偏差

# ---------------- 路径 ----------------
USER_DATA_DIR = Path(__file__).resolve().parents[1]
if str(USER_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(USER_DATA_DIR))


class RangeCalculator:
    """价格区间计算器"""

    _cache = {}  # {(pair, days): (timestamp, result)}

    def __init__(self, exchange=None, config: dict = None):
        """
        :param exchange: CCXT exchange 实例（通常传 self.dp.exchange）
        :param config:   Freqtrade config dict；如果不传，则从默认路径加载
        """
        self.exchange = exchange
        self.config = config or {}
        self._exchange_error = None

        if self.exchange is None:
            self.exchange = self._try_build_exchange()

    # ============================================================
    # 初始化
    # ============================================================
    def _try_build_exchange(self):
        """没有传入 exchange 时，用配置里的 exchange 名称自行构建一个 CCXT 实例"""
        try:
            import ccxt
            cfg = self._load_config()
            name = (cfg.get("exchange", {}) or {}).get("name", "binance")
            exchange_cls = getattr(ccxt, name, None)
            if exchange_cls is None:
                raise ValueError(f"CCXT 不支持交易所: {name}")
            exch = exchange_cls({
                "enableRateLimit": True,
                "options": {"defaultType": "swap"},
            })
            return exch
        except Exception as e:
            self._exchange_error = str(e)
            return None

    def _load_config(self) -> dict:
        if self.config:
            return self.config
        # 默认尝试从 bots/14 读，失败则返回空 dict
        for candidate in (
            USER_DATA_DIR / "bots" / "14" / "config_bot14_long.json",
        ):
            if candidate.exists():
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        self.config = json.load(f)
                        return self.config
                except Exception:
                    pass
        return {}

    # ============================================================
    # 白名单读取
    # ============================================================
    def get_whitelist(self) -> list:
        """从 config 读取白名单交易对"""
        cfg = self._load_config()
        pairs = (cfg.get("exchange", {}) or {}).get("pair_whitelist", []) or []
        # 兼容 dynamic whitelist 文件
        if not pairs:
            wl_file = USER_DATA_DIR / "whitelist.json"
            if wl_file.exists():
                try:
                    with open(wl_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        pairs = data.get("pair_whitelist", []) or []
                    elif isinstance(data, list):
                        pairs = data
                except Exception:
                    pairs = []
        return [p for p in pairs if isinstance(p, str) and p]

    # ============================================================
    # 核心：单 pair 区间计算
    # ============================================================
    def get_pair_bounds(self, pair: str, days: int = DEFAULT_DAYS) -> dict:
        """
        返回:
        {
            'pair': str,
            'days': int,
            'high': float,        # 原始最高价
            'low': float,         # 原始最低价
            'lower': float,       # 下沿（已放宽 1%）
            'upper': float,       # 上沿（已放宽 1%）
            'candles': int,       # 实际使用的日线根数
            'source': str,        # 'ccxt' / 'cache' / 'fallback'
            'error': str | None,
        }
        """
        pair = str(pair)
        days = int(days)
        if days not in SUPPORTED_DAYS:
            days = DEFAULT_DAYS

        cache_key = (pair, days)
        now = time.time()
        cached = self._cache.get(cache_key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            result = dict(cached[1])
            result["source"] = "cache"
            return result

        result = {
            "pair": pair,
            "days": days,
            "high": 0.0,
            "low": 0.0,
            "lower": 0.0,
            "upper": 0.0,
            "candles": 0,
            "source": "ccxt",
            "error": None,
        }

        if self.exchange is None:
            result["error"] = f"Exchange 不可用: {self._exchange_error}"
            result["source"] = "fallback"
            return result

        try:
            ccxt_pair = self._to_ccxt_symbol(pair)
            ohlcv = self.exchange.fetch_ohlcv(
                ccxt_pair, DAILY_TIMEFRAME, limit=days + FETCH_LIMIT_EXTRA
            )
            if not ohlcv:
                raise ValueError("fetch_ohlcv 返回空")

            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df = df.dropna(subset=["high", "low"])
            # 只取最近 days 根，去掉可能未收盘的最新一根
            if len(df) > days:
                df = df.iloc[-(days + 1):]
            recent = df.tail(days)

            if recent.empty:
                raise ValueError("日线数据为空")

            raw_high = float(recent["high"].max())
            raw_low = float(recent["low"].min())
            if raw_high <= 0 or raw_low <= 0 or raw_high <= raw_low:
                raise ValueError(f"极值异常 high={raw_high} low={raw_low}")

            result.update({
                "high": raw_high,
                "low": raw_low,
                "lower": round(raw_low * (1 - PADDING_RATIO), 8),
                "upper": round(raw_high * (1 + PADDING_RATIO), 8),
                "candles": len(recent),
            })

            self._cache[cache_key] = (now, dict(result))
            return result

        except Exception as e:
            result["error"] = str(e)
            result["source"] = "fallback"
            # ★ 兜底：用当前 ticker 价格 ±10%
            try:
                ccxt_pair = self._to_ccxt_symbol(pair)
                ticker = self.exchange.fetch_ticker(ccxt_pair)
                price = float(ticker.get("last") or 0)
                if price > 0:
                    result.update({
                        "high": price,
                        "low": price,
                        "lower": round(price * 0.9, 8),
                        "upper": round(price * 1.1, 8),
                        "candles": 0,
                        "source": "fallback",
                    })
                    self._cache[cache_key] = (now, dict(result))
            except Exception as e2:
                result["error"] = f"{e} | fallback失败: {e2}"
            return result

    # ============================================================
    # 批量计算
    # ============================================================
    def get_all_bounds(self, days: int = DEFAULT_DAYS, pairs: list = None) -> dict:
        """对白名单（或指定 pairs）批量计算，返回 {pair: bounds_dict}"""
        target_pairs = pairs if pairs else self.get_whitelist()
        out = {}
        for p in target_pairs:
            out[p] = self.get_pair_bounds(p, days)
        return out

    # ============================================================
    # 工具
    # ============================================================
    @staticmethod
    def _to_ccxt_symbol(pair: str) -> str:
        """ARIA/USDT:USDT -> ARIA/USDT"""
        if not pair:
            return pair
        return pair.split(":")[0]

    @staticmethod
    def clear_cache():
        RangeCalculator._cache.clear()


# ============================================================
# CLI 入口
# ============================================================
def _fmt_price(v: float) -> str:
    if v >= 100:
        return f"{v:.2f}"
    if v >= 1:
        return f"{v:.4f}"
    return f"{v:.8f}"


def main():
    parser = argparse.ArgumentParser(description="计算白名单交易对在指定天数内的价格区间")
    parser.add_argument("--config", type=str, default=None, help="Freqtrade config json 路径")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        choices=list(SUPPORTED_DAYS), help="回看天数（7/30/90）")
    parser.add_argument("--pair", type=str, default=None, help="只计算指定 pair")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    args = parser.parse_args()

    cfg = {}
    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    calc = RangeCalculator(config=cfg)
    if calc.exchange is None:
        print(f"[ERROR] 无法构建 exchange: {calc._exchange_error}")
        sys.exit(1)

    if args.pair:
        results = {args.pair: calc.get_pair_bounds(args.pair, args.days)}
    else:
        results = calc.get_all_bounds(args.days)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print(f"\n{'=' * 78}")
    print(f"  价格区间计算 | 回看 {args.days} 天 | 生成时间 {datetime.now(timezone.utc).isoformat()}")
    print(f"{'=' * 78}")
    print(f"{'交易对':<22}{'最低价':>14}{'最高价':>14}{'下沿':>14}{'上沿':>14}  {'来源':<8}")
    print("-" * 78)
    for pair, r in results.items():
        if r.get("error") and r.get("source") == "fallback" and r.get("high", 0) <= 0:
            print(f"{pair:<22}{'--':>14}{'--':>14}{'--':>14}{'--':>14}  {r['error'][:20]}")
            continue
        src = r.get("source", "?")
        err = f"  ⚠ {r['error']}" if r.get("error") else ""
        print(
            f"{pair:<22}"
            f"{_fmt_price(r['low']):>14}"
            f"{_fmt_price(r['high']):>14}"
            f"{_fmt_price(r['lower']):>14}"
            f"{_fmt_price(r['upper']):>14}"
            f"  {src:<8}{err}"
        )
    print(f"{'=' * 78}\n")


if __name__ == "__main__":
    main()