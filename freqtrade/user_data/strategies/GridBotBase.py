# freqtrade/user_data/strategies/GridBotBase.py
"""
网格机器人基类（绝对线版 - 1m 收盘价触发，终极修复版）
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

        # 第一道防线：Pair 级别的 1m K 线锁，针对加仓
        self._last_candle_str = {}

        # 第二道防线：内存 Pending 锁，针对减仓（防止重复发平仓单）
        self._pending_reduce = {}  # {trade_id: set([idx1, idx2])}
        self._pending_add = {}  # {trade_id: {"idx": int, "timestamp": float}}

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

    def _grid_tp_price(self, idx: int) -> float:
        try:
            levels = self._build_grid_levels()
            if not levels: return 0.0
            if self._is_short:
                return float(levels[idx - 1]) if 0 < idx < len(levels) else 0.0
            else:
                return float(levels[idx + 1]) if 0 <= idx < len(levels) - 1 else 0.0
        except Exception:
            return 0.0

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

            levels = self._build_grid_levels()
            if not levels: return False

            # immediate 也必须遵守绝对网格上下沿，不能在区间外开仓。
            if rate < lower or rate > upper:
                return False

            idx = bisect.bisect_right(levels, rate) - 1
            if idx < 0: idx = 0
            if idx >= len(levels) - 1: idx = len(levels) - 2

            self._set_bot_grid_pending_level(pair, idx)
            # 同一根 K 线只允许一次首仓，防止整仓止盈后立即重复入场。
            self._last_candle_str[pair] = candle_str
            return True
        except Exception:
            return False

    # ============================================================
    # 核心：加仓 / 减仓（不刷单、不锁仓、防 NaN）
    # ============================================================
    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            g = self._grid_cfg()
            levels = self._build_grid_levels()
            if not levels: return None
            if not self._get_bool(trade, "grid_n_initialized", False): return None

            # 1. 有未完成订单时，绝对不发新单
            if getattr(trade, "has_open_orders", False): return None

            # 2. 获取 K 线字符串
            candle_str = self._get_candle_str(current_time)

            # 3. 若当前 K 线已经处理过加仓，则拦截
            if self._last_candle_str.get(trade.pair) == candle_str: return None

            df, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            if df is None or df.empty: return None
            close_price = float(df.iloc[-1]['close'])
            if close_price <= 0 or pd.isna(close_price) or np.isinf(close_price): return None
            # 某些回测路径中分析数据仍停留在上一根 K 线，而 current_rate
            # 已经反映当前撮合价。取对多头止盈更保守的较高值，避免漏掉止盈。
            try:
                live_rate = float(current_rate or 0.0)
                if np.isfinite(live_rate) and live_rate > 0:
                    close_price = max(close_price, live_rate) if not self._is_short else min(close_price, live_rate)
            except (TypeError, ValueError):
                pass

            # 首仓成交所在 K 线及短暂保护期内不允许立刻止盈/加仓。
            # immediate 模式尤其需要此保护，否则首仓价已高于下一止盈线时
            # 会在同一根 K 线立即生成减仓订单。
            entry_candle = self._get(trade, "grid_entry_candle", None)
            if entry_candle == candle_str:
                return None
            guard_until = self._get_int(trade, "grid_entry_guard_until", 0)
            if guard_until > 0 and current_time.timestamp() < guard_until:
                return None

            positions = self._get_grid_positions(trade)

            # 没有真实持仓数量时，清除失效的虚拟网格状态，避免继续发减仓单。
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

            # 网格仓位已经全部成交退出后，合约精度或保证金换算可能仍在
            # Trade 中留下少量实际数量。不能让这个残余 Trade 一直持有到
            # 回测结束的 force_exit。
            if not positions:
                cleanup_stake = (actual_amount * close_price) / lev if lev > 0 else 0.0
                if cleanup_stake > 0 and np.isfinite(cleanup_stake):
                    self._last_candle_str[trade.pair] = candle_str
                    self._set(trade, "grid_pending_reduce", [])
                    return -float(cleanup_stake), "grid_reduce_cleanup"
                return None

            # ---- 1) 检查止盈（减仓）----
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

            for k, v in positions.items():
                try:
                    idx = int(k)
                    # 如果该网格已经在平仓中，直接跳过
                    if idx in pending_reduce_set:
                        continue

                    entry = float(v.get("entry", 0))
                    if entry <= 0 or pd.isna(entry) or np.isinf(entry): continue

                    tp_price = self._grid_tp_price(idx)
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
                    qty = float(v.get("qty", 0))
                    margin = (entry * qty) / lev if lev > 0 else 0.0
                    pnl = (entry - close_price) * qty if self._is_short else (close_price - entry) * qty

                    # 防 NaN 处理
                    if pd.isna(margin) or np.isinf(margin): margin = 0.0
                    if pd.isna(pnl) or np.isinf(pnl): pnl = 0.0

                    total_margin += margin
                    total_pnl += pnl
                    closed.append((idx, entry, qty, margin, pnl))

                if total_margin <= 0 or not np.isfinite(total_margin):
                    return None

                # 把这几个网格放进 Pending，防止下一次判断又触发。
                # 持仓状态保留到真实成交回调，撤单时不会丢失网格。
                pending_reduce_set.update([idx for idx, _, _, _, _ in closed])
                self._pending_reduce[trade.id] = pending_reduce_set
                self._set(trade, "grid_pending_reduce", sorted(pending_reduce_set))

                self._log_reduce(trade, close_price, closed, total_margin, total_pnl)
                self._log_state_detail(trade, close_price)

                # 防 NaN 返回
                if pd.isna(total_margin) or np.isinf(total_margin): total_margin = 0.0
                return -float(total_margin), f"grid_reduce_multi_{len(closed)}"

            # ---- 2) 检查加仓 ----
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
                # 【#4】pending_add 超时释放：防止订单挂起/重启/回调丢失后永久卡死
                try:
                    ts = float(pending_add.get("timestamp", 0) or 0) \
                        if isinstance(pending_add, dict) else 0.0
                except (TypeError, ValueError):
                    ts = 0.0
                add_timeout = self._cfg_int(g, "pending_add_timeout", 300)  # 默认5分钟
                if ts <= 0 or (current_time.timestamp() - ts) > add_timeout:
                    logger.warning(
                        f"{GRID_TAG} pending_add 超时释放 | trade={trade.id} | "
                        f"ts={ts:.0f} | 已过={current_time.timestamp() - ts:.0f}s"
                    )
                    self._pending_add.pop(trade.id, None)
                    self._set(trade, "grid_pending_add", None)
                    # 释放后继续往下走，本 tick 允许重新判断加仓
                else:
                    return None

            # 【#8】跳空补格：找出所有"价格已触及但尚未持仓"的格，逐格补齐
            held_indices = [int(k) for k in positions.keys()]
            max_grids = self._cfg_int(g, "max_open_grids", self._cfg_int(g, "grid_count", 20))
            if len(positions) >= max_grids:
                return None

            if not self._is_short:
                lowest_idx = min(held_indices)
                # 所有 idx < lowest_idx 且 close_price <= levels[idx] 的格都是待补格
                target_indices = [
                    i for i in range(lowest_idx - 1, -1, -1)
                    if close_price <= levels[i] and str(i) not in positions
                ]
            else:
                highest_idx = max(held_indices)
                target_indices = [
                    i for i in range(highest_idx + 1, len(levels))
                    if close_price >= levels[i] and str(i) not in positions
                ]

            if not target_indices:
                return None

            # 按最大可开格数截断（从最近格开始补）
            room = max_grids - len(positions)
            target_indices = target_indices[:room]
            if not target_indices:
                return None

            # 一次补多格：总额 = 单格 × 格数
            buy_usdt_per = self._calc_grid_amount(trade, close_price)
            if buy_usdt_per <= 0 or pd.isna(buy_usdt_per) or np.isinf(buy_usdt_per):
                return None

            total_buy_usdt = buy_usdt_per * len(target_indices)
            # 可用余额保护：不够补全部时，能补几格补几格
            available = self._available_stake()
            if available > 0 and total_buy_usdt > available * 0.8:
                affordable = int((available * 0.8) // buy_usdt_per)
                if affordable <= 0:
                    logger.warning(
                        f"{GRID_TAG} 可用余额不足补格 | 需要={buy_usdt_per:.2f}/格 | 可用={available:.2f}"
                    )
                    return None
                target_indices = target_indices[:affordable]
                total_buy_usdt = buy_usdt_per * len(target_indices)
                logger.warning(
                    f"{GRID_TAG} 可用余额不足，本次只补 {len(target_indices)} 格"
                )

            add_qty = (total_buy_usdt * lev) / close_price if close_price > 0 else 0
            if add_qty <= 0 or not np.isfinite(add_qty):
                return None

            # 记录本次要补的格（reason 里带格列表，order_filled 按格拆）
            target_indices = sorted(target_indices)   # 多头从高到低补，排序后统一
            idx_tag = ",".join(str(i) for i in target_indices)
            tp_price_first = self._grid_tp_price(target_indices[0])
            logger.info(
                f"{GRID_TAG} {RED}▲ 触发线加仓(补{len(target_indices)}格){RESET} | "
                f"{trade.pair} | 线{idx_tag} | 收盘价={close_price:.4f} | "
                f"首格止盈线={tp_price_first:.4f} | 单格={buy_usdt_per:.2f} | 合计={total_buy_usdt:.2f}"
            )

            self._last_candle_str[trade.pair] = candle_str
            self._pending_add = getattr(self, "_pending_add", {})
            self._pending_add[trade.id] = {
                "idx": target_indices,          # ★ 改为列表
                "timestamp": current_time.timestamp(),
            }
            self._set(
                trade,
                "grid_pending_add",
                json.dumps(self._pending_add[trade.id], allow_nan=False),
            )
            return float(total_buy_usdt), f"grid_add_multi_{idx_tag}"

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
                idx = self._get_bot_grid_pending_level(trade.pair)
                if idx is None:
                    levels = self._build_grid_levels()
                    if levels:
                        idx = bisect.bisect_right(levels, entry_price) - 1
                        if idx < 0: idx = 0
                        if idx >= len(levels) - 1: idx = len(levels) - 2
                    else:
                        idx = 0

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

                self._record_chart_marker(
                    event_type="grid_entry", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time, message=f"网格首仓 线{idx}", candle_time=candle_str
                )
                logger.info(f"{GRID_TAG} ▶ 首仓成交 | 线{idx} | 价格={entry_price:.4f}")
                return

            # ---- B. 加仓成交（支持单格 grid_add_lvN 与多格 grid_add_multi_i,j,k） ----
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
                if not idx_list:
                    return
                if (
                    qty <= 0
                    or entry_price <= 0
                    or not np.isfinite(qty)
                    or not np.isfinite(entry_price)
                ):
                    return

                # 多格时按格均分成交数量；单格时 qty 原样
                per_qty = qty / len(idx_list)

                for i in idx_list:
                    self._add_grid_position(trade, i, entry_price, per_qty)

                self._pending_add.pop(trade.id, None)
                self._set(trade, "grid_pending_add", None)

                grid_str = ",".join([str(i) for i in idx_list])
                self._record_chart_marker(
                    event_type="grid_add", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time,
                    message=f"网格加仓 线{grid_str}", candle_time=candle_str,
                )
                logger.info(
                    f"{GRID_TAG} ▲ 真实加仓成交 | 价格={entry_price:.4f} | "
                    f"金额={margin:.2f} | 格={idx_list} | 每格qty={per_qty:.6f}"
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

                logger.info(
                    f"{GRID_TAG} ▼ 真实减仓成交 | 价格={filled_price:.4f} | 金额={margin:.2f} | 已移除网格: {sorted(pending_reduce_set)}"
                )

            # ---- D. 网格状态已清空后的实际数量清理 ----
            elif reason.startswith("grid_reduce_cleanup"):
                self._pending_reduce.pop(trade.id, None)
                self._pending_add.pop(trade.id, None)
                self._set(trade, "grid_positions", "{}")
                self._set(trade, "grid_pending_reduce", [])
                self._set(trade, "grid_pending_add", None)
                logger.info(f"{GRID_TAG} ▼ 清理残余实际仓位成交 | 价格={entry_price:.4f}")

            # ---- E. 整体止损 ----
            elif reason.startswith("grid_stop"):
                self._record_chart_marker(
                    event_type="stop_loss", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time, message="网格整体止损", candle_time=candle_str
                )
                logger.info(f"{GRID_TAG} ✖ 整体止损成交 | 价格={entry_price:.4f}")
                self._set(trade, "grid_positions", "{}")
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
            logger.info(f"{GRID_TAG} 订单撤销，释放 Pending 锁")
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
            logger.info(f"{GRID_TAG} 订单拒绝，释放 Pending 锁")
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
            # ★ 改为：固定 = dry_run_wallet / grid_count
            wallet = float((self.config or {}).get("dry_run_wallet", 0) or 0)
            grid_count = max(1, self._cfg_int(g, "grid_count", 20))
            per_grid = wallet / grid_count

        # 可用余额保护：保留，但只在不足时截断，并打日志
        available = self._available_stake()
        if available > 0 and per_grid > available * 0.8:
            logger.warning(
                f"{GRID_TAG} 单格保证金 {per_grid:.2f} 超过可用余额80% "
                f"({available * 0.8:.2f})，已截断"
            )
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
                tp_price = self._grid_tp_price(idx)
                logger.info(
                    f"{GRID_TAG} {GREEN}▼ 减仓{RESET} | {trade.pair} | 线{idx} | {entry:.4f} → {price:.4f}(止盈线={tp_price:.4f}) | pnl={pnl_pct:+.2f}% | pnl={pnl:+.2f} USDT | 数量={qty:.6f} | 释放={margin:.2f}"
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
                    idx = int(k)
                    entry = float(v.get("entry", 0))
                    tp_price = self._grid_tp_price(idx)
                    tp_pct = (tp_price - entry) / entry * 100 if entry > 0 else 0
                    parts.append(f"线{idx}={entry:.4f}(止盈={tp_price:.4f}, {tp_pct:+.2f}%)")
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