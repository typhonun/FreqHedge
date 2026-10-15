# backend/app/services/bot_manager.py
import sqlite3
import json
from pathlib import Path
import threading
from config.settings import DCATP_DB
from app.services.freqtrade_client import FreqtradeClient
from app.services.config_service import ConfigService
from app.core.defaults import BOT_DEFAULTS, RISK_DEFAULTS, GRID_DEFAULTS

DB_PATH = Path(DCATP_DB)


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

_c = BOT_DEFAULTS["capital"]
_s = BOT_DEFAULTS["stakeAmount"]
_l = BOT_DEFAULTS["leverage"]
_m = BOT_DEFAULTS["maxOpenTrades"]


def _ensure_table():
    with _conn() as c:
        c.execute(f"""
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pair TEXT NOT NULL,
            capital REAL NOT NULL,
            stakeAmount REAL DEFAULT {_s},
            leverage INTEGER DEFAULT {_l},
            dryRun INTEGER DEFAULT 1,
            maxOpenTrades INTEGER DEFAULT {_m},
            enableLong INTEGER DEFAULT 1,
            enableShort INTEGER DEFAULT 0,
            status TEXT DEFAULT 'stopped',
            port INTEGER,
            longConfig TEXT,
            shortConfig TEXT,
            gridConfig TEXT,
            strategyType TEXT DEFAULT 'dca',
            tradingMode TEXT DEFAULT 'futures',
            marginMode  TEXT DEFAULT 'cross',
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
            ("stakeAmount", f"ALTER TABLE bots ADD COLUMN stakeAmount REAL DEFAULT {_s}"),
            ("leverage", f"ALTER TABLE bots ADD COLUMN leverage INTEGER DEFAULT {_l}"),
            ("maxOpenTrades", f"ALTER TABLE bots ADD COLUMN maxOpenTrades INTEGER DEFAULT {_m}"),
            ("dryRun", "ALTER TABLE bots ADD COLUMN dryRun INTEGER DEFAULT 1"),
            ("exchangeAccountId", "ALTER TABLE bots ADD COLUMN exchangeAccountId TEXT DEFAULT NULL"),
            ("exchangeAccountJson", "ALTER TABLE bots ADD COLUMN exchangeAccountJson TEXT DEFAULT NULL"),
            ("tradingMode", "ALTER TABLE bots ADD COLUMN tradingMode TEXT DEFAULT 'futures'"),
            ("marginMode", "ALTER TABLE bots ADD COLUMN marginMode  TEXT DEFAULT 'cross'"),

            ("gridConfig", "ALTER TABLE bots ADD COLUMN gridConfig TEXT"),
            ("strategyType", "ALTER TABLE bots ADD COLUMN strategyType TEXT DEFAULT 'dca'"),

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

_alloc_lock = threading.Lock()


def _alloc_port(start=None, end=None):
    """
    为每个 bot 分配 2 个连续端口（long=base, short=base+1）。
    从 start 开始找第一个「base 和 base+1 都未被占用」的位置。
    """
    from config.settings import PORT_START, PORT_END
    start = start if start is not None else PORT_START
    end = end if end is not None else PORT_END

    with _conn() as c:
        rows = c.execute(
            "SELECT port FROM bots WHERE port IS NOT NULL"
        ).fetchall()

    used = set()
    for r in rows:
        p = r["port"]
        if p:
            used.add(p)
            used.add(p + 1)   # short 占用的也标记

    with _alloc_lock:
        port = start
        while port + 1 < end:
            if port not in used and (port + 1) not in used:
                return port
            port += 2
    raise RuntimeError(f"no free port in [{start}, {end})")


def _backfill_null_ports():
    """启动时给历史 NULL port 记录补端口"""
    with _conn() as c:
        rows = c.execute("SELECT id FROM bots WHERE port IS NULL").fetchall()
    if not rows:
        return
    for r in rows:
        try:
            p = _alloc_port()
            with _conn() as c:
                c.execute("UPDATE bots SET port=? WHERE id=?", (p, r["id"]))
                c.commit()
            print(f"[port] backfilled bot_id={r['id']} port={p}")
        except Exception as e:
            print(f"[port] backfill failed bot_id={r['id']}: {e}")


_backfill_null_ports()


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
        bot["port"] = int(bot.get("port") or 0) or None
        bot["enableLong"] = bool(bot.get("enableLong"))
        bot["enableShort"] = bool(bot.get("enableShort"))
        bot["dryRun"] = bool(bot.get("dryRun", 1))
        bot["maxOpenTrades"] = int(bot.get("maxOpenTrades") or BOT_DEFAULTS["maxOpenTrades"])
        bot["exchangeAccountJson"] = _parse_json_field(bot.get("exchangeAccountJson"))
        bot["tradingMode"] = bot.get("tradingMode") or BOT_DEFAULTS["tradingMode"]
        bot["marginMode"] = bot.get("marginMode") or BOT_DEFAULTS["marginMode"]
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
        bot["gridConfig"] = _parse_json_field(bot.get("gridConfig"))
        bot["strategyType"] = bot.get("strategyType") or "dca"
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
        risk = payload.get("risk", {})

        # ★ 先算端口（事务外，独立完成）
        port = _alloc_port()

        # ★ 按策略类型决定 long/short/grid 分别写什么
        strategy_type = (base.get("strategyType") or "dca")

        if strategy_type == "grid":
            long_config_json = json.dumps({})
            short_config_json = json.dumps({})
            grid_config_json = json.dumps(payload.get("gridConfig") or {})
        else:
            long_config_json = json.dumps(payload.get("longConfig") or {})
            short_config_json = json.dumps(payload.get("shortConfig") or {})
            grid_config_json = json.dumps({})

        with _conn() as c:
            cur = c.execute(
                """
                INSERT INTO bots (name, pair, capital,
                                  stakeAmount, leverage, maxOpenTrades, dryRun,
                                  enableLong, enableShort,
                                  status, port,
                                  longConfig, shortConfig, gridConfig, strategyType,
                                  createdAt,
                                  exchangeAccountId, exchangeAccountJson,
                                  tradingMode, marginMode,
                                  tp_enabled, tp_mode, tp_amount, tp_ratio,
                                  sl_enabled, sl_mode, sl_amount, sl_ratio,
                                  trail_enabled, trail_mode,
                                  trail_activate_amount, trail_activate_ratio,
                                  trail_drawdown_amount, trail_drawdown_ratio,
                                  auto_stop_on_tp, auto_stop_on_sl, auto_stop_on_trail)
                VALUES (?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        'stopped', ?,
                        ?, ?, ?, ?,
                        datetime('now'),
                        ?, ?,
                        ?, ?,
                        ?, ?, ?, ?,  ?, ?, ?, ?,  ?, ?,  ?, ?,  ?, ?,
                        ?, ?, ?)
                """,
                (
                    base["name"], json.dumps(base["pair"]), base["capital"],

                    base.get("stakeAmount", BOT_DEFAULTS["stakeAmount"]),
                    base.get("leverage", BOT_DEFAULTS["leverage"]),
                    base.get("maxOpenTrades", BOT_DEFAULTS["maxOpenTrades"]),
                    int(base.get("dryRun", BOT_DEFAULTS["dryRun"])),

                    int(base["enableLong"]), int(base["enableShort"]),

                    port,
                    long_config_json,
                    short_config_json,
                    grid_config_json,
                    strategy_type,
                    base.get("exchangeAccountId"),
                    json.dumps(base.get("exchangeAccount") or {}),

                    base.get("tradingMode", BOT_DEFAULTS["tradingMode"]),
                    base.get("marginMode", BOT_DEFAULTS["marginMode"]),

                    int(risk.get("tp_enabled", False)),
                    risk.get("tp_mode", RISK_DEFAULTS["tp_mode"]),
                    float(risk.get("tp_amount", 0) or 0),
                    float(risk.get("tp_ratio", 0) or 0),

                    int(risk.get("sl_enabled", False)),
                    risk.get("sl_mode", RISK_DEFAULTS["sl_mode"]),
                    float(risk.get("sl_amount", 0) or 0),
                    float(risk.get("sl_ratio", 0) or 0),

                    int(risk.get("trail_enabled", False)),
                    risk.get("trail_mode", RISK_DEFAULTS["trail_mode"]),
                    float(risk.get("trail_activate_amount", RISK_DEFAULTS["trail_activate_amount"]) or 0),
                    float(risk.get("trail_activate_ratio", RISK_DEFAULTS["trail_activate_ratio"]) or 0),
                    float(risk.get("trail_drawdown_amount", RISK_DEFAULTS["trail_drawdown_amount"]) or 0),
                    float(risk.get("trail_drawdown_ratio", RISK_DEFAULTS["trail_drawdown_ratio"]) or 0),

                    int(risk.get("auto_stop_on_tp", RISK_DEFAULTS["auto_stop_on_tp"])),
                    int(risk.get("auto_stop_on_sl", RISK_DEFAULTS["auto_stop_on_sl"])),
                    int(risk.get("auto_stop_on_trail", RISK_DEFAULTS["auto_stop_on_trail"])),
                ),
            )
            bot_id = cur.lastrowid
            c.commit()

        print(f"[BotManager] created bot_id={bot_id} port={port} type={strategy_type} risk={risk}")
        return BotManager.get(bot_id)

    @staticmethod
    def update(bot_id: int, payload: dict):
        base = payload["base"]
        risk = payload.get("risk", {}) or {}

        strategy_type = (base.get("strategyType") or "dca")

        if strategy_type == "grid":
            long_config_json = json.dumps({})
            short_config_json = json.dumps({})
            grid_config_json = json.dumps(payload.get("gridConfig") or {})
        else:
            long_config_json = json.dumps(payload.get("longConfig") or {})
            short_config_json = json.dumps(payload.get("shortConfig") or {})
            grid_config_json = json.dumps({})

        with _conn() as c:
            c.execute(
                """
                UPDATE bots SET
                    name=?, pair=?, capital=?,
                    stakeAmount=?, leverage=?, dryRun=?, maxOpenTrades=?,
                    longConfig=?, shortConfig=?, gridConfig=?, strategyType=?,
                    exchangeAccountId=?, exchangeAccountJson=?,
                    tradingMode=?, marginMode=?,

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
                    base.get("stakeAmount", BOT_DEFAULTS["stakeAmount"]),
                    base.get("leverage", BOT_DEFAULTS["leverage"]),
                    int(base.get("dryRun", BOT_DEFAULTS["dryRun"])),
                    base.get("maxOpenTrades", BOT_DEFAULTS["maxOpenTrades"]),
                    long_config_json,
                    short_config_json,
                    grid_config_json,
                    strategy_type,
                    base.get("exchangeAccountId"),
                    json.dumps(base.get("exchangeAccount") or {}),
                    base.get("tradingMode", BOT_DEFAULTS["tradingMode"]),
                    base.get("marginMode", BOT_DEFAULTS["marginMode"]),

                    int(risk.get("tp_enabled", False)),
                    risk.get("tp_mode", RISK_DEFAULTS["tp_mode"]),
                    float(risk.get("tp_amount", 0) or 0),
                    float(risk.get("tp_ratio", 0) or 0),

                    int(risk.get("sl_enabled", False)),
                    risk.get("sl_mode", RISK_DEFAULTS["sl_mode"]),
                    float(risk.get("sl_amount", 0) or 0),
                    float(risk.get("sl_ratio", 0) or 0),

                    int(risk.get("trail_enabled", False)),
                    risk.get("trail_mode", RISK_DEFAULTS["trail_mode"]),
                    float(risk.get("trail_activate_amount", RISK_DEFAULTS["trail_activate_amount"]) or 0),
                    float(risk.get("trail_activate_ratio", RISK_DEFAULTS["trail_activate_ratio"]) or 0),
                    float(risk.get("trail_drawdown_amount", RISK_DEFAULTS["trail_drawdown_amount"]) or 0),
                    float(risk.get("trail_drawdown_ratio", RISK_DEFAULTS["trail_drawdown_ratio"]) or 0),

                    int(risk.get("auto_stop_on_tp", RISK_DEFAULTS["auto_stop_on_tp"])),
                    int(risk.get("auto_stop_on_sl", RISK_DEFAULTS["auto_stop_on_sl"])),
                    int(risk.get("auto_stop_on_trail", RISK_DEFAULTS["auto_stop_on_trail"])),

                    bot_id,
                ),
            )
            c.commit()
        print(f"[BotManager] updated bot_id={bot_id} type={strategy_type} risk={risk}")
        return BotManager.get(bot_id)


    @staticmethod
    def delete(bot_id: int):
        from app.services.process_service import ProcessService
        bot = BotManager.get(bot_id)
        if bot:
            try:
                ProcessService.stop_bot(bot)
            except Exception as e:
                print(f"[BotManager] stop before delete failed bot={bot_id}: {e}")

        # ★ 清 position_service 缓存
        from app.services import position_service
        position_service._snapshot_cache.pop(bot_id, None)
        position_service._snapshot_all_cache["data"] = None
        position_service._snapshot_all_cache["time"] = 0
        for key in list(position_service._last_good_data.keys()):
            if key[0] == bot_id:
                position_service._last_good_data.pop(key, None)
        for key in list(position_service._custom_data_cache.keys()):
            if key[0] == bot_id:
                position_service._custom_data_cache.pop(key, None)

        from app.core import runtime
        runtime.ROUND_INFO_BY_BOT.pop(bot_id, None)
        runtime.clear_exit_reasons(bot_id)

        with _conn() as c:
            c.execute("DELETE FROM bots WHERE id=?", (bot_id,))
            c.commit()

    @staticmethod
    def delete_draft(bot_id: int):
        """
        仅删除 status='draft' 的 bot。
        - 会清理 user_data/bots/{id} 目录
        - 会清理 position_service 缓存（和 delete 一致）
        - 如果 bot 不存在或状态不是 draft，直接返回 False，不抛错
        """
        bot = BotManager.get(bot_id)
        if not bot:
            return False
        if bot.get("status") != "draft":
            return False

        # 1. 停进程（正常情况下 draft 不会在跑，但保险）
        try:
            from app.services.process_service import ProcessService
            ProcessService.stop_bot(bot)
        except Exception as e:
            print(f"[BotManager] delete_draft stop failed bot={bot_id}: {e}")

        # 2. 清缓存（和 delete 一致）
        try:
            from app.services import position_service
            position_service._snapshot_cache.pop(bot_id, None)
            position_service._snapshot_all_cache["data"] = None
            position_service._snapshot_all_cache["time"] = 0
            for key in list(position_service._last_good_data.keys()):
                if key[0] == bot_id:
                    position_service._last_good_data.pop(key, None)
            for key in list(position_service._custom_data_cache.keys()):
                if key[0] == bot_id:
                    position_service._custom_data_cache.pop(key, None)

            from app.core import runtime
            runtime.ROUND_INFO_BY_BOT.pop(bot_id, None)
            runtime.clear_exit_reasons(bot_id)
        except Exception as e:
            print(f"[BotManager] delete_draft clear cache failed bot={bot_id}: {e}")

        # 3. 删 user_data/bots/{id} 目录
        try:
            ConfigService.remove_bot_dir(bot_id)
        except Exception as e:
            print(f"[BotManager] delete_draft remove dir failed bot={bot_id}: {e}")

        # 4. 删 DB 记录
        with _conn() as c:
            c.execute("DELETE FROM bots WHERE id=? AND status='draft'", (bot_id,))
            c.commit()

        print(f"[BotManager] deleted DRAFT bot_id={bot_id}")
        return True

    @staticmethod
    def cleanup_stale_drafts(max_age_minutes: int = 60):
        from datetime import datetime, timedelta
        from app.services.config_service import ConfigService, BOTS_DIR  # ★ 一起 import

        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        deleted = []

        with _conn() as c:
            rows = c.execute(
                "SELECT id, createdAt FROM bots WHERE status='draft'"
            ).fetchall()

        for r in rows:
            bot_id = r["id"]
            created = r["createdAt"]
            try:
                created_dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if created_dt > cutoff:
                continue

            try:
                BotManager.delete_draft(bot_id)
                deleted.append(bot_id)
            except Exception as e:
                print(f"[cleanup] delete draft {bot_id} failed: {e}")

        if deleted:
            print(f"[cleanup] removed stale drafts: {deleted}")
        return deleted

    @staticmethod
    def start(bot_id: int, wait: bool = False):
        """
        启动机器人。
        - 默认 wait=False：后台异步启动，立即返回 {"success": True, "async": True}
        - wait=True：同步等待启动完成（旧行为，保留兼容）
        """
        from app.services.process_service import ProcessService
        bot = BotManager.get(bot_id)
        if not bot:
            return {"success": False, "error": "bot not found"}
        if bot.get("status") == "draft":
            return {"success": False, "error": "草稿机器人不能启动，请先保存"}

        if wait:
            return BotManager._do_start_sync(bot_id, bot)

        # ★ 乐观置 running，立即返回
        with _conn() as c:
            c.execute("UPDATE bots SET status='running' WHERE id=?", (bot_id,))
            c.commit()

        t = threading.Thread(
            target=BotManager._do_start_sync,
            args=(bot_id, bot),
            daemon=True,
        )
        t.start()

        print(f"[BotManager] start bot={bot_id} 已提交后台启动")
        return {"success": True, "async": True, "bot_id": bot_id}

    @staticmethod
    def _do_start_sync(bot_id: int, bot: dict):
        """实际执行启动（同步阻塞），供后台线程调用"""
        from app.services.process_service import ProcessService
        try:
            result = ProcessService.start_bot(bot)
            if result.get("success"):
                # 已经在 start 里置 running，无需再改
                try:
                    from app.services.risk_service import RiskService
                    RiskService.init_round(bot_id)
                except Exception as e:
                    print(f"[BotManager] init_round 失败 bot={bot_id}: {e}")
            else:
                # ★ 启动失败 → 改回 stopped
                with _conn() as c:
                    c.execute("UPDATE bots SET status='stopped' WHERE id=?", (bot_id,))
                    c.commit()
                print(f"[BotManager] start failed bot={bot_id}: {result.get('error')}")
            return result
        except Exception as e:
            print(f"[BotManager] _do_start_sync 异常 bot={bot_id}: {e}")
            with _conn() as c:
                c.execute("UPDATE bots SET status='stopped' WHERE id=?", (bot_id,))
                c.commit()
            return {"success": False, "error": str(e)}

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

    @staticmethod
    def create_draft():
        """创建一个草稿 bot：status='draft'，参数用默认值，允许 pair 为空"""
        default_payload = {
            "base": {
                "name": "未命名机器人",
                "pair": [],
                **BOT_DEFAULTS,
            },
            "risk": {},
            "longConfig": None,
            "shortConfig": None,
        }

        base = default_payload["base"]

        # ★ 先算端口（事务外）
        port = _alloc_port()

        with _conn() as c:
            cur = c.execute(
                """
                INSERT INTO bots (name, pair, capital,
                                  stakeAmount, leverage, maxOpenTrades, dryRun,
                                  enableLong, enableShort,
                                  status, port, longConfig, shortConfig, gridConfig, strategyType, createdAt,
                                  tradingMode, marginMode)
                VALUES (?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        'draft', ?, ?, ?, ?, ?, datetime('now'),
                        ?, ?)
                """,
                (
                    base["name"], json.dumps(base["pair"]), base["capital"],
                    base["stakeAmount"], base["leverage"],
                    base["maxOpenTrades"], int(base["dryRun"]),
                    int(base["enableLong"]), int(base["enableShort"]),
                    port,
                    json.dumps({}),                       # longConfig
                    json.dumps({}),                       # shortConfig
                    json.dumps({"grid": GRID_DEFAULTS}),  # gridConfig
                    "dca",                                 # strategyType（占位，用户选了类型后由 update 覆盖）
                    base["tradingMode"],
                    base["marginMode"],
                ),
            )
            bot_id = cur.lastrowid
            c.commit()

        print(f"[BotManager] created DRAFT bot_id={bot_id} port={port}")
        return BotManager.get(bot_id)

    @staticmethod
    def list_all(include_draft: bool = False):
        with _conn() as c:
            if include_draft:
                rows = c.execute("SELECT * FROM bots ORDER BY id").fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM bots WHERE status != 'draft' ORDER BY id"
                ).fetchall()
        return [BotManager._normalize(r) for r in rows]

    @staticmethod
    def promote(bot_id: int):
        """把 draft 升级为 stopped（正式保存时调用）"""
        with _conn() as c:
            c.execute(
                "UPDATE bots SET status='stopped' WHERE id=? AND status='draft'",
                (bot_id,),
            )
            c.commit()
        return BotManager.get(bot_id)