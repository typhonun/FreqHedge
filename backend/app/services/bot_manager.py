from app.services.freqtrade_client import FreqtradeClient

from config.settings import (
    LONG_URL,
    SHORT_URL
)


class BotManager:

    @staticmethod
    def get_all_status():

        return {
            "long": FreqtradeClient.get_status(LONG_URL),
            "short": FreqtradeClient.get_status(SHORT_URL)
        }

    @staticmethod
    def get_all_balance():

        return {
            "long": FreqtradeClient.get_balance(LONG_URL),
            "short": FreqtradeClient.get_balance(SHORT_URL)
        }

    @staticmethod
    def start_all():

        return {
            "long": FreqtradeClient.start_bot(LONG_URL),
            "short": FreqtradeClient.start_bot(SHORT_URL)
        }

    @staticmethod
    def stop_all():

        return {
            "long": FreqtradeClient.stop_bot(LONG_URL),
            "short": FreqtradeClient.stop_bot(SHORT_URL)
        }