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


class DcaTpLong(IStrategy):
    timeframe = '30m'
    can_short = False
    use_exit_signal = False
    trailing_stop = False
    position_adjustment_enable = True
    use_custom_stoploss = True

    def get_runtime_config(self):

        cfg = ConfigManager.get("long")

        return cfg

    def _cfg(self, cfg: dict, *keys, default=None):
        cur = cfg
        for key in keys:
            if not isinstance(cur, dict):
                return default
            if key not in cur:
                return default
            cur = cur[key]
        return default if cur is None else cur

    def _roi_target(self, cfg: dict, elapsed: float):

        levels = self._cfg(
            cfg,
            "tp",
            "roi_levels",
            default=[]
        ) or []

        parsed = []

        for level in levels:
            if not isinstance(level, dict):
                continue

            try:
                minutes = int(level.get("minutes", 0))
                roi = float(level.get("roi", 0))
            except Exception:
                continue

            parsed.append(
                (
                    minutes,
                    roi / 100
                )
            )

        parsed.sort(
            key=lambda x: x[0],
            reverse=True
        )

        for minutes, roi in parsed:

            if elapsed >= minutes:
                return roi, minutes

        # 未达到任何TP条件
        return None, 0

    def leverage(self, pair, **kwargs):

        try:
            cfg = self.get_runtime_config()

            return float(
                self._cfg(
                    cfg,
                    "strategy",
                    "leverage",
                    default=10
                )
            )

        except Exception:
            return 10.0

    def _available_stake(self):

        try:
            free = self.wallets.get_free(
                "USDT"
            )

            return float(free)

        except Exception:
            return 0

    def order_filled(
            self,
            pair: str,
            trade: Trade,
            order: Order,
            current_time: datetime,
            **kwargs
    ):

        if self._get_bool(
                trade,
                "initialized",
                False
        ):
            return

        cfg = self.get_runtime_config()

        grid_cfg = self._cfg(
            cfg,
            "grid",
            default={}
        )

        upper_pct = float(
            grid_cfg.get(
                "init_upper",
                2
            )
        )

        lower_pct = float(
            grid_cfg.get(
                "init_lower",
                -2
            )
        )

        flags = {
            'dca_count': 0,
            'tp_count': 0,
            'dca_done': False,
            'last_dca_candle': None,
            'last_dca_time': None,
            'need_rebuy': False,
            'last_tp_time': None,
            'trend_level': 0,
            'last_trend_candle': None,
            'reset_needed': False,
            'grid_anchor_price': 0,
            'loss_tp_armed': False,
            'grid_w': 0,
            'loss_tp_min_profit': 0.0,
        }

        for k, v in flags.items():
            self._set(
                trade,
                k,
                v
            )

        entry_price = float(
            getattr(order, "average", None)
            or trade.open_rate
            or 0
        )

        self._set(
            trade,
            "grid_upper",
            entry_price * (1 + upper_pct / 100)
        )

        self._set(
            trade,
            "grid_lower",
            entry_price * (1 + lower_pct / 100)
        )

        self._set(
            trade,
            "grid_count",
            0
        )

        self._set(
            trade,
            "grid_added_total_usdt",
            0
        )

        self._set(
            trade,
            "grid_added_total_qty",
            0
        )

        self._set(
            trade,
            "grid_reduced_total_usdt",
            0
        )

        self._set(
            trade,
            "initialized",
            True
        )

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
        indicator_cfg = self._cfg(
            cfg,
            "indicator",
            default={}
        ) or {}

        rsi_cfg = self._cfg(
            indicator_cfg,
            "rsi",
            default={}
        ) or {}

        bb_cfg = self._cfg(
            indicator_cfg,
            "bb",
            default={}
        ) or {}

        macd_cfg = self._cfg(
            indicator_cfg,
            "macd",
            default={}
        ) or {}

        kdj_cfg = self._cfg(
            indicator_cfg,
            "kdj",
            default={}
        ) or {}

        ema_cfg = self._cfg(
            indicator_cfg,
            "ema",
            default={}
        ) or {}

        rsi_period = int(rsi_cfg.get("period", 14))
        bb_period = int(bb_cfg.get("period", 20))
        bb_std = float(bb_cfg.get("std", 2))

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

        df_tf = dataframe.copy()

        if not df_tf.empty:

            # MACD

            macd, macdsignal, macdhist = ta.MACD(
                df_tf['close'],

                fastperiod=int(
                    macd_cfg.get(
                        "fast",
                        12
                    )
                ),

                slowperiod=int(
                    macd_cfg.get(
                        "slow",
                        26
                    )
                ),

                signalperiod=int(
                    macd_cfg.get(
                        "signal",
                        9
                    )
                )
            )

            # KDJ

            k, d = ta.STOCH(
                df_tf['high'],
                df_tf['low'],
                df_tf['close'],

                fastk_period=int(
                    kdj_cfg.get(
                        "fastk",
                        5
                    )
                ),

                slowk_period=int(
                    kdj_cfg.get(
                        "slowk",
                        3
                    )
                ),

                slowd_period=int(
                    kdj_cfg.get(
                        "slowd",
                        3
                    )
                )
            )

            j = 3 * k - 2 * d

            # EMA

            ema_fast = int(
                ema_cfg.get(
                    "fast",
                    9
                )
            )

            ema_mid = int(
                ema_cfg.get(
                    "mid",
                    21
                )
            )

            ema_slow = int(
                ema_cfg.get(
                    "slow",
                    99
                )
            )

            series_map = {
                'macd_tf': macd,
                'macdsig_tf': macdsignal,
                'macdhist_tf': macdhist,
                'k_tf': k,
                'd_tf': d,
                'j_tf': j,
                f'ema{ema_fast}_tf': ta.EMA(
                    df_tf['close'],
                    timeperiod=ema_fast
                ),

                f'ema{ema_mid}_tf': ta.EMA(
                    df_tf['close'],
                    timeperiod=ema_mid
                ),

                f'ema{ema_slow}_tf': ta.EMA(
                    df_tf['close'],
                    timeperiod=ema_slow
                )
            }
            for name, series in series_map.items():
                dataframe[name] = pd.Series(
                    series,
                    index=df_tf.index
                )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        cfg = self.get_runtime_config()
        entry_cfg = self._cfg(
            cfg,
            "entry",
            default={}
        ) or {}

        rsi_cfg = self._cfg(
            entry_cfg,
            "rsi",
            default={}
        ) or {}

        bb_cfg = self._cfg(
            entry_cfg,
            "bb",
            default={}
        ) or {}

        macd_cfg = self._cfg(
            entry_cfg,
            "macd",
            default={}
        ) or {}

        rsi_enable = bool(rsi_cfg.get("enable", True))
        bb_enable = bool(bb_cfg.get("enable", True))
        macd_enable = bool(macd_cfg.get("enable", True))
        rsi_value = float(rsi_cfg.get("value", 35) or 35)

        conds = []

        if bb_enable:
            conds.append(
                dataframe['close']
                <
                dataframe['bb_lowerband']
            )

        if rsi_enable:
            conds.append(
                dataframe['rsi']
                <
                rsi_value
            )

        if macd_enable:
            conds.append(
                dataframe['macd_tf']
                >
                dataframe['macdsig_tf']
            )
        if conds:
            long_cond = conds[0]
            for cond in conds[1:]:
                long_cond = long_cond & cond
        else:
            long_cond = pd.Series(False, index=dataframe.index)

        dataframe['enter_long'] = long_cond.astype(int)
        logger.info(f"entry_cfg={entry_cfg}")
        logger.info(
            f"conds={len(conds)}, "
            f"rsi={rsi_enable}, "
            f"bb={bb_enable}, "
            f"macd={macd_enable}"
        )
        logger.info(
            f"{metadata['pair']} "
            f"RSI min={dataframe['rsi'].min()}, "
            f"BB触发={(dataframe['close'] < dataframe['bb_lowerband']).sum()}, "
            f"RSI触发={(dataframe['rsi'] < rsi_value).sum()}, "
            f"MACD触发={(dataframe['macd_tf'] > dataframe['macdsig_tf']).sum()}"
        )
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
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

    def _set(self, trade, key, value):

        value = self._serial(value)

        old = self._get(
            trade,
            key,
            None
        )

        # 数值变化过小不保存
        if isinstance(value, float) and isinstance(old, float):
            if abs(value - old) < 1e-8:
                return

        if old == value:
            return

        trade.set_custom_data(
            key,
            value
        )

    def _collateral_total(self) -> float:
        try:
            return float(self.wallets.get_total('USDT'))
        except Exception:
            return 0.0

    def _qty_from_usdt(
            self,
            usdt,
            price,
            lev=None
    ):

        if lev and lev > 0:
            return usdt * lev / price

        return usdt / price

    def _dynamic_profit(self, trade, rate):

        try:
            avg = float(trade.open_rate)

            qty = abs(float(trade.amount))

            if qty <= 0:
                return 0.0

            # 已成交订单真实成本
            filled_orders = trade.select_filled_orders(trade.entry_side)

            total_cost = 0.0
            total_qty = 0.0

            for order in filled_orders:
                if order.average and order.amount:
                    total_cost += float(order.average) * float(order.amount)
                    total_qty += float(order.amount)

            if total_qty > 0:
                avg = total_cost / total_qty

            return (
                    float(rate) - avg
            ) / avg

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
        self._get_int(trade, "dca_count", 0)
        trend_cfg = self._cfg(
            cfg,
            "trend_add",
            default={}
        ) or {}

        # 趋势总开关
        trend_enable = bool(
            trend_cfg.get("enable", True)
        )

        # KDJ减仓配置
        kdj_reduce_cfg = trend_cfg.get(
            "kdj_reduce",
            {}
        ) or {}

        kdj_reduce_enable = bool(
            kdj_reduce_cfg.get(
                "enable",
                True
            )
        )

        # 趋势指标配置

        indicator_cfg = self._cfg(
            cfg,
            "indicator",
            default={}
        ) or {}

        macd_cfg = self._cfg(
            indicator_cfg,
            "macd",
            default={}
        ) or {}

        kdj_cfg = self._cfg(
            indicator_cfg,
            "kdj",
            default={}
        ) or {}

        ema_cfg = self._cfg(
            indicator_cfg,
            "ema",
            default={}
        ) or {}

        condition_mode = trend_cfg.get(
            "condition",
            "and"
        )
        if hasattr(last.name, "timestamp"):
            candle = int(last.name.timestamp())
        else:
            candle = int(last.name)

        last_trend = self._get_int(
            trade,
            'last_trend_candle',
            0
        )

        if candle == last_trend:
            return None
        if not trend_enable:
            return None

        level = self._get_int(trade, 'trend_level', 0)
        reset_needed = self._get_bool(trade, 'reset_needed', False)
        max_count = int(
            trend_cfg.get(
                "max_count",
                3
            )
        )
        ema_fast = int(
            ema_cfg.get(
                "fast",
                9
            )
        )

        ema_mid = int(
            ema_cfg.get(
                "mid",
                21
            )
        )

        ema_slow = int(
            ema_cfg.get(
                "slow",
                99
            )
        )
        try:
            amount_pct = float(
                trend_cfg.get(
                    "amount_percent",
                    0.5
                )
            ) / 100

        except Exception:
            amount_pct = 0.005

        trend_conditions = []

        # MACD

        if bool(
                trend_cfg.get(
                    "macd_enable",
                    True
                )
        ):
            trend_conditions.append(
                last.get('macd_tf', 0)
                >
                last.get('macdsig_tf', 0)
            )

        # KDJ

        if (
                kdj_reduce_enable
                and
                kdj_cfg.get("enable", True)
        ):
            trend_conditions.append(

                last.get('k_tf', 0)
                >
                last.get('d_tf', 0)

            )
        # EMA

        if bool(
                trend_cfg.get(
                    "ema_enable",
                    True
                )
        ):
            trend_conditions.append(
                last.get(f'ema{ema_fast}_tf', 0)
                >
                last.get(f'ema{ema_mid}_tf', 0)
                >
                last.get(f'ema{ema_slow}_tf', 0)
            )

        if not trend_conditions:
            is_bullish_trend = False

        elif condition_mode == "or":
            is_bullish_trend = any(trend_conditions)

        else:
            is_bullish_trend = all(trend_conditions)
        price = last.get('close', None)

        def _add_trend_total_usdt(x):
            self._record_add_usdt(trade, 'trend_total_added_usdt', x)

        if (
                level < max_count
                and not reset_needed
                and price is not None
                and is_bullish_trend
        ):
            self._set(trade, 'kdj_reduced', False)
            amt = min(
                collateral * amount_pct,
                self._available_stake() * 0.8
            )  # 趋势加仓数量
            _add_trend_total_usdt(abs(amt))
            self._set(
                trade,
                'trend_level',
                level + 1
            )
            self._set(
                trade,
                'last_trend_candle',
                candle
            )
            avg_price = float(trade.open_rate)

            old_qty = abs(float(trade.amount))

            lev = float(self.leverage(trade.pair))

            add_qty = self._qty_from_usdt(
                amt,
                price,
                lev
            )

            old_avg = avg_price

            new_avg = old_avg

            if old_qty + add_qty > 0:
                new_avg = (
                                  old_qty * old_avg +
                                  add_qty * price
                          ) / (
                                  old_qty + add_qty
                          )

            logger.info(f"[{trade.pair}] {GREEN}[多头趋势加仓 {amount_pct * 100:.1f}%]{RESET}, "
                        f"{YELLOW} 保证金={margin:.2f}{RESET}, "f"当前价={price:.4f}, "
                        f"加仓={abs(amt):.4f} USDT, 新均价={new_avg:.4f}")
            return float(amt), 'trend_add20_bull'

        if (
                trend_enable
                and level > 0
                and kdj_reduce_enable
        ):

            kdj_reduced = self._get_bool(
                trade,
                'kdj_reduced',
                False
            )

            if (
                    not kdj_reduced
                    and
                    last.get('k_tf', 0)
                    <
                    last.get('d_tf', 0)
            ):
                total_trend_usdt = self._get_float(trade, 'trend_total_added_usdt', 0.0) or 0.0
                reduce_percent = float(
                    kdj_reduce_cfg.get(
                        "reduce_percent",
                        100
                    )
                )

                sell_usdt = min(
                    total_trend_usdt *
                    reduce_percent / 100,

                    margin
                )
                amt = -float(sell_usdt)
                remain_trend_usdt = (
                        total_trend_usdt - sell_usdt
                )

                self._set(
                    trade,
                    'trend_total_added_usdt',
                    max(remain_trend_usdt, 0)
                )
                self._set(trade, 'trend_level', 0)
                self._set(trade, 'kdj_reduced', True)

                logger.info(f"[{trade.pair}] {RED}[KDJ 减仓]{RESET}, "
                            f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={last.get('close'):.4f}, "
                            f"减仓={abs(amt):.4f} USDT")
                return float(amt), 'kdj_reduce_by_trend_added'

    def dca_add(self, trade: Trade, df: DataFrame, last: dict, current_time: datetime, current_rate: float):
        cfg = self.get_runtime_config()
        dca_cfg = self._cfg(cfg, "dca", default={}) or {}
        if not bool(dca_cfg.get("enable", True)):
            return None

        last_idx = df.index[-1]
        candle_ts = pd.Timestamp(last_idx).tz_localize(None).floor('min')
        last_rsi = df['rsi'].iat[-1] if 'rsi' in df.columns else None
        last_j = df['j_tf'].iat[-1] if 'j_tf' in df.columns else None

        u = self._get_int(trade, 'dca_count', 0)
        levels = dca_cfg.get("levels") or []
        level_cfg = levels[min(u, len(levels) - 1)] if levels else {}
        max_dca = int(dca_cfg.get("max_count") or 7)
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

        avg_entry = float(trade.open_rate)

        # ============================
        # DCA价格偏差计算
        # ============================

        base_offset = float(
            dca_cfg.get(
                "price_offset",
                1.0
            )
        )

        price_multiplier = float(
            dca_cfg.get(
                "price_multiplier",
                1.0
            )
        )

        # 当前DCA次数

        u = self._get_int(
            trade,
            'dca_count',
            0
        )

        effective_percent = (
                base_offset *
                (
                        price_multiplier ** u
                )
        )

        threshold = avg_entry * (
                1 -
                effective_percent / 100
        )

        try:
            rsi_limit = float(level_cfg.get("rsi_limit", 20) or 20)
        except Exception:
            rsi_limit = 20.0
        try:
            j_limit = float(level_cfg.get("j_limit", 0) or 0)
        except Exception:
            j_limit = 0.0
        cond_mode = str(dca_cfg.get("condition", "or")).lower()
        cond_j = (last_j is not None and last_j < j_limit)
        cond_rsi = (last_rsi is not None and last_rsi < rsi_limit)
        if cond_mode == "and":
            triggered_cond = cond_j and cond_rsi
            triggered_label = f"J<{j_limit:g} & RSI<{rsi_limit:g}"
        else:
            triggered_cond = cond_j or cond_rsi
            triggered_label = f"J<{j_limit:g} 或 RSI<{rsi_limit:g}"

        try:
            candle_close = float(last.get('close')) if last.get('close') is not None else None
        except Exception:
            candle_close = None

        logger.debug(
            f"[{trade.pair}] DCA check: u={u}, avg_entry={avg_entry:.8f}, threshold={threshold:.8f}, candle_close={candle_close}, triggered_cond={triggered_cond}")

        if within_dca_cooldown:
            logger.debug(f"[{trade.pair}] 浮亏 DCA 冷却中")
            return None
        if dca_done:
            logger.debug(f"[{trade.pair}] 本根 K 已执行 DCA，跳过")
            return None

        if (candle_close is not None) and triggered_cond and (candle_close <= threshold):
            available = self._available_stake()

            if available <= 0:
                logger.info(
                    f"{trade.pair} 无可用资金"
                )
                return None
            collateral = self._collateral_total()
            try:
                margin = float(trade.stake_amount)
            except Exception:
                margin = 0.0

            base_amount = float(
                level_cfg.get(
                    "amount",
                    100
                )
            )
            amount_multiplier = float(
                dca_cfg.get(
                    "amount_multiplier",
                    1.0
                )
            )
            buy_amt = (
                    base_amount *
                    (
                            amount_multiplier ** u
                    )
            )
            try:
                prev_qty = abs(trade.amount)
            except Exception:
                prev_qty = 0.0

            lev = float(self.leverage(trade.pair))

            added_qty = self._qty_from_usdt(
                buy_amt,
                candle_close,
                lev
            )

            prev_value = prev_qty * avg_entry

            added_value = added_qty * candle_close

            new_avg_entry = (
                                    prev_value + added_value
                            ) / (
                                    prev_qty + added_qty
                            )

            self._set(trade, 'dca_count', u + 1)
            self._set(trade, 'dca_done', True)
            self._set(trade, 'last_dca_candle', int(candle_ts.timestamp()))
            self._set(trade, 'last_dca_time', int(current_time.timestamp()))
            self._set(trade, 'tp_count', 0)

            logger.info(
                f"[{trade.pair}] {RED}[浮亏 DCA 加仓 ]{RESET}, u=({u}->{u + 1}), "
                f"价格下跌步骤={effective_percent:.2f}%, 价格偏差={price_multiplier}, 加仓金额={buy_amt:.2f} USDT, 订单规模乘数={amount_multiplier}, "
                f"触发条件={triggered_label}, 触发价={threshold:.4f}, 收盘价={candle_close:.4f}, "
                f"{YELLOW}保证金={margin:.4f}{RESET}, 加仓={buy_amt:.4f} USDT, 新均价={new_avg_entry:.4f}"
            )
            return float(buy_amt), f"dca_u={u + 1}"
        return None

    def profit_rebuy(self, trade: Trade, last: dict, collateral: float):
        cfg = self.get_runtime_config()
        tp_cfg = self._cfg(cfg, "tp", default={}) or {}
        need_rebuy = self._get_bool(trade, 'need_rebuy', False)
        if not need_rebuy or not bool(tp_cfg.get("rebuy_enable", True)):
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
        try:
            current_qty = abs(float(trade.amount))
        except Exception:
            current_qty = 0.0

        current_value = (
                current_qty * price / lev
        ) if price else 0.0

        try:
            target_wallet_percent = float(tp_cfg.get("target_wallet_percent", 5) or 5)
        except Exception:
            target_wallet_percent = 5.0
        target_value = collateral * (target_wallet_percent / 100.0)
        buy_amt = target_value - current_value  # 浮盈加仓数量

        if buy_amt <= 0:
            return None

        n = self._get_int(trade, 'tp_count', 0)
        self._set(trade, 'need_rebuy', False)
        self._set(trade, 'dca_done', False)
        self._set(trade, 'tp_count', n + 1)

        avg_price = float(trade.open_rate or 0.0)
        added_qty = (
                buy_amt / price
        ) if price else 0
        if current_qty <= 0:
            new_avg = price
        else:
            new_avg = (
                              current_qty * avg_price +
                              added_qty * price
                      ) / (
                              current_qty + added_qty
                      )
        logger.info(
            f"[{trade.pair}] {GREEN}[浮盈加仓至 {target_wallet_percent:.0f}%]{RESET}, n=({n}->{n + 1}), 当前价={price:.4f}, "
            f"{YELLOW}保证金={current_value:.4f}{RESET}, 加仓={buy_amt:.4f} USDT, 新均价={new_avg:.4f}"
        )
        return (
            float(buy_amt),
            f"rebuy_to_{target_wallet_percent:.0f}pct"
        )

    def tp_reduce(
            self,
            trade: Trade,
            last: dict,
            current_profit: float,
            margin: float,
            current_rate: float,
            current_time: datetime
    ):

        cfg = self.get_runtime_config()

        tp_cfg = self._cfg(cfg, "tp", default={}) or {}
        loss_tp_cfg = self._cfg(cfg, "loss_tp", default={}) or {}

        if not bool(tp_cfg.get("enable", True)):
            return None

        account_profit = float(current_profit)

        # ==============================
        # 普通浮盈TP ROI计算
        # ==============================

        last_tp = self._get_int(
            trade,
            'last_tp_time',
            None
        )

        if last_tp is not None:

            base_time = datetime.fromtimestamp(
                int(last_tp)
            )

        else:

            base_time = trade.open_date_utc

            if getattr(base_time, 'tzinfo', None):
                base_time = base_time.replace(
                    tzinfo=None
                )

        elapsed = (
                          current_time - base_time
                  ).total_seconds() / 60

        roi_target, roi_minutes = self._roi_target(
            cfg,
            elapsed
        )

        roi_text = (
            f"{roi_target * 100:.2f}%({roi_minutes}min)"
            if roi_target is not None
            else "None"
        )

        # ==============================
        # DCA次数
        # ==============================

        u = self._get_int(
            trade,
            'dca_count',
            0
        )

        # ==============================
        # DCA快速止盈配置
        # ==============================

        try:
            dca_tp_profit = (
                    float(
                        loss_tp_cfg.get(
                            "dca_tp_profit",
                            0.8
                        )
                    )
                    / 100
            )

        except Exception:
            dca_tp_profit = 0.008

        # ==============================
        # 浮亏反弹保护
        # ==============================

        loss_enabled = bool(
            loss_tp_cfg.get(
                "enable",
                True
            )
        )

        loss_tp_ready = False

        if u > 0 and loss_enabled:

            try:
                trigger_loss = (
                        float(
                            loss_tp_cfg.get(
                                "trigger_loss",
                                -10
                            )
                        )
                        / 100
                )

            except Exception:
                trigger_loss = -0.10

            try:
                rebound_from_low = (
                        float(
                            loss_tp_cfg.get(
                                "rebound_from_low",
                                1
                            )
                        )
                        / 100
                )

            except Exception:
                rebound_from_low = 0.01

            armed = self._get_bool(
                trade,
                'loss_tp_armed',
                False
            )

            # 进入深亏状态
            if current_profit <= trigger_loss and not armed:
                self._set(
                    trade,
                    'loss_tp_armed',
                    True
                )

                self._set(
                    trade,
                    'loss_tp_min_profit',
                    float(current_profit)
                )

                return None

            if armed:

                min_profit = self._get_float(
                    trade,
                    'loss_tp_min_profit',
                    current_profit
                )

                # 继续创新低
                if current_profit < min_profit:
                    self._set(
                        trade,
                        'loss_tp_min_profit',
                        float(current_profit)
                    )

                    return None

                # 反弹不足
                min_profit = self._get_float(
                    trade,
                    'loss_tp_min_profit',
                    current_profit
                )

                rebound = max(
                    0,
                    current_profit - min_profit
                )

                if rebound < rebound_from_low:
                    return None

                self._set(
                    trade,
                    'loss_tp_armed',
                    False
                )

                loss_tp_ready = True

        # ==============================
        # DCA快速止盈
        # ==============================

        dca_tp_ready = False

        if u > 0:

            if account_profit >= dca_tp_profit:
                dca_tp_ready = True

        # ==============================
        # TP条件判断
        # ==============================

        if u > 0:

            # DCA止盈
            if not dca_tp_ready and not loss_tp_ready:
                return None


        else:

            # 普通仓位使用ROI
            if roi_target is None:
                return None

            if account_profit < roi_target:
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
            target_usdt = float(collateral_total) * (target_wallet_percent / 100.0)  # 浮亏止盈减仓数量
            target_qty = (target_usdt * lev) / price
            sell_qty = max(0.0, current_qty_abs - target_qty)

            if sell_qty <= 0:
                need_add_usdt = max(0.0, target_usdt - margin_val)
                if need_add_usdt > 0:
                    self._set(trade, 'dca_count', 0)
                    self._set(trade, 'dca_done', False)
                    self._set(trade, 'last_tp_time', int(current_time.timestamp()))

                    logger.info(
                        f"[{trade.pair}] {GREEN}[当前仓位过小，浮亏DCA止盈加仓至 {target_wallet_percent:.0f}%]{RESET}, "
                        f"保证金={margin_val:.4f}, 加仓={need_add_usdt:.4f} USDT"
                    )
                    return float(need_add_usdt), "tp_afterDCA_rebuy_to_target"
                return None

            try:
                sell_usdt = (sell_qty * price) / lev if lev and price else 0.0
            except Exception:
                sell_usdt = 0.0

            sell_usdt_capped = min(sell_usdt, max(0.0, margin_val))

            if sell_usdt_capped <= 0:
                logger.warning(
                    f"[{trade.pair}] [浮亏 DCA 止盈跳过] 计算到的 sell_usdt={sell_usdt_capped:.6f} 无效或被保证金限制, 跳过")
                return None

            self._set(trade, 'dca_count', 0)
            self._set(trade, 'dca_done', False)
            self._set(trade, 'last_tp_time', int(current_time.timestamp()))

            if dca_tp_ready:

                tp_reason = (
                    f"DCA快速止盈目标="
                    f"{dca_tp_profit * 100:.2f}%"
                )

            else:

                min_profit = self._get_float(
                    trade,
                    'loss_tp_min_profit',
                    current_profit
                )

                rebound = current_profit - min_profit

                tp_reason = (
                    f"浮亏反弹止盈 "
                    f"最低={min_profit * 100:.2f}% "
                    f"反弹={rebound * 100:.2f}%"
                )

            logger.info(
                f"[{trade.pair}] {GREEN}[浮亏止盈减仓至 {target_wallet_percent:.0f}%]{RESET}, "
                f"DCA次数={u}, "
                f"{tp_reason}, "
                f"当前收益={account_profit * 100:.2f}%, "
                f"{YELLOW}保证金={margin:.2f} USDT, "
                f"当前价={last.get('close'):.4f}, "
                f"减仓={sell_usdt_capped:.4f} USDT"
            )
            return float(-sell_usdt_capped), "tp_afterDCA_sell_keep_target"

        # -- 浮盈 TP 减仓 --
        try:
            reduce_percent = float(
                tp_cfg.get(
                    "reduce_percent",
                    30
                )
            )

        except Exception:
            reduce_percent = 30
        sell_amt = -(reduce_percent / 100.0) * margin  # 浮盈止盈减仓数量
        self._set(trade, 'dca_done', False)
        self._set(trade, 'last_tp_time', int(current_time.timestamp()))
        self._set(trade, 'last_tp_margin', float(margin))
        self._set(trade, 'need_rebuy', bool(tp_cfg.get("rebuy_enable", True)))

        logger.info(
            f"[{trade.pair}] {GREEN}[浮盈减仓 {reduce_percent:.0f}%]{RESET}, "
            f"持仓时间={elapsed:.0f}min, "
            f"ROI目标={roi_text}, "
            f"当前收益率={account_profit * 100:.2f}%, "
            f"{YELLOW}保证金={margin:.2f}{RESET}, "
            f"当前价={last.get('close'):.4f}, "
            f"减仓={abs(sell_amt):.4f}"
        )
        tp_tag = f"tp_{reduce_percent}"
        return float(sell_amt), tp_tag

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
                anchor = float(trade.open_rate or 0.0)
            except Exception:
                anchor = None
        if anchor is None or anchor <= 0:
            return None

        # 网格阈值
        try:
            grid_lower_pct = float(
                grid_cfg.get(
                    "init_lower",
                    -2
                )
            )
        except Exception:
            grid_lower_pct = -2.0
        try:
            grid_upper_pct = float(
                grid_cfg.get(
                    "init_upper",
                    2
                )
            )
        except Exception:
            grid_upper_pct = 2.0
        grid_lower = anchor * (1 - grid_lower_pct / 100.0)
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

        w = int(self._get_int(trade, 'grid_w', 0))

        max_w = int(grid_cfg.get("max_count", 5))  # 网格加仓次数

        try:
            lev = float(self.leverage(trade.pair) or 1.0)
            if not (lev > 0):
                lev = 1.0
        except Exception:
            lev = 1.0
        price_source = "market" if current_rate is not None else "candle_close"

        if price <= grid_lower:
            if max_w > 0 and w >= max_w:
                logger.debug(f"[{trade.pair}] 网格加仓达到上限 w={w} >= {max_w}，跳过")
                return None

            self._get_int(trade, 'dca_count', 0)

            # 动态网格加仓数量
            try:
                buy_percent = float(grid_cfg.get("buy_percent", 2) or 2)
            except Exception:
                buy_percent = 2.0
            grid_frac = max(0.01, (buy_percent / 100.0) - 0.002 * w)
            buy_usdt = min(collateral * grid_frac, self._available_stake() * 0.8)
            if buy_usdt <= 0:
                return None

            added_qty = self._qty_from_usdt(buy_usdt, price, lev)
            if added_qty <= 0:
                logger.debug(f"[{trade.pair}] 计算到的加仓基础数量为0或无效，跳过")
                return None

            try:
                prev_qty = abs(trade.amount)
            except Exception:
                prev_qty = 0.0
            prev_avg = float(trade.open_rate or 0.0)
            prev_cost = prev_qty * prev_avg

            new_avg = prev_avg
            if (prev_qty + added_qty) > 0:
                new_avg = (prev_cost + buy_usdt * lev) / (prev_qty + added_qty)

            new_w = min(w + 1, max_w) if max_w > 0 else w + 1
            new_anchor = float(price)
            # 下次网格价格
            next_buy = new_anchor * (1 + grid_lower_pct / 100.0)
            next_sell = new_anchor * (1 + grid_upper_pct / 100.0)

            self._set(trade, 'grid_anchor_price', float(new_anchor))
            self._set(trade, 'grid_upper', float(next_sell))
            self._set(trade, 'grid_lower', float(next_buy))
            self._set(trade, 'last_grid_action_time', int(current_time.timestamp()))
            self._record_add_usdt(trade, 'grid_added_total_usdt', buy_usdt)
            self._record_add_qty(trade, 'grid_added_total_qty', added_qty)
            self._set(trade, 'grid_count', int(self._get_int(trade, 'grid_count', 0) + 1))
            self._set(trade, 'grid_w', int(new_w))

            logger.info(
                f"[{trade.pair}] {RED}[网格加仓 {grid_frac * 100:.1f}%]{RESET}, 当前价={price:.4f}, 触发价={grid_lower:.4f}, "
                f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 加仓={buy_usdt:.4f} USDT, 新均价={new_avg:.4f}, w={new_w}, "
                f"下次网格 加仓价={next_buy:.4f}, 减仓价={next_sell:.4f}"
            )
            return float(buy_usdt), f"grid_add_{grid_frac:.3f}"

        if price >= grid_upper:
            try:
                sell_percent = float(grid_cfg.get("sell_percent", 2) or 2)
            except Exception:
                sell_percent = 2.0
            grid_sell_frac = max(0.01, sell_percent / 100.0)
            sell_usdt = collateral * grid_sell_frac
            sell_usdt = min(sell_usdt, cur_margin)

            if sell_usdt <= 0:
                logger.debug(f"[{trade.pair}] 网格减仓触发，保证金不足，跳过")
                return None

            new_w = max(0, w - 1)
            new_anchor = float(price)
            next_buy = new_anchor * (1 + grid_lower_pct / 100.0)
            next_sell = new_anchor * (1 + grid_upper_pct / 100.0)

            self._record_add_usdt(trade, 'grid_reduced_total_usdt', float(sell_usdt))
            self._set(trade, 'grid_anchor_price', float(new_anchor))
            self._set(trade, 'grid_upper', float(next_sell))
            self._set(trade, 'grid_lower', float(next_buy))
            self._set(trade, 'last_grid_action_time', int(current_time.timestamp()))
            self._set(trade, 'grid_count', int(self._get_int(trade, 'grid_count', 0) + 1))
            self._set(trade, 'grid_w', int(new_w))

            logger.info(
                f"[{trade.pair}] {RED}[网格减仓 {grid_sell_frac * 100:.1f}%]{RESET} (triggered by {price_source}), 当前价={price:.4f}, 触发价={grid_upper:.4f}, "
                f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 减仓={sell_usdt:.4f}, w={new_w}{RESET}, "
                f"下次网格 加仓价={next_buy:.4f}, 减仓价={next_sell:.4f}"
            )
            return float(-sell_usdt), "grid_sell_20pct"
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
            open_time = open_time.replace(tzinfo=None)
        candle_ts = pd.Timestamp(df.index[-1]).tz_localize(None).floor('min')
        df_tf, _ = self.dp.get_analyzed_dataframe(trade.pair, '30m')
        if df_tf.empty:
            return None
        last30_ts = pd.Timestamp(df_tf.index[-1]).tz_localize(None).floor('min')
        if candle_ts != last30_ts:
            return None

        collateral = self._collateral_total()
        if collateral <= 0:
            return None

        # 1) 趋势加仓
        res = self.trend_add(trade, last, margin, collateral, current_time, current_profit)
        if res:
            return res

        # 2) DCA 加仓
        res = self.dca_add(trade, df, last, current_time, current_rate)
        if res:
            return res

        # 3) 浮盈加仓
        res = self.profit_rebuy(trade, last, collateral)
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

        if tag.startswith("tp_") and order.side == "sell":
            tp_cfg = self.get_runtime_config().get("tp", {})
            if bool(tp_cfg.get("rebuy_enable", True)):
                self._set(
                    trade,
                    'need_rebuy',
                    True
                )

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
