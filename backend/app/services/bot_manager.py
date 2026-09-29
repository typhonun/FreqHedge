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
            updatedAt TEXT,

            tp_enabled INTEGER DEFAULT 0,
            tp_mode TEXT DEFAULT 'amount',
            tp_amount REAL DEFAULT 0,
            tp_ratio REAL DEFAULT 0,

            sl_enabled INTEGER DEFAULT 0,
            sl_mode TEXT DEFAULT 'amount',
            sl_amount REAL DEFAULT 0,
            sl_ratio REAL DEFAULT 0,

            trail_enabled INTEGER DEFAULT 0,
            trail_mode TEXT DEFAULT 'ratio',
            trail_activate_amount REAL DEFAULT 0,
            trail_activate_ratio REAL DEFAULT 0,
            trail_drawdown_amount REAL DEFAULT 0,
            trail_drawdown_ratio REAL DEFAULT 0,

            auto_stop_on_tp INTEGER DEFAULT 1,
            auto_stop_on_sl INTEGER DEFAULT 1,
            auto_stop_on_trail INTEGER DEFAULT 1
        );
        """)
        c.commit()


def _migrate():
    """为已存在的旧表补充新列（幂等）"""
    with _conn() as c:
        cols = {row["name"] for row in c.execute("PRAGMA table_info(bots)").fetchall()}

        migrations = [
            ("stakeAmount", "ALTER TABLE bots ADD COLUMN stakeAmount REAL DEFAULT 30"),
            ("leverage", "ALTER TABLE bots ADD COLUMN leverage INTEGER DEFAULT 10"),
            ("dryRun", "ALTER TABLE bots ADD COLUMN dryRun INTEGER DEFAULT 1"),

            ("tp_enabled", "ALTER TABLE bots ADD COLUMN tp_enabled INTEGER DEFAULT 0"),
            ("tp_mode", "ALTER TABLE bots ADD COLUMN tp_mode TEXT DEFAULT 'amount'"),
            ("tp_amount", "ALTER TABLE bots ADD COLUMN tp_amount REAL DEFAULT 0"),
            ("tp_ratio", "ALTER TABLE bots ADD COLUMN tp_ratio REAL DEFAULT 0"),

            ("sl_enabled", "ALTER TABLE bots ADD COLUMN sl_enabled INTEGER DEFAULT 0"),
            ("sl_mode", "ALTER TABLE bots ADD COLUMN sl_mode TEXT DEFAULT 'amount'"),
            ("sl_amount", "ALTER TABLE bots ADD COLUMN sl_amount REAL DEFAULT 0"),
            ("sl_ratio", "ALTER TABLE bots ADD COLUMN sl_ratio REAL DEFAULT 0"),

            ("trail_enabled", "ALTER TABLE bots ADD COLUMN trail_enabled INTEGER DEFAULT 0"),
            ("trail_mode", "ALTER TABLE bots ADD COLUMN trail_mode TEXT DEFAULT 'ratio'"),
            ("trail_activate_amount", "ALTER TABLE bots ADD COLUMN trail_activate_amount REAL DEFAULT 0"),
            ("trail_activate_ratio", "ALTER TABLE bots ADD COLUMN trail_activate_ratio REAL DEFAULT 0"),
            ("trail_drawdown_amount", "ALTER TABLE bots ADD COLUMN trail_drawdown_amount REAL DEFAULT 0"),
            ("trail_drawdown_ratio", "ALTER TABLE bots ADD COLUMN trail_drawdown_ratio REAL DEFAULT 0"),

            ("auto_stop_on_tp", "ALTER TABLE bots ADD COLUMN auto_stop_on_tp INTEGER DEFAULT 1"),
            ("auto_stop_on_sl", "ALTER TABLE bots ADD COLUMN auto_stop_on_sl INTEGER DEFAULT 1"),
            ("auto_stop_on_trail", "ALTER TABLE bots ADD COLUMN auto_stop_on_trail INTEGER DEFAULT 1"),
        ]

        for col, ddl in migrations:
            if col not in cols:
                print(f"[migrate] adding column: {col}")
                c.execute(ddl)

        c.commit()


# 启动时初始化
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

        # ★ 风控字段
        bot["tp_enabled"] = bool(bot.get("tp_enabled"))
        bot["sl_enabled"] = bool(bot.get("sl_enabled"))
        bot["trail_enabled"] = bool(bot.get("trail_enabled"))
        bot["auto_stop_on_tp"] = bool(bot.get("auto_stop_on_tp", 1))
        bot["auto_stop_on_sl"] = bool(bot.get("auto_stop_on_sl", 1))
        bot["auto_stop_on_trail"] = bool(bot.get("auto_stop_on_trail", 1))

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
        risk = payload.get("risk", {})  # ★ 新增
        port = _find_free_port()

        with _conn() as c:
            cur = c.execute(
                """
                INSERT INTO bots (name, pair, capital, stakeAmount, leverage, dryRun,
                                  enableLong, enableShort,
                                  status, port, longConfig, shortConfig, createdAt,
                                  tp_enabled, tp_mode, tp_amount, tp_ratio,
                                  sl_enabled, sl_mode, sl_amount, sl_ratio,
                                  trail_enabled, trail_mode,
                                  trail_activate_amount, trail_activate_ratio,
                                  trail_drawdown_amount, trail_drawdown_ratio,
                                  auto_stop_on_tp, auto_stop_on_sl, auto_stop_on_trail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'stopped', ?, ?, ?, datetime('now'),
                        ?, ?, ?, ?,  ?, ?, ?, ?,  ?, ?,  ?, ?,  ?, ?,
                        ?, ?, ?)
                """,
                (
                    base["name"], json.dumps(base["pair"]), base["capital"],
                    base.get("stakeAmount", 30), base.get("leverage", 10),
                    int(base.get("dryRun", True)),
                    int(base["enableLong"]), int(base["enableShort"]),
                    port,
                    json.dumps(payload.get("longConfig") or {}),
                    json.dumps(payload.get("shortConfig") or {}),

                    # ★ 风控
                    int(risk.get("tp_enabled", False)),
                    risk.get("tp_mode", "amount"),
                    float(risk.get("tp_amount", 0) or 0),
                    float(risk.get("tp_ratio", 0) or 0),

                    int(risk.get("sl_enabled", False)),
                    risk.get("sl_mode", "amount"),
                    float(risk.get("sl_amount", 0) or 0),
                    float(risk.get("sl_ratio", 0) or 0),

                    int(risk.get("trail_enabled", False)),
                    risk.get("trail_mode", "ratio"),
                    float(risk.get("trail_activate_amount", 0) or 0),
                    float(risk.get("trail_activate_ratio", 0) or 0),
                    float(risk.get("trail_drawdown_amount", 0) or 0),
                    float(risk.get("trail_drawdown_ratio", 0) or 0),

                    int(risk.get("auto_stop_on_tp", True)),
                    int(risk.get("auto_stop_on_sl", True)),
                    int(risk.get("auto_stop_on_trail", True)),
                ),
            )
            bot_id = cur.lastrowid
            c.commit()
        return BotManager.get(bot_id)

    @staticmethod
    def update(bot_id: int, payload: dict):
        base = payload["base"]
        risk = payload.get("risk", {}) or {}  # ★
        with _conn() as c:
            c.execute(
                """
                UPDATE bots SET
                    name=?, pair=?, capital=?,
                    stakeAmount=?, leverage=?, dryRun=?,
                    enableLong=?, enableShort=?,
                    longConfig=?, shortConfig=?,

                    tp_enabled=?, tp_mode=?, tp_amount=?, tp_ratio=?,
                    sl_enabled=?, sl_mode=?, sl_amount=?, sl_ratio=?,
                    trail_enabled=?, trail_mode=?,
                    trail_activate_amount=?, trail_activate_ratio=?,
                    trail_drawdown_amount=?, trail_drawdown_ratio=?,
                    auto_stop_on_tp=?, auto_stop_on_sl=?, auto_stop_on_trail=?,

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

                    int(risk.get("tp_enabled", False)),
                    risk.get("tp_mode", "amount"),
                    float(risk.get("tp_amount", 0) or 0),
                    float(risk.get("tp_ratio", 0) or 0),

                    int(risk.get("sl_enabled", False)),
                    risk.get("sl_mode", "amount"),
                    float(risk.get("sl_amount", 0) or 0),
                    float(risk.get("sl_ratio", 0) or 0),

                    int(risk.get("trail_enabled", False)),
                    risk.get("trail_mode", "ratio"),
                    float(risk.get("trail_activate_amount", 0) or 0),
                    float(risk.get("trail_activate_ratio", 0) or 0),
                    float(risk.get("trail_drawdown_amount", 0) or 0),
                    float(risk.get("trail_drawdown_ratio", 0) or 0),

                    int(risk.get("auto_stop_on_tp", True)),
                    int(risk.get("auto_stop_on_sl", True)),
                    int(risk.get("auto_stop_on_trail", True)),

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

            # ★ 新增
            try:
                from app.services.risk_service import RiskService
                RiskService.init_round(bot_id)
            except Exception as e:
                print(f"[BotManager] init_round 失败 bot={bot_id}: {e}")

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
