from pathlib import Path

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

FREQTRADE_DIR = (
    BASE_DIR /
    "freqtrade"
)

LONG_URL = "http://127.0.0.1:8011"
SHORT_URL = "http://127.0.0.1:8012"

AUTH_USER = "freqtrader"
AUTH_PASSWORD = "zy147258"

LONG_CONFIG = (
    FREQTRADE_DIR /
    "user_data" /
    "config_long.json"
)

SHORT_CONFIG = (
    FREQTRADE_DIR /
    "user_data" /
    "config_short.json"
)

STRATEGY_LONG = (
    BASE_DIR /
    "config" /
    "strategy_long.json"
)

STRATEGY_SHORT = (
    BASE_DIR /
    "config" /
    "strategy_short.json"
)