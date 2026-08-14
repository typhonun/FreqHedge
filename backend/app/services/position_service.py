from app.services.freqtrade_client import FreqtradeClient
import time

from config.settings import (
    LONG_URL,
    SHORT_URL
)

position_cache = {
    "time": 0,
    "data": None
}

closed_profit_cache = {
    "time": 0,
    "data": None
}
profit_history = []


class PositionService:

    # =========================================================
    # Freqtrade 返回数据统一解析
    # =========================================================

    @staticmethod
    def _extract_trades(data):

        if isinstance(data, list):
            return data

        if isinstance(data, dict):

            trades = data.get("trades")

            if isinstance(trades, list):
                return trades

        return []

    @staticmethod
    def _safe_get_status(url):

        try:

            if not FreqtradeClient.is_freqtrade_alive(url):
                return []

            return FreqtradeClient.get_status(url)

        except Exception as e:

            print(
                "get status error:",
                url,
                e
            )

            return []

    @staticmethod
    def _safe_get_trades(url):

        try:

            if not FreqtradeClient.is_freqtrade_alive(url):
                return []

            return FreqtradeClient.get_trades(url)

        except Exception as e:

            print(
                "get trades error:",
                url,
                e
            )

            return []

    # =========================================================
    # 当前持仓
    # =========================================================

    @staticmethod
    def get_open_positions():

        now = time.time()

        if (
                position_cache["data"]
                and
                now - position_cache["time"] < 5
        ):
            return position_cache["data"]

        long_resp = PositionService._safe_get_status(
            LONG_URL
        )

        short_resp = PositionService._safe_get_status(
            SHORT_URL
        )

        data = {

            "long":
                PositionService._extract_trades(
                    long_resp
                ),

            "short":
                PositionService._extract_trades(
                    short_resp
                )
        }

        position_cache["time"] = now
        position_cache["data"] = data

        return data

    # =========================================================
    # 持仓数量
    # =========================================================

    @staticmethod
    def get_position_count():

        long_resp = PositionService._safe_get_status(
            LONG_URL
        )

        short_resp = PositionService._safe_get_status(
            SHORT_URL
        )

        long_positions = PositionService._extract_trades(
            long_resp
        )

        short_positions = PositionService._extract_trades(
            short_resp
        )

        long_count = len(long_positions)
        short_count = len(short_positions)

        return {

            "long": long_count,

            "short": short_count,

            "total":
                long_count + short_count
        }

    # =========================================================
    # 账户余额
    # =========================================================

    @staticmethod
    def get_account_summary():

        try:
            long_balance = FreqtradeClient.get_balance(
                LONG_URL
            )
        except Exception:
            long_balance = {}

        try:
            short_balance = FreqtradeClient.get_balance(
                SHORT_URL
            )
        except Exception:
            short_balance = {}

        long_available = 0
        short_available = 0

        long_total = 0
        short_total = 0

        for item in long_balance.get(
                "currencies",
                []
        ):

            if item.get("currency") == "USDT":
                long_available = float(
                    item.get("free", 0) or 0
                )

                long_total = float(
                    item.get("balance", 0) or 0
                )

        for item in short_balance.get(
                "currencies",
                []
        ):

            if item.get("currency") == "USDT":
                short_available = float(
                    item.get("free", 0) or 0
                )

                short_total = float(
                    item.get("balance", 0) or 0
                )

        # 当前持仓

        long_positions = PositionService._extract_trades(
            PositionService._safe_get_status(
                LONG_URL
            )
        )

        short_positions = PositionService._extract_trades(
            PositionService._safe_get_status(
                SHORT_URL
            )
        )

        # 多头保证金

        long_margin = sum(
            float(
                trade.get(
                    "stake_amount",
                    0
                ) or 0
            )
            for trade in long_positions
        )

        # 空头保证金

        short_margin = sum(
            float(
                trade.get(
                    "stake_amount",
                    0
                ) or 0
            )
            for trade in short_positions
        )

        # 总保证金

        used_margin = (
                long_margin
                + short_margin
        )

        # 总资金

        total_balance = (
                long_total
                + short_total
        )

        # 可用资金

        available_balance = (
                total_balance
                - used_margin
        )

        return {

            "total_balance":
                round(total_balance, 2),

            "available_balance":
                round(available_balance, 2),

            "used_margin":
                round(used_margin, 2),

            "long_margin":
                round(long_margin, 2),

            "short_margin":
                round(short_margin, 2),

            "long_available":
                round(long_available, 2),

            "short_available":
                round(short_available, 2)
        }

    # =========================================================
    # 当前持仓利润
    # =========================================================

    @staticmethod
    def get_profit_summary():

        long_resp = PositionService._safe_get_status(
            LONG_URL
        )

        short_resp = PositionService._safe_get_status(
            SHORT_URL
        )

        long_positions = PositionService._extract_trades(
            long_resp
        )

        short_positions = PositionService._extract_trades(
            short_resp
        )

        long_profit = sum(
            float(
                trade.get(
                    "profit_abs",
                    0
                ) or 0
            )
            for trade in long_positions
        )

        short_profit = sum(
            float(
                trade.get(
                    "profit_abs",
                    0
                ) or 0
            )
            for trade in short_positions
        )

        return {

            "long_profit":
                round(
                    long_profit,
                    2
                ),

            "short_profit":
                round(
                    short_profit,
                    2
                ),

            "total_profit":
                round(
                    long_profit + short_profit,
                    2
                )
        }

    # =========================================================
    # 浮动利润
    # =========================================================

    @staticmethod
    def get_floating_profit():

        long_resp = PositionService._safe_get_status(
            LONG_URL
        )

        short_resp = PositionService._safe_get_status(
            SHORT_URL
        )

        long_positions = PositionService._extract_trades(
            long_resp
        )

        short_positions = PositionService._extract_trades(
            short_resp
        )

        long_float = sum(
            float(
                trade.get(
                    "profit_abs",
                    0
                ) or 0
            )
            for trade in long_positions
        )

        short_float = sum(
            float(
                trade.get(
                    "profit_abs",
                    0
                ) or 0
            )
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

    # =========================================================
    # 已关闭交易
    # =========================================================

    @staticmethod
    def get_closed_positions():

        long_resp = FreqtradeClient.get_trades(
            LONG_URL
        )

        short_resp = FreqtradeClient.get_trades(
            SHORT_URL
        )

        long_trades = PositionService._extract_trades(
            long_resp
        )

        short_trades = PositionService._extract_trades(
            short_resp
        )

        return {

            "long": [
                {
                    **trade,
                    "side": "LONG"
                }

                for trade in long_trades

                if not trade.get(
                    "is_open",
                    True
                )
            ],

            "short": [
                {
                    **trade,
                    "side": "SHORT"
                }

                for trade in short_trades

                if not trade.get(
                    "is_open",
                    True
                )
            ]
        }

    # =========================================================
    # 已关闭利润
    # =========================================================

    @staticmethod
    def get_closed_profit_summary():

        now = time.time()

        if (
                closed_profit_cache["data"]
                and
                now - closed_profit_cache["time"] < 30
        ):
            return closed_profit_cache["data"]

        long_resp = PositionService._safe_get_trades(
            LONG_URL
        )

        short_resp = PositionService._safe_get_trades(
            SHORT_URL
        )

        long_trades = PositionService._extract_trades(
            long_resp
        )

        short_trades = PositionService._extract_trades(
            short_resp
        )

        long_profit = 0.0
        short_profit = 0.0

        for trade in long_trades:

            if not trade.get(
                    "is_open",
                    True
            ):
                long_profit += float(
                    trade.get(
                        "close_profit_abs",
                        0
                    ) or 0
                )

        for trade in short_trades:

            if not trade.get(
                    "is_open",
                    True
            ):
                short_profit += float(
                    trade.get(
                        "close_profit_abs",
                        0
                    ) or 0
                )

        result = {

            "long_closed_profit":
                round(
                    long_profit,
                    2
                ),

            "short_closed_profit":
                round(
                    short_profit,
                    2
                ),

            "total_closed_profit":
                round(
                    long_profit + short_profit,
                    2
                )
        }

        closed_profit_cache["time"] = now
        closed_profit_cache["data"] = result

        return result

    # =========================================================
    # 总已关闭利润
    # =========================================================

    @staticmethod
    def get_closed_profit():

        result = PositionService.get_closed_profit_summary()

        return result[
            "total_closed_profit"
        ]

    # =========================================================
    # 累计收益
    # =========================================================

    @staticmethod
    def get_total_profit_summary():

        current_profit = (
            PositionService.get_profit_summary()
        )

        closed_profit = (
            PositionService.get_closed_profit_summary()
        )

        long_total = (
                current_profit["long_profit"]
                +
                closed_profit["long_closed_profit"]
        )

        short_total = (
                current_profit["short_profit"]
                +
                closed_profit["short_closed_profit"]
        )

        return {

            "long_total_profit":
                round(long_total, 2),

            "short_total_profit":
                round(short_total, 2),

            "total_profit":
                round(
                    long_total
                    +
                    short_total,
                    2
                ),

            "long_float":
                current_profit["long_profit"],

            "short_float":
                current_profit["short_profit"],

            "long_closed":
                closed_profit["long_closed_profit"],

            "short_closed":
                closed_profit["short_closed_profit"]
        }

    @staticmethod
    def get_profit_curve():

        global profit_history

        profit = (
            PositionService.get_total_profit_summary()
        )

        profit_history.append({

            "time": int(time.time()),

            "total_profit":
                profit["total_profit"],

            "long_profit":
                profit["long_total_profit"],

            "short_profit":
                profit["short_total_profit"]
        })

        if len(profit_history) > 500:
            profit_history = (
                profit_history[-500:]
            )

        return profit_history

    # =========================================================
    # 可开交易对
    # =========================================================

    @staticmethod
    def get_available_pairs(side: str):

        base_url = (
            LONG_URL
            if side == "long"
            else SHORT_URL
        )

        whitelist_resp = FreqtradeClient.get_whitelist(
            base_url
        )

        whitelist = whitelist_resp.get(
            "whitelist",
            []
        )

        positions = PositionService.get_open_positions()

        opened_pairs = {

            trade.get("pair")

            for trade in (
                    positions["long"]
                    +
                    positions["short"]
            )

            if trade.get("pair")
        }

        return [
            pair
            for pair in whitelist
            if pair not in opened_pairs
        ]

    # =========================================================
    # Force Entry
    # =========================================================

    @staticmethod
    def force_enter(
            side: str,
            pair: str,
            stakeamount: float
    ):

        return FreqtradeClient.force_enter(
            side,
            pair,
            stakeamount
        )

    # =========================================================
    # 所有当前持仓
    # =========================================================

    @staticmethod
    def get_all_positions():

        positions = PositionService.get_open_positions()

        result = []

        for trade in positions["long"]:
            trade = {
                **trade,
                "side": "LONG"
            }

            result.append(trade)

        for trade in positions["short"]:
            trade = {
                **trade,
                "side": "SHORT"
            }

            result.append(trade)

        return result

    # =========================================================
    # 单笔交易操作
    # =========================================================

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

        if action == "market_exit":

            payload = {
                "tradeid": trade_id
            }

            if amount is not None:
                payload["amount"] = amount

            return FreqtradeClient.post(
                base_url,
                "/api/v1/forceexit",
                payload
            )

        elif action == "limit_exit":

            payload = {
                "tradeid": trade_id,
                "ordertype": "limit",
                "rate": price
            }

            if amount is not None:
                payload["amount"] = amount

            return FreqtradeClient.post(
                base_url,
                "/api/v1/forceexit",
                payload
            )

        elif action == "increase":

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
                    if t.get("trade_id") == trade_id
                ),
                None
            )

            if not trade:
                raise Exception(
                    "Trade not found"
                )

            payload = {

                "pair":
                    trade["pair"],

                "side":
                    "long"
                    if side == "LONG"
                    else "short",

                "stakeamount":
                    amount,

                "ordertype":
                    "market"
            }

            return FreqtradeClient.post(
                base_url,
                "/api/v1/forceenter",
                payload
            )

        else:

            raise ValueError(
                f"Unsupported action: {action}"
            )

    # =========================================================
    # 全部平仓
    # =========================================================

    @staticmethod
    def close_all(side: str):

        positions = PositionService.get_open_positions()

        if side.lower() == "long":

            trades = positions["long"]
            trade_side = "LONG"

        elif side.lower() == "short":

            trades = positions["short"]
            trade_side = "SHORT"

        else:

            raise Exception(
                "invalid side"
            )

        results = []

        for trade in trades:

            trade_id = trade.get(
                "trade_id"
            )

            if not trade_id:
                continue

            try:

                result = PositionService.force_exit(
                    trade_id,
                    trade_side
                )

                results.append({

                    "trade_id":
                        trade_id,

                    "pair":
                        trade.get("pair"),

                    "success":
                        True,

                    "result":
                        result
                })

            except Exception as e:

                results.append({

                    "trade_id":
                        trade_id,

                    "pair":
                        trade.get("pair"),

                    "success":
                        False,

                    "error":
                        str(e)
                })

        return {

            "success":
                True,

            "side":
                side,

            "closed_count":
                len(results),

            "details":
                results
        }

    # =========================================================
    # 单笔平仓
    # =========================================================

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
