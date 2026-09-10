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
    "global_sl_amount": -50
}

ROUND_INFO = {

    # 本轮开始时累计利润
    "start_profit": None,

    # 本轮开始时资金
    "start_balance": None,

    # 当前轮收益
    "round_profit": 0,

    # 当前轮收益率
    "round_ratio": 0,

    "trigger_reason": ""
}