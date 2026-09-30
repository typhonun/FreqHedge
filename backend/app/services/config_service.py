import json
from app.services.freqtrade_client import FreqtradeClient
from pathlib import Path

from config.settings import (
    LONG_CONFIG,
    SHORT_CONFIG,
    LONG_URL,
    SHORT_URL,
    FREQTRADE_DIR,
)
FREQTRADE_ROOT = Path(FREQTRADE_DIR)
USER_DATA = FREQTRADE_ROOT / "user_data"
BOTS_DIR = USER_DATA / "bots"
BASE_LONG = USER_DATA / "config_long.json"
BASE_SHORT = USER_DATA / "config_short.json"

class ConfigService:

    # ================== 新增：多实例配置生成 ==================
    @staticmethod
    def generate_configs(bot_id: int, payload: dict):
        """为 bot_id 生成 config_long.json / config_short.json"""
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
                template=BASE_LONG,
            )
            (bot_dir / "config_long.json").write_text(
                json.dumps(cfg, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )

        if base["enableShort"]:
            cfg = ConfigService._build_config(
                bot_id=bot_id,
                side="short",
                base=base,
                strategy_params=payload.get("shortConfig") or {},
                template=BASE_SHORT,
            )
            (bot_dir / "config_short.json").write_text(
                json.dumps(cfg, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )

    @staticmethod
    def _build_config(bot_id, side, base, strategy_params, template):
        cfg = ConfigService.read_json(template)

        port = ConfigService._get_port(bot_id, side)
        db_file = (Path(FREQTRADE_DIR) / f"user_data/bots/{bot_id}/tradesv3_{side}.sqlite").as_posix()

        cfg["db_url"] = f"sqlite:///{db_file}"
        cfg["api_server"]["listen_port"] = port
        cfg["api_server"]["CORS_origins"] = ["*"]

        # ★ 新字段生效
        cfg["dry_run"] = bool(base.get("dryRun", True))
        cfg["dry_run_wallet"] = base["capital"]
        cfg["stake_amount"] = base.get("stakeAmount", 10)
        cfg["leverage"] = base.get("leverage", 10)
        cfg["max_open_trades"] = int(base.get("maxOpenTrades", 3))  # ★ 新增这一行
        cfg["tradable_balance_ratio"] = 1.0
        cfg["bot_name"] = f"{base['name']}-{side}"
        cfg.setdefault("exchange", {})
        cfg["exchange"]["pair_whitelist"] = list(base["pair"])

        cfg["custom_params"] = {side: strategy_params}

        return cfg

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

    @classmethod
    def get_config(cls):

        long_cfg = cls.read_json(LONG_CONFIG)
        short_cfg = cls.read_json(SHORT_CONFIG)

        return {
            "long": {
                "dry_run_wallet": long_cfg.get("dry_run_wallet", 300),
                "stake_amount": long_cfg.get("stake_amount", 15),
                "max_open_trades": long_cfg.get("max_open_trades", 3),
                "max_usage": long_cfg.get("tradable_balance_ratio", 0.9) * 100,
                "leverage": long_cfg.get("leverage", 10),

                # ===== 失衡控制 =====
                "imbalance_long_enable": long_cfg.get("imbalance_long_enable", False),
                "imbalance_long_count": long_cfg.get("imbalance_long_count", 2),

                "pair_whitelist": long_cfg.get("exchange", {}).get("pair_whitelist", []),
                "pair_blacklist": long_cfg.get("exchange", {}).get("pair_blacklist", []),
            },

            "short": {
                "dry_run_wallet": short_cfg.get("dry_run_wallet", 300),
                "stake_amount": short_cfg.get("stake_amount", 15),
                "max_open_trades": short_cfg.get("max_open_trades", 3),
                "max_usage": short_cfg.get("tradable_balance_ratio", 0.9) * 100,
                "leverage": short_cfg.get("leverage", 10),

                # ===== 失衡控制 =====
                "imbalance_short_enable": short_cfg.get("imbalance_short_enable", False),
                "imbalance_short_count": short_cfg.get("imbalance_short_count", 2),

                "pair_whitelist": short_cfg.get("exchange", {}).get("pair_whitelist", []),
                "pair_blacklist": short_cfg.get("exchange", {}).get("pair_blacklist", []),
            }
        }

    @classmethod
    def save_config(cls, data):

        path = (
            LONG_CONFIG
            if data["side"] == "long"
            else SHORT_CONFIG
        )

        cfg = cls.read_json(path)

        cfg["stake_amount"] = data.get("stake_amount")
        cfg["dry_run_wallet"] = data.get("dry_run_wallet")
        cfg["max_open_trades"] = data.get("max_open_trades")
        cfg["tradable_balance_ratio"] = data.get("max_usage", 90) / 100

        # 持仓杠杆
        if "leverage" in data:
            cfg["leverage"] = data["leverage"]

        # ===== 失衡控制：写入 config 文件 =====
        if data["side"] == "long":
            imbalance_keys = [
                "imbalance_long_enable",
                "imbalance_long_count",
            ]
        else:
            imbalance_keys = [
                "imbalance_short_enable",
                "imbalance_short_count",
            ]

        for key in imbalance_keys:
            if key in data:
                cfg[key] = data[key]

        # 防止 exchange 不存在
        exchange = cfg.setdefault("exchange", {})

        exchange["pair_whitelist"] = data.get("pair_whitelist", [])
        exchange["pair_blacklist"] = data.get("pair_blacklist", [])

        cls.write_json(path, cfg)

        # reload
        if data["side"] == "long":
            FreqtradeClient.send_command(LONG_URL, "reload_config")
        else:
            FreqtradeClient.send_command(SHORT_URL, "reload_config")

        return {"success": True}
