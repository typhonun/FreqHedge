# freqtrade/user_data/strategies/GridBotBase.py
"""
网格机器人基类（固定价差版）

设计要点：
  - 一个网格 = 一个 Trade（freqtrade 单 pair 只能有一个 trade）
  - 多格同时持有：trade.custom_data["grid_positions"] = {"3": {...}, "7": {...}}
  - 首仓由 confirm_trade_entry 放行
  - 后续加仓/减仓由 adjust_trade_position 处理
  - 减仓按格独立止盈；一次可平多格
  - ★ 卖点 = 该格的上沿（固定价格），不依赖 entry
  - 复用 DcaTpBotBase 的基础设施（图表标记、HTF、Pump、时间止损等）

不做的事情：
  - 不做"每格一个 trade"（freqtrade 不支持）
  - 不做多空同时（由子类 can_short 决定）
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
    """网格机器人基类（固定价差版）"""

    timeframe = '5m'
    can_short = False

    use_exit_signal = True
    trailing_stop = False
    position_adjustment_enable = True
    use_custom_stoploss = False

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
        """★ 网格自己的启动日志，不再走 DcaTpBotBase.bot_start"""
        ft_cfg = self.config or {}

        dry_run_wallet = ft_cfg.get("dry_run_wallet", 0)
        stake_amount = ft_cfg.get("stake_amount", 0)
        max_open_trades = ft_cfg.get("max_open_trades", 0)
        tradable_balance_ratio = ft_cfg.get("tradable_balance_ratio", 0)
        leverage = ft_cfg.get("leverage", 1)

        exchange_cfg = ft_cfg.get("exchange", {}) or {}
        pair_whitelist = exchange_cfg.get("pair_whitelist", []) or []
        pair_blacklist = exchange_cfg.get("pair_blacklist", []) or []

        # ── 网格参数 ──
        g = self._grid_cfg()
        lower = self._cfg_float(g, "lower_price", 0.0)
        upper = self._cfg_float(g, "upper_price", 0.0)
        count = self._cfg_int(g, "grid_count", 0)
        amount_per_grid = self._cfg_float(g, "amount_per_grid", 0.0)
        spacing = str(g.get("spacing_algo", "arithmetic"))
        start_mode = str(g.get("start_mode", "wait"))
        stop_below = bool(g.get("stop_below_lower", True))
        tp_pct = self._cfg_float(g, "tp_per_grid_pct", 0.0)

        step = 0.0
        step_pct = 0.0
        if lower > 0 and upper > lower and count > 0:
            step = (upper - lower) / count
            step_pct = step / lower * 100

        total_invest = amount_per_grid * count

        dir_cn = "空头" if self._is_short else "多头"

        logger.info(
            "\n"
            f"==================== {dir_cn}网格配置概览 ====================\n"
            f"初始资金          : {dry_run_wallet} USDT\n"
            f"开仓金额          : {stake_amount} USDT\n"
            f"最大持仓          : {max_open_trades}\n"
            f"资金利用率        : {tradable_balance_ratio}\n"
            f"持仓杠杆          : {leverage}x\n"
            f"K线时间周期       : {self.timeframe}\n"
            f"白名单            : {', '.join(pair_whitelist) if pair_whitelist else '(空)'}\n"
            f"黑名单            : {', '.join(pair_blacklist) if pair_blacklist else '(空)'}\n"
            f"------------------------------------------------------\n"
            f"价格区间          : [{lower}, {upper}]\n"
            f"网格数量          : {count} 格\n"
            f"格距              : {step:.4f} ({step_pct:.2f}%)\n"
            f"间距算法          : {spacing}\n"
            f"每格金额          : {amount_per_grid} USDT\n"
            f"总投入            : {total_invest} USDT\n"
            f"每格止盈          : {tp_pct}%\n"
            f"启动模式          : {start_mode}\n"
            f"跌破下沿止损      : {'开' if stop_below else '关'}\n"
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

    # ============================================================
    # 网格线
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

    def _find_grid_index(self, price):
        levels = self._build_grid_levels()
        if not levels:
            return None
        if price < levels[0] or price > levels[-1]:
            return None
        idx = bisect.bisect_right(levels, price) - 1
        if idx < 0:
            idx = 0
        if idx >= len(levels) - 1:
            idx = len(levels) - 2
        return idx

    def _grid_range_str(self, idx: int) -> str:
        """返回某格的区间字符串：'[1780.00, 1840.00]'"""
        try:
            levels = self._build_grid_levels()
            if not levels or idx < 0 or idx >= len(levels) - 1:
                return "?"
            return f"[{levels[idx]:.2f}, {levels[idx + 1]:.2f}]"
        except Exception:
            return "?"

    def _grid_tp_price(self, idx: int) -> float:
        """
        ★ 卖点 = 该格的上沿（多头）/ 下沿（空头）
        流派 A：固定价差，不依赖 entry
        """
        try:
            levels = self._build_grid_levels()
            if not levels:
                return 0.0
            if self._is_short:
                # 空头：卖点 = 该格的下沿
                if idx < 0 or idx >= len(levels):
                    return 0.0
                return float(levels[idx])
            else:
                # 多头：卖点 = 该格的上沿
                if idx < 0 or idx >= len(levels) - 1:
                    return 0.0
                return float(levels[idx + 1])
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

        # ★ 模式 3：默认网格触发（极致优化：向量化替代循环）
        # 使用 np.searchsorted 找出每根 K 线价格落在哪个网格区间
        import numpy as np
        close_arr = dataframe['close'].values
        # 计算每根K线所在的网格索引（0 到 len(levels)-1）
        idx_now = np.searchsorted(levels, close_arr, side='right') - 1
        # 边界限制：超出网格的保持边界索引
        idx_now = np.clip(idx_now, 0, len(levels) - 2)

        # 获取上一根 K 线的索引
        idx_prev = np.roll(idx_now, 1)
        idx_prev[0] = idx_now[0]  # 第一根 K 线没有上一根，设为与自己相同

        if self._is_short:
            # 空头：价格向上突破了网格，说明涨到了更高的格子
            # 即：当前索引 > 之前索引
            trigger_mask = (idx_now > idx_prev)
            dataframe.loc[trigger_mask, col_short] = 1
            dataframe.loc[trigger_mask, "enter_tag"] = "grid_line"
        else:
            # 多头：价格向下跌破了网格，说明跌到了更低的格子
            # 即：当前索引 < 之前索引
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
                # 立即启动允许当前价在区间外，只要在合理范围内（±5%）
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
                idx = self._find_grid_index(rate)
                if idx is None:
                    return False

            idx = self._find_grid_index(rate)
            if idx is None:
                levels = self._build_grid_levels()
                if not levels:
                    return False
                if rate <= levels[0]:
                    idx = 0
                else:
                    idx = len(levels) - 2
            self._set_bot_grid_pending_level(pair, idx)

            candle_ts = self._index_candle_key(current_time)
            self._record_chart_marker(
                event_type="grid_entry_signal", pair=pair, trade_id=0,
                side=self._side_str, price=rate, amount=amount,
                current_time=current_time,
                message=f"网格首仓 格{idx}",
                candle_time=candle_ts,
            )
            return True

        except Exception:
            logger.exception(f"{GRID_TAG} confirm_trade_entry 异常")
            return False

    # ============================================================
    # order_filled：首仓成交
    # ============================================================
    def order_filled(self, pair, trade, order, current_time, **kwargs):
        try:
            super().order_filled(pair, trade, order, current_time, **kwargs)
        except Exception:
            logger.exception(f"{GRID_TAG} super().order_filled 异常")

        try:
            if order.ft_order_side != self._entry_order_side:
                return

            if self._get_bool(trade, "grid_n_initialized", False):
                return

            idx = self._get_bot_grid_pending_level(trade.pair)
            entry_price = float(order.average or trade.open_rate)
            if idx is None:
                idx = self._find_grid_index(entry_price)

            qty = abs(float(order.amount or trade.amount or 0.0))

            positions = self._get_grid_positions(trade)
            positions[str(int(idx))] = {"entry": entry_price, "qty": qty}
            self._set_grid_positions(trade, positions)

            # ★ 不再往 taken 里加，positions 已经能防止重复加仓
            self._set(trade, "grid_n_initialized", True)
            self._set(trade, "grid_anchor_price", float(entry_price))

            self._clear_bot_grid_pending_level(trade.pair)

            # ── 日志：首仓
            try:
                lev = float(self.leverage(trade.pair) or 1.0)
            except Exception:
                lev = 1.0
            notional = entry_price * qty
            margin = notional / lev

            range_str = self._grid_range_str(idx)
            tp_price = self._grid_tp_price(idx)
            tp_pct = (tp_price - entry_price) / entry_price * 100 if entry_price > 0 else 0

            logger.info(
                f"{GRID_TAG} {GREEN}▶ 首仓{RESET} | {pair} | 格{idx} | "
                f"区间={range_str} | 成交价={entry_price:.2f} | "
                f"卖点={tp_price:.2f}({tp_pct:+.2f}%) | "
                f"保证金={margin:.2f} | 数量={qty:.6f}"
            )
            self._log_state_detail(trade, entry_price)

            self._record_chart_marker(
                event_type="grid_add",
                pair=pair,
                trade_id=trade.id,
                side=self._side_str,
                price=entry_price,
                amount=margin,
                current_time=current_time,
                message=f"网格首仓 格{idx}",
                candle_time=self._index_candle_key(current_time)
            )

        except Exception:
            logger.exception(f"{GRID_TAG} order_filled 网格记录失败")

    # ============================================================
    # custom_exit
    # ============================================================
    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            base_exit = super().custom_exit(
                pair, trade, current_time, current_rate, current_profit, **kwargs
            )
            if base_exit:
                return base_exit
        except Exception:
            logger.exception(f"{GRID_TAG} super().custom_exit 异常")

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
                    logger.info(
                        f"{GRID_TAG} {RED}✖ 整体止损{RESET} | {pair} | "
                        f"价={rate:.2f} <= 下沿={lower:.2f}"
                    )
                    return "grid_stop_lower"
            else:
                if stop_above and upper > 0 and rate >= upper:
                    logger.info(
                        f"{GRID_TAG} {RED}✖ 整体止损{RESET} | {pair} | "
                        f"价={rate:.2f} >= 上沿={upper:.2f}"
                    )
                    return "grid_stop_upper"

            return None

        except Exception:
            logger.exception(f"{GRID_TAG} custom_exit 网格判断异常")
            return None

    # ============================================================
    # 核心：加仓 / 减仓
    # ============================================================
    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            g = self._grid_cfg()
            levels = self._build_grid_levels()
            if not levels:
                return None

            lower = levels[0]
            upper = levels[-1]

            price = float(current_rate or 0.0)
            if price <= 0:
                return None

            if not self._get_bool(trade, "grid_n_initialized", False):
                return None

            self._cleanup_taken(trade, price)

            cur_idx = self._find_grid_index(price)
            if cur_idx is None:
                return None

            positions = self._get_grid_positions(trade)
            taken = self._get_taken_levels(trade)

            max_grids = self._cfg_int(g, "max_open_grids", 5)

            # 杠杆（用于计算保证金）
            try:
                lev = float(self.leverage(trade.pair) or 1.0)
            except Exception:
                lev = 1.0

            # 1) 止盈
            to_close = []
            for k, v in positions.items():
                try:
                    idx = int(k)
                    entry = float(v.get("entry", 0))
                    if entry <= 0:
                        continue

                    tp_price = self._grid_tp_price(idx)
                    if tp_price <= 0:
                        continue

                    if self._is_short:
                        if price <= tp_price:
                            to_close.append((idx, entry, v))
                    else:
                        if price >= tp_price:
                            to_close.append((idx, entry, v))
                except Exception:
                    pass

            if to_close:
                total_margin = 0.0
                total_pnl = 0.0
                closed = []
                for idx, entry, v in to_close:
                    qty = float(v.get("qty", 0))
                    notional = entry * qty
                    margin = notional / lev  # ★ 保证金 = 名义 / 杠杆
                    if self._is_short:
                        pnl = (entry - price) * qty
                    else:
                        pnl = (price - entry) * qty
                    total_margin += margin
                    total_pnl += pnl
                    self._remove_grid_position(trade, idx)
                    taken.add(idx)
                    closed.append((idx, entry, qty, margin, pnl))

                self._set_taken_levels(trade, taken)

                # cap：减仓不超过当前 stake
                try:
                    current_stake = float(trade.stake_amount or 0)
                    total_margin = min(total_margin, current_stake)
                except Exception:
                    pass

                self._log_reduce(trade, price, closed, total_margin, total_pnl)
                self._log_state_detail(trade, price)
                # ★ 记录减仓图表标记
                self._record_chart_marker(
                    event_type="grid_sell",
                    pair=trade.pair,
                    trade_id=trade.id,
                    side=self._side_str,
                    price=price,
                    amount=total_margin,
                    current_time=current_time,
                    message=f"网格减仓 {len(closed)}格",
                    candle_time=self._index_candle_key(current_time)
                )
                return -float(total_margin), f"grid_reduce_multi_{len(closed)}"

            # 2) 加仓
            if str(cur_idx) in positions:
                return None
            if cur_idx in taken:
                return None
            if len(positions) >= max_grids:
                return None
            if price < lower or price > upper:
                return None

            buy_usdt = self._calc_grid_amount(trade, price)
            if buy_usdt <= 0:
                return None

            add_qty = (buy_usdt * lev) / price if price > 0 else 0
            if add_qty <= 0:
                return None

            self._add_grid_position(trade, cur_idx, price, add_qty)

            range_str = self._grid_range_str(cur_idx)
            tp_price = self._grid_tp_price(cur_idx)
            tp_pct = (tp_price - price) / price * 100 if price > 0 else 0

            logger.info(
                f"{GRID_TAG} {RED}▲ 加仓{RESET} | {trade.pair} | 格{cur_idx} | "
                f"区间={range_str} | 成交价={price:.2f} | "
                f"卖点={tp_price:.2f}({tp_pct:+.2f}%) | "
                f"保证金={buy_usdt:.2f} | 数量={add_qty:.6f}"
            )
            self._log_state_detail(trade, price)
            # ★ 记录加仓图表标记
            self._record_chart_marker(
                event_type="grid_add",
                pair=trade.pair,
                trade_id=trade.id,
                side=self._side_str,
                price=price,
                amount=buy_usdt,
                current_time=current_time,
                message=f"网格加仓 格{cur_idx}",
                candle_time=self._index_candle_key(current_time)
            )
            return float(buy_usdt), f"grid_add_lv{cur_idx}"

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
        per_grid = min(per_grid, available * 0.8)
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

    def _cleanup_taken(self, trade, price: float):
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
                in_grid = levels[t] <= price < levels[t + 1]
                if in_grid:
                    new_taken.add(t)

            if new_taken != taken:
                self._set_taken_levels(trade, new_taken)
                removed = taken - new_taken
                if removed:
                    logger.info(
                        f"{GRID_TAG} ↺ 允许重开 | 价={price:.2f} | "
                        f"释放格: {sorted(removed)}"
                    )
        except Exception:
            logger.warning(f"{GRID_TAG} _cleanup_taken 异常", exc_info=True)

    # ============================================================
    # ★ 日志：减仓摘要
    # ============================================================
    def _log_reduce(self, trade, price, closed, total_margin, total_pnl):
        """
        减仓日志：
          closed = [(idx, entry, qty, margin, pnl), ...]
        """
        try:
            pair = trade.pair

            if len(closed) == 1:
                idx, entry, qty, margin, pnl = closed[0]
                pnl_pct = (price - entry) / entry * 100
                range_str = self._grid_range_str(idx)
                tp_price = self._grid_tp_price(idx)
                logger.info(
                    f"{GRID_TAG} {GREEN}▼ 减仓{RESET} | {pair} | 格{idx} | "
                    f"区间={range_str} | {entry:.2f} → {price:.2f}(卖点={tp_price:.2f}) | "
                    f"pnl={pnl_pct:+.2f}% | pnl={pnl:+.2f} USDT | "
                    f"数量={qty:.6f} | 释放={margin:.2f}"
                )
                logger.info(
                    f"{GRID_TAG}    └ {pair} | "
                    f"释放合计={total_margin:.2f} USDT | pnl合计={total_pnl:+.2f} USDT"
                )
            else:
                idx_list = ",".join(f"格{c[0]}" for c in closed)
                logger.info(
                    f"{GRID_TAG} {GREEN}▼ 减仓{RESET} | {pair} | {idx_list} | "
                    f"释放={total_margin:.2f} | pnl={total_pnl:+.2f} | 笔数={len(closed)}"
                )
                for idx, entry, qty, margin, pnl in closed:
                    pnl_pct = (price - entry) / entry * 100
                    range_str = self._grid_range_str(idx)
                    tp_price = self._grid_tp_price(idx)
                    logger.info(
                        f"{GRID_TAG}    ├ 格{idx}: "
                        f"区间={range_str} | "
                        f"{entry:.2f} → {price:.2f}(卖点={tp_price:.2f}) | "
                        f"pnl={pnl_pct:+.2f}% | pnl={pnl:+.2f} USDT | "
                        f"数量={qty:.6f} | 释放={margin:.2f}"
                    )
        except Exception:
            logger.warning(f"{GRID_TAG} _log_reduce 异常", exc_info=True)

    # ============================================================
    # ★ 日志：状态明细
    # ============================================================
    def _log_state_detail(self, trade, price: float):
        try:
            g = self._grid_cfg()
            levels = self._build_grid_levels()
            if not levels:
                return

            try:
                lev = float(self.leverage(trade.pair) or 1.0)
            except Exception:
                lev = 1.0

            cur_idx = self._find_grid_index(price)
            positions = self._get_grid_positions(trade)
            taken = self._get_taken_levels(trade)

            if positions:
                parts = []
                for k in sorted(positions.keys(), key=lambda x: int(x)):
                    v = positions[k]
                    try:
                        idx = int(k)
                        entry = float(v.get("entry", 0))
                        qty = float(v.get("qty", 0))
                        margin = entry * qty / lev  # ★ 保证金
                        tp_price = self._grid_tp_price(idx)
                        tp_pct = (tp_price - entry) / entry * 100 if entry > 0 else 0
                        parts.append(
                            f"格{idx}={entry:.2f}(卖点={tp_price:.2f}, {tp_pct:+.2f}%, 保证金={margin:.0f})"
                        )
                    except Exception:
                        pass
                logger.info(
                    f"{GRID_TAG}    └ 持仓: {' '.join(parts)} | "
                    f"共{len(positions)}格 | 已止盈{len(taken)}格"
                )
            else:
                logger.info(
                    f"{GRID_TAG}    └ 持仓: 无 | 共0格 | 已止盈{len(taken)}格"
                )

            # 下次加仓 / 下次止盈
            next_add_idx = None
            next_reduce_idx = None

            if self._is_short:
                for i in range(cur_idx + 1, len(levels)):
                    if str(i) not in positions:
                        next_add_idx = i
                        break
                for i in range(cur_idx, -1, -1):
                    if str(i) in positions:
                        next_reduce_idx = i
                        break
            else:
                for i in range(cur_idx, -1, -1):
                    if str(i) not in positions:
                        next_add_idx = i
                        break
                for i in range(cur_idx + 1, len(levels)):
                    if str(i) in positions:
                        next_reduce_idx = i
                        break

            next_add_str = "无"
            if next_add_idx is not None:
                p = levels[next_add_idx]
                diff = (p - price) / price * 100
                next_add_str = f"格{next_add_idx}@{p:.2f}({diff:+.2f}%)"

            next_reduce_str = "无"
            if next_reduce_idx is not None:
                v = positions.get(str(next_reduce_idx))
                if v:
                    try:
                        tp_price = self._grid_tp_price(next_reduce_idx)
                        diff = (tp_price - price) / price * 100
                        next_reduce_str = (
                            f"格{next_reduce_idx}@{tp_price:.2f}({diff:+.2f}%)"
                        )
                    except Exception:
                        pass

            logger.info(
                f"{GRID_TAG}    └ 下次加仓={next_add_str} | 下次止盈={next_reduce_str}"
            )

        except Exception:
            logger.warning(f"{GRID_TAG} _log_state_detail 异常", exc_info=True)


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