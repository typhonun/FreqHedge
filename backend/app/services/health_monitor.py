"""
Freqtrade 健康监控

策略：
- 每 30s 检查一次 LONG / SHORT 是否存活
- 只有该 side 存在未平仓交易（SQLite 里 is_open=1）时才探活，无持仓不管
- 连续 N 次（默认 3 次）探活失败才重启，避免网络抖动误重启
- 探活成功一次立刻清零失败计数
- 重启时打日志，重启失败不抛出，等下一轮继续尝试
"""

import threading
import time
import sqlite3
import traceback

from app.services.freqtrade_client import FreqtradeClient
from app.services.process_service import ProcessService
from config.settings import (
    LONG_URL,
    SHORT_URL,
    LONG_DB,
    SHORT_DB,
)

# =========================================================
# 配置
# =========================================================

CHECK_INTERVAL = 30        # 检查周期（秒）
FAIL_THRESHOLD = 3         # 连续失败多少次才重启
PROBE_TIMEOUT = 3          # is_freqtrade_alive 内部超时

# =========================================================
# 运行状态
# =========================================================

_health_thread = None
_health_stop = threading.Event()

_health_state = {
    "long": {
        "fail": 0,
        "restarting": False,
        "last_alive": None,       # True / False / None(未知)
        "last_probe_ts": 0,
        "last_restart_ts": 0,
        "restart_count": 0,
    },
    "short": {
        "fail": 0,
        "restarting": False,
        "last_alive": None,
        "last_probe_ts": 0,
        "last_restart_ts": 0,
        "restart_count": 0,
    },
}


# =========================================================
# 内部工具
# =========================================================

def _has_open_trades(db_path) -> bool:
    """
    直接查 Freqtrade sqlite，判断该 side 是否有未平仓交易。
    不用 get_open_positions，避免依赖 snapshot 缓存。
    """
    if not db_path:
        return False

    try:
        conn = sqlite3.connect(db_path, timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE is_open = 1")
        row = cur.fetchone()
        conn.close()

        if not row:
            return False

        return int(row[0]) > 0

    except Exception as e:
        print(f"[health] check open trades failed ({db_path}): {e}")
        return False


def _restart_side(side, url):    # ← 去掉 db_path
    try:
        print(f"[health] {side} 开始重启 ...")

        ProcessService.start_freqtrade()

        if not ProcessService.wait_until_alive(url):
            print(f"[health] {side} 重启失败：API 启动超时")
            return False

        FreqtradeClient.start_bot(url)

        try:
            from app.services.state_service import StateService
            state = StateService.load()
            if side == "long":
                state["long"] = True
            else:
                state["short"] = True
            StateService.save(state["long"], state["short"])
        except Exception as e:
            print(f"[health] StateService.save failed: {e}")

        print(f"[health] {side} 重启成功")
        return True

    except Exception as e:
        print(f"[health] {side} 重启异常: {e}")
        traceback.print_exc()
        return False


def _check_one(side: str, url: str, db_path) -> None:
    state = _health_state[side]

    now = time.time()
    state["last_probe_ts"] = now

    if state["restarting"]:
        return

    try:
        # ---------- 1) 无持仓 → 不探活 ----------
        if not _has_open_trades(db_path):
            state["fail"] = 0
            state["last_alive"] = None
            return

        # ---------- 2) 探活 ----------
        try:
            alive = FreqtradeClient.is_freqtrade_alive(url)
        except Exception as e:
            print(f"[health] {side} 探活异常: {e}")
            alive = False

        state["last_alive"] = alive

        # ---------- 3) 在线 → 清零 ----------
        if alive:
            if state["fail"] > 0:
                print(f"[health] {side} 已恢复在线")
            state["fail"] = 0
            return

        # ---------- 4) 离线 + 有持仓 → 累加 ----------
        state["fail"] += 1

        print(f"[health] {side} offline ({state['fail']}/{FAIL_THRESHOLD})")

        if state["fail"] < FAIL_THRESHOLD:
            return

        # ---------- 5) 达阈值 → 重启 ----------
        state["restarting"] = True
        state["fail"] = 0

        try:
            ok = _restart_side(side, url)   # ← 注意：这行现在跟方案 A 对齐

            if ok:
                state["last_alive"] = True
                state["restart_count"] += 1
            else:
                state["last_alive"] = False

            state["last_restart_ts"] = time.time()

        finally:
            state["restarting"] = False

    except Exception as e:
        print(f"[health] {side} check_one error: {e}")
        traceback.print_exc()


# =========================================================
# 主循环
# =========================================================

def _health_loop():
    print(
        f"[health] monitor started "
        f"(interval={CHECK_INTERVAL}s, threshold={FAIL_THRESHOLD})"
    )

    while not _health_stop.is_set():

        # ---------- LONG ----------
        try:
            _check_one("long", LONG_URL, LONG_DB)
        except Exception as e:
            print(f"[health] long loop error: {e}")
            traceback.print_exc()

        # ---------- SHORT ----------
        try:
            _check_one("short", SHORT_URL, SHORT_DB)
        except Exception as e:
            print(f"[health] short loop error: {e}")
            traceback.print_exc()

        # ---------- 可中断 sleep ----------
        for _ in range(CHECK_INTERVAL):
            if _health_stop.is_set():
                break
            time.sleep(1)

    print("[health] monitor stopped")


# =========================================================
# 对外入口
# =========================================================

def start_health_monitor():
    global _health_thread

    if _health_thread and _health_thread.is_alive():
        print("[health] monitor already running")
        return

    _health_stop.clear()

    _health_thread = threading.Thread(
        target=_health_loop,
        name="freqtrade-health",
        daemon=True,
    )

    _health_thread.start()


def stop_health_monitor():
    _health_stop.set()


def get_health_state():
    """可选：给 /control/health 用的快照"""
    return {
        "long": dict(_health_state["long"]),
        "short": dict(_health_state["short"]),
    }