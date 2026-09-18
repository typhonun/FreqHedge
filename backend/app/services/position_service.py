from app.services.freqtrade_client import FreqtradeClient
import time
import sqlite3
import json
from pathlib import Path
from app.database import SessionLocal
from app.models.equity_history import EquityHistory
from app.models.profit_history import ProfitHistory
from app.core import runtime
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from config.settings import (
    LONG_URL,
    SHORT_URL
)

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "strategy.db"

snapshot_cache = {
    "time": 0,
    "data": None
}

last_good_data = {

    "long_balance": {},
    "short_balance": {},

    "long_status": [],
    "short_status": [],

    "long_trades": [],
    "short_trades": []
}


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
    def _safe_get_status(url, cache_key):

        try:

            if not FreqtradeClient.is_freqtrade_alive(url):
                raise Exception("bot offline")

            data = FreqtradeClient.get_status(url)

            if data:
                last_good_data[cache_key] = data

            return data

        except Exception as e:

            print(
                "get status error:",
                url,
                e
            )

            return last_good_data[cache_key]

    @staticmethod
    def _safe_get_trades(url, cache_key):

        try:

            if not FreqtradeClient.is_freqtrade_alive(url):
                raise Exception("bot offline")

            data = FreqtradeClient.get_trades(url)

            if data:
                last_good_data[cache_key] = data

            return data

        except Exception as e:

            print(
                "get trades error:",
                url,
                e
            )

            return last_good_data[cache_key]

    @staticmethod
    def _safe_get_balance(url, cache_key):

        try:

            if not FreqtradeClient.is_freqtrade_alive(url):
                raise Exception("bot offline")

            data = FreqtradeClient.get_balance(url)

            if data:
                last_good_data[cache_key] = data

            return data

        except Exception as e:

            print(
                "get balance error:",
                url,
                e
            )

            return last_good_data[cache_key]

    @staticmethod
    def get_snapshot(cache_seconds=5):

        now = time.time()

        if (
                snapshot_cache["data"]
                and
                now - snapshot_cache["time"] < cache_seconds
        ):
            return snapshot_cache["data"]

        with ThreadPoolExecutor(max_workers=6) as executor:
            long_balance_future = executor.submit(
                PositionService._safe_get_balance,
                LONG_URL,
                "long_balance"
            )

            short_balance_future = executor.submit(
                PositionService._safe_get_balance,
                SHORT_URL,
                "short_balance"
            )

            long_status_future = executor.submit(
                PositionService._safe_get_status,
                LONG_URL,
                "long_status"
            )

            short_status_future = executor.submit(
                PositionService._safe_get_status,
                SHORT_URL,
                "short_status"
            )

            long_trades_future = executor.submit(
                PositionService._safe_get_trades,
                LONG_URL,
                "long_trades"
            )

            short_trades_future = executor.submit(
                PositionService._safe_get_trades,
                SHORT_URL,
                "short_trades"
            )

            snapshot = {

                "long_balance":
                    long_balance_future.result(),

                "short_balance":
                    short_balance_future.result(),

                "long_status":
                    long_status_future.result(),

                "short_status":
                    short_status_future.result(),

                "long_trades":
                    long_trades_future.result(),

                "short_trades":
                    short_trades_future.result()

            }

        snapshot_cache["time"] = now
        snapshot_cache["data"] = snapshot

        return snapshot

    @staticmethod
    def _holding_minutes(open_date_str):

        try:

            open_time = datetime.fromisoformat(
                open_date_str
            )

            if open_time.tzinfo is None:
                open_time = open_time.replace(
                    tzinfo=timezone.utc
                )

            now = datetime.now(
                timezone.utc
            )

            return int(
                (now - open_time).total_seconds()
                / 60
            )

        except Exception as e:

            print(
                "holding_minutes error:",
                open_date_str,
                e
            )

            return 0

    @staticmethod
    def _get_roi_levels(side):

        conn = sqlite3.connect(
            str(DB_PATH)
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT config_json
            FROM strategy_config
            WHERE side=?
            """,
            (side,)
        )

        row = cursor.fetchone()

        conn.close()

        if not row:
            return []

        config = json.loads(
            row[0]
        )

        return (
            config
            .get("tp", {})
            .get("roi_levels", [])
        )

    @staticmethod
    def _current_roi(
            holding_minutes,
            roi_levels
    ):

        roi = 0

        levels = sorted(

            roi_levels,

            key=lambda x: x["minutes"]

        )

        for level in levels:

            if holding_minutes >= level["minutes"]:
                roi = level["roi"]

        return roi

    # =========================================================
    # 当前持仓
    # =========================================================

    @staticmethod
    def get_open_positions():

        snapshot = PositionService.get_snapshot()

        long_roi_levels = PositionService._get_roi_levels(
            "long"
        )

        short_roi_levels = PositionService._get_roi_levels(
            "short"
        )

        long_trades = PositionService._extract_trades(
            snapshot["long_status"]
        )

        short_trades = PositionService._extract_trades(
            snapshot["short_status"]
        )

        for trade in long_trades:
            holding_minutes = (
                PositionService._holding_minutes(
                    trade.get("open_date")
                )
            )

            trade["holding_minutes"] = holding_minutes

            trade["tp_roi"] = (
                PositionService._current_roi(
                    holding_minutes,
                    long_roi_levels
                )
            )

        for trade in short_trades:
            holding_minutes = (
                PositionService._holding_minutes(
                    trade.get("open_date")
                )
            )

            trade["holding_minutes"] = holding_minutes

            trade["tp_roi"] = (
                PositionService._current_roi(
                    holding_minutes,
                    short_roi_levels
                )
            )

        return {
            "long": long_trades,
            "short": short_trades
        }

    # =========================================================
    # 持仓数量
    # =========================================================

    @staticmethod
    def get_position_count():

        snapshot = PositionService.get_snapshot()

        long_positions = (
            PositionService._extract_trades(
                snapshot["long_status"]
            )
        )

        short_positions = (
            PositionService._extract_trades(
                snapshot["short_status"]
            )
        )

        return {
            "long": len(long_positions),
            "short": len(short_positions),
            "total": len(long_positions) + len(short_positions)
        }

    # =========================================================
    # 账户余额
    # =========================================================

    @staticmethod
    def get_account_summary(snapshot=None):

        if snapshot is None:
            snapshot = PositionService.get_snapshot()

        long_balance = snapshot["long_balance"]
        short_balance = snapshot["short_balance"]

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

        long_positions = (
            PositionService._extract_trades(
                snapshot["long_status"]
            )
        )

        short_positions = (
            PositionService._extract_trades(
                snapshot["short_status"]
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
    def get_profit_summary(snapshot=None):

        if snapshot is None:
            snapshot = PositionService.get_snapshot()

        long_positions = PositionService._extract_trades(snapshot["long_status"])
        short_positions = PositionService._extract_trades(snapshot["short_status"])

        long_float = sum(
            float(trade.get("profit_abs", 0) or 0)
            for trade in long_positions
        )

        short_float = sum(
            float(trade.get("profit_abs", 0) or 0)
            for trade in short_positions
        )

        # 当前历史全部已平仓
        closed = PositionService.get_closed_profit_summary(snapshot)

        # 本轮开始时已平仓（重启后 ROUND_INFO 可能是 None，兜底 0）
        start_long_closed = runtime.ROUND_INFO.get("start_long_closed")
        start_short_closed = runtime.ROUND_INFO.get("start_short_closed")

        if start_long_closed is None:
            start_long_closed = closed["long_closed_profit"]
        if start_short_closed is None:
            start_short_closed = closed["short_closed_profit"]

        # 本轮已平仓 = 当前 - 本轮基准
        long_closed_round = closed["long_closed_profit"] - start_long_closed
        short_closed_round = closed["short_closed_profit"] - start_short_closed

        # 本轮累计 = 浮盈 + 本轮已平仓
        long_round = long_float + long_closed_round
        short_round = short_float + short_closed_round

        return {
            # 本轮累计
            "long_profit": round(long_round, 2),
            "short_profit": round(short_round, 2),
            "total_profit": round(long_round + short_round, 2),

            # 浮盈
            "long_float": round(long_float, 2),
            "short_float": round(short_float, 2),

            # 本轮已平仓
            "long_closed": round(long_closed_round, 2),
            "short_closed": round(short_closed_round, 2),

            # 新增
            "global_tp_count": runtime.ROUND_INFO.get("global_tp_count", 0),
            "global_sl_count": runtime.ROUND_INFO.get("global_sl_count", 0),
        }

    # =========================================================
    # 浮动利润
    # =========================================================

    @staticmethod
    def get_floating_profit(snapshot=None):

        if snapshot is None:
            snapshot = PositionService.get_snapshot()

        long_positions = PositionService._extract_trades(snapshot["long_status"])
        short_positions = PositionService._extract_trades(snapshot["short_status"])

        long_float = 0.0
        short_float = 0.0

        for trade in long_positions:
            profit = trade.get("profit_abs")

            if profit is None:
                try:
                    open_rate = float(trade.get("open_rate", 0) or 0)
                    current_rate = float(trade.get("current_rate", 0) or 0)
                    amount = abs(float(trade.get("amount", 0) or 0))
                    profit = (current_rate - open_rate) * amount
                except Exception:
                    profit = 0.0

            long_float += float(profit or 0)

        for trade in short_positions:
            profit = trade.get("profit_abs")

            if profit is None:
                try:
                    open_rate = float(trade.get("open_rate", 0) or 0)
                    current_rate = float(trade.get("current_rate", 0) or 0)
                    amount = abs(float(trade.get("amount", 0) or 0))
                    profit = (open_rate - current_rate) * amount
                except Exception:
                    profit = 0.0

            short_float += float(profit or 0)

        return {
            "long_float": round(long_float, 2),
            "short_float": round(short_float, 2),
            "total_float": round(long_float + short_float, 2)
        }

    # =========================================================
    # 已关闭交易
    # =========================================================

    @staticmethod
    def get_closed_positions():

        snapshot = PositionService.get_snapshot()

        long_trades = PositionService._extract_trades(snapshot["long_trades"])
        short_trades = PositionService._extract_trades(snapshot["short_trades"])

        def enrich(trade, side):
            trade = {**trade, "side": side}

            trade_id = trade.get("trade_id")

            # 覆盖 exit_reason
            if trade_id in runtime.GLOBAL_EXIT_REASONS:
                trade["exit_reason"] = runtime.GLOBAL_EXIT_REASONS[trade_id]

            return trade

        return {
            "long": [
                enrich(trade, "LONG")
                for trade in long_trades
                if not trade.get("is_open", True)
            ],
            "short": [
                enrich(trade, "SHORT")
                for trade in short_trades
                if not trade.get("is_open", True)
            ]
        }

    # =========================================================
    # 已关闭利润
    # =========================================================

    @staticmethod
    def get_closed_profit_summary(snapshot=None):

        if snapshot is None:
            snapshot = PositionService.get_snapshot()

        long_trades = PositionService._extract_trades(snapshot["long_trades"])
        short_trades = PositionService._extract_trades(snapshot["short_trades"])

        long_status = PositionService._extract_trades(snapshot["long_status"])
        short_status = PositionService._extract_trades(snapshot["short_status"])

        # 用 status 的 realized_profit（当前持仓，包括部分平仓）
        long_open_realized = sum(
            float(t.get("realized_profit", 0) or 0)
            for t in long_status
        )
        short_open_realized = sum(
            float(t.get("realized_profit", 0) or 0)
            for t in short_status
        )

        # 用 trades 的 close_profit_abs（完全平仓）
        long_closed = sum(
            float(t.get("close_profit_abs", 0) or 0)
            for t in long_trades
            if not t.get("is_open", True)
        )
        short_closed = sum(
            float(t.get("close_profit_abs", 0) or 0)
            for t in short_trades
            if not t.get("is_open", True)
        )

        long_profit = long_open_realized + long_closed
        short_profit = short_open_realized + short_closed

        return {
            "long_closed_profit": round(long_profit, 2),
            "short_closed_profit": round(short_profit, 2),
            "total_closed_profit": round(long_profit + short_profit, 2)
        }

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
    def get_total_profit_summary(snapshot=None):

        if snapshot is None:
            snapshot = PositionService.get_snapshot()

        current_profit = (
            PositionService.get_profit_summary(
                snapshot
            )
        )

        closed_profit = (
            PositionService.get_closed_profit_summary(
                snapshot
            )
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
    def record_metrics():

        db = SessionLocal()

        try:

            snapshot = PositionService.get_snapshot(
                cache_seconds=0
            )

            summary = (
                PositionService.get_account_summary(
                    snapshot
                )
            )

            floating = (
                PositionService.get_floating_profit(
                    snapshot
                )
            )

            profit = (
                PositionService.get_total_profit_summary(
                    snapshot
                )
            )

            now = int(time.time())

            wallet = summary["total_balance"]

            floating_profit = (
                floating["total_float"]
            )

            equity = (
                    wallet
                    + floating_profit
            )

            equity_record = EquityHistory(

                timestamp=now,

                equity=round(
                    equity,
                    2
                ),

                wallet=round(
                    wallet,
                    2
                ),

                profit=round(
                    floating_profit,
                    2
                )
            )

            profit_record = ProfitHistory(

                timestamp=now,

                total_profit=round(
                    profit["total_profit"],
                    2
                ),

                long_profit=round(
                    profit["long_total_profit"],
                    2
                ),

                short_profit=round(
                    profit["short_total_profit"],
                    2
                )
            )

            db.add(equity_record)
            db.add(profit_record)

            db.commit()

            print(
                f"[Metrics] "
                f"equity={equity:.2f} "
                f"profit={profit['total_profit']:.2f}"
            )

        except Exception as e:

            db.rollback()

            print(
                "record metrics error:",
                e
            )

        finally:

            db.close()

    @staticmethod
    def collect_account_snapshot():

        snapshot = PositionService.get_snapshot()

        summary = (
            PositionService.get_account_summary(
                snapshot
            )
        )

        floating = (
            PositionService.get_floating_profit(
                snapshot
            )
        )

        total_profit = (
            PositionService.get_total_profit_summary(
                snapshot
            )
        )

        return {

            "summary": summary,

            "floating": floating,

            "profit": total_profit

        }

    @staticmethod
    def get_balance_curve(period="1D"):

        db = SessionLocal()

        try:

            now = int(time.time())

            start_time = (
                    now -
                    PositionService._period_seconds(period)
            )

            records = (

                db.query(
                    EquityHistory
                )

                .filter(
                    EquityHistory.timestamp >= start_time
                )

                .order_by(
                    EquityHistory.timestamp.asc()
                )

                .all()

            )

            step = PositionService._sampling_step(
                period
            )

            records = records[::step]

            return [

                {
                    "time": record.timestamp,
                    "balance": record.equity,
                    "wallet": record.wallet,
                    "profit": record.profit
                }

                for record in records
            ]

        finally:

            db.close()

    @staticmethod
    def get_profit_curve(
            period="1D"
    ):

        db = SessionLocal()

        try:

            now = int(time.time())

            start_time = (
                    now
                    -
                    PositionService._period_seconds(
                        period
                    )
            )

            records = (

                db.query(
                    ProfitHistory
                )

                .filter(
                    ProfitHistory.timestamp >= start_time
                )

                .order_by(
                    ProfitHistory.timestamp.asc()
                )

                .all()

            )

            step = PositionService._sampling_step(
                period
            )

            records = records[::step]

            return [

                {
                    "time":
                        record.timestamp,

                    "total_profit":
                        record.total_profit,

                    "long_profit":
                        record.long_profit,

                    "short_profit":
                        record.short_profit
                }

                for record in records
            ]

        finally:

            db.close()

    @staticmethod
    def _sampling_step(period):

        mapping = {

            "1D": 1,

            "7D": 5,

            "30D": 15,

            "90D": 60

        }

        return mapping.get(period, 1)

    @staticmethod
    def _period_seconds(period: str):

        mapping = {

            "1D": 86400,

            "7D": 86400 * 7,

            "30D": 86400 * 30,

            "90D": 86400 * 90

        }

        return mapping.get(
            period,
            86400
        )

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
