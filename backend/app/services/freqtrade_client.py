import requests

from config.settings import *

class FreqtradeClient:

    @staticmethod
    def get(url):

        return requests.get(
            url,
            auth=(AUTH_USER, AUTH_PASSWORD)
        )

    @staticmethod
    def post(url, payload=None):

        return requests.post(
            url,
            json=payload,
            auth=(AUTH_USER, AUTH_PASSWORD)
        )