import json
import time
from app.db import get_conn       # ← 复用 db 的连接


class ConfigManager:
    _cache = {}
    _last_load = {}
    CACHE_SECONDS = 3

    @classmethod
    def get(cls, side):

        now = time.time()

        if (
            side in cls._cache
            and now - cls._last_load.get(side, 0) < cls.CACHE_SECONDS
        ):
            return cls._cache[side]

        conn = get_conn()        # ← 用 db.py 的连接
        try:
            row = conn.execute(
                """
                SELECT config_json
                FROM strategy_config
                WHERE side=?
                """,
                (side,)
            ).fetchone()
        finally:
            conn.close()

        if not row:
            return {}

        config = json.loads(row["config_json"])
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