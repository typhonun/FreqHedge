# app/core/runtime.py

# ❌ 删除
# LONG_PROCESS = None
# SHORT_PROCESS = None
# PROCESSES = {}
# RUNNING = {"long": False, "short": False}
# STOP_ENTRY = {"long": False, "short": False}

# ===== 保留：全局风控配置（不是单实例专属）=====
GLOBAL_RISK = {
    "global_tp_enabled": False,
    "global_sl_enabled": False,
    "global_tp_amount": 100,
    "global_sl_amount": 50,
    "global_tp_mode": "amount",
    "global_sl_mode": "amount",
    "global_tp_ratio": 5.0,
    "global_sl_ratio": 100.0,
    "global_trail_enabled": False,
    "global_trail_mode": "ratio",
    "global_trail_activate_amount": 10.0,
    "global_trail_activate_ratio": 3.0,
    "global_trail_drawdown_amount": 5.0,
    "global_trail_drawdown_ratio": 1.0,
    "imbalance_long_enable": False,
    "imbalance_long_count": 2,
    "imbalance_short_enable": False,
    "imbalance_short_count": 2,
}

GLOBAL_EXIT_REASONS = {}

# ===== 保留：全局 ROUND_INFO（Dashboard 展示用）=====
ROUND_INFO = {
    "start_profit": None,
    "start_long_closed": None,
    "start_short_closed": None,
    "start_balance": None,
    "round_profit": 0,
    "round_ratio": 0,
    "global_tp_count": 0,
    "global_sl_count": 0,
    "last_tp_time": 0,
    "trigger_reason": "",
    "peak_profit": 0.0,
    "peak_ratio": 0.0,
    "trough_profit": 0.0,
    "trough_ratio": 0.0,
    "trail_active": False,
    "global_trail_count": 0,
}

# ===== 保留：per-bot 隔离的 ROUND_INFO / exit reasons =====
ROUND_INFO_BY_BOT = {}

EXIT_REASONS_BY_BOT: dict[int, dict[int, str]] = {}


def set_exit_reason(bot_id: int, trade_id: int, reason: str):
    if bot_id is None or trade_id is None:
        return
    EXIT_REASONS_BY_BOT.setdefault(bot_id, {})[trade_id] = reason


def get_exit_reason(bot_id: int, trade_id: int) -> str | None:
    if bot_id is None or trade_id is None:
        return None
    return EXIT_REASONS_BY_BOT.get(bot_id, {}).get(trade_id)


def clear_exit_reasons(bot_id: int):
    EXIT_REASONS_BY_BOT.pop(bot_id, None)