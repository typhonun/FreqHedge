from fastapi import APIRouter
import ccxt
import json
import time
from app.services.position_service import PositionService
from pathlib import Path
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.trade_event import TradeEvent
from app.schemas.chart import (
    TradeEventCreate,
    TradeEventOut
)

BASE_DIR = Path(__file__).resolve().parents[3]
router = APIRouter()
kline_cache = {}

exchange = ccxt.binance({

    "enableRateLimit": True,

    "rateLimit": 1200,

    "options": {

        "defaultType":"future"

    }

})


def load_whitelist_pairs():
    pairs = set()

    config_files = [

        BASE_DIR / "freqtrade/user_data/config_long.json",

        BASE_DIR / "freqtrade/user_data/config_short.json"

    ]

    for cfg in config_files:

        if not cfg.exists():
            continue

        try:

            with open(
                    cfg,
                    "r",
                    encoding="utf8"
            ) as f:

                data = json.load(f)

            pairs.update(
                data["exchange"]["pair_whitelist"]
            )

        except Exception as e:

            print(
                f"读取配置失败: {e}"
            )

    return list(pairs)


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
    key = f"{pair}_{timeframe}"

    now = time.time()

    if key in kline_cache:

        cache_time, data = kline_cache[key]

        if now - cache_time < 300:
            return data

    ohlcv = exchange.fetch_ohlcv(
        pair,
        timeframe=timeframe,
        limit=2000
    )

    data = [
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

    kline_cache[key] = (
        now,
        data
    )

    return data


@router.get("/latest")
def latest_candle(
        pair: str,
        timeframe: str = "30m"
):
    key = f"{pair}_{timeframe}"

    if key in kline_cache:
        data = kline_cache[key][1]

        return data[-1]

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


@router.get("/strategy-positions/{strategy}")
def get_strategy_positions(strategy: str):
    positions = PositionService.get_open_positions()

    if strategy == "DcaTpLong":

        return [
            {
                **p,
                "side": "LONG"
            }
            for p in positions["long"]
        ]

    elif strategy == "DcaTpShort":

        return [
            {
                **p,
                "side": "SHORT"
            }
            for p in positions["short"]
        ]

    return []


def cache_refresh_loop():
    warmup_cache()

    while True:

        try:

            warmup_cache()

        except Exception as e:

            print(
                f"缓存刷新失败: {e}"
            )

        time.sleep(60)


def warmup_cache():
    print(
        "\n===== 开始预热K线缓存 ====="
    )

    pairs = load_whitelist_pairs()

    timeframes = [
        "30m"
    ]

    for pair in pairs:

        for tf in timeframes:

            try:

                key = f"{pair}_{tf}"

                print(
                    f"预热: {key}"
                )

                ohlcv = exchange.fetch_ohlcv(
                    pair,
                    timeframe=tf,
                    limit=1000
                )

                data = [

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

                kline_cache[key] = (
                    time.time(),
                    data
                )

            except Exception as e:

                print(
                    f"{pair} 预热失败: {e}"
                )

    print(
        "===== K线缓存预热完成 =====\n"
    )


@router.post("/event")
def create_event(
        event: TradeEventCreate,
        db:Session=Depends(get_db)
):


    exists = db.query(
        TradeEvent
    ).filter(
        TradeEvent.strategy==event.strategy,
        TradeEvent.pair==event.pair,
        TradeEvent.event_type==event.event_type,
        TradeEvent.candle_time==event.candle_time
    ).first()


    if exists:
        return exists

    obj = TradeEvent(

        strategy=event.strategy,

        pair=event.pair,

        trade_id=event.trade_id,

        event_type=event.event_type,

        side=event.side,

        price=event.price,

        amount=event.amount,

        time=event.time,

        candle_time=event.candle_time,

        message=event.message
    )


    db.add(obj)

    db.commit()

    db.refresh(obj)

    return obj


@router.get(
    "/events",
    response_model=list[TradeEventOut]
)
def get_events(
        strategy: str,
        pair: str,
        db: Session = Depends(get_db)
):
    pairs = [
        pair,
        pair.replace(":USDT", ""),
        pair.replace("/", "")
    ]

    return (

        db.query(
            TradeEvent
        )

        .filter(
            TradeEvent.strategy == strategy,
            TradeEvent.pair.in_(pairs)
        )

        .order_by(
            TradeEvent.time
        )

        .all()

    )
