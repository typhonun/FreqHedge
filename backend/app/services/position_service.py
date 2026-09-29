# backend/app/services/position_service.py
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
from app.services.bot_manager import BotManager
from config.settings import LONG_URL, SHORT_URL  # 保留作为兜底

from app.services.bot_runtime import (
    get_bot_url,
    get_bot_db_path,
    get_enabled_sides,
    list_running_bots,
    list_all_bots,
)

# =========================================================
# 缓存
# =========================================================

# 单 bot 的 snapshot 缓存： key = f"{bot_id}:{cache_seconds_group}"
_snapshot_cache = {}  # {bot_id: {"time": ts, "data": snapshot}}
_snapshot_all_cache = {"time": 0, "data": None}

_last_good_data = {}  # {(bot_id, side, kind): data}
_custom_data_cache = {}  # {(bot_id, side): {"time": ts, "data": {}}}

CUSTOM_DATA_CACHE_SECONDS = 3
SNAPSHOT_CACHE_SECONDS = 5


def _empty_snapshot():
    return {
        "long_balance": {},
        "short_balance": {},
        "long_status": [],
        "short_status": [],
        "long_trades": [],
        "short_trades": [],
    }


def _default_for(kind):
    if kind == "balance":
        return {}
    return []


class PositionService:

    # =========================================================
    # 底层：单 bot 拉数据（带缓存 + 兜底）
    # =========================================================

    @staticmethod
    def _extract_trades(data):
        if isinstance(data, list):
            return list(data)  # shallow copy
        if isinstance(data, dict):
            trades = data.get("trades")
            if isinstance(trades, list):
                return list(trades)
        return []

    @staticmethod
    def _fetch_one(bot_id: int, side: str, kind: str):
        """
        kind ∈ {"balance", "status", "trades"}
        带 last_good 兜底
        """
        key = (bot_id, side, kind)

        try:
            url = get_bot_url(bot_id, side)
            if not FreqtradeClient.is_freqtrade_alive(url):
                raise Exception("bot offline")

            if kind == "balance":
                data = FreqtradeClient.get_balance(url)
            elif kind == "status":
                data = FreqtradeClient.get_status(url)
            elif kind == "trades":
                data = FreqtradeClient.get_trades(url)
            else:
                raise ValueError(f"unknown kind {kind}")

            if data:
                _last_good_data[key] = data
            return data

        except Exception as e:
            print(f"[position] fetch error bot={bot_id} side={side} kind={kind}: {e}")
            return _last_good_data.get(key, _default_for(kind))

    @staticmethod
    def _build_snapshot_single(bot_id: int) -> dict:

        bot = BotManager.get(bot_id)
        if not bot:
            return _empty_snapshot()

        snap = _empty_snapshot()
        sides = get_enabled_sides(bot)

        tasks = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            for side in sides:
                for kind in ("balance", "status", "trades"):
                    tasks.append(
                        (side, kind, executor.submit(PositionService._fetch_one, bot_id, side, kind))
                    )

            for side, kind, future in tasks:
                snap[f"{side}_{kind}"] = future.result()

        return snap

    # =========================================================
    # 对外：snapshot
    # =========================================================

    @staticmethod
    def get_snapshot(bot_id: int | None = None, cache_seconds: int = SNAPSHOT_CACHE_SECONDS):
        """
        bot_id = None → 聚合所有 running bot
        bot_id = N   → 只拉这个 bot
        """
        now = time.time()

        if bot_id is not None:
            cached = _snapshot_cache.get(bot_id)
            if cached and now - cached["time"] < cache_seconds:
                return cached["data"]

            snap = PositionService._build_snapshot_single(bot_id)
            _snapshot_cache[bot_id] = {"time": now, "data": snap}
            return snap

        # 聚合模式
        if (
                _snapshot_all_cache["data"]
                and now - _snapshot_all_cache["time"] < cache_seconds
        ):
            return _snapshot_all_cache["data"]

        agg = _empty_snapshot()
        bots = list_running_bots()
        for bot in bots:
            snap = PositionService.get_snapshot(bot_id=bot["id"], cache_seconds=cache_seconds)

            for side in ("long", "short"):
                status_list = PositionService._extract_trades(snap.get(f"{side}_status"))
                trades_list = PositionService._extract_trades(snap.get(f"{side}_trades"))

                for t in status_list:
                    t.setdefault("bot_id", bot["id"])
                for t in trades_list:
                    t.setdefault("bot_id", bot["id"])

                agg[f"{side}_balance"] = PositionService._merge_balance(
                    agg[f"{side}_balance"],
                    snap.get(f"{side}_balance") or {},
                )
                agg[f"{side}_status"].extend(status_list)
                agg[f"{side}_trades"].extend(trades_list)

        _snapshot_all_cache["time"] = now
        _snapshot_all_cache["data"] = agg
        return agg

    @staticmethod
    def _merge_balance(acc: dict, incoming: dict) -> dict:
        """把两个 balance dict 的 currencies 累加"""
        if not incoming:
            return acc
        if not acc:
            return json.loads(json.dumps(incoming))  # deep copy

        acc_cur = {c["currency"]: c for c in acc.get("currencies", [])}
        for c in incoming.get("currencies", []):
            code = c["currency"]
            if code in acc_cur:
                acc_cur[code]["free"] = float(acc_cur[code].get("free", 0) or 0) + float(c.get("free", 0) or 0)
                acc_cur[code]["balance"] = float(acc_cur[code].get("balance", 0) or 0) + float(c.get("balance", 0) or 0)
                acc_cur[code]["used"] = float(acc_cur[code].get("used", 0) or 0) + float(c.get("used", 0) or 0)
            else:
                acc_cur[code] = json.loads(json.dumps(c))

        acc["currencies"] = list(acc_cur.values())
        return acc

    # =========================================================
    # ROI levels：从 bots 表读
    # =========================================================

    @staticmethod
    def _get_roi_levels(bot_id: int, side: str):

        bot = BotManager.get(bot_id)
        if not bot:
            return []

        cfg = bot.get(f"{side}Config") or {}
        if not isinstance(cfg, dict):
            return []

        return (cfg.get("tp", {}) or {}).get("roi_levels", []) or []

    @staticmethod
    def _current_roi(holding_minutes, roi_levels):
        """根据持仓分钟数，从 roi_levels 里挑出当前档位对应的 roi(%)"""
        roi = 0
        for level in sorted(roi_levels, key=lambda x: x.get("minutes", 0)):
            if holding_minutes >= level.get("minutes", 0):
                roi = level.get("roi", 0)
        return roi
    
    # =========================================================
    # 时间计算
    # =========================================================

    @staticmethod
    def _holding_minutes(open_date_str):
        try:
            open_time = datetime.fromisoformat(open_date_str)
            if open_time.tzinfo is None:
                open_time = open_time.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return int((now - open_time).total_seconds() / 60)
        except Exception as e:
            print("holding_minutes error:", open_date_str, e)
            return 0

    @staticmethod
    def _holding_minutes_from_ts(ts):
        try:
            if ts is None:
                return 0
            if isinstance(ts, (int, float)):
                ts = float(ts)
                if ts > 1e12:
                    ts = ts / 1000.0
                open_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                open_time = datetime.fromisoformat(str(ts))
                if open_time.tzinfo is None:
                    open_time = open_time.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return int((now - open_time).total_seconds() / 60)
        except Exception as e:
            print("holding_minutes_from_ts error:", ts, e)
            return 0

    # =========================================================
    # 当前持仓（支持 bot_id）
    # =========================================================

    @staticmethod
    def get_open_positions(bot_id: int | None = None):
        if bot_id is None:
            # 聚合
            all_long, all_short = [], []
            for bot in list_running_bots():
                pos = PositionService.get_open_positions(bot_id=bot["id"])
                for t in pos["long"]:
                    t.setdefault("bot_id", bot["id"])
                for t in pos["short"]:
                    t.setdefault("bot_id", bot["id"])
                all_long.extend(pos["long"])
                all_short.extend(pos["short"])
            return {"long": all_long, "short": all_short}

        snapshot = PositionService.get_snapshot(bot_id=bot_id)

        long_roi_levels = PositionService._get_roi_levels(bot_id, "long")
        short_roi_levels = PositionService._get_roi_levels(bot_id, "short")

        long_trades = PositionService._extract_trades(snapshot["long_status"])
        short_trades = PositionService._extract_trades(snapshot["short_status"])

        # 从 sqlite 补 last_tp_time
        long_custom = PositionService._load_custom_data(
            [t.get("trade_id") for t in long_trades if t.get("trade_id")],
            get_bot_db_path(bot_id, "long"),
            cache_key=(bot_id, "long"),
        )
        short_custom = PositionService._load_custom_data(
            [t.get("trade_id") for t in short_trades if t.get("trade_id")],
            get_bot_db_path(bot_id, "short"),
            cache_key=(bot_id, "short"),
        )

        def _attach(trades, custom_map):
            for t in trades:
                tid = t.get("trade_id")
                c = custom_map.get(tid, {})
                if c.get("last_tp_time"):
                    t["last_tp_time"] = c["last_tp_time"]

        _attach(long_trades, long_custom)
        _attach(short_trades, short_custom)

        def _pick_base_ts(trade):
            last_tp = trade.get("last_tp_time")
            if last_tp:
                try:
                    return float(last_tp)
                except Exception:
                    pass
            ts = trade.get("open_timestamp") or trade.get("open_fill_timestamp")
            if ts:
                try:
                    return float(ts)
                except Exception:
                    pass
            return trade.get("open_date")

        def _enrich(trades, roi_levels):
            for t in trades:
                base_ts = _pick_base_ts(t)
                round_minutes = (
                    PositionService._holding_minutes_from_ts(base_ts)
                    if base_ts and not isinstance(base_ts, str)
                    else PositionService._holding_minutes(base_ts)
                )
                total_minutes = PositionService._holding_minutes(t.get("open_date"))
                t["holding_minutes"] = total_minutes
                t["round_minutes"] = round_minutes
                t["tp_roi"] = PositionService._current_roi(round_minutes, roi_levels)
                t.setdefault("bot_id", bot_id)

        _enrich(long_trades, long_roi_levels)
        _enrich(short_trades, short_roi_levels)

        return {"long": long_trades, "short": short_trades}

    @staticmethod
    def _load_custom_data(trade_ids, db_path, cache_key=None):
        if not trade_ids or not db_path:
            return {}

        if cache_key:
            cache = _custom_data_cache.get(cache_key)
            if cache and time.time() - cache["time"] < CUSTOM_DATA_CACHE_SECONDS:
                cached = cache["data"]
                return {tid: cached.get(tid, {}) for tid in trade_ids}

        result = {tid: {} for tid in trade_ids}

        try:
            conn = sqlite3.connect(db_path, timeout=5)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            placeholders = ",".join("?" * len(trade_ids))
            cur.execute(
                f"SELECT ft_trade_id, cd_key, cd_type, cd_value "
                f"FROM trade_custom_data WHERE ft_trade_id IN ({placeholders})",
                list(trade_ids),
            )
            for row in cur.fetchall():
                tid = row["ft_trade_id"]
                key = row["cd_key"]
                ctype = row["cd_type"]
                raw = row["cd_value"]
                if raw is None:
                    continue
                result.setdefault(tid, {})[key] = PositionService._decode_custom_value(ctype, raw)
            conn.close()
        except Exception as e:
            print("[PositionService] load custom_data error:", e)

        if cache_key:
            _custom_data_cache[cache_key] = {"time": time.time(), "data": result}

        return result

    @staticmethod
    def _decode_custom_value(ctype, raw):
        try:
            if ctype == "int":
                return int(float(raw))
            if ctype == "float":
                return float(raw)
            if ctype == "bool":
                return str(raw).lower() in ("1", "true", "t", "yes", "y")
            if ctype in ("json", "dict", "list"):
                return json.loads(raw)
            if ctype == "str":
                return raw
        except Exception:
            pass
        try:
            return json.loads(raw)
        except Exception:
            return raw

    # =========================================================
    # 计数 / 余额 / 利润
    # =========================================================

    @staticmethod
    def get_position_count(bot_id: int | None = None):
        if bot_id is None:
            all_positions = PositionService.get_all_positions()
            long_cnt = sum(1 for p in all_positions if p.get("side") == "LONG")
            short_cnt = sum(1 for p in all_positions if p.get("side") == "SHORT")
            return {"long": long_cnt, "short": short_cnt, "total": long_cnt + short_cnt}

        snapshot = PositionService.get_snapshot(bot_id=bot_id)
        long_positions = PositionService._extract_trades(snapshot["long_status"])
        short_positions = PositionService._extract_trades(snapshot["short_status"])
        return {
            "long": len(long_positions),
            "short": len(short_positions),
            "total": len(long_positions) + len(short_positions),
        }

    @staticmethod
    def get_account_summary(snapshot=None, bot_id: int | None = None):
        if snapshot is None:
            snapshot = PositionService.get_snapshot(bot_id=bot_id)

        long_balance = snapshot["long_balance"]
        short_balance = snapshot["short_balance"]

        long_available = short_available = 0.0
        long_total = short_total = 0.0

        for item in long_balance.get("currencies", []):
            if item.get("currency") == "USDT":
                long_available = float(item.get("free", 0) or 0)
                long_total = float(item.get("balance", 0) or 0)

        for item in short_balance.get("currencies", []):
            if item.get("currency") == "USDT":
                short_available = float(item.get("free", 0) or 0)
                short_total = float(item.get("balance", 0) or 0)

        long_positions = PositionService._extract_trades(snapshot["long_status"])
        short_positions = PositionService._extract_trades(snapshot["short_status"])

        long_margin = sum(float(t.get("stake_amount", 0) or 0) for t in long_positions)
        short_margin = sum(float(t.get("stake_amount", 0) or 0) for t in short_positions)

        used_margin = long_margin + short_margin
        total_balance = long_total + short_total
        available_balance = total_balance - used_margin

        return {
            "total_balance": round(total_balance, 2),
            "available_balance": round(available_balance, 2),
            "used_margin": round(used_margin, 2),
            "long_margin": round(long_margin, 2),
            "short_margin": round(short_margin, 2),
            "long_available": round(long_available, 2),
            "short_available": round(short_available, 2),
        }

    @staticmethod
    def get_floating_profit(snapshot=None, long_positions=None, short_positions=None, bot_id: int | None = None):
        if snapshot is None:
            snapshot = PositionService.get_snapshot(bot_id=bot_id)
        if long_positions is None:
            long_positions = PositionService._extract_trades(snapshot["long_status"])
        if short_positions is None:
            short_positions = PositionService._extract_trades(snapshot["short_status"])

        long_float = 0.0
        for t in long_positions:
            p = t.get("profit_abs")
            if p is None:
                try:
                    p = (float(t.get("current_rate", 0)) - float(t.get("open_rate", 0))) * abs(
                        float(t.get("amount", 0)))
                except Exception:
                    p = 0.0
            long_float += float(p or 0)

        short_float = 0.0
        for t in short_positions:
            p = t.get("profit_abs")
            if p is None:
                try:
                    p = (float(t.get("open_rate", 0)) - float(t.get("current_rate", 0))) * abs(
                        float(t.get("amount", 0)))
                except Exception:
                    p = 0.0
            short_float += float(p or 0)

        return {
            "long_float": round(long_float, 2),
            "short_float": round(short_float, 2),
            "total_float": round(long_float + short_float, 2),
        }

    @staticmethod
    def get_closed_profit_summary(snapshot=None, long_trades=None, short_trades=None,
                                  long_status=None, short_status=None, bot_id: int | None = None):
        if snapshot is None:
            snapshot = PositionService.get_snapshot(bot_id=bot_id)
        if long_trades is None:
            long_trades = PositionService._extract_trades(snapshot["long_trades"])
        if short_trades is None:
            short_trades = PositionService._extract_trades(snapshot["short_trades"])
        if long_status is None:
            long_status = PositionService._extract_trades(snapshot["long_status"])
        if short_status is None:
            short_status = PositionService._extract_trades(snapshot["short_status"])

        long_open_realized = sum(float(t.get("realized_profit", 0) or 0) for t in long_status)
        short_open_realized = sum(float(t.get("realized_profit", 0) or 0) for t in short_status)

        long_closed = sum(
            float(t.get("close_profit_abs", 0) or 0) for t in long_trades if not t.get("is_open", True)
        )
        short_closed = sum(
            float(t.get("close_profit_abs", 0) or 0) for t in short_trades if not t.get("is_open", True)
        )

        long_profit = long_open_realized + long_closed
        short_profit = short_open_realized + short_closed

        return {
            "long_closed_profit": round(long_profit, 2),
            "short_closed_profit": round(short_profit, 2),
            "total_closed_profit": round(long_profit + short_profit, 2),
        }

    @staticmethod
    def get_closed_profit(bot_id: int | None = None):
        return PositionService.get_closed_profit_summary(bot_id=bot_id)["total_closed_profit"]

    @staticmethod
    def get_total_profit_summary(snapshot=None, bot_id: int | None = None):
        if snapshot is None:
            snapshot = PositionService.get_snapshot(bot_id=bot_id)

        current = PositionService.get_profit_summary(snapshot, bot_id=bot_id)
        closed = PositionService.get_closed_profit_summary(snapshot, bot_id=bot_id)

        long_total = current["long_float"] + closed["long_closed_profit"]
        short_total = current["short_float"] + closed["short_closed_profit"]

        return {
            "long_total_profit": round(long_total, 2),
            "short_total_profit": round(short_total, 2),
            "total_profit": round(long_total + short_total, 2),
            "long_float": current["long_float"],
            "short_float": current["short_float"],
            "long_closed": closed["long_closed_profit"],
            "short_closed": closed["short_closed_profit"],
        }

    @staticmethod
    def get_profit_summary(snapshot=None, bot_id: int | None = None):
        if snapshot is None:
            snapshot = PositionService.get_snapshot(bot_id=bot_id)

        long_positions = PositionService._extract_trades(snapshot["long_status"])
        short_positions = PositionService._extract_trades(snapshot["short_status"])
        long_trades = PositionService._extract_trades(snapshot["long_trades"])
        short_trades = PositionService._extract_trades(snapshot["short_trades"])

        long_float = sum(float(t.get("profit_abs", 0) or 0) for t in long_positions)
        short_float = sum(float(t.get("profit_abs", 0) or 0) for t in short_positions)

        closed = PositionService.get_closed_profit_summary(
            snapshot,
            long_trades=long_trades,
            short_trades=short_trades,
            long_status=long_positions,
            short_status=short_positions,
        )

        if bot_id is not None:
            info = runtime.ROUND_INFO_BY_BOT.get(bot_id) or {}
            start_long_closed = info.get("start_long_closed")
            start_short_closed = info.get("start_short_closed")
            start_balance = info.get("start_balance") or 0.0
            tp_count = info.get("global_tp_count", 0)
            sl_count = info.get("global_sl_count", 0)
        else:
            start_long_closed = runtime.ROUND_INFO.get("start_long_closed")
            start_short_closed = runtime.ROUND_INFO.get("start_short_closed")
            start_balance = runtime.ROUND_INFO.get("start_balance") or 0.0
            tp_count = runtime.ROUND_INFO.get("global_tp_count", 0)
            sl_count = runtime.ROUND_INFO.get("global_sl_count", 0)

        if start_long_closed is None:
            start_long_closed = closed["long_closed_profit"]
        if start_short_closed is None:
            start_short_closed = closed["short_closed_profit"]

        long_closed_round = closed["long_closed_profit"] - start_long_closed
        short_closed_round = closed["short_closed_profit"] - start_short_closed

        long_round = long_float + long_closed_round
        short_round = short_float + short_closed_round
        total_round = long_round + short_round

        if start_balance:
            round_ratio = total_round / start_balance * 100
            long_ratio = long_round / start_balance * 100
            short_ratio = short_round / start_balance * 100
        else:
            round_ratio = long_ratio = short_ratio = 0.0

        return {
            "long_profit": round(long_round, 2),
            "short_profit": round(short_round, 2),
            "total_profit": round(total_round, 2),
            "long_float": round(long_float, 2),
            "short_float": round(short_float, 2),
            "long_closed": round(long_closed_round, 2),
            "short_closed": round(short_closed_round, 2),
            "round_ratio": round(round_ratio, 2),
            "long_ratio": round(long_ratio, 2),
            "short_ratio": round(short_ratio, 2),
            "position_count": {
                "long": len(long_positions),
                "short": len(short_positions),
                "total": len(long_positions) + len(short_positions),
            },
            "global_tp_count": tp_count,
            "global_sl_count": sl_count,
        }

    # =========================================================
    # 已关闭交易
    # =========================================================

    @staticmethod
    def get_closed_positions(bot_id: int | None = None):
        if bot_id is None:
            all_long, all_short = [], []
            for bot in list_running_bots():
                pos = PositionService.get_closed_positions(bot_id=bot["id"])
                for t in pos["long"]:
                    t.setdefault("bot_id", bot["id"])
                for t in pos["short"]:
                    t.setdefault("bot_id", bot["id"])
                all_long.extend(pos["long"])
                all_short.extend(pos["short"])
            return {"long": all_long, "short": all_short}

        snapshot = PositionService.get_snapshot(bot_id=bot_id)
        long_trades = PositionService._extract_trades(snapshot["long_trades"])
        short_trades = PositionService._extract_trades(snapshot["short_trades"])

        def enrich(trade, side):
            trade = {**trade, "side": side, "bot_id": bot_id}
            tid = trade.get("trade_id")
            if tid in runtime.GLOBAL_EXIT_REASONS:
                trade["exit_reason"] = runtime.GLOBAL_EXIT_REASONS[tid]
            return trade

        return {
            "long": [enrich(t, "LONG") for t in long_trades if not t.get("is_open", True)],
            "short": [enrich(t, "SHORT") for t in short_trades if not t.get("is_open", True)],
        }

    # =========================================================
    # 所有持仓
    # =========================================================

    @staticmethod
    def get_all_positions(bot_id: int | None = None):
        positions = PositionService.get_open_positions(bot_id=bot_id)
        result = []
        for t in positions["long"]:
            result.append({**t, "side": "LONG"})
        for t in positions["short"]:
            result.append({**t, "side": "SHORT"})
        return result

    # =========================================================
    # Force entry / exit
    # =========================================================

    @staticmethod
    def get_available_pairs(side: str, bot_id: int | None = None):
        if bot_id is None:
            # 聚合：从所有 running bot 里取
            all_pairs = set()
            opened = {
                p.get("pair")
                for p in PositionService.get_all_positions()
                if p.get("pair")
            }
            for bot in list_running_bots():
                if side == "long" and not bot.get("enableLong"):
                    continue
                if side == "short" and not bot.get("enableShort"):
                    continue
                try:
                    url = get_bot_url(bot["id"], side)
                    resp = FreqtradeClient.get_whitelist(url)
                    all_pairs.update(resp.get("whitelist", []))
                except Exception:
                    continue
            return [p for p in all_pairs if p not in opened]

        url = get_bot_url(bot_id, side)
        resp = FreqtradeClient.get_whitelist(url)
        whitelist = resp.get("whitelist", [])

        positions = PositionService.get_open_positions(bot_id=bot_id)
        opened = {
            t.get("pair")
            for t in (positions["long"] + positions["short"])
            if t.get("pair")
        }
        return [p for p in whitelist if p not in opened]

    @staticmethod
    def force_enter(side: str, pair: str, stakeamount: float, bot_id: int | None = None):
        if bot_id is None:
            raise ValueError("force_enter 需要指定 bot_id")

        url = get_bot_url(bot_id, side)
        payload = {
            "pair": pair,
            "side": side,
            "stakeamount": stakeamount,
            "ordertype": "market",
        }
        return FreqtradeClient.post(url, "/api/v1/forceenter", payload)

    @staticmethod
    def trade_action(trade_id: int, side: str, action: str, amount: float = None,
                     price: float = None, bot_id: int | None = None):
        if bot_id is None:
            # 尝试从所有 running bot 里找
            for bot in list_running_bots():
                try:
                    return PositionService.trade_action(
                        trade_id, side, action, amount, price, bot_id=bot["id"]
                    )
                except Exception:
                    continue
            raise ValueError("trade_id 未匹配到任何 bot")

        url = get_bot_url(bot_id, side.lower())

        if action == "market_exit":
            payload = {"tradeid": trade_id}
            if amount is not None:
                payload["amount"] = amount
            return FreqtradeClient.post(url, "/api/v1/forceexit", payload)

        if action == "limit_exit":
            payload = {"tradeid": trade_id, "ordertype": "limit", "rate": price}
            if amount is not None:
                payload["amount"] = amount
            return FreqtradeClient.post(url, "/api/v1/forceexit", payload)

        if action == "increase":
            positions = PositionService.get_open_positions(bot_id=bot_id)
            trades = positions["long"] if side.upper() == "LONG" else positions["short"]
            trade = next((t for t in trades if t.get("trade_id") == trade_id), None)
            if not trade:
                raise Exception("Trade not found")
            payload = {
                "pair": trade["pair"],
                "side": "long" if side.upper() == "LONG" else "short",
                "stakeamount": amount,
                "ordertype": "market",
            }
            return FreqtradeClient.post(url, "/api/v1/forceenter", payload)

        raise ValueError(f"Unsupported action: {action}")

    @staticmethod
    def close_all(side: str, bot_id: int | None = None):
        if bot_id is None:
            results = []
            for bot in list_running_bots():
                res = PositionService.close_all(side, bot_id=bot["id"])
                results.extend(res.get("details", []))
            return {"success": True, "side": side, "closed_count": len(results), "details": results}

        positions = PositionService.get_open_positions(bot_id=bot_id)
        trades = positions["long"] if side.lower() == "long" else positions["short"]
        trade_side = "LONG" if side.lower() == "long" else "SHORT"

        results = []
        for t in trades:
            tid = t.get("trade_id")
            if not tid:
                continue
            try:
                r = PositionService.force_exit(tid, trade_side, bot_id=bot_id)
                results.append({"trade_id": tid, "pair": t.get("pair"), "success": True, "result": r})
            except Exception as e:
                results.append({"trade_id": tid, "pair": t.get("pair"), "success": False, "error": str(e)})

        return {"success": True, "side": side, "closed_count": len(results), "details": results}

    @staticmethod
    def force_exit(trade_id, side, bot_id: int | None = None):
        return PositionService.trade_action(
            trade_id=trade_id, side=side, action="market_exit", bot_id=bot_id
        )

    # =========================================================
    # 曲线（历史数据，保持全局）
    # =========================================================

    @staticmethod
    def record_metrics():
        db = SessionLocal()
        try:
            snapshot = PositionService.get_snapshot(cache_seconds=0)
            summary = PositionService.get_account_summary(snapshot)
            floating = PositionService.get_floating_profit(snapshot)
            profit = PositionService.get_total_profit_summary(snapshot)

            now = int(time.time())
            wallet = summary["total_balance"]
            fp = floating["total_float"]
            equity = wallet + fp

            db.add(EquityHistory(timestamp=now, equity=round(equity, 2),
                                 wallet=round(wallet, 2), profit=round(fp, 2)))
            db.add(ProfitHistory(timestamp=now,
                                 total_profit=round(profit["total_profit"], 2),
                                 long_profit=round(profit["long_total_profit"], 2),
                                 short_profit=round(profit["short_total_profit"], 2)))
            db.commit()
            print(f"[Metrics] equity={equity:.2f} profit={profit['total_profit']:.2f}")
        except Exception as e:
            db.rollback()
            print("record metrics error:", e)
        finally:
            db.close()

    @staticmethod
    def get_balance_curve(period="1D"):
        db = SessionLocal()
        try:
            now = int(time.time())
            start_time = now - PositionService._period_seconds(period)
            records = (
                db.query(EquityHistory)
                .filter(EquityHistory.timestamp >= start_time)
                .order_by(EquityHistory.timestamp.asc())
                .all()
            )
            step = PositionService._sampling_step(period)
            records = records[::step]
            return [
                {"time": r.timestamp, "balance": r.equity, "wallet": r.wallet, "profit": r.profit}
                for r in records
            ]
        finally:
            db.close()

    @staticmethod
    def get_profit_curve(period="1D"):
        db = SessionLocal()
        try:
            now = int(time.time())
            start_time = now - PositionService._period_seconds(period)
            records = (
                db.query(ProfitHistory)
                .filter(ProfitHistory.timestamp >= start_time)
                .order_by(ProfitHistory.timestamp.asc())
                .all()
            )
            step = PositionService._sampling_step(period)
            records = records[::step]
            return [
                {"time": r.timestamp, "total_profit": r.total_profit,
                 "long_profit": r.long_profit, "short_profit": r.short_profit}
                for r in records
            ]
        finally:
            db.close()

    @staticmethod
    def _sampling_step(period):
        return {"1D": 1, "7D": 5, "30D": 15, "90D": 60}.get(period, 1)

    @staticmethod
    def _period_seconds(period: str):
        return {"1D": 86400, "7D": 86400 * 7, "30D": 86400 * 30, "90D": 86400 * 90}.get(period, 86400)

    @staticmethod
    def collect_account_snapshot(bot_id: int | None = None):
        snapshot = PositionService.get_snapshot(bot_id=bot_id)
        return {
            "summary": PositionService.get_account_summary(snapshot),
            "floating": PositionService.get_floating_profit(snapshot),
            "profit": PositionService.get_total_profit_summary(snapshot),
        }
