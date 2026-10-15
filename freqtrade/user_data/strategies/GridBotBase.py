# freqtrade/user_data/strategies/GridBotBase.py
"""
网格机器人基类（最小可用版）

设计要点：
  - 一个网格 = 一个 trade（freqtrade 单 pair 只能有一个 trade）
  - 每格状态用 custom_data 记录：level_idx / qty / entry_price / closed
  - 用 confirm_trade_entry 拦截"到价才开仓"，用 custom_exit 逐格止盈
  - 复用 DcaTpBotBase 的基础设施（图表标记、HTF、Pump、时间止损等）
  - 不用 adjust_trade_position 加仓（避免与 DCA 冲突）

不做的事情：
  - 不做"每格一个 trade"（freqtrade 不支持）
  - 不做多空同时（由子类 can_short 决定）
"""

import sys
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
RESET = "\033[0m"


class GridBotBase(DcaTpBotBase):
    """
    网格机器人基类。

    子类必须：
      - 设置 can_short = False（做多网格）或 True（做空网格）

    配置键（runtime config）：
      grid:
        upper_price        : float   # 网格上限价
        lower_price        : float   # 网格下限价
        grid_count         : int     # 网格数量 N（会生成 N+1 条格线）
        spacing_algo       : str     # 'arithmetic'（默认）或 'geometric'
        amount_per_grid    : float   # 每格下单保证金（USDT）
        tp_per_grid_pct    : float   # 每格止盈百分比（例如 0.5 表示 0.5%）
        start_mode         : str     # 'wait'（默认，等价格进入区间）/ 'immediate'
        stop_below_lower   : bool    # 跌破下沿是否止损
        stop_above_upper   : bool    # 涨破上沿是否停止（暂只做标记）
        max_open_grids     : int     # 同时最多持有的格数（默认 1，网格通常 1）
    """

    timeframe = '5m'          # 网格用较小周期
    can_short = False         # 子类覆盖

    use_exit_signal = True
    trailing_stop = False
    position_adjustment_enable = False   # ★ 网格不通过 DCA 加仓
    use_custom_stoploss = False

    # ============================================================
    # ★ 覆盖基类的 get_runtime_config：网格读 gridConfig 而不是 long/short
    # ============================================================
    def get_runtime_config(self):
        custom = (self.config or {}).get("custom_params", {}) or {}

        # 1) 推荐路径：后端把网格配置平铺到 custom_params.config
        if custom.get("config"):
            return custom["config"]

        # 2) 兼容：custom_params.gridConfig / custom_params.grid
        if custom.get("gridConfig"):
            return custom["gridConfig"]
        if custom.get("grid"):
            return custom["grid"]

        # 3) 兜底：ConfigManager 里的 grid 键
        try:
            from core.config_manager import ConfigManager
            return ConfigManager.get("grid") or {}
        except Exception:
            return {}

    # ============================================================
    # 配置读取
    # ============================================================
    def _grid_cfg(self):
        cfg = self.get_runtime_config() or {}
        return self._cfg(cfg, "grid", default={}) or {}

    # ============================================================
    # 网格线计算
    # ============================================================
    def _build_grid_levels(self):
        """
        返回格线价格列表（升序），长度 = grid_count + 1。

        arithmetic:
            price[i] = lower + i * (upper - lower) / N
        geometric:
            ratio = (upper / lower) ** (1 / N)
            price[i] = lower * (ratio ** i)
        """
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
        """给定价格，找到它落在的格区间索引 i，使得 levels[i] <= price < levels[i+1]"""
        levels = self._build_grid_levels()
        if not levels:
            return None
        if price < levels[0] or price > levels[-1]:
            return None
        # 二分
        import bisect
        idx = bisect.bisect_right(levels, price) - 1
        if idx < 0:
            idx = 0
        if idx >= len(levels) - 1:
            idx = len(levels) - 2
        return idx

    # ============================================================
    # 交易方向辅助
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
    # 禁用 DCA 基类的信号（网格不用 RSI/MACD/BB 开仓）
    # ============================================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        网格开仓完全由 confirm_trade_entry 判断（价格触线）。
        这里把 enter_* 全部置 0，防止基类的信号逻辑误开仓。
        """
        col_long = "enter_long"
        col_short = "enter_short"
        if col_long not in dataframe.columns:
            dataframe[col_long] = 0
        if col_short not in dataframe.columns:
            dataframe[col_short] = 0

        dataframe[col_long] = 0
        dataframe[col_short] = 0

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """网格平仓由 custom_exit 判断，不用 exit_* 信号。"""
        if self._is_short:
            dataframe['exit_short'] = 0
        else:
            dataframe['exit_long'] = 0
        return dataframe

    # ============================================================
    # 开仓拦截：价格触线才开仓
    # ============================================================
    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force,
                            current_time, entry_tag, side, **kwargs):
        """
        只有满足以下条件才允许开仓：
          1. 价格落在 [lower, upper] 区间内
          2. 当前没有已持有的格（单格模式）或持有格数 < max_open_grids
          3. 该格之前未被开过（记录在 bot 级别 custom_data，用 dict 存）
        """
        try:
            g = self._grid_cfg()

            upper = self._cfg_float(g, "upper_price", 0.0)
            lower = self._cfg_float(g, "lower_price", 0.0)
            if upper <= 0 or lower <= 0:
                logger.warning(f"[{pair}] 网格上下沿未配置，拒绝开仓")
                return False

            # 已开过的格索引（bot 级别，不用 trade，因为 trade 还不存在）
            used_levels = self._get_bot_grid_used_levels()
            max_grids = self._cfg_int(g, "max_open_grids", 1)

            if len(used_levels) >= max_grids:
                logger.info(
                    f"[{pair}] {YELLOW}网格已达最大持有数 {max_grids}，拒绝开仓{RESET}"
                )
                return False

            # 价格必须落在区间内
            if rate < lower or rate > upper:
                logger.info(
                    f"[{pair}] 当前价 {rate:.4f} 不在网格区间 [{lower:.4f}, {upper:.4f}]，拒绝开仓"
                )
                return False

            idx = self._find_grid_index(rate)
            if idx is None:
                return False

            if idx in used_levels:
                logger.info(f"[{pair}] 格 {idx} 已持有/已用过，拒绝重复开仓")
                return False

            # 记录将要开仓的格
            self._set_bot_grid_pending_level(pair, idx)

            # 记录图表标记
            candle_ts = self._index_candle_key(current_time)
            self._record_chart_marker(
                event_type="grid_entry_signal", pair=pair, trade_id=0,
                side=self._side_str, price=rate, amount=amount,
                current_time=current_time,
                message=f"网格开仓 格{idx}",
                candle_time=candle_ts,
            )

            logger.info(
                f"[{pair}] {GREEN}网格开仓信号 {RESET}"
                f"格={idx}, 价格={rate:.4f}, "
                f"区间=[{lower:.4f}, {upper:.4f}], 格线={self._build_grid_levels()}"
            )
            return True

        except Exception:
            logger.exception(f"[{pair}] confirm_trade_entry 异常")
            return False

    # ============================================================
    # order_filled：把 pending 格信息固化到 trade
    # ============================================================
    def order_filled(self, pair, trade, order, current_time, **kwargs):
        """开仓成交后，把格信息写入 trade custom_data。"""
        try:
            super().order_filled(pair, trade, order, current_time, **kwargs)
        except Exception:
            logger.exception(f"[{pair}] super().order_filled 异常")

        try:
            if order.ft_order_side != self._entry_order_side:
                return

            # 是否已初始化过格信息
            if self._get_bool(trade, "grid_initialized", False):
                return

            idx = self._get_bot_grid_pending_level(trade.pair)
            if idx is None:
                idx = self._find_grid_index(float(order.average or trade.open_rate))

            entry_price = float(order.average or trade.open_rate)
            qty = abs(float(order.amount or trade.amount or 0.0))

            self._set(trade, "grid_level_idx", idx)
            self._set(trade, "grid_entry_price", entry_price)
            self._set(trade, "grid_entry_qty", qty)
            self._set(trade, "grid_initialized", True)
            self._set(trade, "grid_closed", False)

            # 记入已用格集合
            self._add_bot_grid_used_level(trade.pair, idx)
            self._clear_bot_grid_pending_level(trade.pair)

            logger.info(
                f"[{pair}] 网格格信息已写入 trade: "
                f"level_idx={idx}, entry_price={entry_price:.4f}, qty={qty}"
            )

        except Exception:
            logger.exception(f"[{pair}] order_filled 网格记录失败")


    def _remove_bot_grid_used_level(self, pair, idx: int):
        try:
            from core.config_manager import ConfigManager
            cur = self._get_bot_grid_used_levels()
            cur.discard(int(idx))
            ConfigManager.set_bot_kv(
                f"grid_used_levels_{self._side_str}",
                list(cur),
            )
        except Exception:
            logger.warning(f"[{pair}] 移除已用格失败 idx={idx}", exc_info=True)


    # ============================================================
    # custom_exit：逐格止盈 / 跌破下沿止损
    # ============================================================
    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        # 先让基类处理时间止损 / ROI 止损
        try:
            base_exit = super().custom_exit(
                pair, trade, current_time, current_rate, current_profit, **kwargs
            )
            if base_exit:
                return base_exit
        except Exception:
            logger.exception(f"[{pair}] super().custom_exit 异常")

        try:
            g = self._grid_cfg()

            lower = self._cfg_float(g, "lower_price", 0.0)
            upper = self._cfg_float(g, "upper_price", 0.0)
            tp_pct = self._cfg_float(g, "tp_per_grid_pct", 0.5)
            stop_below = bool(g.get("stop_below_lower", True))

            entry_price = self._get_float(trade, "grid_entry_price", 0.0)
            level_idx = self._get_int(trade, "grid_level_idx", -1)
            initialized = self._get_bool(trade, "grid_initialized", False)

            if not initialized or entry_price <= 0:
                return None

            rate = float(current_rate or 0.0)
            if rate <= 0:
                return None

            # ── 做多网格：达到 entry * (1 + tp_pct/100) 平仓
            # ── 做空网格：达到 entry * (1 - tp_pct/100) 平仓
            if self._is_short:
                tp_price = entry_price * (1 - tp_pct / 100.0)
                tp_hit = rate <= tp_price
                sl_hit = stop_below and upper > 0 and rate >= upper  # 空头"上沿"是亏损方向
            else:
                tp_price = entry_price * (1 + tp_pct / 100.0)
                tp_hit = rate >= tp_price
                sl_hit = stop_below and lower > 0 and rate <= lower

            if tp_hit:
                self._record_chart_marker(
                    event_type="grid_tp", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=rate,
                    amount=abs(float(trade.amount or 0)),
                    current_time=current_time,
                    message=f"网格止盈 格{level_idx}",
                    candle_time=self._index_candle_key(current_time),
                )
                logger.info(
                    f"[{pair}] {GREEN}网格止盈 {RESET}"
                    f"格={level_idx}, entry={entry_price:.4f}, "
                    f"tp={tp_price:.4f}, now={rate:.4f}"
                )
                self._remove_bot_grid_used_level(pair, level_idx)
                return f"grid_tp_lv{level_idx}"

            if sl_hit:
                self._record_chart_marker(
                    event_type="grid_stop", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=rate,
                    amount=abs(float(trade.amount or 0)),
                    current_time=current_time,
                    message=f"网格止损 格{level_idx}",
                    candle_time=self._index_candle_key(current_time),
                )
                logger.info(
                    f"[{pair}] {RED}网格止损 {RESET}"
                    f"格={level_idx}, entry={entry_price:.4f}, "
                    f"下沿={lower:.4f}, now={rate:.4f}"
                )
                # ★ 止损后同样释放该格，允许回到区间时重新进入
                self._remove_bot_grid_used_level(pair, level_idx)
                return f"grid_stop_lv{level_idx}"

            return None

        except Exception:
            logger.exception(f"[{pair}] custom_exit 网格判断异常")
            return None

    # ============================================================
    # adjust_trade_position：网格模式不通过 DCA 加仓
    # ============================================================
    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, **kwargs):
        """
        网格用"一格一仓"模式，不用 adjust_trade_position 加仓。
        如果你想加"止盈后再次进下一格"，由 confirm_trade_entry 在 trade 平仓后
        再次触发即可（freqtrade 会在下一个信号周期重新评估）。
        """
        return None

    # ============================================================
    # bot 级别 custom_data：已用格 / 待开仓格
    # ============================================================
    def _get_bot_grid_used_levels(self) -> set:
        try:
            from core.config_manager import ConfigManager
            raw = ConfigManager.get_bot_kv(f"grid_used_levels_{self._side_str}")
            if not raw:
                return set()
            return set(int(x) for x in raw)  # raw 已经是 list
        except Exception:
            logger.warning("[Grid] 读取已用格失败", exc_info=True)
            return set()

    def _add_bot_grid_used_level(self, pair, idx: int):
        try:
            from core.config_manager import ConfigManager
            cur = self._get_bot_grid_used_levels()
            cur.add(int(idx))
            ConfigManager.set_bot_kv(
                f"grid_used_levels_{self._side_str}",
                list(cur),
            )
        except Exception:
            logger.warning(f"[{pair}] 记录已用格失败 idx={idx}", exc_info=True)

    def _clear_bot_grid_used_levels(self):
        try:
            from core.config_manager import ConfigManager
            ConfigManager.set_bot_kv(f"grid_used_levels_{self._side_str}", [])
        except Exception:
            pass

    def _set_bot_grid_pending_level(self, pair, idx: int):
        try:
            from core.config_manager import ConfigManager
            ConfigManager.set_bot_kv(f"grid_pending_level_{self._side_str}", int(idx))
        except Exception:
            pass

    def _get_bot_grid_pending_level(self, pair):
        try:
            from core.config_manager import ConfigManager
            raw = ConfigManager.get_bot_kv(f"grid_pending_level_{self._side_str}")
            if raw is None or raw == "":
                return None
            return int(raw)
        except Exception:
            return None

    def _clear_bot_grid_pending_level(self, pair):
        try:
            from core.config_manager import ConfigManager
            ConfigManager.set_bot_kv(f"grid_pending_level_{self._side_str}", None)
        except Exception:
            pass


# ============================================================
# 子类：只设置方向
# ============================================================
class GridBotLong(GridBotBase):
    can_short = False


class GridBotShort(GridBotBase):
    can_short = True