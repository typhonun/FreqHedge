# freqtrade/user_data/strategies/GridBotBase.py
"""
网格机器人基类（动态锚点版 - 彻底修复滑点重启导致的网格脱节）
"""

import sys
import json
import bisect
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
from pandas import DataFrame

USER_DATA_DIR = Path(__file__).resolve().parents[1]
if str(USER_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(USER_DATA_DIR))

from freqtrade.persistence import Trade
from DcaTpBotBase import DcaTpBotBase

import logging

logger = logging.getLogger(__name__)

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"
GRID_TAG = f"{CYAN}[Grid]{RESET}"


class GridBotBase(DcaTpBotBase):
    can_short = False
    use_exit_signal = True
    trailing_stop = False
    position_adjustment_enable = True
    use_custom_stoploss = False

    @property
    def timeframe(self) -> str:
        cfg = self.get_runtime_config() or {}
        tf = str(cfg.get("timeframe", "1m")).lower()
        return tf if tf else "1m"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.position_adjustment_enable = True

        self._last_candle_str = {}
        self._pending_reduce = {}  # {trade_id: set([idx1, idx2])}
        self._pending_add = {}  # {trade_id: {"idx": list, "timestamp": float}}

    def bot_start(self, **kwargs) -> None:
        ft_cfg = self.config or {}
        dry_run_wallet = ft_cfg.get("dry_run_wallet", 0)
        leverage = ft_cfg.get("leverage", 1)
        g = self._grid_cfg()
        dir_cn = "空头" if self._is_short else "多头"
        logger.info(
            f"\n==================== {dir_cn}网格配置概览 ====================\n"
            f"初始资金          : {dry_run_wallet} USDT\n"
            f"持仓杠杆          : {leverage}x\n"
            f"价格区间          : [{self._cfg_float(g, 'lower_price', 0.0)}, {self._cfg_float(g, 'upper_price', 0.0)}]\n"
            f"网格数量          : {self._cfg_int(g, 'grid_count', 0)} 格\n"
            f"触发周期          : {self.timeframe} 收盘价\n"
            f"======================================================"
        )

    # ============================================================
    # 工具函数
    # ============================================================
    def get_runtime_config(self):
        custom = (self.config or {}).get("custom_params", {}) or {}
        if custom.get("config"): return custom["config"]
        if custom.get("gridConfig"): return custom["gridConfig"]
        if custom.get("grid"): return custom["grid"]
        try:
            from core.config_manager import ConfigManager
            return ConfigManager.get("grid") or {}
        except Exception:
            return {}

    def _grid_cfg(self):
        cfg = self.get_runtime_config() or {}
        return self._cfg(cfg, "grid", default={}) or {}

    def _amount_mode(self) -> str:
        cfg = self.get_runtime_config() or {}
        mode = str(cfg.get("amount_mode", "amount")).lower()
        return mode if mode in ("amount", "percent") else "amount"

    def _get_candle_str(self, current_time) -> str:
        tf = str(self.timeframe or "1m").lower().strip()
        try:
            value = int(tf[:-1])
            unit = tf[-1]
            seconds = value * {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}[unit]
            epoch = int(current_time.timestamp())
            aligned = epoch - (epoch % seconds)
            return datetime.fromtimestamp(aligned, tz=current_time.tzinfo).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return current_time.strftime("%Y-%m-%d %H:%M")

    def _order_filled_quantity(self, order) -> float:
        for attr in ("safe_filled", "filled"):
            try:
                value = getattr(order, attr, None)
                if callable(value): value = value()
                if value is not None and float(value) > 0: return abs(float(value))
            except Exception:
                pass
        try:
            return abs(float(getattr(order, "amount", 0) or 0))
        except Exception:
            return 0.0

    def _build_grid_levels(self):
        g = self._grid_cfg()
        upper = self._cfg_float(g, "upper_price", 0.0)
        lower = self._cfg_float(g, "lower_price", 0.0)
        count = self._cfg_int(g, "grid_count", 0)
        algo = str(g.get("spacing_algo", "arithmetic")).lower()

        if upper <= 0 or lower <= 0 or count <= 0 or upper <= lower: return []
        if algo == "geometric":
            ratio = (upper / lower) ** (1.0 / count)
            return [lower * (ratio ** i) for i in range(count + 1)]
        step = (upper - lower) / count
        return [lower + step * i for i in range(count + 1)]

    # ★ 新增：动态获取网格步长
    def _get_grid_step(self) -> float:
        g = self._grid_cfg()
        upper = self._cfg_float(g, "upper_price", 0.0)
        lower = self._cfg_float(g, "lower_price", 0.0)
        count = self._cfg_int(g, "grid_count", 0)
        algo = str(g.get("spacing_algo", "arithmetic")).lower()
        if count <= 0 or upper <= lower or lower <= 0:
            return 0.0
        if algo == "geometric":
            # 等比取第一格间距作为近似基准
            ratio = (upper / lower) ** (1.0 / count)
            return lower * (ratio - 1.0)
        return (upper - lower) / count

    # ★ 重写：基于动态开仓价计算止盈价
    def _grid_tp_price(self, entry_price: float) -> float:
        step = self._get_grid_step()
        if step <= 0 or entry_price <= 0:
            return 0.0
        if self._is_short:
            return entry_price - step
        else:
            return entry_price + step

    @property
    def _is_short(self) -> bool:
        return bool(self.can_short)

    @property
    def _entry_order_side(self) -> str:
        return "sell" if self._is_short else "buy"

    @property
    def _exit_order_side(self) -> str:
        return "buy" if self._is_short else "sell"

    # ============================================================
    # 入场信号
    # ============================================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        col_long = "enter_long"
        col_short = "enter_short"
        if col_long not in dataframe.columns: dataframe[col_long] = 0
        if col_short not in dataframe.columns: dataframe[col_short] = 0

        dataframe[col_long] = 0
        dataframe[col_short] = 0

        g = self._grid_cfg()
        upper = self._cfg_float(g, "upper_price", 0.0)
        lower = self._cfg_float(g, "lower_price", 0.0)
        start_mode = str(g.get("start_mode", "grid")).lower()
        trigger_price = self._cfg_float(g, "trigger_price", 0.0)

        if upper <= 0 or lower <= 0 or upper <= lower: return dataframe
        levels = self._build_grid_levels()
        if not levels: return dataframe

        if start_mode == "trigger" and trigger_price > 0:
            prev_close = dataframe['close'].shift(1)
            if self._is_short:
                cross_up = (prev_close < trigger_price) & (dataframe['close'] >= trigger_price)
                dataframe.loc[cross_up, col_short] = 1
                dataframe.loc[cross_up, "enter_tag"] = "grid_trigger"
            else:
                cross_down = (prev_close > trigger_price) & (dataframe['close'] <= trigger_price)
                dataframe.loc[cross_down, col_long] = 1
                dataframe.loc[cross_down, "enter_tag"] = "grid_trigger"
            return dataframe

        if start_mode == "immediate":
            in_range = (dataframe['close'] >= lower) & (dataframe['close'] <= upper)
            if self._is_short:
                dataframe.loc[in_range, col_short] = 1
                dataframe.loc[in_range, "enter_tag"] = "grid_immediate"
            else:
                dataframe.loc[in_range, col_long] = 1
                dataframe.loc[in_range, "enter_tag"] = "grid_immediate"
            return dataframe

        close_arr = dataframe['close'].values
        idx_now = np.searchsorted(levels, close_arr, side='right') - 1
        idx_now = np.clip(idx_now, 0, len(levels) - 2)
        idx_prev = np.roll(idx_now, 1)
        idx_prev[0] = idx_now[0]

        if self._is_short:
            trigger_mask = (idx_now > idx_prev)
            dataframe.loc[trigger_mask, col_short] = 1
            dataframe.loc[trigger_mask, "enter_tag"] = "grid_line"
        else:
            trigger_mask = (idx_now < idx_prev)
            dataframe.loc[trigger_mask, col_long] = 1
            dataframe.loc[trigger_mask, "enter_tag"] = "grid_line"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self._is_short:
            dataframe['exit_short'] = 0
        else:
            dataframe['exit_long'] = 0
        return dataframe

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side,
                            **kwargs):
        try:
            candle_str = self._get_candle_str(current_time)
            if self._last_candle_str.get(pair) == candle_str: return False

            g = self._grid_cfg()
            upper = self._cfg_float(g, "upper_price", 0.0)
            lower = self._cfg_float(g, "lower_price", 0.0)
            if upper <= 0 or lower <= 0: return False

            try:
                open_count = len(list(Trade.get_trades_proxy(pair=pair, is_open=True)))
            except Exception:
                open_count = 0
            if open_count > 0: return False

            # immediate 也必须遵守绝对网格上下沿
            if rate < lower or rate > upper:
                return False

            self._last_candle_str[pair] = candle_str
            return True
        except Exception:
            return False

    # ============================================================
    # 核心：加仓 / 减仓（基于动态锚点）
    # ============================================================
    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            g = self._grid_cfg()
            if not self._get_bool(trade, "grid_n_initialized", False): return None

            if getattr(trade, "has_open_orders", False): return None

            candle_str = self._get_candle_str(current_time)
            if self._last_candle_str.get(trade.pair) == candle_str: return None

            df, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            if df is None or df.empty: return None
            close_price = float(df.iloc[-1]['close'])
            if close_price <= 0 or pd.isna(close_price) or np.isinf(close_price): return None

            try:
                live_rate = float(current_rate or 0.0)
                if np.isfinite(live_rate) and live_rate > 0:
                    close_price = max(close_price, live_rate) if not self._is_short else min(close_price, live_rate)
            except (TypeError, ValueError):
                pass

            entry_candle = self._get(trade, "grid_entry_candle", None)
            if entry_candle == candle_str:
                return None
            guard_until = self._get_int(trade, "grid_entry_guard_until", 0)
            if guard_until > 0 and current_time.timestamp() < guard_until:
                return None

            positions = self._get_grid_positions(trade)

            try:
                actual_amount = float(getattr(trade, "amount", 0) or 0)
                if actual_amount <= 0:
                    self._set_grid_positions(trade, {})
                    self._pending_reduce.pop(trade.id, None)
                    return None
            except (TypeError, ValueError):
                return None

            try:
                lev = float(self.leverage(trade.pair) or 1.0)
            except Exception:
                lev = 1.0

            if not positions:
                cleanup_stake = (actual_amount * close_price) / lev if lev > 0 else 0.0
                if cleanup_stake > 0 and np.isfinite(cleanup_stake):
                    self._last_candle_str[trade.pair] = candle_str
                    self._set(trade, "grid_pending_reduce", [])
                    return -float(cleanup_stake), "grid_reduce_cleanup"

                restart = bool(g.get("restart_after_all_tp", False))
                if restart:
                    if self._get_bool(trade, "grid_stopped", False):
                        return None

                    if not self._get_bool(trade, "grid_allow_restart", False):
                        return None

                    if self._last_candle_str.get(trade.pair) == candle_str:
                        return None
                    if getattr(trade, "has_open_orders", False):
                        return None

                    buy_usdt = self._calc_grid_amount(trade, close_price)
                    if buy_usdt <= 0 or pd.isna(buy_usdt) or np.isinf(buy_usdt):
                        return None

                    logger.info(
                        f"{GRID_TAG} {RED}▲ 触发全部平仓后重启(立即开首仓){RESET} | "
                        f"{trade.pair} | 价格={close_price:.4f} | 保证金={buy_usdt:.2f}"
                    )

                    self._last_candle_str[trade.pair] = candle_str
                    self._pending_add = getattr(self, "_pending_add", {})

                    # 用时间戳作为新首仓的唯一 ID
                    new_idx = int(current_time.timestamp())
                    self._pending_add[trade.id] = {
                        "idx": [new_idx],
                        "timestamp": current_time.timestamp(),
                    }
                    self._set(
                        trade,
                        "grid_pending_add",
                        json.dumps(self._pending_add[trade.id], allow_nan=False),
                    )
                    self._set(trade, "grid_allow_restart", False)

                    return float(buy_usdt), f"grid_add_multi_{new_idx}"

                return None

            # ---- 1) 检查止盈（动态计算）----
            to_close = []
            pending_reduce_set = self._pending_reduce.get(trade.id)
            if pending_reduce_set is None:
                raw_pending = self._get(trade, "grid_pending_reduce", [])
                if isinstance(raw_pending, str):
                    try:
                        raw_pending = json.loads(raw_pending)
                    except (TypeError, ValueError):
                        raw_pending = []
                try:
                    pending_reduce_set = {int(x) for x in (raw_pending or [])}
                except (TypeError, ValueError):
                    pending_reduce_set = set()

            # Freqtrade can reject a partial exit before creating an order when
            # exchange precision leaves a remainder below the minimum stake.
            # There is then no cancellation callback to clear this in-memory/
            # persisted marker, so recover it on the next adjustment cycle.
            if pending_reduce_set:
                logger.warning(
                    f"{GRID_TAG} 清理无订单的遗留减仓状态 | pending={sorted(pending_reduce_set)}"
                )
                pending_reduce_set.clear()
                self._pending_reduce.pop(trade.id, None)
                self._set(trade, "grid_pending_reduce", [])

            for k, v in positions.items():
                try:
                    idx = int(k)
                    if idx in pending_reduce_set:
                        continue

                    entry = float(v.get("entry", 0.0))
                    if entry <= 0 or pd.isna(entry) or np.isinf(entry): continue

                    # ★ 基于开仓价计算止盈价
                    tp_price = self._grid_tp_price(entry)
                    if tp_price <= 0: continue

                    if self._is_short:
                        if close_price <= tp_price: to_close.append((idx, entry, v))
                    else:
                        if close_price >= tp_price: to_close.append((idx, entry, v))
                except Exception:
                    pass

            if to_close:
                total_margin = 0.0
                total_pnl = 0.0
                closed = []
                for idx, entry, v in to_close:
                    qty = float(v.get("qty", 0.0))
                    margin = (entry * qty) / lev if lev > 0 else 0.0
                    pnl = (entry - close_price) * qty if self._is_short else (close_price - entry) * qty
                    if pd.isna(margin) or np.isinf(margin): margin = 0.0
                    if pd.isna(pnl) or np.isinf(pnl): pnl = 0.0
                    total_margin += margin
                    total_pnl += pnl
                    closed.append((idx, entry, qty, margin, pnl))

                if total_margin <= 0 or not np.isfinite(total_margin):
                    return None

                # ★★★ 核心修复：检查本次减仓是否满足交易所最小下单量 ★★★
                requested_qty = sum(item[2] for item in closed)
                min_qty = 0.001
                try:
                    market = self.dp.market(trade.pair)
                    if market and market.get("limits", {}).get("amount", {}).get("min"):
                        min_qty = float(market["limits"]["amount"]["min"])
                except Exception:
                    pass

                if requested_qty < min_qty:
                    logger.warning(
                        f"{GRID_TAG} 减仓数量 {requested_qty:.6f} 低于交易所最小限制 {min_qty:.6f}，"
                        f"将强制全平所有剩余网格，防止尾仓残留在交易所！"
                    )
                    # 清空所有本地仓位记录
                    self._set_grid_positions(trade, {})
                    self._pending_reduce.pop(trade.id, None)
                    self._set(trade, "grid_pending_reduce", [])

                    # 返回全平指令（使用当前 trade 的 stake_amount 作为金额）
                    full_close_stake = float(getattr(trade, "stake_amount", 0) or total_margin)
                    if full_close_stake <= 0 or not np.isfinite(full_close_stake):
                        return None

                    return -full_close_stake, f"grid_reduce_multi_{len(positions)}"

                # 正常流程
                pending_reduce_set.update([idx for idx, _, _, _, _ in closed])
                self._pending_reduce[trade.id] = pending_reduce_set
                self._set(trade, "grid_pending_reduce", sorted(pending_reduce_set))
                self._log_reduce(trade, close_price, closed, total_margin, total_pnl)
                self._log_state_detail(trade, close_price)

                return -float(total_margin), f"grid_reduce_multi_{len(closed)}"

            # ---- 2) 检查加仓（动态计算）----
            pending_add = getattr(self, "_pending_add", {}).get(trade.id)
            if pending_add is None:
                raw_pending_add = self._get(trade, "grid_pending_add", None)
                if isinstance(raw_pending_add, str):
                    try:
                        raw_pending_add = json.loads(raw_pending_add)
                    except (TypeError, ValueError):
                        raw_pending_add = None
                pending_add = raw_pending_add

            if pending_add:
                try:
                    ts = float(pending_add.get("timestamp", 0) or 0) \
                        if isinstance(pending_add, dict) else 0.0
                except (TypeError, ValueError):
                    ts = 0.0
                add_timeout = self._cfg_int(g, "pending_add_timeout", 300)
                if ts <= 0 or (current_time.timestamp() - ts) > add_timeout:
                    logger.warning(f"{GRID_TAG} pending_add 超时释放")
                    self._pending_add.pop(trade.id, None)
                    self._set(trade, "grid_pending_add", None)
                else:
                    return None

            max_grids = self._cfg_int(g, "max_open_grids", self._cfg_int(g, "grid_count", 20))
            grid_count = self._cfg_int(g, "grid_count", 20)
            # 强制不超过网格总数（防止历史/外部配置越界）
            if grid_count > 0:
                max_grids = max(1, min(max_grids, grid_count))
            if len(positions) >= max_grids:
                return None

            step = self._get_grid_step()
            if step <= 0:
                return None

            # 找出最边缘的 entry
            all_entries = [float(v.get("entry", 0)) for v in positions.values() if "entry" in v]
            if not all_entries: return None

            should_add = False
            if not self._is_short:
                # 做多：跌破最低开仓价 - step
                lowest_entry = min(all_entries)
                if close_price <= (lowest_entry - step):
                    should_add = True
            else:
                # 做空：突破最高开仓价 + step
                highest_entry = max(all_entries)
                if close_price >= (highest_entry + step):
                    should_add = True

            if not should_add:
                return None

            buy_usdt_per = self._calc_grid_amount(trade, close_price)
            if buy_usdt_per <= 0 or pd.isna(buy_usdt_per) or np.isinf(buy_usdt_per):
                return None

            # 可用余额保护
            available = self._available_stake()
            if available > 0 and buy_usdt_per > available * 0.8:
                logger.warning(f"{GRID_TAG} 可用余额不足补格 | 需要={buy_usdt_per:.2f} | 可用={available:.2f}")
                return None

            add_qty = (buy_usdt_per * lev) / close_price if close_price > 0 else 0
            if add_qty <= 0 or not np.isfinite(add_qty):
                return None

            # ★ 用时间戳作为新加仓的唯一 ID
            new_idx = int(current_time.timestamp())
            logger.info(
                f"{GRID_TAG} {RED}▲ 触发线加仓{RESET} | "
                f"{trade.pair} | 价格={close_price:.4f} | 保证金={buy_usdt_per:.2f}"
            )

            self._last_candle_str[trade.pair] = candle_str
            self._pending_add = getattr(self, "_pending_add", {})
            self._pending_add[trade.id] = {
                "idx": [new_idx],
                "timestamp": current_time.timestamp(),
            }
            self._set(
                trade,
                "grid_pending_add",
                json.dumps(self._pending_add[trade.id], allow_nan=False),
            )
            return float(buy_usdt_per), f"grid_add_multi_{new_idx}"

        except Exception:
            logger.exception(f"{GRID_TAG} adjust_trade_position 异常")
            return None

    # ============================================================
    # 订单成交回调
    # ============================================================
    def order_filled(self, pair, trade, order, current_time, **kwargs):
        try:
            super().order_filled(pair, trade, order, current_time, **kwargs)
        except Exception:
            pass

        try:
            if order.ft_order_side not in (self._entry_order_side, self._exit_order_side): return
            reason = str(getattr(order, "ft_order_tag", None) or getattr(order, "ft_order_reason", None) or "")
            entry_price = float(getattr(order, "average", None) or trade.open_rate or 0.0)
            qty = self._order_filled_quantity(order)

            try:
                lev = float(self.leverage(trade.pair) or 1.0)
            except Exception:
                lev = 1.0
            margin = (entry_price * qty) / lev if lev > 0 else 0.0
            candle_str = self._get_candle_str(current_time)

            # ---- A. 首仓成交 ----
            if not self._get_bool(trade, "grid_n_initialized", False) and order.ft_order_side == self._entry_order_side:
                # 由于是动态网格，用时间戳作为首仓 ID
                idx = int(current_time.timestamp())

                positions = self._get_grid_positions(trade)
                positions[str(int(idx))] = {"entry": entry_price, "qty": qty}
                self._set_grid_positions(trade, positions)
                self._set(trade, "grid_n_initialized", True)
                self._clear_bot_grid_pending_level(trade.pair)
                self._set(trade, "grid_entry_candle", candle_str)
                self._set(
                    trade,
                    "grid_entry_guard_until",
                    self._safe_int(current_time.timestamp()) + max(
                        self._cfg_int(self._grid_cfg(), "cooldown_seconds", 60),
                        60,
                    ),
                )
                self._set(trade, "grid_pending_add", None)
                self._set(trade, "grid_pending_reduce", [])
                self._set(trade, "grid_allow_restart", False)

                self._record_chart_marker(
                    event_type="grid_entry", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time, message=f"网格首仓 价格{entry_price:.4f}",
                    candle_time=current_time
                )
                logger.info(f"[STRATEGY] [ENTRY] {GRID_TAG} ▶ 首仓成交 | 价格={entry_price:.4f}")
                return

            # ---- B. 加仓成交 ----
            if reason.startswith("grid_add_lv") or reason.startswith("grid_add_multi_"):
                try:
                    if reason.startswith("grid_add_lv"):
                        idx_list = [int(reason[len("grid_add_lv"):])]
                    else:
                        tail = reason[len("grid_add_multi_"):]
                        idx_list = [int(x) for x in tail.split(",") if x != ""]
                except Exception:
                    logger.error(f"{GRID_TAG} 无法解析加仓 reason={reason}")
                    return
                if not idx_list: return
                if qty <= 0 or entry_price <= 0 or not np.isfinite(qty) or not np.isfinite(entry_price):
                    return

                per_qty = qty / len(idx_list)
                for i in idx_list:
                    self._add_grid_position(trade, i, entry_price, per_qty)

                self._pending_add.pop(trade.id, None)
                self._set(trade, "grid_pending_add", None)

                grid_str = ",".join([str(i) for i in idx_list])
                self._record_chart_marker(
                    event_type="grid_add",  # ✅ 改回加仓
                    pair=pair,
                    trade_id=trade.id,
                    side=self._side_str,
                    price=entry_price,      # ✅ 加仓用 entry_price
                    amount=margin,
                    current_time=current_time,
                    message=f"网格加仓 价格{entry_price:.2f}", # ✅ 文案改回加仓
                    candle_time=current_time
                )
                logger.info(
                    f"[STRATEGY] [ADD] {GRID_TAG} ▲ 真实加仓成交 | 价格={entry_price:.4f} | "
                    f"金额={margin:.2f} | ID={idx_list} | 每格qty={per_qty:.6f}"
                )

            # ---- C. 减仓成交 ----
            elif reason.startswith("grid_reduce_multi"):
                pending_reduce_set = self._pending_reduce.pop(trade.id, set())
                filled_price = entry_price

                positions = self._get_grid_positions(trade)
                for idx in pending_reduce_set:
                    positions.pop(str(int(idx)), None)
                self._set_grid_positions(trade, positions)
                self._set(trade, "grid_pending_reduce", [])
                self._pending_reduce.pop(trade.id, None)

                if not positions:
                    logger.info(f"{GRID_TAG} 🏁 当前所有网格已平仓，等待后续 K 线继续操作。")
                    self._set(trade, "grid_allow_restart", True)
                else:
                    self._set(trade, "grid_allow_restart", False)

                logger.info(
                    f"[STRATEGY] [REDUCE] {GRID_TAG} ▼ 真实减仓成交 | 价格={filled_price:.4f} | "
                    f"金额={margin:.2f} | 已移除: {sorted(pending_reduce_set)}"
                )

                # ★ 新增：记录网格减仓的图表标记
                self._record_chart_marker(
                    event_type="grid_reduce",  # 我们新增一种事件类型
                    pair=pair,
                    trade_id=trade.id,
                    side=self._side_str,
                    price=filled_price,
                    amount=margin,
                    current_time=current_time,
                    message=f"网格减仓 价格{filled_price:.2f}",
                    candle_time=current_time
                )

            # ---- D. 网格状态已清空后的实际数量清理 ----
            elif reason.startswith("grid_reduce_cleanup"):
                self._pending_reduce.pop(trade.id, None)
                self._pending_add.pop(trade.id, None)
                self._set(trade, "grid_positions", "{}")
                self._set(trade, "grid_pending_reduce", [])
                self._set(trade, "grid_pending_add", None)
                self._set(trade, "grid_allow_restart", False)
                logger.info(f"[STRATEGY] [REDUCE] {GRID_TAG} ▼ 清理残余实际仓位成交 | 价格={entry_price:.4f}")

            # ---- E. 整体止损 ----
            elif reason.startswith("grid_stop"):
                self._record_chart_marker(
                    event_type="stop_loss", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time, message="网格整体止损", candle_time=candle_str
                )
                logger.info(f"{GRID_TAG} ✖ 整体止损成交 | 价格={entry_price:.4f}")
                self._set(trade, "grid_positions", "{}")
                self._set(trade, "grid_stopped", True)
                self._set(trade, "grid_allow_restart", False)
                self._pending_add.pop(trade.id, None)
                self._pending_reduce.pop(trade.id, None)
        except Exception:
            logger.exception(f"{GRID_TAG} order_filled 网格记录失败")

    # ============================================================
    # 订单撤销 / 拒绝（失败直接释放 Pending，无锁仓）
    # ============================================================
    def order_cancelled(self, pair, trade, order, current_time, **kwargs):
        try:
            super().order_cancelled(pair, trade, order, current_time, **kwargs)
        except Exception:
            pass
        if trade.id in self._pending_reduce:
            self._pending_reduce.pop(trade.id, None)
            self._set(trade, "grid_pending_reduce", [])
        if trade.id in self._pending_add:
            self._pending_add.pop(trade.id, None)
            self._set(trade, "grid_pending_add", None)

    def order_rejected(self, pair, trade, order, current_time, **kwargs):
        try:
            super().order_rejected(pair, trade, order, current_time, **kwargs)
        except Exception:
            pass
        if trade.id in self._pending_reduce:
            self._pending_reduce.pop(trade.id, None)
            self._set(trade, "grid_pending_reduce", [])
        if trade.id in self._pending_add:
            self._pending_add.pop(trade.id, None)
            self._set(trade, "grid_pending_add", None)

    # ============================================================
    # 自定义止损
    # ============================================================
    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            g = self._grid_cfg()
            lower = self._cfg_float(g, "lower_price", 0.0)
            upper = self._cfg_float(g, "upper_price", 0.0)
            stop_below = bool(g.get("stop_below_lower", True))
            stop_above = bool(g.get("stop_above_upper", False))
            rate = float(current_rate or 0.0)
            if rate <= 0: return None

            if not self._is_short:
                if stop_below and lower > 0 and rate <= lower: return "grid_stop_lower"
            else:
                if stop_above and upper > 0 and rate >= upper: return "grid_stop_upper"
            return None
        except Exception:
            return None

    # ============================================================
    # 工具函数
    # ============================================================
    def _calc_grid_amount(self, trade, price: float) -> float:
        g = self._grid_cfg()
        amount_per_grid = self._cfg_float(g, "amount_per_grid", 0.0)
        mode = self._amount_mode()

        if amount_per_grid > 0:
            if mode == "amount":
                per_grid = amount_per_grid
            else:
                per_grid = self._collateral_total() * (amount_per_grid / 100.0)
        else:
            wallet = float((self.config or {}).get("dry_run_wallet", 0) or 0)
            grid_count = max(1, self._cfg_int(g, "grid_count", 20))
            per_grid = wallet / grid_count

        available = self._available_stake()
        if available > 0 and per_grid > available * 0.8:
            per_grid = available * 0.8

        if pd.isna(per_grid) or np.isinf(per_grid) or per_grid <= 0:
            return 0.0
        return float(per_grid)

    def _get_grid_positions(self, trade) -> dict:
        raw = self._get(trade, "grid_positions", None)
        if not raw: return {}
        if isinstance(raw, dict): return raw
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _set_grid_positions(self, trade, positions: dict):
        clean = {}
        for key, value in positions.items():
            try:
                idx = str(int(key))
                entry = float(value.get("entry", 0))
                qty = float(value.get("qty", 0))
                if entry > 0 and qty > 0 and np.isfinite(entry) and np.isfinite(qty):
                    clean[idx] = {"entry": entry, "qty": qty}
            except (AttributeError, TypeError, ValueError):
                continue
        self._set(trade, "grid_positions", json.dumps(clean, allow_nan=False))

    def _add_grid_position(self, trade, idx: int, entry: float, qty: float):
        positions = self._get_grid_positions(trade)
        positions[str(int(idx))] = {"entry": float(entry), "qty": float(qty)}
        self._set_grid_positions(trade, positions)

    def _log_reduce(self, trade, price, closed, total_margin, total_pnl):
        try:
            if len(closed) == 1:
                idx, entry, qty, margin, pnl = closed[0]
                pnl_pct = (price - entry) / entry * 100 if entry > 0 else 0
                tp_price = self._grid_tp_price(entry)
                logger.info(
                    f"[STRATEGY] [REDUCE] {GRID_TAG} {GREEN}▼ 减仓{RESET} | {trade.pair} | {entry:.4f} → {price:.4f}(止盈线={tp_price:.4f}) | pnl={pnl_pct:+.2f}% | pnl={pnl:+.2f} USDT | 数量={qty:.6f} | 释放={margin:.2f}"
                )
            else:
                logger.info(f"{GRID_TAG} {GREEN}▼ 减仓多格{RESET} | 释放={total_margin:.2f} | pnl={total_pnl:+.2f}")
        except Exception:
            pass

    def _log_state_detail(self, trade, price: float):
        try:
            positions = self._get_grid_positions(trade)
            if getattr(trade, "amount", 0) == 0 and positions:
                positions = {}
                self._set_grid_positions(trade, positions)
            if positions:
                parts = []
                for k in sorted(positions.keys(), key=lambda x: int(x)):
                    v = positions[k]
                    entry = float(v.get("entry", 0.0))
                    tp_price = self._grid_tp_price(entry)
                    tp_pct = (tp_price - entry) / entry * 100 if entry > 0 else 0
                    parts.append(f"建仓={entry:.4f}(止盈={tp_price:.4f}, {tp_pct:+.2f}%)")
                logger.info(f"{GRID_TAG}    └ 持仓: {' '.join(parts)} | 共{len(positions)}单")
            else:
                logger.info(f"{GRID_TAG}    └ 持仓: 无 | 共0单")
        except Exception:
            pass

    @property
    def _bot_id(self):
        return self._get_bot_id()

    def _grid_kv_key(self, suffix: str) -> str:
        return f"grid_{suffix}_{self._bot_id}_{self._side_str}"

    def _set_bot_grid_pending_level(self, pair, idx: int):
        try:
            from core.config_manager import ConfigManager
            ConfigManager.set_bot_kv(self._grid_kv_key("pending_level"), int(idx))
        except Exception:
            pass

    def _get_bot_grid_pending_level(self, pair):
        try:
            from core.config_manager import ConfigManager
            raw = ConfigManager.get_bot_kv(self._grid_kv_key("pending_level"))
            if raw is None or raw == "": return None
            return int(raw)
        except Exception:
            return None

    def _clear_bot_grid_pending_level(self, pair):
        try:
            from core.config_manager import ConfigManager
            ConfigManager.set_bot_kv(self._grid_kv_key("pending_level"), None)
        except Exception:
            pass


class GridBotLong(GridBotBase):
    can_short = False


class GridBotShort(GridBotBase):
    can_short = True