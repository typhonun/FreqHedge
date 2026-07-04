import json

from config.settings import (
    STRATEGY_LONG,
    STRATEGY_SHORT
)


class StrategyService:

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

        return {
            "long": cls.read_json(
                STRATEGY_LONG
            ),
            "short": cls.read_json(
                STRATEGY_SHORT
            )
        }

    @classmethod
    def save_config(cls, data):

        side = data["side"]

        path = (
            STRATEGY_LONG
            if side == "long"
            else STRATEGY_SHORT
        )

        cls.write_json(
            path,
            data["config"]
        )

        return {
            "success": True
        }