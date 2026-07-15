import json
from db import get_conn
from config.settings import (
    STRATEGY_LONG,
    STRATEGY_SHORT
)


class StrategyService:

    @staticmethod
    def _strategy_path(side):
        if side == "long":
            return STRATEGY_LONG
        if side == "short":
            return STRATEGY_SHORT
        raise ValueError(f"Unsupported strategy side: {side}")

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

    @staticmethod
    def get_config():
        conn = get_conn()

        rows = conn.execute("""
            SELECT side, config_json
            FROM strategy_config
        """).fetchall()

        conn.close()

        result = {
            "long": {},
            "short": {}
        }

        for row in rows:
            result[row["side"]] = json.loads(
                row["config_json"]
            )

        for side, path in (
            ("long", STRATEGY_LONG),
            ("short", STRATEGY_SHORT)
        ):
            if result[side]:
                continue

            if path.exists():
                result[side] = StrategyService.read_json(path)

        return result

    @staticmethod
    def save_config(data):

        side = data.get("side")

        config = data.get("config", {})

        print("====================")
        print("SAVE SIDE:", side)
        print(
            "SAVE RSI:",
            config["entry"]["rsi"]["value"]
        )
        print("====================")

        conn = get_conn()

        conn.execute(
            """
            INSERT OR REPLACE INTO strategy_config
            (
                side,
                config_json,
                update_time
            )
            VALUES
            (
                ?,
                ?,
                CURRENT_TIMESTAMP
            )
            """,
            (
                side,
                json.dumps(
                    config,
                    ensure_ascii=False
                )
            )
        )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "side": side
        }