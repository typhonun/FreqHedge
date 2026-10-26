# freqtrade/user_data/strategies/event_logger.py
import requests
from datetime import datetime, timezone
import threading
import queue
import time

EVENT_API = "http://127.0.0.1:9000/chart/event"

# =========================================================
# ★ 异步队列机制（生产者-消费者模型）
# =========================================================
_event_queue = queue.Queue(maxsize=10000)


def _event_worker():
    """后台工作线程：专门负责发 HTTP 请求"""
    while True:
        try:
            payload = _event_queue.get()
            if payload is None:
                break

            # 发送请求，加上重试机制
            for _ in range(3):
                try:
                    requests.post(EVENT_API, json=payload, timeout=3)
                    break  # 成功则跳出重试
                except Exception:
                    time.sleep(0.5)  # 失败等 0.5 秒重试

            _event_queue.task_done()
        except Exception:
            pass


# 启动后台守护线程（只启动一次）
_worker_thread = threading.Thread(target=_event_worker, daemon=True)
_worker_thread.start()


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
        candle_time=None,
        bot_id=None,
):
    try:
        if current_time:
            event_dt = current_time
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
        else:
            event_dt = datetime.now(timezone.utc)

        utc_dt = event_dt.astimezone(timezone.utc)

        if candle_time is not None:
            if isinstance(candle_time, (int, float)):
                candle_dt = datetime.fromtimestamp(candle_time, tz=timezone.utc)
            elif isinstance(candle_time, datetime):
                candle_dt = candle_time
                if candle_dt.tzinfo is None:
                    candle_dt = candle_dt.replace(tzinfo=timezone.utc)
                candle_dt = candle_dt.astimezone(timezone.utc)
            else:
                candle_dt = utc_dt.replace(
                    minute=(utc_dt.minute // 30) * 30,
                    second=0,
                    microsecond=0
                )
        else:
            candle_dt = utc_dt.replace(
                minute=(utc_dt.minute // 30) * 30,
                second=0,
                microsecond=0
            )

        # 构造 payload
        payload = {
            "bot_id": bot_id,
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
        }

        # ★ 核心修改：非阻塞入队，瞬间返回
        try:
            _event_queue.put_nowait(payload)
        except queue.Full:
            # 如果队列满了（极端高频），直接丢弃，防止拖死策略
            pass

    except Exception as e:
        # 这里的 print 只是为了兜底，正常不会触发
        print("record_event format error", e)