# freqtrade/user_data/strategies/GridBotBase.py
"""
网格机器人基类（绝对线版 - 1m收盘价触发）

设计要点：
  - 一个网格 = 一个 Trade（freqtrade 单 pair 只能有一个 trade）
  - 多单同时持有：trade.custom_data["grid_positions"] = {"3": {...}, "7": {...}}
  - 首仓由 confirm_trade_entry 放行
  - 后续加仓/减仓由 adjust_trade_position 处理
  - ★ 挂单逻辑（基于 1m 收盘价）：
      - 多头：收盘价跌破当前最低持仓网格-1线时加仓；涨破当前持仓网格+1线时止盈。
      - 空头：收盘价突破当前最高持仓网格+1线时加仓；跌破当前持仓网格-1线时止盈。
"""

import sys
import json
import bisect
import traceback
import time as _time
from pathlib import Path
import numpy as np
import pandas as pd
from pandas import DataFrame, Timestamp
from datetime import datetime

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
BLUE = "\033[34m"
CYAN = "\033[36m"
RESET = "\033[0m"

GRID_TAG = f"{CYAN}[Grid]{RESET}"


class GridBotBase(DcaTpBotBase):
    """网格机器人基类（绝对线版）"""
    can_short = False
    use_exit_signal = True
    trailing_stop = False
    position_adjustment_enable = True
    use_custom_stoploss = False

    # ★ 动态读取配置中的 K 线周期（前端可配），默认兜底 5m
    @property
    def timeframe(self) -> str:
        cfg = self.get_runtime_config() or {}
        tf = str(cfg.get("timeframe", "1m")).lower()
        return tf if tf else "1m"

    # ============================================================
    # 初始化
    # ============================================================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.position_adjustment_enable = True

        try:
            self._clear_bot_grid_used_levels()
            self._clear_bot_grid_pending_level(None)
        except Exception:
            logger.warning(f"{GRID_TAG} 启动清空 used_levels 失败", exc_info=True)

    def bot_start(self, **kwargs) -> None:
        """网格启动日志"""
        ft_cfg = self.config or {}

        dry_run_wallet = ft_cfg.get("dry_run_wallet", 0)
        leverage = ft_cfg.get("leverage", 1)
        exchange_cfg = ft_cfg.get("exchange", {}) or {}
        pair_whitelist = exchange_cfg.get("pair_whitelist", []) or []

        g = self._grid_cfg()
        lower = self._cfg_float(g, "lower_price", 0.0)
        upper = self._cfg_float(g, "upper_price", 0.0)
        count = self._cfg_int(g, "grid_count", 0)
        amount_per_grid = self._cfg_float(g, "amount_per_grid", 0.0)
        spacing = str(g.get("spacing_algo", "arithmetic"))
        start_mode = str(g.get("start_mode", "grid"))

        dir_cn = "空头" if self._is_short else "多头"

        logger.info(
            "\n"
            f"==================== {dir_cn}网格配置概览 ====================\n"
            f"初始资金          : {dry_run_wallet} USDT\n"
            f"持仓杠杆          : {leverage}x\n"
            f"白名单            : {', '.join(pair_whitelist) if pair_whitelist else '(空)'}\n"
            f"价格区间          : [{lower}, {upper}]\n"
            f"网格数量          : {count} 格\n"
            f"间距算法          : {spacing}\n"
            f"每格金额          : {amount_per_grid} USDT\n"
            f"启动模式          : {start_mode}\n"
            f"触发周期          : {self.timeframe} 收盘价\n"
            f"======================================================"
        )

    # ============================================================
    # 配置读取
    # ============================================================
    def get_runtime_config(self):
        custom = (self.config or {}).get("custom_params", {}) or {}
        if custom.get("config"):
            return custom["config"]
        if custom.get("gridConfig"):
            return custom["gridConfig"]
        if custom.get("grid"):
            return custom["grid"]
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

    def _grid_cooldown(self) -> int:
        g = self._grid_cfg()
        # 默认冷却时间 60 秒，防止同一秒内疯狂刷单
        return self._cfg_int(g, "cooldown_seconds", 60)

    # ============================================================
    # 网格线生成（绝对线）
    # ============================================================
    def _build_grid_levels(self):
        g = self._grid_cfg()
        upper = self._cfg_float(g, "upper_price", 0.0)
        lower = self._cfg_float(g, "lower_price", 0.0)
        count = self._cfg_int(g, "grid_count", 0)
        algo = str(g.get("spacing_algo", "arithmetic")).lower()

        if upper <= 0 or lower <= 0 or count <= 0 or upper <= lower:
            return []

        if algo == "geometric":
            ratio = (upper / lower) ** (1.0 / count)
            return [lower * (ratio ** i) for i in range(count + 1)]

        step = (upper - lower) / count
        return [lower + step * i for i in range(count + 1)]

    def _get_line_idx(self, price: float) -> int:
        """获取当前价格落在哪个网格区间（返回左侧线的索引）"""
        levels = self._build_grid_levels()
        if not levels:
            return -1
        idx = bisect.bisect_right(levels, price) - 1
        return max(0, min(idx, len(levels) - 2))

    def _grid_tp_price(self, idx: int) -> float:
        """
        ★ 绝对线止盈逻辑：
        - 空头：建仓在 idx 线，向下看一格（idx-1）止盈。
        - 多头：建仓在 idx 线，向上看一格（idx+1）止盈。
        """
        try:
            levels = self._build_grid_levels()
            if not levels:
                return 0.0
            if self._is_short:
                return float(levels[idx - 1]) if 0 < idx < len(levels) else 0.0
            else:
                return float(levels[idx + 1]) if 0 <= idx < len(levels) - 1 else 0.0
        except Exception:
            return 0.0

    # ============================================================
    # 方向辅助
    # ============================================================
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

        if col_long not in dataframe.columns:
            dataframe[col_long] = 0
        if col_short not in dataframe.columns:
            dataframe[col_short] = 0

        dataframe[col_long] = 0
        dataframe[col_short] = 0

        g = self._grid_cfg()
        upper = self._cfg_float(g, "upper_price", 0.0)
        lower = self._cfg_float(g, "lower_price", 0.0)
        start_mode = str(g.get("start_mode", "grid")).lower()
        trigger_price = self._cfg_float(g, "trigger_price", 0.0)

        if upper <= 0 or lower <= 0 or upper <= lower:
            return dataframe

        levels = self._build_grid_levels()
        if not levels:
            return dataframe

        # ★ 模式 1：触发价启动
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

        # ★ 模式 2：立即启动
        if start_mode == "immediate":
            first_idx = dataframe.index[0] if len(dataframe) else None
            if first_idx is not None:
                if self._is_short:
                    dataframe.loc[first_idx, col_short] = 1
                    dataframe.loc[first_idx, "enter_tag"] = "grid_immediate"
                else:
                    dataframe.loc[first_idx, col_long] = 1
                    dataframe.loc[first_idx, "enter_tag"] = "grid_immediate"
            in_range = (dataframe['close'] >= lower) & (dataframe['close'] <= upper)
            if self._is_short:
                dataframe.loc[in_range, col_short] = 1
                dataframe.loc[in_range, "enter_tag"] = "grid_immediate"
            else:
                dataframe.loc[in_range, col_long] = 1
                dataframe.loc[in_range, "enter_tag"] = "grid_immediate"
            return dataframe

        # ★ 模式 3：默认网格触发（跌破某条线多头买入，突破某条线空头卖出）
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

    # ============================================================
    # 首仓拦截
    # ============================================================
    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force,
                            current_time, entry_tag, side, **kwargs):
        try:
            g = self._grid_cfg()
            upper = self._cfg_float(g, "upper_price", 0.0)
            lower = self._cfg_float(g, "lower_price", 0.0)
            start_mode = str(g.get("start_mode", "grid")).lower()
            trigger_price = self._cfg_float(g, "trigger_price", 0.0)

            if upper <= 0 or lower <= 0:
                logger.warning(f"{GRID_TAG} 上下沿未配置，拒绝首仓")
                return False

            try:
                open_trades = Trade.get_trades_proxy(pair=pair, is_open=True)
                open_count = len(list(open_trades))
            except Exception:
                open_count = 0

            if open_count > 0:
                return False

            # ★ 模式 1：触发价启动
            if start_mode == "trigger" and trigger_price > 0:
                if not self._is_short and rate > trigger_price * 1.01:
                    return False
                if self._is_short and rate < trigger_price * 0.99:
                    return False
            # ★ 模式 2：立即启动
            elif start_mode == "immediate":
                if not self._is_short and rate > upper * 1.05:
                    return False
                if not self._is_short and rate < lower * 0.95:
                    return False
                if self._is_short and rate < lower * 0.95:
                    return False
                if self._is_short and rate > upper * 1.05:
                    return False
            # ★ 模式 3：默认网格触发
            else:
                if rate < lower or rate > upper:
                    return False

            levels = self._build_grid_levels()
            if not levels:
                return False

            # 找距离当前价最近的线索引，用于挂首仓
            idx = bisect.bisect_right(levels, rate) - 1
            if idx < 0: idx = 0
            if idx >= len(levels) - 1: idx = len(levels) - 2

            self._set_bot_grid_pending_level(pair, idx)

            candle_ts = self._index_candle_key(current_time)
            self._record_chart_marker(
                event_type="grid_entry_signal", pair=pair, trade_id=0,
                side=self._side_str, price=rate, amount=amount,
                current_time=current_time,
                message=f"网格首仓 线{idx}",
                candle_time=candle_ts,
            )
            return True

        except Exception:
            logger.exception(f"{GRID_TAG} confirm_trade_entry 异常")
            return False

    # ============================================================
    # order_filled：唯一真实的成交记录点
    # ============================================================
    def order_filled(self, pair, trade, order, current_time, **kwargs):
        try:
            super().order_filled(pair, trade, order, current_time, **kwargs)
        except Exception:
            logger.exception(f"{GRID_TAG} super().order_filled 异常")

        try:
            if order.ft_order_side not in (self._entry_order_side, self._exit_order_side):
                return

            reason = str(
                getattr(order, "ft_order_tag", None)
                or getattr(order, "ft_order_reason", None)
                or ""
            )

            entry_price = float(order.average or trade.open_rate or 0.0)
            qty = abs(float(order.amount or 0.0))

            try:
                lev = float(self.leverage(trade.pair) or 1.0)
            except Exception:
                lev = 1.0
            margin = (entry_price * qty) / lev if lev > 0 else 0.0
            candle_ts = self._index_candle_key(current_time)

            # ── A. 首仓成交 ──
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
                self._set(
                    trade,
                    "grid_entry_candle",
                    self._index_candle_key(current_time),
                )
                self._set(
                    trade,
                    "grid_entry_guard_until",
                    self._safe_int(current_time.timestamp()) + max(
                        self._grid_cooldown(), 60
                    ),
                )
                self._set(trade, "grid_pending_add", None)
                self._set(trade, "grid_pending_reduce", [])

                # 设置冷却时间初始值，防止首仓后立刻触发第二次
                self._set(trade, 'last_grid_action_time', self._safe_int(current_time.timestamp()))

                self._record_chart_marker(
                    event_type="grid_entry", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time, message=f"网格首仓 线{idx}",
                    candle_time=candle_ts
                )
                logger.info(f"{GRID_TAG} ▶ 首仓成交 | 线{idx} | 价格={entry_price:.4f}")
                return

            # ── B. 网格加仓成交 ──
            if reason.startswith("grid_add_lv"):
                # 只有订单真实成交后才登记该网格，避免未成交/被拒订单
                # 提前占用网格，导致后续永远不会再次尝试。
                try:
                    idx = int(reason[len("grid_add_lv"):])
                except (TypeError, ValueError):
                    logger.warning(
                        f"{GRID_TAG} 无法解析加仓网格编号 | reason={reason!r}"
                    )
                    return

                if qty <= 0 or entry_price <= 0:
                    logger.warning(
                        f"{GRID_TAG} 忽略无效加仓成交 | 价格={entry_price} | 数量={qty}"
                    )
                    return

                self._add_grid_position(trade, idx, entry_price, qty)
                self._set(trade, "grid_pending_add", None)
                self._set(
                    trade,
                    "last_grid_action_time",
                    self._safe_int(current_time.timestamp()),
                )
                self._record_chart_marker(
                    event_type="grid_add", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time, message=f"网格加仓 {reason}",
                    candle_time=candle_ts
                )
                logger.info(f"{GRID_TAG} ▲ 真实加仓成交 | 价格={entry_price:.4f} | 金额={margin:.2f}")

            # ── C. 网格减仓成交 ──
            elif reason.startswith("grid_reduce_multi"):
                pending = self._get(trade, "grid_pending_reduce", [])
                try:
                    pending_indices = [int(x) for x in (pending or [])]
                except (TypeError, ValueError):
                    pending_indices = []

                positions = self._get_grid_positions(trade)
                taken = self._get_taken_levels(trade)
                for idx in pending_indices:
                    positions.pop(str(idx), None)
                    taken.add(idx)
                self._set_grid_positions(trade, positions)
                if not positions:
                    taken = set()
                    logger.info(f"{GRID_TAG} 🏁 本轮网格已全平，重置状态。")
                self._set_taken_levels(trade, taken)
                self._set(trade, "grid_pending_reduce", [])
                self._set(
                    trade,
                    "last_grid_action_time",
                    self._safe_int(current_time.timestamp()),
                )
                self._record_chart_marker(
                    event_type="grid_sell", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time, message=f"网格减仓 {reason}",
                    candle_time=candle_ts
                )
                logger.info(f"{GRID_TAG} ▼ 真实减仓成交 | 价格={entry_price:.4f} | 金额={margin:.2f}")

            # ── D. 整体止损（下沿/上沿） ──
            elif reason.startswith("grid_stop"):
                self._record_chart_marker(
                    event_type="stop_loss", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time, message="网格整体止损",
                    candle_time=candle_ts
                )
                logger.info(f"{GRID_TAG} ✖ 整体止损成交 | 价格={entry_price:.4f}")

        except Exception:
            logger.exception(f"{GRID_TAG} order_filled 网格记录失败")

    # ============================================================
    # custom_exit
    # ============================================================
    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            g = self._grid_cfg()
            lower = self._cfg_float(g, "lower_price", 0.0)
            upper = self._cfg_float(g, "upper_price", 0.0)
            stop_below = bool(g.get("stop_below_lower", True))
            stop_above = bool(g.get("stop_above_upper", False))

            rate = float(current_rate or 0.0)
            if rate <= 0:
                return None

            if not self._is_short:
                if stop_below and lower > 0 and rate <= lower:
                    logger.info(f"{GRID_TAG} {RED}✖ 整体止损{RESET} | 价={rate:.4f} <= 下沿={lower:.4f}")
                    return "grid_stop_lower"
            else:
                if stop_above and upper > 0 and rate >= upper:
                    logger.info(f"{GRID_TAG} {RED}✖ 整体止损{RESET} | 价={rate:.4f} >= 上沿={upper:.4f}")
                    return "grid_stop_upper"

            return None

        except Exception:
            logger.exception(f"{GRID_TAG} custom_exit 网格判断异常")
            return None

    # ============================================================
    # 核心：加仓 / 减仓（绝对线 1m 收盘价逻辑）
    # ============================================================
    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            g = self._grid_cfg()
            levels = self._build_grid_levels()
            if not levels:
                return None

            if not self._get_bool(trade, "grid_n_initialized", False):
                return None

            # 同一 Trade 存在未完成订单时，不再创建新的调仓订单。
            # 这是防止限价单未成交期间重复提交同一网格的第一道保护。
            if trade.has_open_orders:
                return None

            df, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            if df is None or df.empty:
                return None

            close_price = float(df.iloc[-1]['close'])
            if close_price <= 0:
                return None

            guard_until = self._get_int(trade, "grid_entry_guard_until", 0)
            if guard_until > 0 and current_time.timestamp() < guard_until:
                return None

            current_candle = self._index_candle_key(
                df.iloc[-1].get("date", df.index[-1])
            )
            entry_candle = self._get(trade, "grid_entry_candle", None)
            if entry_candle is not None and current_candle == entry_candle:
                # 首仓成交所在 K 线只负责建立状态，不能用该 K 线的
                # 最新收盘价立即触发止盈或加仓。
                return None

            # 冷却机制
            last_action = self._get_int(trade, 'last_grid_action_time', 0)
            cooldown = self._grid_cooldown()
            if last_action > 0 and current_time.timestamp() - last_action < cooldown:
                return None

            self._cleanup_taken(trade, close_price)

            positions = self._get_grid_positions(trade)
            taken = self._get_taken_levels(trade)
            max_grids = self._cfg_int(g, "max_open_grids", 20)

            if not positions:
                # 没有真实网格持仓时，绝不能生成减仓或调仓订单。
                self._set(trade, "grid_pending_reduce", [])
                self._set(trade, "grid_pending_add", None)
                return None

            # Freqtrade 可能在订单成交回调前多次调用调整函数。
            # 同一网格在此期间只能有一个待成交加仓请求。
            pending_add = self._get(trade, "grid_pending_add", None)
            if pending_add:
                if isinstance(pending_add, str):
                    try:
                        pending_add = json.loads(pending_add)
                    except Exception:
                        pending_add = None
                if isinstance(pending_add, dict):
                    try:
                        pending_at = float(pending_add.get("timestamp", 0))
                    except (TypeError, ValueError):
                        pending_at = 0
                    pending_timeout = max(cooldown, 60)
                    if (
                        pending_at > 0
                        and current_time.timestamp() - pending_at < pending_timeout
                    ):
                        return None
                self._set(trade, "grid_pending_add", None)

            # ---------- 修复 1：简化 pending_reduce 检查 ----------
            pending_reduce = self._get(trade, "grid_pending_reduce", [])
            if isinstance(pending_reduce, str):
                try:
                    pending_reduce = json.loads(pending_reduce)
                except Exception:
                    pending_reduce = []
            if not isinstance(pending_reduce, list):
                pending_reduce = []

            # ★ 只要存在未完成的减仓单，直接拦截！绝不做任何多余判断，防止死循环刷单
            if pending_reduce:
                return None

            try:
                lev = float(self.leverage(trade.pair) or 1.0)
            except Exception:
                lev = 1.0

            # ── 1) 检查止盈（减仓） ──
            to_close = []
            if positions:
                for k, v in positions.items():
                    try:
                        idx = int(k)
                        entry = float(v.get("entry", 0))
                        if entry <= 0:
                            continue
                        tp_price = self._grid_tp_price(idx)
                        if tp_price <= 0:
                            continue

                        # 基于收盘价判断止盈
                        if self._is_short:
                            if close_price <= tp_price:
                                to_close.append((idx, entry, v))
                        else:
                            if close_price >= tp_price:
                                to_close.append((idx, entry, v))
                    except Exception:
                        pass

            if to_close:
                total_margin = 0.0
                total_pnl = 0.0
                closed = []
                for idx, entry, v in to_close:
                    qty = float(v.get("qty", 0))
                    margin = (entry * qty) / lev
                    pnl = (entry - close_price) * qty if self._is_short else (close_price - entry) * qty
                    total_margin += margin
                    total_pnl += pnl
                    closed.append((idx, entry, qty, margin, pnl))

                # ★ 修复 2：立刻在内存中删除这些持仓并加入锁定！
                for idx, _, _, _, _ in closed:
                    positions.pop(str(int(idx)), None)
                    taken.add(int(idx))

                # 保存更新后的持仓状态
                self._set_grid_positions(trade, positions)
                self._set_taken_levels(trade, taken)

                # 记录 pending_reduce，给 order_filled 用
                self._set(
                    trade,
                    "grid_pending_reduce",
                    [idx for idx, _, _, _, _ in closed],
                )

                # ★ 修复 3：发出减仓的瞬间，立刻更新冷却时间！
                self._set(trade, 'last_grid_action_time', self._safe_int(current_time.timestamp()))

                self._log_reduce(trade, close_price, closed, total_margin, total_pnl)
                self._log_state_detail(trade, close_price)
                return -float(total_margin), f"grid_reduce_multi_{len(closed)}"

            # ── 2) 检查加仓（开仓） ──
            held_indices = [int(k) for k in positions.keys()]
            # 如果有持仓，找最边缘的网格线来触发加仓
            if not self._is_short:
                lowest_idx = min(held_indices)
                target_idx = lowest_idx - 1
                if target_idx < 0:
                    return None
                target_line_price = levels[target_idx]
                if close_price > target_line_price:
                    return None
            else:
                highest_idx = max(held_indices)
                target_idx = highest_idx + 1
                if target_idx >= len(levels):
                    return None
                target_line_price = levels[target_idx]
                if close_price < target_line_price:
                    return None

            if str(target_idx) in positions:
                return None
            if target_idx in taken:
                return None
            if len(positions) >= max_grids:
                return None

            buy_usdt = self._calc_grid_amount(trade, close_price)
            if buy_usdt <= 0:
                return None

            add_qty = (buy_usdt * lev) / close_price if close_price > 0 else 0
            if add_qty <= 0:
                return None

            tp_price = self._grid_tp_price(target_idx)
            logger.info(
                f"{GRID_TAG} {RED}▲ 触发线加仓{RESET} | {trade.pair} | 线{target_idx} | "
                f"收盘价={close_price:.4f} | 止盈线={tp_price:.4f} | 保证金={buy_usdt:.2f}"
            )

            self._set(
                trade,
                "grid_pending_add",
                json.dumps({
                    "idx": int(target_idx),
                    "timestamp": self._safe_int(current_time.timestamp()),
                }),
            )
            self._set(trade, 'last_grid_action_time', self._safe_int(current_time.timestamp()))
            return float(buy_usdt), f"grid_add_lv{target_idx}"

        except Exception:
            logger.exception(f"{GRID_TAG} adjust_trade_position 异常")
            return None

    # ============================================================
    # 金额
    # ============================================================
    def _calc_grid_amount(self, trade, price: float) -> float:
        g = self._grid_cfg()
        amount_per_grid = self._cfg_float(g, "amount_per_grid", 0.0)

        if amount_per_grid > 0:
            mode = self._amount_mode()
            if mode == "amount":
                per_grid = amount_per_grid
            else:
                collateral = self._collateral_total()
                per_grid = collateral * (amount_per_grid / 100.0)
        else:
            try:
                per_grid = float(trade.stake_amount or 0.0)
            except Exception:
                per_grid = 0.0
            if per_grid <= 0:
                capital = self._collateral_total()
                grid_count = self._cfg_int(g, "grid_count", 20)
                per_grid = capital / max(1, grid_count)

        available = self._available_stake()
        # 回测及部分 futures 钱包实现可能无法提供 free USDT（返回 0），
        # 不能因此把合法的网格金额裁剪为 0，否则所有加仓都会被静默跳过。
        if available > 0:
            per_grid = min(per_grid, available * 0.8)
        elif per_grid > 0:
            logger.debug(
                f"{GRID_TAG} free USDT 不可用，使用配置/首仓金额 | amount={per_grid:.4f}"
            )
        return max(0.0, per_grid)

    # ============================================================
    # 多格持仓读写
    # ============================================================
    def _get_grid_positions(self, trade) -> dict:
        raw = self._get(trade, "grid_positions", None)
        if not raw:
            return {}
        if isinstance(raw, dict):
            return raw
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _set_grid_positions(self, trade, positions: dict):
        self._set(trade, "grid_positions", json.dumps(positions))

    def _add_grid_position(self, trade, idx: int, entry: float, qty: float):
        positions = self._get_grid_positions(trade)
        positions[str(int(idx))] = {"entry": float(entry), "qty": float(qty)}
        self._set_grid_positions(trade, positions)

    def _remove_grid_position(self, trade, idx: int):
        positions = self._get_grid_positions(trade)
        positions.pop(str(int(idx)), None)
        self._set_grid_positions(trade, positions)

    def _get_taken_levels(self, trade) -> set:
        raw = self._get(trade, "grid_taken_levels", None)
        if not raw:
            return set()
        if isinstance(raw, list):
            return set(int(x) for x in raw)
        try:
            return set(int(x) for x in json.loads(raw))
        except Exception:
            return set()

    def _set_taken_levels(self, trade, levels: set):
        self._set(trade, "grid_taken_levels", json.dumps(sorted(levels)))

    def _cleanup_taken(self, trade, close_price: float):
        try:
            levels = self._build_grid_levels()
            if not levels:
                return

            taken = self._get_taken_levels(trade)
            if not taken:
                return

            n = len(levels) - 1
            new_taken = set()
            for t in taken:
                if t < 0 or t >= n:
                    continue
                # ★ 释放逻辑：只有当 1m 收盘价彻底离开了该网格及其相邻网格，才解锁
                if not self._is_short:
                    if close_price > levels[t + 1] or close_price < levels[max(0, t - 1)]:
                        continue
                else:
                    if close_price < levels[t] or close_price > levels[min(n, t + 2)]:
                        continue
                new_taken.add(t)

            if new_taken != taken:
                self._set_taken_levels(trade, new_taken)
                removed = taken - new_taken
                if removed:
                    logger.info(f"{GRID_TAG} ↺ 允许重开 | 收盘价={close_price:.4f} | 释放格: {sorted(removed)}")
        except Exception:
            logger.warning(f"{GRID_TAG} _cleanup_taken 异常", exc_info=True)

    # ============================================================
    # ★ 日志
    # ============================================================
    def _log_reduce(self, trade, price, closed, total_margin, total_pnl):
        try:
            pair = trade.pair
            if len(closed) == 1:
                idx, entry, qty, margin, pnl = closed[0]
                pnl_pct = (price - entry) / entry * 100
                tp_price = self._grid_tp_price(idx)
                logger.info(
                    f"{GRID_TAG} {GREEN}▼ 减仓{RESET} | {pair} | 线{idx} | "
                    f"{entry:.4f} → {price:.4f}(止盈线={tp_price:.4f}) | "
                    f"pnl={pnl_pct:+.2f}% | pnl={pnl:+.2f} USDT | "
                    f"数量={qty:.6f} | 释放={margin:.2f}"
                )
            else:
                logger.info(f"{GRID_TAG} {GREEN}▼ 减仓多格{RESET} | 释放={total_margin:.2f} | pnl={total_pnl:+.2f}")
        except Exception:
            pass

    def _log_state_detail(self, trade, price: float):
        try:
            lev = float(self.leverage(trade.pair) or 1.0)
            positions = self._get_grid_positions(trade)
            taken = self._get_taken_levels(trade)

            if positions:
                parts = []
                for k in sorted(positions.keys(), key=lambda x: int(x)):
                    v = positions[k]
                    idx = int(k)
                    entry = float(v.get("entry", 0))
                    tp_price = self._grid_tp_price(idx)
                    tp_pct = (tp_price - entry) / entry * 100 if entry > 0 else 0
                    parts.append(f"线{idx}={entry:.4f}(止盈={tp_price:.4f}, {tp_pct:+.2f}%)")
                logger.info(f"{GRID_TAG}    └ 持仓: {' '.join(parts)} | 共{len(positions)}单 | 锁定{len(taken)}线")
            else:
                logger.info(f"{GRID_TAG}    └ 持仓: 无 | 共0单")
        except Exception:
            pass

    # ============================================================
    # bot 级 custom_data（保留接口）
    # ============================================================
    @property
    def _bot_id(self):
        return self._get_bot_id()

    def _grid_kv_key(self, suffix: str) -> str:
        return f"grid_{suffix}_{self._bot_id}_{self._side_str}"

    def _get_bot_grid_used_levels(self) -> set:
        try:
            from core.config_manager import ConfigManager
            raw = ConfigManager.get_bot_kv(self._grid_kv_key("used_levels"))
            if not raw:
                return set()
            return set(int(x) for x in raw)
        except Exception:
            return set()

    def _clear_bot_grid_used_levels(self):
        try:
            from core.config_manager import ConfigManager
            ConfigManager.set_bot_kv(self._grid_kv_key("used_levels"), [])
        except Exception:
            pass

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
            if raw is None or raw == "":
                return None
            return int(raw)
        except Exception:
            return None

    def _clear_bot_grid_pending_level(self, pair):
        try:
            from core.config_manager import ConfigManager
            ConfigManager.set_bot_kv(self._grid_kv_key("pending_level"), None)
        except Exception:
            pass


# ============================================================
# 子类
# ============================================================
class GridBotLong(GridBotBase):
    can_short = False


class GridBotShort(GridBotBase):
    can_short = True