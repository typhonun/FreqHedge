# backend/config/settings.py

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

FREQTRADE_DIR = BASE_DIR / "freqtrade"

AUTH_USER = "freqtrader"
AUTH_PASSWORD = "zy147258"

DATA_DIR = BASE_DIR / "backend" / "app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DCATP_DB = DATA_DIR / "dcatp.db"


# ===== 多实例路径 helper =====
def bot_config_path(bot_id: int, side: str) -> Path:
    return FREQTRADE_DIR / "user_data" / "bots" / str(bot_id) / f"config_bot{bot_id}_{side}.json"


def bot_log_path(bot_id: int, side: str) -> Path:
    return FREQTRADE_DIR / "user_data" / "bots" / str(bot_id) / "logs" / f"{side}.log"


def bot_db_path(bot_id: int, side: str) -> Path:
    return FREQTRADE_DIR / "user_data" / "bots" / str(bot_id) / f"tradesv3_bot{bot_id}_{side}.sqlite"


# ===== config 模板（唯一的模板）=====
CONFIG_TEMPLATE = FREQTRADE_DIR / "user_data" / "config_template.json"
