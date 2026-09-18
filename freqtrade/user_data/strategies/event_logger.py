import requests
from datetime import datetime, timezone

EVENT_API = "http://127.0.0.1:9000/chart/event"


def record_event(
        strategy,
        pair,
        trade_id,
        event_type,
        side,
        price,
        amount,
        message="",
        current_time=None,
        candle_time=None  # 新增：策略层传入的 K 线时间戳
):
    try:
        if current_time:
            event_dt = current_time
            # 关键：如果传入的是 naive datetime，按 UTC 处理
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
        else:
            event_dt = datetime.now(timezone.utc)

        utc_dt = event_dt.astimezone(timezone.utc)

        # 优先使用策略层传入的 candle_time
        if candle_time is not None:
            if isinstance(candle_time, (int, float)):
                # 秒级时间戳
                candle_dt = datetime.fromtimestamp(candle_time, tz=timezone.utc)
            elif isinstance(candle_time, datetime):
                candle_dt = candle_time
                if candle_dt.tzinfo is None:
                    candle_dt = candle_dt.replace(tzinfo=timezone.utc)
                candle_dt = candle_dt.astimezone(timezone.utc)
            else:
                # 兜底：按 30 分钟对齐
                candle_dt = utc_dt.replace(
                    minute=(utc_dt.minute // 30) * 30,
                    second=0,
                    microsecond=0
                )
        else:
            # 没传 candle_time 时，退化为按 30 分钟对齐
            candle_dt = utc_dt.replace(
                minute=(utc_dt.minute // 30) * 30,
                second=0,
                microsecond=0
            )

        # 调试日志
        print(
            f"[event_logger] {event_type} {pair} "
            f"time={utc_dt.isoformat()} candle={candle_dt.isoformat()}"
        )

        requests.post(
            EVENT_API,
            json={
                "strategy": strategy,
                "pair": pair,
                "trade_id": trade_id,
                "event_type": event_type,
                "side": side,
                "price": price,
                "amount": amount,
                "time": utc_dt.isoformat(),
                "candle_time": candle_dt.isoformat(),
                "message": message
            },
            timeout=1
        )
    except Exception as e:
        print("record_event error", e)