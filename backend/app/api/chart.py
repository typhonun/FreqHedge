from fastapi import APIRouter
import ccxt
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
router = APIRouter()


@router.get("/strategies")
def get_strategies():
    return [
        "DcaTpLong",
        "DcaTpShort"
    ]


@router.get("/pairs/{strategy}")
def get_pairs(strategy: str):
    if strategy == "DcaTpLong":
        cfg = BASE_DIR / "freqtrade/user_data/config_long.json"

    elif strategy == "DcaTpShort":
        cfg = BASE_DIR / "freqtrade/user_data/config_short.json"

    with open(cfg, "r", encoding="utf8") as f:
        data = json.load(f)

    return data["exchange"]["pair_whitelist"]


@router.get("/candles")
def get_candles(
        pair: str,
        timeframe: str = "5m"
):
    exchange = ccxt.binance({
        "options": {
            "defaultType": "future"
        }
    })

    ohlcv = exchange.fetch_ohlcv(
        pair,
        timeframe=timeframe,
        limit=2000
    )

    return [
        {
            "time": c[0],
            "open": c[1],
            "high": c[2],
            "low": c[3],
            "close": c[4],
            "volume": c[5]
        }
        for c in ohlcv
    ]


@router.get("/latest")
def latest_candle(
        pair: str,
        timeframe: str = "5m"
):

    exchange = ccxt.binance({
        "options": {
            "defaultType": "future"
        }
    })

    candle = exchange.fetch_ohlcv(
        pair,
        timeframe=timeframe,
        limit=1
    )[0]

    return {
        "time": candle[0],
        "open": candle[1],
        "high": candle[2],
        "low": candle[3],
        "close": candle[4],
        "volume": candle[5]
    }
