import json
import sqlite3
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
DB_FILE = BASE_DIR / "backend" / "strategy.db"
CONFIG_DIR = BASE_DIR / "config"


class ConfigManager:

    _cache = {}

    _last_load = {}

    CACHE_SECONDS = 3

    @classmethod
    def get(cls, side):

        print(
            "读取RSI:",
            config["entry"]["rsi"]["value"]
        )

        now = time.time()

        if (
                side in cls._cache
                and now - cls._last_load.get(side, 0)
                < cls.CACHE_SECONDS
        ):
            return cls._cache[side]

        conn = sqlite3.connect(
            str(DB_FILE)
        )

        row = conn.execute(
            """
            SELECT config_json
            FROM strategy_config
            WHERE side = ?
            """,
            (side,)
        ).fetchone()

        conn.close()

        if row is None:
            file_path = CONFIG_DIR / f"strategy_{side}.json"
            if not file_path.exists():
                return {}

            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = json.loads(row[0])

        cls._cache[side] = config

        cls._last_load[side] = now

        return config

    @classmethod
    def force_reload(cls, side=None):

        if side:
            cls._cache.pop(side, None)
            cls._last_load.pop(side, None)
        else:
            cls._cache.clear()
            cls._last_load.clear()


    