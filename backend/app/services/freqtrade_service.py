import requests

from config.settings import (
    LONG_URL,
    SHORT_URL,
    AUTH_USER,
    AUTH_PASSWORD
)


class FreqtradeService:

    auth = (AUTH_USER, AUTH_PASSWORD)

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