import json
from pathlib import Path

from config.settings import (
    FREQTRADE_DIR,
)
FREQTRADE_ROOT = Path(FREQTRADE_DIR)
USER_DATA = FREQTRADE_ROOT / "user_data"
BOTS_DIR = USER_DATA / "bots"
BASE_TEMPLATE = USER_DATA / "config_template.json"
BASE_LONG = BASE_TEMPLATE
BASE_SHORT = BASE_TEMPLATE


class ConfigService:

    # ================== 新增：多实例配置生成 ==================
    @staticmethod
    def generate_configs(bot_id: int, payload: dict):
        bot_dir = BOTS_DIR / str(bot_id)
        bot_dir.mkdir(parents=True, exist_ok=True)
        (bot_dir / "logs").mkdir(exist_ok=True)

        base = payload["base"]

        if base["enableLong"]:
            cfg = ConfigService._build_config(
                bot_id=bot_id,
                side="long",
                base=base,
                strategy_params=payload.get("longConfig") or {},
                template=BASE_TEMPLATE,
            )
            # ★ 改这里：带 bot_id 前缀
            cfg_name = f"config_bot{bot_id}_long.json"
            (bot_dir / cfg_name).write_text(
                json.dumps(cfg, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )

        if base["enableShort"]:
            cfg = ConfigService._build_config(
                bot_id=bot_id,
                side="short",
                base=base,
                strategy_params=payload.get("shortConfig") or {},
                template=BASE_TEMPLATE,
            )
            cfg_name = f"config_bot{bot_id}_short.json"
            (bot_dir / cfg_name).write_text(
                json.dumps(cfg, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )

    @staticmethod
    def _build_config(bot_id, side, base, strategy_params, template):
        cfg = ConfigService.read_json(template)

        port = ConfigService._get_port(bot_id, side)
        db_file = (Path(FREQTRADE_DIR)
                   / f"user_data/bots/{bot_id}/tradesv3_bot{bot_id}_{side}.sqlite").as_posix()

        cfg["db_url"] = f"sqlite:///{db_file}"
        cfg["api_server"]["listen_port"] = port
        cfg["api_server"]["CORS_origins"] = ["*"]

        # ★ 新增：把 bot_id 写到配置顶层，策略能直接读
        cfg["bot_id"] = bot_id

        cfg["side"] = side
        cfg["strategy"] = "DcaTpShort" if side == "short" else "DcaTpLong"

        cfg["dry_run"] = bool(base.get("dryRun", True))
        cfg["dry_run_wallet"] = base["capital"]
        cfg["stake_amount"] = base.get("stakeAmount", 10)
        cfg["leverage"] = base.get("leverage", 10)
        cfg["max_open_trades"] = int(base.get("maxOpenTrades", 3))
        cfg["tradable_balance_ratio"] = 0.99
        cfg["bot_name"] = f"{base['name']}-{side}"

        cfg.setdefault("exchange", {})
        cfg["exchange"]["pair_whitelist"] = list(base["pair"])

        # ★ custom_params 里也塞一份，方便策略直接读
        cfg["custom_params"] = {
            "bot_id": bot_id,
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
        base = 8011 + bot_id * 2
        return base if side == "long" else base + 1

    @staticmethod
    def remove_bot_dir(bot_id: int):
        import shutil
        bot_dir = BOTS_DIR / str(bot_id)
        if bot_dir.exists():
            shutil.rmtree(bot_dir)

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