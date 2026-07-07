import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DB_FILE = BASE_DIR / "strategy.db"


def get_conn():

    conn = sqlite3.connect(
        str(DB_FILE),
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn