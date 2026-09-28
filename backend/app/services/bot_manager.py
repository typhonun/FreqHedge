# backend/app/services/bot_manager.py
import sqlite3
import socket
import json
from pathlib import Path

from config.settings import DCATP_DB
from app.services.freqtrade_client import FreqtradeClient

DB_PATH = Path(DCATP_DB)


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table():
    with _conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pair TEXT NOT NULL,
            capital REAL NOT NULL,
            stakeAmount REAL DEFAULT 30,
            leverage INTEGER DEFAULT 10,
            dryRun INTEGER DEFAULT 1,
            enableLong INTEGER DEFAULT 1,
            enableShort INTEGER DEFAULT 0,
            status TEXT DEFAULT 'stopped',
            port INTEGER,
            longConfig TEXT,
            shortConfig TEXT,
            createdAt TEXT,
            updatedAt TEXT
        );
        """)
        c.commit()


def _migrate():
    """为已存在的旧表补充新列（幂等）"""
    with _conn() as c:
        cols = {row["name"] for row in c.execute("PRAGMA table_info(bots)").fetchall()}

        migrations = [
            ("stakeAmount", "ALTER TABLE bots ADD COLUMN stakeAmount REAL DEFAULT 30"),
            ("leverage",    "ALTER TABLE bots ADD COLUMN leverage INTEGER DEFAULT 10"),
            ("dryRun",      "ALTER TABLE bots ADD COLUMN dryRun INTEGER DEFAULT 1"),
        ]

        for col, ddl in migrations:
            if col not in cols:
                print(f"[migrate] adding column: {col}")
                c.execute(ddl)

        c.commit()


_ensure_table()
_migrate()


def _find_free_port(start=8011, end=9000):
    port = start
    while port < end:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    raise RuntimeError("no free port")


def _parse_json_field(v):
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return None
    return None


class BotManager:

    @staticmethod
    def _normalize(row: dict) -> dict:
        bot = dict(row)
        bot["enableLong"] = bool(bot.get("enableLong"))
        bot["enableShort"] = bool(bot.get("enableShort"))
        bot["dryRun"] = bool(bot.get("dryRun", 1))
        bot["pair"] = _parse_json_field(bot.get("pair")) or []
        bot["longConfig"] = _parse_json_field(bot.get("longConfig"))
        bot["shortConfig"] = _parse_json_field(bot.get("shortConfig"))
        return bot

    @staticmethod
    def list_all():
        with _conn() as c:
            rows = c.execute("SELECT * FROM bots ORDER BY id").fetchall()
        return [BotManager._normalize(r) for r in rows]

    @staticmethod
    def get(bot_id: int):
        with _conn() as c:
            row = c.execute("SELECT * FROM bots WHERE id=?", (bot_id,)).fetchone()
        if not row:
            return None
        return BotManager._normalize(row)

    @staticmethod
    def create(payload: dict):
        base = payload["base"]
        port = _find_free_port()

        with _conn() as c:
            cur = c.execute(
                """
                INSERT INTO bots (name, pair, capital, stakeAmount, leverage, dryRun,
                                  enableLong, enableShort,
                                  status, port, longConfig, shortConfig, createdAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'stopped', ?, ?, ?, datetime('now'))
                """,
                (
                    base["name"],
                    json.dumps(base["pair"]),  # list → JSON 字符串
                    base["capital"],
                    base.get("stakeAmount", 30),
                    base.get("leverage", 10),
                    int(base.get("dryRun", True)),
                    int(base["enableLong"]),
                    int(base["enableShort"]),
                    port,
                    json.dumps(payload.get("longConfig") or {}),
                    json.dumps(payload.get("shortConfig") or {}),
                ),
            )
            bot_id = cur.lastrowid
            c.commit()

        return BotManager.get(bot_id)

    @staticmethod
    def update(bot_id: int, payload: dict):
        base = payload["base"]
        with _conn() as c:
            c.execute(
                """
                UPDATE bots SET name=?, pair=?, capital=?,
                                stakeAmount=?, leverage=?, dryRun=?,
                                enableLong=?, enableShort=?,
                                longConfig=?, shortConfig=?,
                                updatedAt=datetime('now')
                WHERE id=?
                """,
                (
                    base["name"],
                    json.dumps(base["pair"]),
                    base["capital"],
                    base.get("stakeAmount", 30),
                    base.get("leverage", 10),
                    int(base.get("dryRun", True)),
                    int(base["enableLong"]),
                    int(base["enableShort"]),
                    json.dumps(payload.get("longConfig") or {}),
                    json.dumps(payload.get("shortConfig") or {}),
                    bot_id,
                ),
            )
            c.commit()
        return BotManager.get(bot_id)

    @staticmethod
    def delete(bot_id: int):
        with _conn() as c:
            c.execute("DELETE FROM bots WHERE id=?", (bot_id,))
            c.commit()

    @staticmethod
    def start(bot_id: int):
        from app.services.process_service import ProcessService
        bot = BotManager.get(bot_id)
        if not bot:
            return {"success": False, "error": "bot not found"}

        result = ProcessService.start_bot(bot)
        if result.get("success"):
            with _conn() as c:
                c.execute("UPDATE bots SET status='running' WHERE id=?", (bot_id,))
                c.commit()
        return result

    @staticmethod
    def stop(bot_id: int):
        from app.services.process_service import ProcessService
        bot = BotManager.get(bot_id)
        if not bot:
            return {"success": False, "error": "bot not found"}

        result = ProcessService.stop_bot(bot)
        with _conn() as c:
            c.execute("UPDATE bots SET status='stopped' WHERE id=?", (bot_id,))
            c.commit()
        return result

    @staticmethod
    def status(bot_id: int):
        from app.services.process_service import ProcessService
        bot = BotManager.get(bot_id)
        if not bot:
            return {"success": False, "error": "bot not found"}
        return ProcessService.status_bot(bot)
