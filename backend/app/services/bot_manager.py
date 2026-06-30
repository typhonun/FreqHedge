from .freqtrade_service import FreqtradeService

from config.settings import (
    LONG_URL,
    SHORT_URL
)


class BotManager:

    @staticmethod
    def get_all_status():

        return {
            "long": FreqtradeService.get_status(LONG_URL),
            "short": FreqtradeService.get_status(SHORT_URL)
        }

    @staticmethod
    def get_all_balance():

        return {
            "long": FreqtradeService.get_balance(LONG_URL),
            "short": FreqtradeService.get_balance(SHORT_URL)
        }

    @staticmethod
    def start_all():

        return {
            "long": FreqtradeService.start_bot(LONG_URL),
            "short": FreqtradeService.start_bot(SHORT_URL)
        }

    @staticmethod
    def stop_all():

        return {
            "long": FreqtradeService.stop_bot(LONG_URL),
            "short": FreqtradeService.stop_bot(SHORT_URL)
        }