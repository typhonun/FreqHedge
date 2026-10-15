# ⚠️ 修改时请同步 frontend/src/config/botDefaults.js 与 frontend/src/config/gridDefaults.js
BOT_DEFAULTS = {
    "capital": 1000,
    "stakeAmount": 50,
    "leverage": 5,
    "maxOpenTrades": 3,
    "dryRun": True,
    "enableLong": True,
    "enableShort": False,
    "tradingMode": "futures",
    "marginMode": "cross",
    "strategyType": "dca",         # ★ 新增：策略类型
}

RISK_DEFAULTS = {
    "tp_enabled": False,
    "tp_mode": "amount",
    "tp_amount": 0,
    "tp_ratio": 0,
    "sl_enabled": False,
    "sl_mode": "amount",
    "sl_amount": 0,
    "sl_ratio": 0,
    "trail_enabled": False,
    "trail_mode": "ratio",
    "trail_activate_amount": 10,
    "trail_activate_ratio": 1,
    "trail_drawdown_amount": 5,
    "trail_drawdown_ratio": 0.5,
    "auto_stop_on_tp": True,
    "auto_stop_on_sl": True,
    "auto_stop_on_trail": True,
}

# ★ 新增：网格机器人默认值（与前端 gridDefaults.js 保持一致）
GRID_DEFAULTS = {
    "lower_price": 0,
    "upper_price": 0,
    "grid_count": 20,
    "spacing_algo": "arithmetic",
    "amount_per_grid": 50,
    "tp_per_grid_pct": 0.5,
    "stop_below_lower": True,
    "stop_above_upper": False,
    "start_mode": "wait",
    "max_open_grids": 1,
}


def bot_default(name):
    return BOT_DEFAULTS[name]


def risk_default(name):
    return RISK_DEFAULTS[name]