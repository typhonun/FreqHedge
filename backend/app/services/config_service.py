import json
from app.services.freqtrade_client import FreqtradeClient

from config.settings import (
    LONG_CONFIG,
    SHORT_CONFIG,
    LONG_URL,
    SHORT_URL
)


class ConfigService:

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
