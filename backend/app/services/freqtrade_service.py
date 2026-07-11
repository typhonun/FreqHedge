import subprocess

import requests

from config.settings import (
    LONG_URL,
    SHORT_URL,
    AUTH_USER,
    AUTH_PASSWORD
)

from config.settings import FREQTRADE_DIR
from app.core import runtime


class FreqtradeService:
    auth = (AUTH_USER, AUTH_PASSWORD)

    @classmethod
    def post(
            cls,
            url,
            endpoint,
            payload=None
    ):

        r = requests.post(
            f"{url}{endpoint}",
            json=payload or {},
            auth=cls.auth,
            timeout=20
        )

        r.raise_for_status()

        return r.json()

    @classmethod
    def get_status(cls, url):
        r = requests.get(
            f"{url}/api/v1/status",
            auth=cls.auth,
            timeout=10
        )

        return r.json()

    @classmethod
    def get_balance(cls, url):
        r = requests.get(
            f"{url}/api/v1/balance",
            auth=cls.auth,
            timeout=10
        )

        return r.json()

    @classmethod
    def get_trades(cls, url):
        r = requests.get(
            f"{url}/api/v1/trades",
            auth=cls.auth,
            timeout=10
        )

        return r.json()

    @classmethod
    def start_bot(cls, url):
        r = requests.post(
            f"{url}/api/v1/start",
            auth=cls.auth
        )

        return r.json()

    @classmethod
    def stop_bot(cls, url):
        r = requests.post(
            f"{url}/api/v1/stop",
            auth=cls.auth
        )

        return r.json()

    @classmethod
    def start_bot_service(cls, data: dict):

        cls.start_freqtrade()

        if data.get("long"):
            requests.post(
                f"{LONG_URL}/api/v1/start",
                auth=cls.auth
            )

            runtime.RUNNING["long"] = True

        if data.get("short"):
            requests.post(
                f"{SHORT_URL}/api/v1/start",
                auth=cls.auth
            )

            runtime.RUNNING["short"] = True

        return {
            "success": True
        }

    @classmethod
    def stop_bot_service(cls, data: dict):
        try:
            if data.get("long"):
                requests.post(f"{LONG_URL}/api/v1/stop", auth=cls.auth)
                runtime.RUNNING["long"] = False

            if data.get("short"):
                requests.post(f"{SHORT_URL}/api/v1/stop", auth=cls.auth)
                runtime.RUNNING["short"] = False

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def reload_service(cls):
        try:
            cls.send_command(LONG_URL, "reload_config")
            cls.send_command(SHORT_URL, "reload_config")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def get_bot_state(cls, url):

        r = requests.get(
            f"{url}/api/v1/status",
            auth=cls.auth,
            timeout=10
        )

        data = r.json()

        if isinstance(data, dict):
            return str(
                data.get("state", "")
            ).upper()

        return ""

    @classmethod
    def stop_entry(cls, data: dict):

        # LONG

        if data["long"]:

            requests.post(
                f"{LONG_URL}/api/v1/stopentry",
                auth=cls.auth
            )

        else:

            requests.post(
                f"{LONG_URL}/api/v1/startentry",
                auth=cls.auth
            )

            state = cls.get_bot_state(
                LONG_URL
            )

            if state == "PAUSED":
                requests.post(
                    f"{LONG_URL}/api/v1/start",
                    auth=cls.auth
                )

        # SHORT

        if data["short"]:

            requests.post(
                f"{SHORT_URL}/api/v1/stopentry",
                auth=cls.auth
            )

        else:

            requests.post(
                f"{SHORT_URL}/api/v1/startentry",
                auth=cls.auth
            )

            state = cls.get_bot_state(
                SHORT_URL
            )

            if state == "PAUSED":
                requests.post(
                    f"{SHORT_URL}/api/v1/start",
                    auth=cls.auth
                )

        return {
            "success": True
        }

    @classmethod
    def get_stop_entry_status(cls):

        return {
            "long": runtime.STOP_ENTRY["long"],
            "short": runtime.STOP_ENTRY["short"]
        }

    @classmethod
    def delete_trade(cls):

        try:

            # 先停止机器人

            requests.post(
                f"{LONG_URL}/api/v1/stop",
                auth=cls.auth,
                timeout=10
            )

            requests.post(
                f"{SHORT_URL}/api/v1/stop",
                auth=cls.auth,
                timeout=10
            )

            runtime.RUNNING["long"] = False
            runtime.RUNNING["short"] = False

            # 清空数据库记录

            requests.delete(
                f"{LONG_URL}/api/v1/delete_trade",
                auth=cls.auth,
                timeout=30
            )

            requests.delete(
                f"{SHORT_URL}/api/v1/delete_trade",
                auth=cls.auth,
                timeout=30
            )

            return {
                "success": True
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e)
            }

    @classmethod
    def get_status_service(cls):
        return {
            "long": runtime.RUNNING["long"],
            "short": runtime.RUNNING["short"]
        }

    @classmethod
    def send_command(cls, url, command):
        return requests.post(
            f"{url}/api/v1/{command}",
            auth=cls.auth,
            timeout=10
        )

    @classmethod
    def start_freqtrade(cls):

        if runtime.LONG_PROCESS is None or \
                runtime.LONG_PROCESS.poll() is not None:
            runtime.LONG_PROCESS = subprocess.Popen(
                [
                    "freqtrade",
                    "trade",
                    "--config",
                    "user_data/config_long.json",
                    "--strategy",
                    "DcaTpLong"
                ],
                cwd=str(FREQTRADE_DIR)
            )

            print(
                "LONG PID:",
                runtime.LONG_PROCESS.pid
            )

        if runtime.SHORT_PROCESS is None or \
                runtime.SHORT_PROCESS.poll() is not None:
            runtime.SHORT_PROCESS = subprocess.Popen(
                [
                    "freqtrade",
                    "trade",
                    "--config",
                    "user_data/config_short.json",
                    "--strategy",
                    "DcaTpShort"
                ],
                cwd=str(FREQTRADE_DIR)
            )

            print(
                "SHORT PID:",
                runtime.SHORT_PROCESS.pid
            )

    @classmethod
    def get_whitelist(cls, url):

        r = requests.get(
            f"{url}/api/v1/whitelist",
            auth=cls.auth,
            timeout=10
        )

        return r.json()

    @classmethod
    def force_enter(
            cls,
            side: str,
            pair: str,
            stakeamount: float
    ):

        base_url = (
            LONG_URL
            if side == "long"
            else SHORT_URL
        )

        payload = {
            "pair": pair,
            "side": side,
            "stakeamount": stakeamount,
            "ordertype": "market"
        }

        return cls.post(
            base_url,
            "/api/v1/forceenter",
            payload
        )
