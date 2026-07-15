import json
from db import get_conn
from app.core.config_manager import ConfigManager


class StrategyService:

    @staticmethod
    def get_config():
        conn = get_conn()

        rows = conn.execute(
            """
            SELECT side, config_json
            FROM strategy_config
            """
        ).fetchall()

        conn.close()

        result = {
            "long": {},
            "short": {}
        }

        for row in rows:
            result[row["side"]] = json.loads(
                row["config_json"]
            )

        return result

    @staticmethod
    def save_config(data):
        side = data.get("side")

        config = data.get(
            "config",
            {}
        )

        print(
            "SAVE SIDE:",
            side
        )

        print(
            "SAVE RSI:",
            config
            .get("entry", {})
            .get("rsi", {})
            .get("value")
        )

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

        ConfigManager.force_reload(side)

        return {
            "success": True,
            "side": side
        }
