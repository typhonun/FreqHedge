# backend/app/services/health_monitor.py
import threading
import time
import sqlite3
import traceback
from pathlib import Path
from app.services.freqtrade_client import FreqtradeClient
from app.services.process_service import ProcessService
from app.services.bot_runtime import (
    list_running_bots, get_bot_url, get_bot_db_path, get_enabled_sides,
)

CHECK_INTERVAL = 30
FAIL_THRESHOLD = 3

_health_thread = None
_health_stop = threading.Event()

# key = (bot_id, side)
_health_state = {}


def _state(bot_id, side):
    return _health_state.setdefault((bot_id, side), {
        "fail": 0, "restarting": False, "last_alive": None,
        "last_probe_ts": 0, "last_restart_ts": 0, "restart_count": 0,
    })


def _has_open_trades(db_path) -> bool:
    if not db_path:
        return False
    if not Path(db_path).exists():
        return False
    try:
        conn = sqlite3.connect(db_path, timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE is_open = 1")
        row = cur.fetchone()
        conn.close()
        return bool(row and int(row[0]) > 0)
    except Exception as e:
        print(f"[health] check open trades failed ({db_path}): {e}")
        return False


def _restart_bot_side(bot_id: int, side: str, url: str):
    try:
        print(f"[health] bot={bot_id} {side} 重启...")
        ProcessService.restart_bot_side(bot_id, side)
        if not ProcessService.wait_until_alive(url, timeout=30):
            print(f"[health] bot={bot_id} {side} 重启失败")
            return False
        FreqtradeClient.start_bot(url)

        # ★ 新增：重置 risk round
        try:
            from app.services.risk_service import RiskService
            RiskService.init_round(bot_id)
        except Exception as e:
            print(f"[health] init_round 失败 bot={bot_id}: {e}")

        return True
    except Exception as e:
        print(f"[health] bot={bot_id} {side} 重启异常: {e}")
        traceback.print_exc()
        return False


def _check_one(bot_id: int, side: str):
    state = _state(bot_id, side)
    now = time.time()
    state["last_probe_ts"] = now

    if state["restarting"]:
        return

    url = get_bot_url(bot_id, side)
    db_path = get_bot_db_path(bot_id, side)

    try:
        if not _has_open_trades(db_path):
            state["fail"] = 0
            state["last_alive"] = None
            return

        try:
            alive = FreqtradeClient.is_freqtrade_alive(url)
        except Exception:
            alive = False

        state["last_alive"] = alive

        if alive:
            state["fail"] = 0
            return

        state["fail"] += 1
        print(f"[health] bot={bot_id} {side} offline ({state['fail']}/{FAIL_THRESHOLD})")

        if state["fail"] < FAIL_THRESHOLD:
            return

        state["restarting"] = True
        state["fail"] = 0
        try:
            ok = _restart_bot_side(bot_id, side, url)
            state["last_alive"] = bool(ok)
            state["restart_count"] += 1
            state["last_restart_ts"] = time.time()
        finally:
            state["restarting"] = False
    except Exception as e:
        print(f"[health] check_one error bot={bot_id} side={side}: {e}")
        traceback.print_exc()


def _health_loop():
    print(f"[health] monitor started (interval={CHECK_INTERVAL}s)")
    while not _health_stop.is_set():
        try:
            for bot in list_running_bots():
                for side in get_enabled_sides(bot):
                    try:
                        _check_one(bot["id"], side)
                    except Exception as e:
                        print(f"[health] loop error bot={bot['id']} side={side}: {e}")
        except Exception as e:
            print(f"[health] main loop error: {e}")
            traceback.print_exc()

        for _ in range(CHECK_INTERVAL):
            if _health_stop.is_set():
                break
            time.sleep(1)
    print("[health] monitor stopped")


def start_health_monitor():
    global _health_thread
    if _health_thread and _health_thread.is_alive():
        return
    _health_stop.clear()
    _health_thread = threading.Thread(target=_health_loop, name="freqtrade-health", daemon=True)
    _health_thread.start()


def stop_health_monitor():
    _health_stop.set()


def get_health_state():
    return {f"{bid}:{side}": dict(s) for (bid, side), s in _health_state.items()}