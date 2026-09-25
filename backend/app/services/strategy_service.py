import json
from app.db import get_conn
from app.core.config_manager import ConfigManager

from app.services.freqtrade_client import FreqtradeClient
from config.settings import LONG_URL, SHORT_URL


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

        # 内存配置刷新
        ConfigManager.force_reload(side)

        # ===== 热重载 Freqtrade =====
        reload_ok = False
        reload_err = None

        try:
            if side == "long":
                FreqtradeClient.send_command(LONG_URL, "reload_config")
            elif side == "short":
                FreqtradeClient.send_command(SHORT_URL, "reload_config")
            reload_ok = True
        except Exception as e:
            reload_err = str(e)
            print(f"[strategy save] reload_config failed: {e}")

        return {
            "success": True,
            "side": side,
            "reload_ok": reload_ok,
            "reload_err": reload_err,
        }