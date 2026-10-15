# ⚠️ 修改时请同步 frontend/src/config/botDefaults.js
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


def bot_default(name):
    return BOT_DEFAULTS[name]


def risk_default(name):
    return RISK_DEFAULTS[name]
