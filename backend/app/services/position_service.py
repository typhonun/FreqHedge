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

    @staticmethod
    def trade_action(
            trade_id: int,
            side: str,
            action: str,
            amount: float = None,
            price: float = None
    ):

        base_url = (
            LONG_URL
            if side == "LONG"
            else SHORT_URL
        )

        # ===================
        # 市价退出
        # ===================

        if action == "market_exit":

            payload = {
                "tradeid": trade_id
            }

            if amount:
                payload["amount"] = amount

            return FreqtradeService.post(
                base_url,
                "/api/v1/forceexit",
                payload
            )

        # ===================
        # 限价退出
        # ===================

        elif action == "limit_exit":

            payload = {
                "tradeid": trade_id,
                "ordertype": "limit",
                "rate": price
            }

            if amount:
                payload["amount"] = amount

            return FreqtradeService.post(
                base_url,
                "/api/v1/forceexit",
                payload
            )

        # ===================
        # 加仓
        # ===================

        elif action == "increase":

            endpoint = "/api/v1/forceenter"

            positions = PositionService.get_open_positions()

            trades = (

                positions["long"]

                if side == "LONG"

                else positions["short"]

            )

            trade = next(

                (

                    t

                    for t in trades

                    if t["trade_id"] == trade_id

                ),

                None

            )

            if not trade:
                raise Exception("Trade not found")

            payload = {

                "pair": trade["pair"],

                "side": "long" if side == "LONG" else "short",

                "stakeamount": amount,

                "ordertype": "market"

            }

            return FreqtradeService.post(

                base_url,

                endpoint,

                payload

            )

    @staticmethod
    def get_available_pairs(side: str):

        base_url = (
            LONG_URL
            if side == "long"
            else SHORT_URL
        )

        whitelist_resp = FreqtradeService.get_whitelist(
            base_url
        )

        whitelist = whitelist_resp.get(
            "whitelist",
            []
        )

        positions = PositionService.get_open_positions()

        opened_pairs = {

            trade["pair"]

            for trade in (
                positions["long"]
                + positions["short"]
            )
        }

        return [

            pair

            for pair in whitelist

            if pair not in opened_pairs
        ]

    @staticmethod
    def force_enter(
            side: str,
            pair: str,
            stakeamount: float
    ):

        return FreqtradeService.force_enter(
            side,
            pair,
            stakeamount
        )

    @staticmethod
    def get_closed_profit():

        closed = PositionService.get_closed_positions()
        if closed["long"]:
            print(closed["long"][0])
            
        total = 0

        for trade in closed["long"]:
            total += trade.get(
                "close_profit_abs",
                0
            )

        for trade in closed["short"]:
            total += trade.get(
                "close_profit_abs",
                0
            )

        return round(total, 2)

    @staticmethod
    def get_all_positions():

        positions = \
            PositionService.get_open_positions()

        result = []

        for trade in positions["long"]:
            trade["side"] = "LONG"

            result.append(trade)

        for trade in positions["short"]:
            trade["side"] = "SHORT"

            result.append(trade)

        return result

    @staticmethod
    def force_exit(
            trade_id,
            side
    ):

        return PositionService.trade_action(
            trade_id=trade_id,
            side=side,
            action="market_exit"
        )