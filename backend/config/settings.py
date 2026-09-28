# backend/config/settings.py

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

FREQTRADE_DIR = BASE_DIR / "freqtrade"

LONG_URL = "http://127.0.0.1:8011"
SHORT_URL = "http://127.0.0.1:8012"

AUTH_USER = "freqtrader"
AUTH_PASSWORD = "zy147258"

# ---------- 后端数据库（关键，新增）----------
# 你截图里 dcatp.db 在 backend/app/data/dcatp.db
DATA_DIR = BASE_DIR / "backend" / "app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DCATP_DB = DATA_DIR / "dcatp.db"

# 原有
LONG_CONFIG = FREQTRADE_DIR / "user_data" / "config_long.json"
SHORT_CONFIG = FREQTRADE_DIR / "user_data" / "config_short.json"

STRATEGY_LONG = BASE_DIR / "config" / "strategy_long.json"
STRATEGY_SHORT = BASE_DIR / "config" / "strategy_short.json"

LONG_DB = FREQTRADE_DIR / "tradesv3_long.sqlite"
SHORT_DB = FREQTRADE_DIR / "tradesv3_short.sqlite"