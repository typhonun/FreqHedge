from fastapi import APIRouter
import ccxt
import json
import time
from app.services.position_service import PositionService
from pathlib import Path
from fastapi import Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models.trade_event import TradeEvent
from app.services.bot_manager import BotManager
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
        "defaultType": "future"
    }
})


def load_whitelist_pairs():
    """从 bots 表读所有 bot 的 pair 并集"""
    pairs = set()
    try:
        bots = BotManager.list_all()
        for b in bots:
            for p in (b.get("pair") or []):
                pairs.add(p)
    except Exception as e:
        print(f"[chart] 读取 bot pair 失败: {e}")
    return list(pairs)


@router.get("/strategies")
def get_strategies():
    return [
        "DcaTpLong",
        "DcaTpShort"
    ]


@router.get("/pairs/{bot_id}")
def get_pairs(bot_id: int):
    bot = BotManager.get(bot_id)
    if not bot:
        return []
    return bot.get("pair") or []


@router.get("/candles")
def get_candles(pair: str, timeframe: str = "5m"):
    key = f"{pair}_{timeframe}"
    now = time.time()

    if key in kline_cache:
        cache_time, data = kline_cache[key]
        if now - cache_time < 300:
            return data

    ohlcv = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=2000)
    data = [
        {"time": c[0], "open": c[1], "high": c[2], "low": c[3],
         "close": c[4], "volume": c[5]}
        for c in ohlcv
    ]
    kline_cache[key] = (now, data)
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


@router.get("/bot-positions/{bot_id}")
def get_bot_positions(bot_id: int):
    positions = PositionService.get_open_positions(bot_id=bot_id)
    result = []
    for p in positions["long"]:
        result.append({**p, "side": "LONG"})
    for p in positions["short"]:
        result.append({**p, "side": "SHORT"})
    return result


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
def create_event(event: TradeEventCreate, db: Session = Depends(get_db)):
    # 用 candle_time 去重：同一策略、同一交易对、同一事件类型、同一根 K 线，只记录一次
    if event.candle_time:
        exists = db.query(TradeEvent).filter(
            TradeEvent.strategy == event.strategy,
            TradeEvent.pair == event.pair,
            TradeEvent.event_type == event.event_type,
            TradeEvent.candle_time == event.candle_time
        ).first()
        if exists:
            return exists

    # 如果没有 candle_time，退化为用 time 做 5 分钟窗口去重
    else:
        time_threshold = datetime.now() - timedelta(minutes=5)
        exists = db.query(TradeEvent).filter(
            TradeEvent.strategy == event.strategy,
            TradeEvent.pair == event.pair,
            TradeEvent.event_type == event.event_type,
            TradeEvent.time >= time_threshold
        ).first()

        if exists:
            return exists

    # 插入逻辑（无论是否有 candle_time，都要走到这里）
    obj = TradeEvent(
        bot_id=event.bot_id,
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


@router.get("/events", response_model=list[TradeEventOut])
def get_events(
    bot_id: int | None = None,
    strategy: str | None = None,
    pair: str = None,
    db: Session = Depends(get_db),
):
    pairs = [pair, pair.replace(":USDT", ""), pair.replace("/", "")]
    q = db.query(TradeEvent).filter(TradeEvent.pair.in_(pairs))
    if bot_id is not None:
        q = q.filter(TradeEvent.bot_id == bot_id)
    if strategy:
        q = q.filter(TradeEvent.strategy == strategy)
    return q.order_by(TradeEvent.time).all()


# ============================================================
# ★ 网格智能区间建议
# ============================================================
@router.get("/grid/suggest")
def suggest_grid_range(
    pair: str,
    days: int = 30,
    timeframe: str = "1d"
):
    """
    根据近 N 天的最高/最低价，给出网格上下限建议。
    - 安全垫：向外扩展 3%
    - 兜底：如果当前价不在区间内，强制把当前价包进去（再扩 5%）
    - 默认网格数量：20
    """
    try:
        # 1. 拉取 K 线
        limit = max(int(days), 10)
        ohlcv = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
        if not ohlcv or len(ohlcv) < 2:
            return {"error": "no data"}

        highs  = [c[2] for c in ohlcv]
        lows   = [c[3] for c in ohlcv]
        closes = [c[4] for c in ohlcv]

        high = max(highs)
        low  = min(lows)
        current = closes[-1]

        # 2. 安全垫 ±3%
        lower_price = low  * 0.97
        upper_price = high * 1.03

        # 3. 兜底：确保当前价在区间内
        if current >= upper_price:
            upper_price = current * 1.05
        if current <= lower_price:
            lower_price = current * 0.95

        # 4. 价格保留 4 位小数（兼容小币种）
        return {
            "lower_price": round(lower_price, 4),
            "upper_price": round(upper_price, 4),
            "raw_high": round(high, 4),
            "raw_low": round(low, 4),
            "current_price": round(current, 4),
            "suggest_grid_count": 20,
            "days": days,
        }

    except Exception as e:
        print(f"[grid/suggest] error: {e}")
        return {"error": str(e)}