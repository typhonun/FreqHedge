# app/db.py
import sqlite3
from pathlib import Path

# app/db.py
from pathlib import Path

# app/db.py -> app/ -> backend/
BASE_DIR = Path(__file__).resolve().parents[1]     # backend/
DATA_DIR = BASE_DIR / "data"                       # backend/data/
DATA_DIR.mkdir(exist_ok=True)

DB_FILE = DATA_DIR / "strategy.db"


def get_conn():
    conn = sqlite3.connect(
        str(DB_FILE),
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS strategy_config(
            side TEXT PRIMARY KEY,
            config_json TEXT NOT NULL,
            update_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
    finally:
        conn.close()
    print(f"[db] initialized: {DB_FILE}")