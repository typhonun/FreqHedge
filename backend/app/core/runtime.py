LONG_PROCESS = None
SHORT_PROCESS = None

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