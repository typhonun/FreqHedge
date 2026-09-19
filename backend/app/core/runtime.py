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

    # 新增：模式 "amount" / "ratio"
    "global_tp_mode": "amount",
    "global_sl_mode": "amount",

    # 新增：百分比阈值
    "global_tp_ratio": 5.0,
    "global_sl_ratio": 100.0,
}

GLOBAL_EXIT_REASONS = {}

ROUND_INFO = {

    # 本轮开始时累计利润
    "start_profit": None,

    # 本轮开始时多单已平仓
    "start_long_closed": None,

    # 本轮开始时空单已平仓
    "start_short_closed": None,

    # 本轮开始时资金
    "start_balance": None,

    # 当前轮收益
    "round_profit": 0,

    # 当前轮收益率
    "round_ratio": 0,

    # 新增
    "global_tp_count": 0,
    "global_sl_count": 0,

    # 冷却时间
    "last_tp_time": 0,

    "trigger_reason": ""
}