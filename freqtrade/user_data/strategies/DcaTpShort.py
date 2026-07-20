import sys
from pathlib import Path

USER_DATA_DIR = Path(__file__).resolve().parents[1]
if str(USER_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(USER_DATA_DIR))

from core.config_manager import ConfigManager
from freqtrade.strategy.interface import IStrategy
from freqtrade.persistence import Trade, Order
from pandas import DataFrame, Timestamp
import pandas as pd
from typing import Any, Optional
import talib.abstract as ta
from datetime import datetime
import logging

RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RESET = "\033[0m"
logger = logging.getLogger(__name__)


class DcaTpShort(IStrategy):
    timeframe = '30m'
    stoploss = -9
    can_short = True
    can_long = False
    use_exit_signal = False
    trailing_stop = False
    position_adjustment_enable = True
    use_custom_stoploss = True

    def get_runtime_config(self):

        return ConfigManager.get("short")

    def _cfg(self, cfg: dict, *keys, default=None):
        cur = cfg
        for key in keys:
            if not isinstance(cur, dict):
                return default
            if key not in cur:
                return default
            cur = cur[key]
        return default if cur is None else cur

    def _roi_target(self, cfg: dict, elapsed: float) -> tuple[float, int]:
        levels = self._cfg(cfg, "tp", "roi_levels", default=[]) or []
        parsed = []
        for level in levels:
            if not isinstance(level, dict):
                continue
            try:
                minutes = int(level.get("minutes", 0))
                roi = float(level.get("roi", 0))
            except Exception:
                continue
            parsed.append((minutes, roi / 100.0))

        parsed.sort(key=lambda item: item[0], reverse=True)
        for minutes, roi in parsed:
            if elapsed >= minutes:
                return roi, minutes
        return 0.0, 0

    minimal_roi = {"0": 999.0}

    def leverage(self, pair: str, **kwargs) -> float:
        return 10

    def on_trade_open(self, trade: Trade, **kwargs) -> None:
        flags = {
            'dca_count': 0, 'tp_count': 0, 'dca_done': False,
            'last_dca_candle': None, 'last_dca_time': None,
            'need_resell': False, 'last_tp_time': None,
            'trend_level': 0,
            'reset_needed': False,
            'loss_tp_armed': False,
            'loss_tp_min_profit': 0.0,
        }

        for k, v in flags.items():
            self._set(trade, k, v)
        self._set(trade, 'dynamic_avg_entry', float(trade.open_rate or 0.0))
        base_avg = float(trade.open_rate or 0.0)
        self._set(trade, 'grid_upper', float(base_avg * 1.02))
        self._set(trade, 'grid_lower', float(base_avg * 0.98))
        self._set(trade, 'last_grid_action_time', None)
        self._set(trade, 'grid_count', 0)
        self._set(trade, 'grid_added_total_usdt', 0.0)
        self._set(trade, 'grid_added_total_qty', 0.0)
        self._set(trade, 'grid_reduced_total_usdt', 0.0)

    def _serial(self, v):
        if v is None:
            return None

        if isinstance(v, (pd.Timestamp, Timestamp, datetime)):
            return int(pd.Timestamp(v).timestamp())

        try:
            import numpy as np
            if isinstance(v, (np.floating, np.integer)):
                return float(v)
            if isinstance(v, np.bool_):
                return bool(v)
        except ImportError:
            pass

        if isinstance(v, (int, float, bool)):
            return v

        if isinstance(v, str):
            s = v.strip()
            if s.lower() in ("", "null", "none", "nan", "na", "n/a"):
                return None
            return s
        return str(v)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cfg = self.get_runtime_config()
        entry_cfg = self._cfg(cfg, "entry", default={}) or {}
        rsi_cfg = self._cfg(entry_cfg, "rsi", default={}) or {}
        bb_cfg = self._cfg(entry_cfg, "bb", default={}) or {}
        macd_cfg = self._cfg(entry_cfg, "macd", default={}) or {}
        volume_cfg = self._cfg(entry_cfg, "volume", default={}) or {}

        rsi_period = int(rsi_cfg.get("period", 14) or 14)
        bb_period = int(bb_cfg.get("period", 20) or 20)
        bb_std = float(bb_cfg.get("std", 2) or 2)
        macd_fast = int(macd_cfg.get("fast", 12) or 12)
        macd_slow = int(macd_cfg.get("slow", 26) or 26)
        macd_signal = int(macd_cfg.get("signal", 9) or 9)

        upper, mid, lower = ta.BBANDS(
            dataframe['close'],
            timeperiod=bb_period,
            nbdevup=bb_std,
            nbdevdn=bb_std
        )
        dataframe['bb_upperband'] = upper
        dataframe['bb_midband'] = mid
        dataframe['bb_lowerband'] = lower
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=rsi_period)
        dataframe['volume_sma_20'] = ta.SMA(dataframe['volume'], timeperiod=20)

        df30 = self.dp.get_pair_dataframe(metadata['pair'], '30m')

        if not df30.empty:
            macd, macdsignal, macdhist = ta.MACD(
                df30['close'],
                fastperiod=macd_fast,
                slowperiod=macd_slow,
                signalperiod=macd_signal
            )
            # KDJ
            k, d = ta.STOCH(df30['high'], df30['low'], df30['close'],
                            fastk_period=5, slowk_period=3, slowk_matype=0,
                            slowd_period=3, slowd_matype=0)
            j = 3 * k - 2 * d
            # EMA
            ema9 = ta.EMA(df30['close'], timeperiod=9)
            ema21 = ta.EMA(df30['close'], timeperiod=21)
            ema99 = ta.EMA(df30['close'], timeperiod=99)
            adx = ta.ADX(df30['high'], df30['low'], df30['close'])

            series_map = {
                'macd_30': macd, 'macdsig_30': macdsignal, 'macdhist_30': macdhist,
                'k_30': k, 'd_30': d, 'j_30': j,
                'ema9_30': ema9, 'ema21_30': ema21, 'ema99_30': ema99,
                'adx_30': adx
            }
            for name, series in series_map.items():
                dataframe[name] = pd.Series(series, index=df30.index).reindex(dataframe.index).ffill()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cfg = self.get_runtime_config()
        entry_cfg = self._cfg(cfg, "entry", default={}) or {}
        rsi_cfg = self._cfg(entry_cfg, "rsi", default={}) or {}
        bb_cfg = self._cfg(entry_cfg, "bb", default={}) or {}
        volume_cfg = self._cfg(entry_cfg, "volume", default={}) or {}

        rsi_enable = bool(rsi_cfg.get("enable", True))
        bb_enable = bool(bb_cfg.get("enable", True))
        volume_enable = bool(volume_cfg.get("enable", True))
        rsi_value = float(rsi_cfg.get("value", 65) or 65)

        conds = []
        if bb_enable and 'bb_upperband' in dataframe.columns:
            conds.append(dataframe['close'] > dataframe['bb_upperband'])
        if rsi_enable and 'rsi' in dataframe.columns:
            conds.append(dataframe['rsi'] > rsi_value)
        if volume_enable and 'volume_sma_20' in dataframe.columns:
            conds.append(dataframe['volume'] > dataframe['volume_sma_20'])

        if conds:
            short_cond = conds[0]
            for cond in conds[1:]:
                short_cond = short_cond & cond
        else:
            short_cond = pd.Series(False, index=dataframe.index)

        dataframe['enter_short'] = short_cond.astype(int)
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_short'] = 0
        return dataframe

    def _clean_val(self, v: Any) -> Optional[Any]:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            if not s or s.lower() in ("null", "none", "nan", "na", "n/a"):
                return None
            return s
        try:
            import numpy as np
            if isinstance(v, (np.floating, np.integer)):
                return float(v)
            if isinstance(v, np.bool_):
                return bool(v)
        except ImportError:
            pass
        if isinstance(v, (int, float, bool)):
            return v
        return str(v)

    def _get(self, trade: Trade, key: str, default: Any = None) -> Any:
        try:
            raw = trade.get_custom_data(key)
        except Exception:
            raw = None
        val = self._clean_val(raw)
        return default if val is None else val

    def _get_float(self, trade: Trade, key: str, default: float = 0.0) -> float:
        v = self._get(trade, key, None)
        if v is None:
            return default
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        try:
            f = float(v)
            if not (float('-inf') < f < float('inf')) or pd.isna(f):
                return default
            return f
        except Exception:
            return default

    def _get_int(self, trade: Trade, key: str, default: int = 0) -> int:
        v = self._get(trade, key, None)
        if v is None:
            return default
        if isinstance(v, bool):
            return int(v)
        try:
            return int(float(v))
        except Exception:
            return default

    def _get_bool(self, trade: Trade, key: str, default: bool = False) -> bool:
        v = self._get(trade, key, None)
        if v is None:
            return default
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        s = str(v).strip().lower()
        if s in ("1", "true", "t", "yes", "y"):
            return True
        if s in ("0", "false", "f", "no", "n"):
            return False
        try:
            return bool(float(s))
        except Exception:
            return default

    def _set(self, trade: Trade, key: str, value: Any) -> None:
        trade.set_custom_data(key, self._serial(value))

    def _collateral_total(self) -> float:
        try:
            return float(self.wallets.get_total('USDT'))
        except Exception:
            return 0.0

    def _qty_from_usdt(self, usdt: float, price: float, lev: float) -> float:
        try:
            return (usdt * float(lev)) / float(price) if price and lev else 0.0
        except Exception:
            return 0.0

    def _record_add_usdt(self, trade: Trade, key: str, usdt: float) -> None:
        prev = self._get_float(trade, key, 0.0)
        try:
            add = float(usdt)
            if pd.isna(add) or not (float('-inf') < add < float('inf')):
                add = 0.0
        except Exception:
            add = 0.0
        self._set(trade, key, prev + add)

    def _record_add_qty(self, trade: Trade, key: str, qty: float) -> None:
        prev = self._get_float(trade, key, 0.0)
        try:
            add = float(qty)
            if pd.isna(add) or not (float('-inf') < add < float('inf')):
                add = 0.0
        except Exception:
            add = 0.0
        self._set(trade, key, prev + add)

    def _record_add(self, trade: Trade, key: str, value: float) -> None:
        prev = self._get_float(trade, key, 0.0)
        try:
            add = float(value)
            if pd.isna(add) or not (float('-inf') < add < float('inf')):
                add = 0.0
        except Exception:
            add = 0.0
        self._set(trade, key, prev + add)

    def trend_add(self, trade: Trade, last: dict, margin: float, collateral: float, current_time: datetime,
                  current_profit: float):
        cfg = self.get_runtime_config()
        trend_cfg = self._cfg(cfg, "trend_add", default={}) or {}
        entry_cfg = self._cfg(cfg, "entry", default={}) or {}
        macd_cfg = self._cfg(entry_cfg, "macd", default={}) or {}
        if not bool(trend_cfg.get("enable", True)) or not bool(macd_cfg.get("enable", True)):
            return None

        level = self._get_int(trade, 'trend_level', 0)
        reset_needed = self._get_bool(trade, 'reset_needed', False)
        u = self._get_int(trade, 'dca_count', 0)
        levels = trend_cfg.get("levels") or []
        level_cfg = levels[min(level, len(levels) - 1)] if levels else {}
        max_count = max(1, int(trend_cfg.get("max_count", 3) or 3))
        try:
            profit_threshold = float(level_cfg.get("profit", 2) or 2) / 100.0
        except Exception:
            profit_threshold = 0.02
        try:
            rsi_threshold = float(level_cfg.get("rsi", 40) or 40)
        except Exception:
            rsi_threshold = 40.0
        try:
            amount_pct = float(level_cfg.get("amount", 0.5) or 0.5) / 100.0
        except Exception:
            amount_pct = 0.005

        is_bearish_trend = (
                last.get('macd_30', 0) < last.get('macdsig_30', 0) and
                last.get('k_30', 0) < last.get('d_30', 0) and
                last.get('adx_30', 0) > 25 and
                last.get('ema9_30', 0) < last.get('ema21_30', 0) < last.get('ema99_30', 0)
        )
        price = last.get('close', None)

        def _add_trend_total_usdt(x):
            self._record_add_usdt(trade, 'trend_total_added_usdt', x)

        if (
                level < max_count
                and u == 0
                and (not reset_needed)
                and price is not None
                and is_bearish_trend
                and current_profit >= profit_threshold
                and float(last.get("rsi", 0) or 0) <= rsi_threshold
        ):
            self._set(trade, 'trend_level', level + 1)
            self._set(trade, 'kdj_reduced', False)
            add_amt = collateral * amount_pct  # 趋势加仓
            _add_trend_total_usdt(abs(add_amt))

            avg_price = getattr(trade, 'open_rate', None)
            if avg_price is None:
                avg_price = 0.0

            logger.info(f"[{trade.pair}] {GREEN}[空头趋势加仓 {amount_pct * 100:.1f}%]{RESET}, "
                        f"{YELLOW} 保证金={margin:.2f}{RESET}, 当前价={price:.4f}, "
                        f"加仓={abs(add_amt):.4f} USDT, 新均价={avg_price:.4f}")
            return float(add_amt), 'trend_add20_bear'

        if level > 0:
            kdj_reduced = self._get_bool(trade, 'kdj_reduced', False)
            if (not kdj_reduced) and last.get('k_30', 0) > last.get('d_30', 0):
                total_trend_usdt = self._get_float(trade, 'trend_total_added_usdt', 0.0) or 0.0
                buy_usdt = min(total_trend_usdt, margin)
                amt = float(buy_usdt)
                self._set(trade, 'trend_total_added_usdt', 0.0)
                self._set(trade, 'trend_level', 0)
                self._set(trade, 'kdj_reduced', True)

                logger.info(f"[{trade.pair}] {RED}[KDJ 减仓]{RESET}, "
                            f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={last.get('close'):.4f}, "
                            f"减仓={abs(amt):.4f} USDT")
                return float(-amt), 'kdj_reduce_by_trend_added'

    def dca_add(self, trade: Trade, df: DataFrame, last: dict, current_time: datetime, current_rate: float):
        cfg = self.get_runtime_config()
        dca_cfg = self._cfg(cfg, "dca", default={}) or {}
        if not bool(dca_cfg.get("enable", True)):
            return None

        last_idx = df.index[-1]
        candle_ts = pd.Timestamp(last_idx).tz_localize(None).floor('min')
        last_rsi = df['rsi'].iat[-1] if 'rsi' in df.columns else None
        last_j = df['j_30'].iat[-1] if 'j_30' in df.columns else None

        u = self._get_int(trade, 'dca_count', 0)
        levels = dca_cfg.get("levels") or []
        level_cfg = levels[min(u, len(levels) - 1)] if levels else {}
        max_dca = int(dca_cfg.get("max_count", 7) or 7)
        cooldown_minutes = int(dca_cfg.get("cooldown_minutes", 60) or 60)
        last_dca = self._get_int(trade, 'last_dca_candle', 0)
        last_dca_ts = Timestamp(int(last_dca), unit='s') if last_dca else None
        if last_dca_ts is None or last_dca_ts != candle_ts:
            self._set(trade, 'dca_done', False)
        dca_done = self._get_bool(trade, 'dca_done', False)

        within_dca_cooldown = False
        last_dca_time = self._get_int(trade, 'last_dca_time', 0)
        if last_dca_time:
            try:
                last_dca_dt = datetime.fromtimestamp(int(last_dca_time))
                if (current_time - last_dca_dt).total_seconds() < 60 * cooldown_minutes:
                    within_dca_cooldown = True
            except Exception:
                within_dca_cooldown = False

        if u >= max_dca:
            logger.debug(f"[{trade.pair}] 已达 DCA 次数上限 u={u}，跳过浮亏 DCA")
            return None

        avg_entry = self._get_float(trade, 'dynamic_avg_entry', float(trade.open_rate or 0.0)) or float(
            trade.open_rate or 0.0)
        try:
            lev = float(self.leverage(trade.pair) or 1.0)
        except Exception:
            lev = 1.0

        try:
            drawdown = abs(float(level_cfg.get("drawdown", -3) or -3))
        except Exception:
            drawdown = 3.0

        threshold = avg_entry * (1 + drawdown / 100.0)  # dca 阈值
        try:
            rsi_limit = float(level_cfg.get("rsi_limit", 80) or 80)
        except Exception:
            rsi_limit = 80.0
        try:
            j_limit = float(level_cfg.get("j_limit", 100) or 100)
        except Exception:
            j_limit = 100.0
        cond_mode = str(dca_cfg.get("condition", "or")).lower()
        cond_j = (last_j is not None and last_j > j_limit)
        cond_rsi = (last_rsi is not None and last_rsi > rsi_limit)
        if cond_mode == "and":
            triggered_cond = cond_j and cond_rsi
            triggered_label = f"J>{j_limit:g} & RSI>{rsi_limit:g}"
        else:
            triggered_cond = cond_j or cond_rsi
            triggered_label = f"J>{j_limit:g} 或 RSI>{rsi_limit:g}"

        try:
            candle_close = float(last.get('close')) if last.get('close') is not None else None
        except Exception:
            candle_close = None

        logger.debug(
            f"[{trade.pair}] DCA(check for short): u={u}, avg_entry={avg_entry:.8f}, threshold={threshold:.8f}, candle_close={candle_close}, triggered_cond={triggered_cond}")

        if within_dca_cooldown:
            logger.debug(f"[{trade.pair}] 浮亏 DCA 冷却中")
            return None
        if dca_done:
            logger.debug(f"[{trade.pair}] 本根 K 已执行 DCA，跳过")
            return None

        if (candle_close is not None) and triggered_cond and (candle_close >= threshold):
            collateral = self._collateral_total()
            try:
                margin = float(trade.stake_amount)
            except Exception:
                margin = 0.0

            try:
                dca_pct = float(level_cfg.get("amount", 1) or 1) / 100.0
            except Exception:
                dca_pct = 0.01
            sell_amt = collateral * dca_pct
            try:
                prev_qty = abs(trade.amount)
            except Exception:
                prev_qty = 0.0
            prev_cost = prev_qty * avg_entry
            added_qty = self._qty_from_usdt(sell_amt, candle_close, lev)
            new_avg_entry = avg_entry
            if (prev_qty + added_qty) > 0:
                new_avg_entry = (prev_cost + sell_amt * lev) / (prev_qty + added_qty)

            self._set(trade, 'dca_count', u + 1)
            self._set(trade, 'dca_done', True)
            self._set(trade, 'last_dca_candle', int(candle_ts.timestamp()))
            self._set(trade, 'last_dca_time', int(current_time.timestamp()))
            self._set(trade, 'tp_count', 0)
            self._set(trade, 'dynamic_avg_entry', float(new_avg_entry))

            logger.info(
                f"[{trade.pair}] {RED}[浮亏 DCA 加仓 {dca_pct * 100:.1f}%]{RESET}, u=({u}->{u + 1}), "
                f"触发条件={triggered_label}, 触发价={threshold:.4f}, 收盘价={candle_close:.4f}, "
                f"{YELLOW}保证金={margin:.4f}{RESET}, 加仓={sell_amt:.4f} USDT, 新均价={new_avg_entry:.4f}"
            )
            return float(sell_amt), f"dca_u={u + 1}"

    def profit_resell(self, trade: Trade, last: dict, collateral: float):
        cfg = self.get_runtime_config()
        tp_cfg = self._cfg(cfg, "tp", default={}) or {}
        need_resell = self._get_bool(trade, 'need_resell', False)
        if not need_resell or not bool(tp_cfg.get("rebuy_enable", True)):
            return None

        price = last.get('close', None)
        if price is None:
            return None

        try:
            lev = float(self.leverage(trade.pair) or 1.0)
        except Exception:
            lev = 1.0

        try:
            current_qty = float(trade.amount)
        except Exception:
            current_qty = 0.0

        current_value = (current_qty * price) / lev if price and lev else 0.0
        try:
            target_wallet_percent = float(tp_cfg.get("target_wallet_percent", 5) or 5)
        except Exception:
            target_wallet_percent = 5.0
        target_value = collateral * (target_wallet_percent / 100.0)
        sell_amt = target_value - current_value

        if sell_amt <= 0:
            self._set(trade, 'need_resell', False)
            return None

        n = self._get_int(trade, 'tp_count', 0)

        self._set(trade, 'need_resell', False)
        self._set(trade, 'dca_done', False)
        self._set(trade, 'tp_count', n + 1)

        avg_price = getattr(trade, 'open_rate', None)
        if avg_price is None:
            avg_price = 0.0

        added_qty = (sell_amt * lev) / price if price and lev else 0.0
        prev_cost = current_qty * avg_price
        new_avg = avg_price
        if (current_qty + added_qty) > 0:
            new_avg = (prev_cost + sell_amt * lev) / (current_qty + added_qty)

        logger.info(
            f"[{trade.pair}] {GREEN}[浮盈加仓至 {target_wallet_percent:.0f}%]{RESET}, "
            f"n=({n}->{n + 1}), 当前价={price:.4f}, "
            f"{YELLOW}保证金={current_value:.4f}{RESET}, "
            f"加仓={sell_amt:.4f} USDT, 新均价={new_avg:.4f}"
        )

        return float(sell_amt), "add_to_5pct"

    def tp_reduce(self, trade: Trade, last: dict, current_profit: float, margin: float, current_rate: float,
                  current_time: datetime):
        cfg = self.get_runtime_config()
        tp_cfg = self._cfg(cfg, "tp", default={}) or {}
        loss_tp_cfg = self._cfg(cfg, "loss_tp", default={}) or {}
        if not bool(tp_cfg.get("enable", True)):
            return None

        last_tp = self._get_int(trade, 'last_tp_time', None)
        if last_tp is not None:
            base_time = datetime.fromtimestamp(int(last_tp))
        else:
            base_time = trade.open_date_utc
            if getattr(base_time, 'tzinfo', None):
                base_time = base_time.replace(tzinfo=None)
        elapsed = (current_time - base_time).total_seconds() / 60
        roi_target, roi_minutes = self._roi_target(cfg, elapsed)
        u = self._get_int(trade, 'dca_count', 0)
        loss_enabled = bool(loss_tp_cfg.get("enable", True))
        loss_tp_ready = False
        if u > 0 and loss_enabled:
            try:
                trigger_loss = float(loss_tp_cfg.get("trigger_loss", -10) or -10) / 100.0
            except Exception:
                trigger_loss = -0.10
            try:
                trigger_rebound = float(loss_tp_cfg.get("trigger_rebound", 2) or 2) / 100.0
            except Exception:
                trigger_rebound = 0.02
            armed = self._get_bool(trade, 'loss_tp_armed', False)
            if current_profit <= trigger_loss:
                self._set(trade, 'loss_tp_armed', True)
                self._set(trade, 'loss_tp_min_profit', float(current_profit))
                return None
            if armed:
                min_profit = self._get_float(trade, 'loss_tp_min_profit', current_profit)
                if current_profit < min_profit:
                    self._set(trade, 'loss_tp_min_profit', float(current_profit))
                    return None
                if current_profit < trigger_rebound:
                    return None
                self._set(trade, 'loss_tp_armed', False)
                loss_tp_ready = True

        if current_profit < roi_target and not loss_tp_ready:
            return None

        # -- 浮亏 DCA 止盈 --
        if u > 0:
            try:
                current_qty = float(trade.amount)
            except Exception:
                current_qty = 0.0
            current_qty_abs = abs(current_qty)

            try:
                price = float(current_rate) if current_rate is not None else None
            except Exception:
                price = None

            try:
                lev = float(self.leverage(trade.pair) or 1.0)
            except Exception:
                lev = 1.0

            if price is None or price <= 0 or lev <= 0:
                logger.warning(f"[{trade.pair}] [浮亏 DCA 止盈跳过] 无效 price/lev (price={price}, lev={lev})")
                return None

            margin_val = margin
            collateral_total = self._collateral_total()
            try:
                target_wallet_percent = float(tp_cfg.get("target_wallet_percent", 5) or 5)
            except Exception:
                target_wallet_percent = 5.0
            target_usdt = float(collateral_total) * (target_wallet_percent / 100.0)
            target_qty = (target_usdt * lev) / price
            buy_qty = max(0.0, current_qty_abs - target_qty)

            if buy_qty <= 0:
                need_add_usdt = max(0.0, target_usdt - margin_val)
                if need_add_usdt > 0:
                    self._set(trade, 'dca_count', 0)
                    self._set(trade, 'dca_done', False)
                    self._set(trade, 'last_tp_time', int(current_time.timestamp()))

                    logger.info(
                        f"[{trade.pair}] {GREEN}[当前仓位过小，浮亏DCA止盈加仓至 {target_wallet_percent:.0f}%]{RESET}, "
                        f"保证金={margin_val:.4f}, 加仓={need_add_usdt:.4f} USDT"
                    )
                    return float(need_add_usdt), "tp_afterDCA_resell_to_target"
                return None

            try:
                buy_usdt = (buy_qty * price) / lev if lev and price else 0.0
            except Exception:
                buy_usdt = 0.0
            buy_usdt_capped = min(buy_usdt, max(0.0, margin_val))

            if buy_usdt_capped <= 0:
                logger.warning(
                    f"[{trade.pair}] [浮亏 DCA 止盈跳过] 计算到的 buy_usdt={buy_usdt_capped:.6f} 无效或被保证金限制, 跳过")
                return None

            self._set(trade, 'dca_count', 0)
            self._set(trade, 'dca_done', False)
            self._set(trade, 'last_tp_time', int(current_time.timestamp()))

            logger.info(
                f"[{trade.pair}] {GREEN}[浮亏止盈减仓至 {target_wallet_percent:.0f}%]{RESET}, "
                f"持仓时间={roi_minutes}min, 目标收益率={roi_target * 100:.0f}%, 当前收益率={current_profit * 100:.2f}%, "
                f"{YELLOW}保证金={margin:.4f} USDT, 当前价={last.get('close'):.4f}, "
                f"减仓={buy_usdt_capped:.4f} USDT"
            )
            return float(-buy_usdt_capped), "tp_afterDCA_reduce_keep_target"

        # -- 浮盈 TP 减仓 --
        try:
            reduce_percent = float(tp_cfg.get("reduce_percent", 30) or 30)
        except Exception:
            reduce_percent = 30.0
        buy_amt = (reduce_percent / 100.0) * margin
        self._set(trade, 'dca_done', False)
        self._set(trade, 'last_tp_time', int(current_time.timestamp()))
        self._set(trade, 'last_tp_margin', float(margin))
        self._set(trade, 'need_resell', bool(tp_cfg.get("rebuy_enable", True)))

        logger.info(f"[{trade.pair}] {GREEN}[浮盈分批减仓 {reduce_percent:.0f}%]{RESET}, "
                    f"持仓时间>{roi_minutes}min, 目标收益率={roi_target * 100:.0f}%, 当前收益率={current_profit * 100:.2f}%, "
                    f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={last.get('close'):.4f}, "
                    f"减仓={abs(buy_amt):.4f}")
        return float(-buy_amt), "tp30"

    # -- 网格 --
    def grid_single(self, trade: Trade, last: dict, current_time: datetime, current_rate: float,
                    margin: float = None):
        cfg = self.get_runtime_config()
        grid_cfg = self._cfg(cfg, "grid", default={}) or {}
        if not bool(grid_cfg.get("enable", True)):
            return None

        try:
            price = float(current_rate) if current_rate is not None else None
        except Exception:
            price = None

        if price is None:
            price = last.get('close', None)

        if price is None:
            return None

        if getattr(current_time, 'tzinfo', None):
            current_time = current_time.replace(tzinfo=None)

        anchor = self._get_float(trade, 'grid_anchor_price', None)
        if anchor is None or anchor <= 0:
            try:
                anchor = self._get_float(trade, 'dynamic_avg_entry', None)
            except Exception:
                anchor = None
        if anchor is None or anchor <= 0:
            try:
                anchor = float(trade.open_rate or 0.0)
            except Exception:
                anchor = None
        if anchor is None or anchor <= 0:
            return None

        # 网格阈值
        try:
            grid_lower_pct = float(grid_cfg.get("grid_lower", -2) or -2)
        except Exception:
            grid_lower_pct = -2.0
        try:
            grid_upper_pct = float(grid_cfg.get("grid_upper", 2) or 2)
        except Exception:
            grid_upper_pct = 2.0
        grid_lower = anchor * (1 + grid_lower_pct / 100.0)
        grid_upper = anchor * (1 + grid_upper_pct / 100.0)

        collateral = self._collateral_total()
        try:
            cur_margin = float(trade.stake_amount) if margin is None else float(margin)
        except Exception:
            cur_margin = 0.0
        if collateral <= 0 and cur_margin <= 0:
            return None

        last_grid_ts = self._get_int(trade, 'last_grid_action_time', None)
        if last_grid_ts is not None:
            try:
                last_dt = datetime.fromtimestamp(int(last_grid_ts))
                cooldown_minutes = int(grid_cfg.get("cooldown_minutes", 30) or 30)
                if (current_time - last_dt).total_seconds() < 60 * cooldown_minutes:
                    logger.debug(f"[{trade.pair}] 网格冷却中（{cooldown_minutes}min），上次动作 ts={last_grid_ts}")
                    return None
            except Exception:
                pass

        m = int(self._get_int(trade, 'grid_m', 0))
        max_m = 5  # 网格加仓次数上限

        try:
            lev = float(self.leverage(trade.pair) or 1.0)
            if not (lev > 0):
                lev = 1.0
        except Exception:
            lev = 1.0

        if price >= grid_upper:
            if max_m > 0 and m >= max_m:
                logger.debug(f"[{trade.pair}] 网格加仓达到上限 m={m} >= {max_m}，跳过")
                return None

            self._get_int(trade, 'dca_count', 0)
            # 动态网格加仓数量
            try:
                sell_percent = float(grid_cfg.get("sell_percent", 2) or 2)
            except Exception:
                sell_percent = 2.0
            grid_frac = max(0.01, (sell_percent / 100.0) - 0.002 * m)

            add_usdt = collateral * grid_frac

            if add_usdt <= 0:
                return None

            added_qty = self._qty_from_usdt(add_usdt, price, lev)
            if added_qty <= 0:
                logger.debug(f"[{trade.pair}] 计算到的加仓基础数量为0或无效，跳过")
                return None

            try:
                prev_qty = abs(trade.amount)
            except Exception:
                prev_qty = 0.0
            prev_base_qty = abs(prev_qty)

            prev_avg = self._get_float(trade, 'dynamic_avg_entry', float(trade.open_rate or 0.0)) or float(
                trade.open_rate or 0.0)
            prev_cost = prev_base_qty * prev_avg

            new_avg = prev_avg
            if (prev_base_qty + added_qty) > 0:
                new_avg = (prev_cost + added_qty * price) / (prev_base_qty + added_qty)

            new_m = min(m + 1, max_m) if max_m > 0 else m + 1
            new_anchor = float(price)
            # 下次网格价格
            next_buy = new_anchor * (1 + grid_lower_pct / 100.0)
            next_sell = new_anchor * (1 + grid_upper_pct / 100.0)

            self._set(trade, 'dynamic_avg_entry', float(new_avg))
            self._set(trade, 'grid_anchor_price', float(new_anchor))
            self._set(trade, 'grid_upper', float(next_sell))
            self._set(trade, 'grid_lower', float(next_buy))
            self._set(trade, 'last_grid_action_time', int(current_time.timestamp()))
            self._record_add_usdt(trade, 'grid_added_total_usdt', add_usdt)
            self._record_add_qty(trade, 'grid_added_total_qty', added_qty)
            self._set(trade, 'grid_count', int(self._get_int(trade, 'grid_count', 0) + 1))
            self._set(trade, 'grid_m', int(new_m))

            logger.info(
                f"[{trade.pair}] {RED}[网格加仓 {grid_frac * 100:.1f}%]{RESET}, 当前价={price:.4f}, 触发价={grid_upper:.4f}, "
                f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 加仓={add_usdt:.4f} USDT, 新均价={new_avg:.4f}, m={new_m}, "
                f"下次网格 减仓价={next_buy:.4f}, 加仓价={next_sell:.4f}"
            )
            return float(add_usdt), f"grid_add_{grid_frac:.3f}"

        if price <= grid_lower:
            try:
                buy_percent = float(grid_cfg.get("buy_percent", 2) or 2)
            except Exception:
                buy_percent = 2.0
            grid_reduce_frac = max(0.01, buy_percent / 100.0)
            buy_usdt = collateral * grid_reduce_frac
            buy_usdt = min(buy_usdt, cur_margin) if cur_margin > 0 else buy_usdt

            if buy_usdt <= 0:
                logger.debug(f"[{trade.pair}] 网格减仓触发，但当前保证金不足")
                return None

            new_m = max(0, m - 1)
            new_anchor = float(price)
            next_buy = new_anchor * (1 + grid_lower_pct / 100.0)
            next_sell = new_anchor * (1 + grid_upper_pct / 100.0)

            self._record_add_usdt(trade, 'grid_reduced_total_usdt', float(buy_usdt))
            self._set(trade, 'grid_anchor_price', float(new_anchor))
            self._set(trade, 'grid_upper', float(next_sell))
            self._set(trade, 'grid_lower', float(next_buy))
            self._set(trade, 'last_grid_action_time', int(current_time.timestamp()))
            self._set(trade, 'grid_count', int(self._get_int(trade, 'grid_count', 0) + 1))
            self._set(trade, 'grid_m', int(new_m))

            logger.info(
                f"[{trade.pair}] {RED}[网格减仓 {grid_reduce_frac * 100:.1f}%]{RESET}, 当前价={price:.4f}, 触发价={grid_lower:.4f}, "
                f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 减仓={buy_usdt:.4f} USDT, w={new_m}, "
                f"下次网格 减仓价={next_buy:.4f}, 加仓价={next_sell:.4f}"
            )
            return float(-buy_usdt), "grid_reduce_2pct"
        return None

    def adjust_trade_position(self, trade: Trade, current_time: datetime, current_rate: float, current_profit: float,
                              **kwargs) -> tuple[float, str] | None:
        if trade.has_open_orders:
            return None

        df, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        if df.empty:
            return None
        last = df.iloc[-1]

        try:
            margin = float(trade.stake_amount)
        except Exception:
            margin = 0.0

        if current_time.tzinfo:
            current_time = current_time.replace(tzinfo=None)
        open_time = trade.open_date_utc
        if getattr(open_time, 'tzinfo', None):
            open_time.replace(tzinfo=None)
        candle_ts = pd.Timestamp(df.index[-1]).tz_localize(None).floor('min')
        df30, _ = self.dp.get_analyzed_dataframe(trade.pair, '30m')
        if df30.empty:
            return None
        last30_ts = pd.Timestamp(df30.index[-1]).tz_localize(None).floor('min')
        if candle_ts != last30_ts:
            return None

        collateral = self._collateral_total()
        if collateral <= 0:
            return None

        # 1) 趋势加仓
        res = self.trend_add(trade, last, margin, collateral, current_time, current_profit)
        if res:
            return res

        # 2) DCA 加仓（空头）
        res = self.dca_add(trade, df, last, current_time, current_rate)
        if res:
            return res

        # 3) 浮盈加仓
        res = self.profit_resell(trade, last, collateral)
        if res:
            return res

        # 4) tp 止盈
        res = self.tp_reduce(trade, last, current_profit, margin, current_rate, current_time)
        if res:
            return res

        # 5) 网格
        res = self.grid_single(trade, last, current_time, current_rate, margin)
        if res:
            return res
        return None

    def order_filled(self, pair: str, trade: Trade, order: Order, current_time: datetime, **kwargs) -> None:
        tag = getattr(order, 'ft_order_tag', '') or ''

        if tag in ("tp30", "tp30_with_prior_repull") and order.side == "buy":
            self._set(trade, 'need_resell', True)

    def custom_stoploss(self, *args, **kwargs) -> float | None:
        trade = kwargs.get("trade")
        if trade is None and len(args) > 0:
            trade = args[0]
        if trade is None:
            return None

        cfg = self.get_runtime_config()
        sl_cfg = self._cfg(cfg, "sl", default={}) or {}
        if not bool(sl_cfg.get("enable", True)):
            return -0.99

        try:
            stoploss = float(sl_cfg.get("stoploss", -9) or -9)
        except Exception:
            stoploss = -9.0
        return stoploss / 100.0
