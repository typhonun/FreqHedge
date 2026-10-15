# E:\code\python_code\DcaTp\backend\app\core\config_manager.py
import json
import time
from app.db import get_conn       # ← 复用 db 的连接


class ConfigManager:
    _cache = {}
    _last_load = {}
    _bot_kv_cache = {}
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
        cls._bot_kv_cache.clear()

    # ============================================================
    # ★ 新增：bot 级 KV 持久化（用于网格状态）
    # ============================================================
    @classmethod
    def _ensure_kv_table(cls):
        conn = get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_kv (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def get_bot_kv(cls, key, default=None):
        # 内存缓存
        if key in cls._bot_kv_cache:
            return cls._bot_kv_cache[key]

        cls._ensure_kv_table()
        conn = get_conn()
        try:
            row = conn.execute(
                "SELECT value FROM bot_kv WHERE key=?", (key,)
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return default
        try:
            val = json.loads(row["value"])
        except Exception:
            val = row["value"]
        cls._bot_kv_cache[key] = val
        return val

    @classmethod
    def set_bot_kv(cls, key, value):
        cls._ensure_kv_table()
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO bot_kv(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value))
            )
            conn.commit()
        finally:
            conn.close()
        cls._bot_kv_cache[key] = value