# backend/app/services/exchange_service.py
import time
import requests

BINANCE_FAPI = "https://fapi.binance.com"

_cache = {
    "pairs": None,
    "time": 0,
}
CACHE_SECONDS = 600  # 10 分钟


class ExchangeService:

    @staticmethod
    def get_binance_usdt_futures_pairs(force=False):
        now = time.time()
        if (
            not force
            and _cache["pairs"]
            and now - _cache["time"] < CACHE_SECONDS
        ):
            return _cache["pairs"]

        url = f"{BINANCE_FAPI}/fapi/v1/exchangeInfo"
        resp = requests.get(url, timeout=10)
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
                "symbol": symbol,               # BTCUSDT
                "name": f"{s['baseAsset']}/USDT:USDT",  # BTC/USDT:USDT
                "base": s["baseAsset"],
            })

        pairs.sort(key=lambda x: x["name"])
        _cache["pairs"] = pairs
        _cache["time"] = now
        return pairs