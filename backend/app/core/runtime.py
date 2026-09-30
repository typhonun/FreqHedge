LONG_PROCESS = None
SHORT_PROCESS = None

PROCESSES = {}

RUNNING = {
    "long": False,
    "short": False
}

STOP_ENTRY = {
    "long": False,
    "short": False
}

GLOBAL_RISK = {

    "global_tp_enabled": False,
    "global_sl_enabled": False,

    "global_tp_amount": 100,
    "global_sl_amount": 50,

    "global_tp_mode": "amount",
    "global_sl_mode": "amount",

    "global_tp_ratio": 5.0,
    "global_sl_ratio": 100.0,

    # ===== 追踪止损 =====
    "global_trail_enabled": False,

    # "amount" / "ratio"
    "global_trail_mode": "ratio",

    # 触发盈亏（可正可负）
    # 正数 = 盈利区追踪；负数 = 亏损区追踪
    "global_trail_activate_amount": 10.0,
    "global_trail_activate_ratio": 3.0,

    # 追踪回撤幅度（永远正数）
    "global_trail_drawdown_amount": 5.0,
    "global_trail_drawdown_ratio": 1.0,

    # ===== 多空失衡控制（只拦新开仓） =====
    # 多头侧：多单 - 空单 >= imbalance_long_count 时，暂停开多
    "imbalance_long_enable": False,
    "imbalance_long_count": 2,

    # 空头侧：空单 - 多单 >= imbalance_short_count 时，暂停开空
    "imbalance_short_enable": False,
    "imbalance_short_count": 2,
}

GLOBAL_EXIT_REASONS = {}

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

    # ===== 追踪止损状态 =====
    "peak_profit": 0.0,      # 本轮最高收益（金额）
    "peak_ratio": 0.0,       # 本轮最高收益率
    "trough_profit": 0.0,    # 本轮最低收益（金额）
    "trough_ratio": 0.0,     # 本轮最低收益率
    "trail_active": False,   # 追踪止损是否已激活

    # ===== 追踪触发次数 =====
    "global_trail_count": 0,
}

ROUND_INFO_BY_BOT = {}


# 按 bot 隔离的退出原因： {bot_id: {trade_id: reason}}
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