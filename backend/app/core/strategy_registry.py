# backend/app/core/strategy_registry.py
"""
策略注册表：所有机器人类型的元信息唯一来源。
加新机器人时，只需要在 STRATEGIES 里加一项。
"""

from app.core.defaults import GRID_DEFAULTS

STRATEGIES = {
    "dca": {
        "label": "DCA 机器人",
        # 该类型提交到后端时用的字段名（payload 里 payload["longConfig"]）
        "config_key": "longConfig",
        "extra_config_key": "shortConfig",
        # 该类型写进 DB 的列
        "db_columns": ["longConfig", "shortConfig"],
        # 默认值（有就填，没有就 None）
        "default_config": None,
        "default_extra": None,
        # (strategy_type, side) → freqtrade 策略类名
        "class_map": {
            "long": "DcaTpLong",
            "short": "DcaTpShort",
        },
        # custom_params 注入方式
        # "dca" 类型：custom_params[side] = config
        # "single" 类型：custom_params["config"] = config
        "inject_mode": "side",
    },
    "grid": {
        "label": "网格机器人",
        "config_key": "gridConfig",
        "extra_config_key": None,
        "db_columns": ["gridConfig"],
        "default_config": {"grid": GRID_DEFAULTS},
        "default_extra": None,
        "class_map": {
            "long": "GridBotLong",
            "short": "GridBotShort",
        },
        "inject_mode": "single",
        "timeframe": "5m",
    },
    # ★ 未来加第三种：
    # "trailing": {
    #     "label": "跟踪止盈机器人",
    #     "config_key": "trailingConfig",
    #     "extra_config_key": None,
    #     "db_columns": ["trailingConfig"],
    #     "default_config": {"trailing": TRAILING_DEFAULTS},
    #     "default_extra": None,
    #     "class_map": {"long": "TrailingBotLong", "short": "TrailingBotShort"},
    #     "inject_mode": "single",
    # },
}


def get_strategy(strategy_type: str):
    return STRATEGIES.get(strategy_type or "dca") or STRATEGIES["dca"]


def strategy_class(strategy_type: str, side: str):
    return get_strategy(strategy_type)["class_map"].get(side)