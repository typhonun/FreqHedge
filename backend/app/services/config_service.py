import json
from pathlib import Path
from typing import Optional

from config.settings import (
    FREQTRADE_DIR,
)
from app.core.defaults import BOT_DEFAULTS
FREQTRADE_ROOT = Path(FREQTRADE_DIR)
USER_DATA = FREQTRADE_ROOT / "user_data"
BOTS_DIR = USER_DATA / "bots"
BASE_TEMPLATE = USER_DATA / "config_template.json"
BASE_LONG = BASE_TEMPLATE
BASE_SHORT = BASE_TEMPLATE

# ★ 策略类型 × 方向 → freqtrade 策略类名
STRATEGY_CLASS_MAP = {
    ("dca",  "long"):  "DcaTpLong",
    ("dca",  "short"): "DcaTpShort",
    ("grid", "long"):  "GridBotLong",
    ("grid", "short"): "GridBotShort",
}

class ConfigService:

    # ================== 新增：多实例配置生成 ==================
    @staticmethod
    def generate_configs(bot_id: int, payload: dict):
        bot_dir = BOTS_DIR / str(bot_id)
        bot_dir.mkdir(parents=True, exist_ok=True)
        (bot_dir / "logs").mkdir(exist_ok=True)

        base = payload["base"]
        enable_long = bool(base.get("enableLong", True))
        enable_short = bool(base.get("enableShort", False))
        strategy_type = base.get("strategyType") or "dca"

        long_path = bot_dir / f"config_bot{bot_id}_long.json"
        short_path = bot_dir / f"config_bot{bot_id}_short.json"

        # ---------- 1. 写需要的 ----------
        if enable_long:
            if strategy_type == "grid":
                sp = payload.get("gridConfig") or {}
            else:
                sp = payload.get("longConfig") or {}

            cfg = ConfigService._build_config(
                bot_id=bot_id,
                side="long",
                base=base,
                strategy_params=sp,
                strategy_type=strategy_type,
                template=BASE_TEMPLATE,
            )
            long_path.write_text(
                json.dumps(cfg, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )

        if enable_short:
            if strategy_type == "grid":
                sp = payload.get("gridConfig") or {}
            else:
                sp = payload.get("shortConfig") or {}

            cfg = ConfigService._build_config(
                bot_id=bot_id,
                side="short",
                base=base,
                strategy_params=sp,
                strategy_type=strategy_type,
                template=BASE_TEMPLATE,
            )
            short_path.write_text(
                json.dumps(cfg, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )

        # ---------- 2. 删多余的 ----------
        if not enable_long and long_path.exists():
            try:
                long_path.unlink()
                print(f"[config] 删除多余文件: {long_path.name}")
            except Exception as e:
                print(f"[config] 删除失败 {long_path}: {e}")

        if not enable_short and short_path.exists():
            try:
                short_path.unlink()
                print(f"[config] 删除多余文件: {short_path.name}")
            except Exception as e:
                print(f"[config] 删除失败 {short_path}: {e}")


    @staticmethod
    def resolve_config_path(bot_id: int, side: str) -> Optional[Path]:
        """
        返回某 bot 某方向的 config 路径；如果该方向不存在，返回 None。
        """
        p = BOTS_DIR / str(bot_id) / f"config_bot{bot_id}_{side}.json"
        return p if p.exists() else None

    @staticmethod
    def _build_config(bot_id, side, base, strategy_params, strategy_type, template):
        cfg = ConfigService.read_json(template)

        port = ConfigService._get_port(bot_id, side)
        db_file = (Path(FREQTRADE_DIR)
                   / f"user_data/bots/{bot_id}/tradesv3_bot{bot_id}_{side}.sqlite").as_posix()

        cfg["db_url"] = f"sqlite:///{db_file}"
        cfg["api_server"]["listen_port"] = port
        cfg["api_server"]["CORS_origins"] = ["*"]

        cfg["bot_id"] = bot_id
        cfg["side"] = side

        # ★ 按 (strategy_type, side) 选策略类名
        strategy_cls = STRATEGY_CLASS_MAP.get((strategy_type, side))
        if strategy_cls is None:
            raise ValueError(f"未知策略类型: {strategy_type}/{side}")
        cfg["strategy"] = strategy_cls

        cfg["dry_run"] = bool(base.get("dryRun", BOT_DEFAULTS["dryRun"]))
        cfg["dry_run_wallet"] = base["capital"]
        cfg["stake_amount"] = base.get("stakeAmount", BOT_DEFAULTS["stakeAmount"])
        trading_mode = base.get("tradingMode", BOT_DEFAULTS["tradingMode"])
        margin_mode = base.get("marginMode", BOT_DEFAULTS["marginMode"])

        cfg["trading_mode"] = trading_mode

        if trading_mode == "futures":
            cfg["margin_mode"] = margin_mode
            cfg["leverage"] = base.get("leverage", BOT_DEFAULTS["leverage"])
        else:
            cfg.pop("margin_mode", None)
            cfg["leverage"] = 1
        cfg["max_open_trades"] = int(base.get("maxOpenTrades", BOT_DEFAULTS["maxOpenTrades"]))
        cfg["tradable_balance_ratio"] = 0.99
        cfg["bot_name"] = f"{base['name']}-{side}"

        # ★ 网格固定用 5m 主周期（避免与 DCA 的 30m 混在一起）
        if strategy_type == "grid":
            cfg["timeframe"] = "5m"

        cfg.setdefault("exchange", {})
        cfg["exchange"]["pair_whitelist"] = list(base["pair"])

        # ★ 交易所账户注入
        acct = base.get("exchangeAccount") or {}
        if acct.get("exchange"):
            cfg["exchange"]["name"] = acct["exchange"]
            cfg["exchange"]["key"] = acct.get("apiKey", "") or ""
            cfg["exchange"]["secret"] = acct.get("apiSecret", "") or ""
            if acct.get("passphrase"):
                cfg["exchange"]["password"] = acct["passphrase"]
            cfg["exchange"].setdefault("ccxt_config", {})
            cfg["exchange"].setdefault("ccxt_async_config", {})

        if not cfg["exchange"].get("name"):
            cfg["exchange"]["name"] = "binance"
            cfg["exchange"].setdefault("key", "")
            cfg["exchange"].setdefault("secret", "")
            cfg["exchange"].setdefault("ccxt_config", {"enableRateLimit": True})
            cfg["exchange"].setdefault("ccxt_async_config", {"enableRateLimit": True, "rateLimit": 200})
            print("[config] exchange.name 为空，回退到 binance")

        # ★★★ custom_params 分叉 ★★★
        if strategy_type == "grid":
            # GridBotBase.get_runtime_config 会读 custom_params["config"]
            cfg["custom_params"] = {
                "bot_id": bot_id,
                "strategyType": "grid",
                "config": strategy_params,        # 里面就是 {"grid": {...}}
            }
        else:
            # DcaTpBotBase.get_runtime_config 读 custom_params[side]
            cfg["custom_params"] = {
                "bot_id": bot_id,
                "strategyType": "dca",
                side: strategy_params,
            }

        return cfg

    @staticmethod
    def config_path(bot_id: int, side: str) -> Path:
        """返回某个 bot 某个方向的 config 绝对路径"""
        return BOTS_DIR / str(bot_id) / f"config_bot{bot_id}_{side}.json"

    @staticmethod
    def log_path(bot_id: int, side: str) -> Path:
        return BOTS_DIR / str(bot_id) / "logs" / f"{side}.log"

    @staticmethod
    def db_path(bot_id: int, side: str) -> Path:
        return BOTS_DIR / str(bot_id) / f"tradesv3_bot{bot_id}_{side}.sqlite"

    @staticmethod
    def _get_port(bot_id, side):
        """★ 从 DB 读 port 字段 """
        from app.services.bot_manager import BotManager  # 延迟导入，避免循环
        bot = BotManager.get(bot_id)
        if not bot or not bot.get("port"):
            raise ValueError(f"bot {bot_id} 没有分配端口，请检查 DB 完整性")
        base = int(bot["port"])
        return base if side == "long" else base + 1

    @staticmethod
    def remove_bot_dir(bot_id: int, retries: int = 5, retry_delay: float = 0.5):
        import shutil
        import time
        bot_dir = BOTS_DIR / str(bot_id)
        if not bot_dir.exists():
            return

        for attempt in range(1, retries + 1):
            try:
                shutil.rmtree(bot_dir)
                print(f"[config] 已删除 bot 目录: {bot_dir}")
                return
            except PermissionError as e:
                print(f"[config] 删除失败（{attempt}/{retries}）: {e}")
                time.sleep(retry_delay * attempt)

        # 兜底
        print(f"[config] 重试失败，降级忽略错误删除: {bot_dir}")
        shutil.rmtree(bot_dir, ignore_errors=True)
        if bot_dir.exists():
            print(f"[config] 警告：目录残留，请手动清理 {bot_dir}")

    @staticmethod
    def read_json(path):

        with open(
                path,
                "r",
                encoding="utf-8"
        ) as f:
            return json.load(f)

    @staticmethod
    def write_json(path, data):

        with open(
                path,
                "w",
                encoding="utf-8"
        ) as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )