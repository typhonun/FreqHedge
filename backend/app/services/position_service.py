from .freqtrade_service import FreqtradeService
import time

from config.settings import (
    LONG_URL,
    SHORT_URL
)

position_cache = {
    "time": 0,
    "data": None
}


class PositionService:

    @staticmethod
    def get_open_positions():

        now = time.time()

        if (
                position_cache["data"]
                and now - position_cache["time"] < 5
        ):
            return position_cache["data"]

        data = {
            "long":
                FreqtradeService.get_status(
                    LONG_URL
                ),

            "short":
                FreqtradeService.get_status(
                    SHORT_URL
                )
        }

        position_cache["time"] = now
        position_cache["data"] = data

        return data

    @staticmethod
    def get_position_count():

        long_positions = FreqtradeService.get_status(LONG_URL)
        short_positions = FreqtradeService.get_status(SHORT_URL)

        return {
            "long": len(long_positions),
            "short": len(short_positions),
            "total": len(long_positions) + len(short_positions)
        }

    @staticmethod
    def get_account_summary():

        long_balance = FreqtradeService.get_balance(LONG_URL)
        short_balance = FreqtradeService.get_balance(SHORT_URL)

        long_available = 0
        short_available = 0

        long_total = 0
        short_total = 0

        for item in long_balance.get("currencies", []):

            if item["currency"] == "USDT":
                long_available = item["free"]
                long_total = item["balance"]

        for item in short_balance.get("currencies", []):

            if item["currency"] == "USDT":
                short_available = item["free"]
                short_total = item["balance"]

        return {

            "total_balance":
                round(long_total + short_total, 2),

            "long_available":
                round(long_available, 2),

            "short_available":
                round(short_available, 2)
        }

    @staticmethod
    def get_profit_summary():

        long_positions = FreqtradeService.get_status(LONG_URL)
        short_positions = FreqtradeService.get_status(SHORT_URL)

        long_profit = sum(
            trade.get("profit_abs") or 0
            for trade in long_positions
        )

        short_profit = sum(
            trade.get("profit_abs") or 0
            for trade in short_positions
        )

        return {
            "long_profit": round(long_profit, 2),
            "short_profit": round(short_profit, 2),
            "total_profit": round(
                long_profit + short_profit,
                2
            )
        }

    @staticmethod
    def get_floating_profit():

        long_positions = FreqtradeService.get_status(LONG_URL)
        short_positions = FreqtradeService.get_status(SHORT_URL)

        long_float = sum(
            trade.get("profit_abs", 0)
            for trade in long_positions
        )

        short_float = sum(
            trade.get("profit_abs", 0)
            for trade in short_positions
        )

        return {

            "long_float":
                round(long_float, 2),

            "short_float":
                round(short_float, 2),

            "total_float":
                round(
                    long_float + short_float,
                    2
                )
        }

    @staticmethod
    def get_closed_positions():

        long_resp = FreqtradeService.get_trades(
            LONG_URL
        )

        short_resp = FreqtradeService.get_trades(
            SHORT_URL
        )

        long_trades = (
            long_resp["trades"]
            if isinstance(long_resp, dict)
            else long_resp
        )

        short_trades = (
            short_resp["trades"]
            if isinstance(short_resp, dict)
            else short_resp
        )

        return {
            "long": [
                {
                    **t,
                    "side": "LONG"
                }
                for t in long_trades
                if not t.get("is_open", True)
            ],

            "short": [
                {
                    **t,
                    "side": "SHORT"
                }
                for t in short_trades
                if not t.get("is_open", True)
            ]
        }