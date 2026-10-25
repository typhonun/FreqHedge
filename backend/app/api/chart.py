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

# 全局 K 线缓存
kline_cache = {}
# 网格建议缓存
suggest_cache = {}

exchange = ccxt.binance({
    "enableRateLimit": True,
    "rateLimit": 1200,  # 略微调大速率限制，防止瞬间并发触发限流
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

    # 缓存 300 秒有效
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
def latest_candle(pair: str, timeframe: str = "30m"):
    key = f"{pair}_{timeframe}"

    # ★ 核心优化 1：只允许读缓存，绝不允许穿透请求交易所
    if key in kline_cache:
        data = kline_cache[key][1]
        if data:
            return data[-1]

    # 如果缓存未命中，直接返回 None，由前端逻辑处理
    return None


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
            print(f"缓存刷新失败: {e}")

        # ★ 核心优化 2：从 60 秒改为 300 秒（5分钟），大幅降低请求频率
        time.sleep(300)


def warmup_cache():
    print("\n===== 开始预热K线缓存 =====")
    pairs = load_whitelist_pairs()

    # 仅为 30m 周期做预热（如果要支持前端随意切周期，建议前端切换时自行拉取）
    timeframes = ["30m"]

    for pair in pairs:
        for tf in timeframes:
            try:
                key = f"{pair}_{tf}"
                print(f"预热: {key}")
                ohlcv = exchange.fetch_ohlcv(pair, timeframe=tf, limit=1000)
                data = [
                    {"time": c[0], "open": c[1], "high": c[2], "low": c[3],
                     "close": c[4], "volume": c[5]}
                    for c in ohlcv
                ]
                kline_cache[key] = (time.time(), data)
            except Exception as e:
                print(f"{pair} 预热失败: {e}")

    print("===== K线缓存预热完成 =====\n")


@router.post("/event")
def create_event(event: TradeEventCreate, db: Session = Depends(get_db)):
    # 用 candle_time 去重
    if event.candle_time:
        exists = db.query(TradeEvent).filter(
            TradeEvent.strategy == event.strategy,
            TradeEvent.pair == event.pair,
            TradeEvent.event_type == event.event_type,
            TradeEvent.candle_time == event.candle_time
        ).first()
        if exists:
            return exists

    # 退化为用 time 做 5 分钟窗口去重
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


@router.get("/grid/suggest")
def suggest_grid_range(
        pair: str,
        days: int = 30,
        timeframe: str = "1d"
):
    # ★ 核心优化 3：为智能建议添加 10 分钟缓存，防止用户狂点按钮
    cache_key = f"{pair}_{days}_{timeframe}"
    now = time.time()

    if cache_key in suggest_cache:
        cache_time, cached_data = suggest_cache[cache_key]
        if now - cache_time < 600:
            return cached_data

    try:
        limit = max(int(days), 10)
        ohlcv = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
        if not ohlcv or len(ohlcv) < 2:
            return {"error": "no data"}

        highs = [c[2] for c in ohlcv]
        lows = [c[3] for c in ohlcv]
        closes = [c[4] for c in ohlcv]

        high = max(highs)
        low = min(lows)
        current = closes[-1]

        lower_price = low * 0.97
        upper_price = high * 1.03

        if current >= upper_price:
            upper_price = current * 1.05
        if current <= lower_price:
            lower_price = current * 0.95

        result = {
            "lower_price": round(lower_price, 4),
            "upper_price": round(upper_price, 4),
            "raw_high": round(high, 4),
            "raw_low": round(low, 4),
            "current_price": round(current, 4),
            "suggest_grid_count": 20,
            "days": days,
        }

        # 写入缓存
        suggest_cache[cache_key] = (now, result)
        return result

    except Exception as e:
        print(f"[grid/suggest] error: {e}")
        return {"error": str(e)}