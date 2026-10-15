# E:\code\python_code\DcaTp\freqtrade\user_data\core\config_manager.py
import json
import time
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# ★ 计算 dcatp.db 的绝对路径（freqtrade 子进程也能用）
# 文件位置：freqtrade/user_data/core/config_manager.py
# parents[0]=core, parents[1]=user_data, parents[2]=freqtrade, parents[3]=DcaTp
BASE_DIR = Path(__file__).resolve().parents[3]
DB_FILE = BASE_DIR / "backend" / "data" / "strategy.db"


def _get_conn():
    """
    独立连接，不依赖 backend 的 app.db。
    先尝试复用 backend.app.db.get_conn（同进程后端场景），
    失败则自己 sqlite3.connect。
    """
    # 1) 后端进程里：优先复用 backend 的连接（row_factory 已设好）
    try:
        from app.db import get_conn as _backend_get_conn
        return _backend_get_conn()
    except Exception:
        pass

    # 2) freqtrade 子进程：自己连
    conn = sqlite3.connect(str(DB_FILE), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


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

        try:
            conn = _get_conn()
            try:
                row = conn.execute(
                    "SELECT config_json FROM strategy_config WHERE side=?",
                    (side,)
                ).fetchone()
            finally:
                conn.close()

            if row:
                raw = row["config_json"] if hasattr(row, "keys") else row[0]
                config = json.loads(raw)
                cls._cache[side] = config
                cls._last_load[side] = now
                return config
        except Exception as e:
            logger.error(f"load strategy config error: {e}")

        return {}

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
    # bot 级 KV 持久化（用于网格状态）
    # ============================================================
    @classmethod
    def _ensure_kv_table(cls):
        conn = _get_conn()
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
        if key in cls._bot_kv_cache:
            return cls._bot_kv_cache[key]

        cls._ensure_kv_table()
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT value FROM bot_kv WHERE key=?", (key,)
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return default
        raw = row["value"] if hasattr(row, "keys") else row[0]
        try:
            val = json.loads(raw)
        except Exception:
            val = raw
        cls._bot_kv_cache[key] = val
        return val

    @classmethod
    def set_bot_kv(cls, key, value):
        cls._ensure_kv_table()
        conn = _get_conn()
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