import requests

from config.settings import (
    AUTH_USER,
    AUTH_PASSWORD,
    LONG_URL,
    SHORT_URL
)


class FreqtradeClient:

    AUTH = (
        AUTH_USER,
        AUTH_PASSWORD
    )

    # =========================
    # GET
    # =========================

    @classmethod
    def get(cls, base_url, endpoint, params=None):

        r = requests.get(
            f"{base_url}{endpoint}",
            params=params,
            auth=cls.AUTH,
            timeout=10
        )

        r.raise_for_status()

        return r.json()

    # =========================
    # POST
    # =========================

    @classmethod
    def post(cls, base_url, endpoint, payload=None):

        r = requests.post(
            f"{base_url}{endpoint}",
            json=payload,
            auth=cls.AUTH,
            timeout=10
        )

        r.raise_for_status()

        return r.json()

    # =========================
    # 状态
    # =========================

    @classmethod
    def get_status(cls, url):

        return cls.get(
            url,
            "/api/v1/status"
        )

    # =========================
    # 余额
    # =========================

    @classmethod
    def get_balance(cls, url):

        return cls.get(
            url,
            "/api/v1/balance"
        )

    # =========================
    # 历史交易
    # =========================

    @classmethod
    def get_trades(cls, url):

        return cls.get(
            url,
            "/api/v1/trades"
        )

    # =========================
    # 启动
    # =========================

    @classmethod
    def start_bot(cls, url):

        return cls.post(
            url,
            "/api/v1/start"
        )

    # =========================
    # 停止
    # =========================

    @classmethod
    def stop_bot(cls, url):

        return cls.post(
            url,
            "/api/v1/stop"
        )

    # =========================
    # 停止入场
    # =========================

    @classmethod
    def stop_entry(cls, url):

        return cls.post(
            url,
            "/api/v1/stopentry"
        )

    # =========================
    # 开启入场
    # =========================

    @classmethod
    def start_entry(cls, url):

        return cls.post(
            url,
            "/api/v1/reload_config"
        )

    # =========================
    # 通用 command
    # =========================

    @classmethod
    def send_command(cls, url, command):

        return cls.post(
            url,
            f"/api/v1/{command}"
        )

    # =========================
    # Bot状态
    # =========================

    @classmethod
    def get_bot_state(cls, url):

        try:

            data = cls.get(
                url,
                "/api/v1/status"
            )

            if isinstance(data, dict):

                state = data.get("state")

                if state:
                    return state.upper()

            return "STOPPED"

        except Exception as e:

            print(
                "status error:",
                e
            )

            return "STOPPED"

    # =========================
    # 是否存活
    # =========================

    @classmethod
    def is_freqtrade_alive(cls, url):

        try:

            r = requests.get(
                f"{url}/api/v1/status",
                auth=cls.AUTH,
                timeout=3
            )

            return r.status_code == 200

        except Exception:

            return False

    # =========================
    # 白名单
    # =========================

    @classmethod
    def get_whitelist(cls, url):

        return cls.get(
            url,
            "/api/v1/whitelist"
        )

    # =========================
    # Force Entry
    # =========================

    @classmethod
    def force_enter(cls, side, pair, stakeamount):
        base_url = LONG_URL if side == "long" else SHORT_URL

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