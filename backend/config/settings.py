# backend/config/settings.py

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

FREQTRADE_DIR = BASE_DIR / "freqtrade"

# 每个 bot 占 2 个连续端口：long = base, short = base + 1
PORT_START = 8100
PORT_END   = 8900

AUTH_USER = "freqtrader"
AUTH_PASSWORD = "zy147258"

DATA_DIR = BASE_DIR / "backend" / "data"
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

# ===== Auth =====
SECRET_KEY = "change-me-to-a-random-64-char-string-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
RESET_TOKEN_EXPIRE_MINUTES = 30

# 前端地址（生成邮件里的链接用）
FRONTEND_URL = "http://localhost:5173"

# ===== SMTP =====
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = "your@qq.com"
SMTP_PASSWORD = "smtp-auth-code"
SMTP_FROM = "your@qq.com"
SMTP_FROM_NAME = "DcaTp"
# False: 走真实邮件（上线前必须改 False）
DEV_MODE = True