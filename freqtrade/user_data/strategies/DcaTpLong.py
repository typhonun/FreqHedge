import sys
import traceback
from pathlib import Path
import requests
import time as _time
import numpy as np

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
from event_logger import record_event
import logging

RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RESET = "\033[0m"
logger = logging.getLogger(__name__)

_direction_cache = {
    "ts": 0,
    "data": None,
}

RISK_API_URL = "http://127.0.0.1:9000/api/risk/direction"
class DcaTpLong(IStrategy):

    timeframe = '30m'
    can_short = False
    use_exit_signal = True
    trailing_stop = False
    position_adjustment_enable = True
    use_custom_stoploss = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_loss_logged = set()
        self._pair_limit_logged = set()

    def bot_start(self, **kwargs) -> None:
        """策略启动时打印一次配置概览"""

        ft_cfg = self.config or {}

        dry_run_wallet = ft_cfg.get("dry_run_wallet", 0)
        stake_amount = ft_cfg.get("stake_amount", 0)
        max_open_trades = ft_cfg.get("max_open_trades", 0)
        tradable_balance_ratio = ft_cfg.get("tradable_balance_ratio", 0)
        leverage = ft_cfg.get("leverage", 1)

        exchange_cfg = ft_cfg.get("exchange", {}) or {}
        pair_whitelist = exchange_cfg.get("pair_whitelist", []) or []
        pair_blacklist = exchange_cfg.get("pair_blacklist", []) or []

        # ===== 失衡控制（多头侧） =====
        imbalance_enable = ft_cfg.get("imbalance_long_enable", False)
        imbalance_count = ft_cfg.get("imbalance_long_count", 2)

        logger.info(
            "\n"
            f"==================== 多头配置概览 ====================\n"
            f"初始资金          : {dry_run_wallet} USDT\n"
            f"开仓金额          : {stake_amount} USDT\n"
            f"最大持仓          : {max_open_trades}\n"
            f"资金利用率        : {tradable_balance_ratio}\n"
            f"持仓杠杆          : {leverage}x\n"
            f"K线时间周期       : {self.timeframe}\n"
            f"白名单            : {', '.join(pair_whitelist) if pair_whitelist else '(空)'}\n"
            f"黑名单            : {', '.join(pair_blacklist) if pair_blacklist else '(空)'}\n"
            f"------------------------------------------------------\n"
            f"持仓差上限        : {'开启' if imbalance_enable else '关闭'}, 上限={imbalance_count}\n"
            f"======================================================"
        )

        # ==================== 运行时策略配置详情 ====================
        try:
            cfg = self.get_runtime_config() or {}
        except Exception as e:
            logger.error(f"读取运行时策略配置失败: {e}")
            return

        side = str(cfg.get("side", "long")).lower()
        amount_mode = str(cfg.get("amount_mode", "percent")).lower()

        def _fmt(v, digits=4):
            if isinstance(v, bool):
                return "开" if v else "关"
            if isinstance(v, float):
                return f"{v:.{digits}f}"
            if v is None:
                return "(空)"
            return str(v)

        def _section(title):
            logger.info(
                f"\n-------------------- {title} --------------------"
            )

        # ========== 1. 金额模式 ==========
        _section("金额模式")
        logger.info(
            f"amount_mode       : {amount_mode} "
            f"({'百分比' if amount_mode == 'percent' else '固定金额 USDT'})"
        )

        # ========== 2. 指标配置 ==========
        _section("指标配置")
        ind = cfg.get("indicator", {}) or {}
        macd = ind.get("macd", {}) or {}
        kdj = ind.get("kdj", {}) or {}
        ema = ind.get("ema", {}) or {}
        rsi = ind.get("rsi", {}) or {}
        bb = ind.get("bb", {}) or {}
        logger.info(
            f"MACD              : fast={_fmt(macd.get('fast'))}, "
            f"slow={_fmt(macd.get('slow'))}, "
            f"signal={_fmt(macd.get('signal'))}\n"
            f"KDJ               : fastk={_fmt(kdj.get('fastk'))}, "
            f"slowk={_fmt(kdj.get('slowk'))}, "
            f"slowd={_fmt(kdj.get('slowd'))}\n"
            f"EMA               : fast={_fmt(ema.get('fast'))}, "
            f"mid={_fmt(ema.get('mid'))}, "
            f"slow={_fmt(ema.get('slow'))}\n"
            f"RSI.period        : {_fmt(rsi.get('period'))}\n"
            f"BB                : period={_fmt(bb.get('period'))}, "
            f"std={_fmt(bb.get('std'), 2)}"
        )

        # ========== 3. ROI止盈规则 ==========
        _section("ROI止盈规则")
        tp_cfg = cfg.get("tp", {}) or {}
        roi_levels = tp_cfg.get("roi_levels", []) or []
        if roi_levels:
            for i, lv in enumerate(roi_levels, start=1):
                logger.info(
                    f"  [{i}] minutes={_fmt(lv.get('minutes'))}, "
                    f"roi={_fmt(lv.get('roi'), 2)}%"
                )
        else:
            logger.info("  (空)")

        # ========== 4. 开仓信号 ==========
        _section("开仓信号")
        entry = cfg.get("entry", {}) or {}
        e_rsi = entry.get("rsi", {}) or {}
        e_macd = entry.get("macd", {}) or {}
        e_bb = entry.get("bb", {}) or {}
        logger.info(
            f"condition         : {entry.get('condition', 'and')}\n"
            f"RSI  enable={_fmt(e_rsi.get('enable'))}, "
            f"value={_fmt(e_rsi.get('value'))}\n"
            f"MACD enable={_fmt(e_macd.get('enable'))}\n"
            f"BB   enable={_fmt(e_bb.get('enable'))}"
        )

        # ========== 5. TP止盈 + 止损 ==========
        _section("TP止盈")
        logger.info(
            f"rebuy_enable         : {_fmt(tp_cfg.get('rebuy_enable'))}\n"
            f"reduce_amount        : {_fmt(tp_cfg.get('reduce_amount'), 2)}\n"
            f"reduce_percent       : {_fmt(tp_cfg.get('reduce_percent'))}\n"
            f"target_wallet_amount : {_fmt(tp_cfg.get('target_wallet_amount'), 2)}\n"
            f"target_wallet_percent: {_fmt(tp_cfg.get('target_wallet_percent'), 2)}"
        )

        _section("止损配置")
        sl = cfg.get("sl", {}) or {}
        ts = sl.get("time_stop", {}) or {}
        logger.info(
            f"enable            : {_fmt(sl.get('enable'))}\n"
            f"stoploss          : {_fmt(sl.get('stoploss'))}%\n"
            f"时间止损 enable   : {_fmt(ts.get('enable'))}\n"
            f"未成交时长        : {_fmt(ts.get('hours'), 1)}h\n"
            f"收益阈值模式      : {ts.get('mode', 'percent')}\n"
            f"收益阈值          : {_fmt(ts.get('profit_threshold'), 2)}"
        )

        # ========== 6. DCA配置 ==========
        _section("DCA配置")
        dca = cfg.get("dca", {}) or {}
        logger.info(
            f"enable            : {_fmt(dca.get('enable'))}\n"
            f"amount_mode       : {dca.get('amount_mode', 'auto')}\n"
            f"condition         : {dca.get('condition', 'or')}\n"
            f"max_count         : {_fmt(dca.get('max_count'))}\n"
            f"cooldown_minutes  : {_fmt(dca.get('cooldown_minutes'))}\n"
            f"price_offset      : {_fmt(dca.get('price_offset'), 2)}\n"
            f"price_multiplier  : {_fmt(dca.get('price_multiplier'), 2)}\n"
            f"base_amount       : {_fmt(dca.get('base_amount'), 2)}\n"
            f"base_percent      : {_fmt(dca.get('base_percent'), 2)}\n"
            f"amount_multiplier : {_fmt(dca.get('amount_multiplier'), 2)}"
        )
        dca_levels = dca.get("levels", []) or []
        if dca_levels:
            for i, lv in enumerate(dca_levels, start=1):
                logger.info(
                    f"  level[{i}] amount={_fmt(lv.get('amount'), 2)}, "
                    f"percent={_fmt(lv.get('percent'), 2)}, "
                    f"rsi_limit={_fmt(lv.get('rsi_limit'))}, "
                    f"j_limit={_fmt(lv.get('j_limit'))}"
                )
        else:
            logger.info("  levels: (空)")

        # ========== 7. 浮亏止盈 ==========
        _section("浮亏止盈")
        loss_tp = cfg.get("loss_tp", {}) or {}
        logger.info(
            f"enable               : {_fmt(loss_tp.get('enable'))}\n"
            f"dca_tp_profit        : {_fmt(loss_tp.get('dca_tp_profit'), 2)}%\n"
            f"close_all            : {_fmt(loss_tp.get('close_all'))}\n"
            f"target_wallet_amount : {_fmt(loss_tp.get('target_wallet_amount'), 2)}\n"
            f"target_wallet_percent: {_fmt(loss_tp.get('target_wallet_percent'), 2)}"
        )

        # ========== 8. 趋势加仓 ==========
        _section("趋势加仓")
        trend = cfg.get("trend_add", {}) or {}
        kdj_reduce = trend.get("kdj_reduce", {}) or {}
        logger.info(
            f"enable            : {_fmt(trend.get('enable'))}\n"
            f"amount_amount     : {_fmt(trend.get('amount_amount'), 2)}\n"
            f"amount_percent    : {_fmt(trend.get('amount_percent'), 2)}\n"
            f"condition         : {trend.get('condition', 'and')}\n"
            f"macd_enable       : {_fmt(trend.get('macd_enable'))}\n"
            f"kdj_enable        : {_fmt(trend.get('kdj_enable'))}\n"
            f"ema_enable        : {_fmt(trend.get('ema_enable'))}\n"
            f"KDJ减仓 enable    : {_fmt(kdj_reduce.get('enable'))}\n"
            f"KDJ减仓 reduce_amount : {_fmt(kdj_reduce.get('reduce_amount'), 2)}\n"
            f"KDJ减仓 reduce_percent: {_fmt(kdj_reduce.get('reduce_percent'))}"
        )

        # ========== 9. 网格配置 ==========
        _section("网格配置")
        grid = cfg.get("grid", {}) or {}
        logger.info(
            f"enable            : {_fmt(grid.get('enable'))}\n"
            f"max_count         : {_fmt(grid.get('max_count'))}\n"
            f"cooldown_minutes  : {_fmt(grid.get('cooldown_minutes'))}\n"
            f"grid_lower        : {_fmt(grid.get('grid_lower'), 2)}%\n"
            f"grid_upper        : {_fmt(grid.get('grid_upper'), 2)}%\n"
            f"buy_amount        : {_fmt(grid.get('buy_amount'), 2)}\n"
            f"buy_percent       : {_fmt(grid.get('buy_percent'), 2)}\n"
            f"sell_amount       : {_fmt(grid.get('sell_amount'), 2)}\n"
            f"sell_percent      : {_fmt(grid.get('sell_percent'), 2)}\n"
            f"order_scale       : {_fmt(grid.get('order_scale'), 2)}"
        )

        # ========== 10. 单交易对持仓限制 ==========
        _section("单交易对持仓限制")
        pm = cfg.get("pair_max_position", {}) or {}
        logger.info(
            f"enable            : {_fmt(pm.get('enable'))}\n"
            f"percent           : {_fmt(pm.get('percent'), 2)}%"
        )

        logger.info(
            f"\n==================== 策略配置详情结束 ====================\n"
        )

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
                minutes = self._cfg_int(level, "minutes", 0)
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
            # 1) 优先读 Freqtrade 加载的 config（顶层 leverage）
            ft_cfg = self.config or {}
            ft_leverage = ft_cfg.get("leverage", None)
            if ft_leverage is not None:
                try:
                    return float(ft_leverage)
                except (TypeError, ValueError):
                    pass

            # 2) 再读 ConfigManager
            cfg = self.get_runtime_config()
            top_level = self._cfg(cfg, "leverage", default=None)
            if top_level is not None:
                try:
                    return float(top_level)
                except (TypeError, ValueError):
                    pass

            nested = self._cfg(cfg, "strategy", "leverage", default=None)
            if nested is not None:
                try:
                    return float(nested)
                except (TypeError, ValueError):
                    pass

            return 10.0

        except Exception:
            return 10.0

    def _available_stake(self):
        try:
            free = self.wallets.get_free("USDT")
            if free is None:
                return 0.0
            return float(free)
        except Exception:
            return 0.0

    def _get_direction_state(self, ttl: int = 5):
        """读取后端多空失衡状态，缓存 ttl 秒"""

        now = _time.time()

        if _direction_cache["data"] and now - _direction_cache["ts"] < ttl:
            return _direction_cache["data"]

        try:
            r = requests.get(RISK_API_URL, timeout=2)
            if r.status_code == 200:
                data = r.json()
                _direction_cache["data"] = data
                _direction_cache["ts"] = now
                return data
        except Exception as e:
            logger.warning(f"获取多空失衡状态失败: {e}")

        # 失败返回 None，调用方默认放行
        return None

    def _time_stop_triggered(self, trade: Trade, current_time: datetime, current_rate: float) -> bool:
        """判断是否触发时间止损。

        条件：
            1) 距最后成交时间 >= hours 小时
            2) 累计收益 < profit_threshold
        """
        cfg = self.get_runtime_config()
        sl_cfg = self._cfg(cfg, "sl", default={}) or {}
        ts_cfg = sl_cfg.get("time_stop", {}) or {}

        if not bool(ts_cfg.get("enable", False)):
            return False

        try:
            hours = float(ts_cfg.get("hours", 24.0) or 24.0)
        except Exception:
            hours = 24.0
        if hours <= 0:
            return False

        try:
            threshold = float(ts_cfg.get("profit_threshold", -5.0) or -5.0)
        except Exception:
            threshold = -5.0

        mode = str(ts_cfg.get("mode", "percent")).lower()
        if mode not in ("percent", "amount"):
            mode = "percent"

        # ===== 1) 计算未成交时长 =====
        last_fill = self._get_int(trade, 'last_fill_time', 0)

        if last_fill <= 0:
            # 没有任何成交记录（不该发生，开仓时 order_filled 会记录）
            # 退回开仓时间
            try:
                base_ts = int(trade.open_date_utc.timestamp())
            except Exception:
                base_ts = 0
            if base_ts <= 0:
                return False
            last_fill = base_ts

        now_ts = int(current_time.timestamp())
        elapsed_hours = (now_ts - last_fill) / 3600.0

        if elapsed_hours < hours:
            return False

        # ===== 2) 计算累计收益 =====
        # 已平仓利润（realized）
        try:
            realized = float(getattr(trade, "realized_profit", 0) or 0)
        except Exception:
            realized = 0.0

        # 浮盈（unrealized）
        try:
            qty = abs(float(trade.amount or 0.0))
        except Exception:
            qty = 0.0

        try:
            open_rate = float(trade.open_rate or 0.0)
        except Exception:
            open_rate = 0.0

        try:
            rate = float(current_rate or 0.0)
        except Exception:
            rate = 0.0

        if qty > 0 and open_rate > 0 and rate > 0:
            try:
                unrealized = float(trade.calc_profit(rate))
            except Exception:
                unrealized = 0.0

        else:
            unrealized = 0.0

        total_profit = realized + unrealized

        # ===== 3) 换算成同单位比较 =====
        if mode == "percent":
            # 用「保证金」做分母，把 total_profit 换算成收益率
            try:
                stake = float(trade.stake_amount or 0.0)
            except Exception:
                stake = 0.0
            if stake <= 0:
                return False
            profit_ratio = total_profit / stake  # 相对保证金
            # 注：如果你的收益率定义是相对总仓位，用 total_profit / (stake * lev)
            triggered = profit_ratio < (threshold / 100.0)
            profit_display = f"{profit_ratio * 100:.2f}%"
            threshold_display = f"{threshold}%"
        else:
            # amount 模式：直接比较 USDT
            triggered = total_profit < threshold
            profit_display = f"{total_profit:.2f} USDT"
            threshold_display = f"{threshold} USDT"

        if triggered:
            if trade.id not in self._stop_loss_logged:
                self._stop_loss_logged.add(trade.id)
                logger.info(
                    f"[{trade.pair}] {RED}触发时间止损{RESET} "
                    f"未成交时长={elapsed_hours:.2f}h (阈值={hours}h), "
                    f"累计收益={profit_display} (阈值<{threshold_display}), "
                    f"当前价={rate:.4f}"
                )
                self._record_chart_marker(
                    event_type="time_stop",
                    pair=trade.pair,
                    trade_id=trade.id,
                    side="long" if not self.can_short else "short",
                    price=rate,
                    amount=abs(float(trade.amount or 0)),
                    current_time=current_time,
                    message=f"时间止损 {elapsed_hours:.1f}h",
                    candle_time=self._index_candle_key(current_time)
                )
            return True

        return False

    def _record_chart_marker(
            self,
            *,
            event_type: str,
            pair: str,
            trade_id: int,
            side: str,
            price,
            amount,
            current_time,
            message: str,
            candle_time=None  # 新增
    ) -> None:
        if current_time is None or price is None:
            return

        try:
            price = float(price)
            amount = float(amount)
        except Exception:
            return

        record_event(
            strategy=self.__class__.__name__,
            pair=pair,
            trade_id=trade_id,
            event_type=event_type,
            side=side,
            price=price,
            amount=amount,
            message=message,
            current_time=current_time,
            candle_time=candle_time  # 传给后端
        )

    def order_filled(
            self,
            pair,
            trade,
            order,
            current_time,
            **kwargs
    ):
        entry_price = float(
            order.average
            or trade.open_rate
        )

        reason = str(
            getattr(order, "ft_order_reason", None)
            or getattr(order, "ft_order_tag", None)
            or ""
        ).lower()

        # 新增：统一计算 K 线时间戳
        candle_ts = self._index_candle_key(current_time)

        try:
            self._set(trade, 'last_fill_time', self._safe_int(current_time.timestamp()))
        except Exception as e:
            logger.warning(f"[{pair}] 记录 last_fill_time 失败: {e}")

        if order.ft_order_side == "buy":

            if reason.startswith("trend_add"):
                self._record_chart_marker(
                    event_type="trend_add",
                    pair=pair,
                    trade_id=trade.id,
                    side="long",
                    price=entry_price,
                    amount=order.amount,
                    current_time=current_time,
                    message="趋势加仓成交",
                    candle_time=candle_ts  # 新增
                )

            elif reason.startswith("grid_add"):
                self._record_chart_marker(
                    event_type="grid_add",
                    pair=pair,
                    trade_id=trade.id,
                    side="long",
                    price=entry_price,
                    amount=order.amount,
                    current_time=current_time,
                    message="网格加仓成交",
                    candle_time=candle_ts  # 新增
                )

            elif reason.startswith("dca"):
                self._record_chart_marker(
                    event_type="dca",
                    pair=pair,
                    trade_id=trade.id,
                    side="long",
                    price=entry_price,
                    amount=order.amount,
                    current_time=current_time,
                    message="DCA加仓成交",
                    candle_time=candle_ts  # 新增
                )

        elif order.ft_order_side == "sell":

            if reason == "kdj_reduce_by_trend_added":
                self._record_chart_marker(
                    event_type="kdj_reduce",
                    pair=pair,
                    trade_id=trade.id,
                    side="long",
                    price=entry_price,
                    amount=order.amount,
                    current_time=current_time,
                    message="KDJ减仓成交",
                    candle_time=candle_ts  # 新增
                )

            elif reason.startswith("tp_afterDCA"):
                self._record_chart_marker(
                    event_type="tp",
                    pair=pair,
                    trade_id=trade.id,
                    side="long",
                    price=entry_price,
                    amount=order.amount,
                    current_time=current_time,
                    message="DCA止盈",
                    candle_time=candle_ts  # 新增
                )

            elif reason.startswith("tp_"):
                self._record_chart_marker(
                    event_type="tp",
                    pair=pair,
                    trade_id=trade.id,
                    side="long",
                    price=entry_price,
                    amount=order.amount,
                    current_time=current_time,
                    message="普通止盈",
                    candle_time=candle_ts  # 新增
                )

            elif reason.startswith("grid_sell"):
                self._record_chart_marker(
                    event_type="grid_sell",
                    pair=pair,
                    trade_id=trade.id,
                    side="long",
                    price=entry_price,
                    amount=order.amount,
                    current_time=current_time,
                    message="网格减仓成交",
                    candle_time=candle_ts  # 新增
                )

        # =========================
        # 初始化只执行一次
        # =========================

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

        upper_pct = self._cfg_float(
            grid_cfg,
            "init_upper",
            self._cfg_float(grid_cfg, "grid_upper", 2.0)
        )

        lower_pct = self._cfg_float(
            grid_cfg,
            "init_lower",
            self._cfg_float(grid_cfg, "grid_lower", -2.0)
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

            'grid_anchor_price': 0.0,

            'grid_w': 0,

        }

        for k, v in flags.items():
            self._set(
                trade,
                k,
                v
            )

        entry_price = float(

            getattr(
                order,
                "average",
                None
            )

            or trade.open_rate

            or 0

        )

        self._set(

            trade,

            "grid_upper",

            entry_price * (
                    1 + upper_pct / 100
            )

        )

        self._set(

            trade,

            "grid_lower",

            entry_price * (
                    1 + lower_pct / 100
            )

        )

        self._set(
            trade,
            "grid_count",
            0
        )

        self._set(
            trade,
            "grid_added_total_usdt",
            0.0
        )

        self._set(
            trade,
            "grid_added_total_qty",
            0.0
        )

        self._set(
            trade,
            "grid_reduced_total_usdt",
            0.0
        )

        self._set(
            trade,
            "initialized",
            True
        )
        tag = getattr(order, 'ft_order_tag', '') or ''

        if tag.startswith("tp_") and order.side == "sell":
            tp_cfg = self.get_runtime_config().get("tp", {})
            if bool(tp_cfg.get("rebuy_enable", True)):
                self._set(
                    trade,
                    'need_rebuy',
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
        if isinstance(v, bool):
            return bool(v)
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s.lower() in ("", "null", "none", "nan", "na", "n/a"):
                return None
            try:
                f = float(s)
                if f.is_integer():
                    return int(f)
                return f
            except ValueError:
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

        rsi_period = self._cfg_int(rsi_cfg, "period", 14)
        bb_period = self._cfg_int(bb_cfg, "period", 20)
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

                fastperiod=self._cfg_int(macd_cfg, "fast", 12),
                slowperiod=self._cfg_int(macd_cfg, "slow", 26),
                signalperiod=self._cfg_int(macd_cfg, "signal", 9)
            )

            # KDJ

            k, d = ta.STOCH(
                df_tf['high'],
                df_tf['low'],
                df_tf['close'],

                fastk_period=self._cfg_int(kdj_cfg, "fastk", 5),
                slowk_period=self._cfg_int(kdj_cfg, "slowk", 3),
                slowd_period=self._cfg_int(kdj_cfg, "slowd", 3)
            )

            j = 3 * k - 2 * d

            # EMA

            ema_fast = self._cfg_int(ema_cfg, "fast", 9)
            ema_mid = self._cfg_int(ema_cfg, "mid", 21)
            ema_slow = self._cfg_int(ema_cfg, "slow", 99)

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

    def populate_entry_trend(self, dataframe, metadata):

        cfg = self.get_runtime_config()
        entry_cfg = self._cfg(cfg, "entry", default={}) or {}

        rsi_cfg = self._cfg(entry_cfg, "rsi", default={}) or {}
        bb_cfg = self._cfg(entry_cfg, "bb", default={}) or {}
        macd_cfg = self._cfg(entry_cfg, "macd", default={}) or {}

        rsi_enable = bool(rsi_cfg.get("enable", True))
        bb_enable = bool(bb_cfg.get("enable", True))
        macd_enable = bool(macd_cfg.get("enable", True))
        rsi_value = float(rsi_cfg.get("value", 35) or 35)

        cond_map = {}

        if bb_enable:
            cond_map["BB"] = dataframe['close'] < dataframe['bb_lowerband']

        if rsi_enable:
            cond_map["RSI"] = dataframe['rsi'] < rsi_value

        if macd_enable:
            cond_map["MACD"] = dataframe['macd_tf'] > dataframe['macdsig_tf']

        condition_mode = str(
            entry_cfg.get("condition", "and")
        ).lower()

        if cond_map:
            if condition_mode == "or":
                long_cond = None
                for cond in cond_map.values():
                    long_cond = cond if long_cond is None else (long_cond | cond)
            else:
                # 默认 and
                long_cond = None
                for cond in cond_map.values():
                    long_cond = cond if long_cond is None else (long_cond & cond)
        else:
            long_cond = pd.Series(False, index=dataframe.index)

        names = list(cond_map.keys())
        tag_matrix = np.column_stack([
            cond.values.astype(bool)
            for cond in cond_map.values()
        ]) if cond_map else np.zeros((len(dataframe), 0), dtype=bool)

        enter_tags = [
            "_".join([names[i] for i, v in enumerate(row) if v]) or "NONE"
            for row in tag_matrix
        ]

        tag_prefix = "AND" if condition_mode == "and" else "OR"
        enter_tags = [
            f"{tag_prefix}_{t}" if t != "NONE" else "NONE"
            for t in enter_tags
        ]

        enter_tags = pd.Series(enter_tags, index=dataframe.index)

        dataframe["enter_long"] = long_cond.astype(int)
        dataframe.loc[long_cond, "enter_tag"] = enter_tags[long_cond]

        return dataframe

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force,
                            current_time, entry_tag, side, **kwargs):

        # 先判断是否手动
        entry_tag_str = str(entry_tag or "").lower()
        is_manual = (
                entry_tag_str.startswith("force_entry")
                or entry_tag_str in ("manual", "manual_entry")
        )

        # 手动开仓跳过持仓差闸门
        if not is_manual:
            imbalance_enable = self.config.get("imbalance_long_enable", False)
            imbalance_count = self.config.get("imbalance_long_count", 2)

            if imbalance_enable:
                state = self._get_direction_state()
                if state:
                    long_count = int(state.get("long_count", 0) or 0)
                    short_count = int(state.get("short_count", 0) or 0)
                    direction_diff = long_count - short_count

                    if direction_diff >= imbalance_count:
                        logger.info(
                            f"[{pair}] {YELLOW}持仓差超限，暂停开多{RESET} "
                            f"(多={long_count}, 空={short_count}, "
                            f"差={direction_diff}, 上限={imbalance_count})"
                        )
                        return False

        try:
            lev = float(self.leverage(pair) or 1.0)
        except Exception:
            lev = 1.0

        try:
            notional = float(amount) * float(rate)
        except Exception:
            notional = 0.0

        try:
            stake_amount = notional / lev
        except Exception:
            stake_amount = 0.0

        # 取当前 dataframe 的最后一根 K 线
        rsi_value = None
        macd_value = None
        macdsig_value = None
        bb_lower_value = None
        close_value = None

        try:
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if df is not None and not df.empty:
                last = df.iloc[-1]
                rsi_value = float(last.get("rsi")) if last.get("rsi") is not None else None
                macd_value = float(last.get("macd_tf")) if last.get("macd_tf") is not None else None
                macdsig_value = float(last.get("macdsig_tf")) if last.get("macdsig_tf") is not None else None
                bb_lower_value = float(last.get("bb_lowerband")) if last.get("bb_lowerband") is not None else None
                close_value = float(last.get("close")) if last.get("close") is not None else None
        except Exception as e:
            logger.warning(f"[{pair}] confirm_trade_entry 读取指标失败: {e}")

        logger.info(
            f"[{pair}] {GREEN} 开仓信号触发 {RESET}"
            f"entry_tag={entry_tag} "
            f"当前价={rate:.4f} "
            f"保证金={stake_amount:.4f} USDT "
            f"RSI={rsi_value} "
            f"is_manual={is_manual}"
        )

        if not is_manual:
            candle_ts = self._index_candle_key(current_time)
            if candle_ts is not None:
                self._record_chart_marker(
                    event_type="signal",
                    pair=pair,
                    trade_id=0,
                    side="long",
                    price=rate,
                    amount=stake_amount,
                    current_time=current_time,
                    message=f"入场信号 {entry_tag}",
                    candle_time=candle_ts  # 关键：传 K 线时间戳
                )

        return True

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

    def _get(self, trade, key, default=None):
        try:
            raw = trade.get_custom_data(key)
        except Exception:
            logger.error(
                f"_get 失败 key={key}\n{traceback.format_exc()}"
            )
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

    def _get_int(self, trade, key, default=0):
        value = self._get(trade, key, default)

        if value is None:
            return default

        try:
            f = float(value)
            if pd.isna(f) or not (float('-inf') < f < float('inf')):
                return default
            return int(f)
        except (TypeError, ValueError):
            return default

    def _cfg_int(self, cfg: dict, key: str, default: int) -> int:
        v = cfg.get(key, default)
        if isinstance(v, bool):
            return int(v)
        try:
            return int(float(v))
        except Exception:
            return default

    def _cfg_float(self, cfg: dict, key: str, default: float) -> float:
        v = cfg.get(key, default)
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        try:
            f = float(v)
            if not (float('-inf') < f < float('inf')) or pd.isna(f):
                return default
            return f
        except Exception:
            return default

    def _safe_int(self, value, default=0):
        if value is None:
            return default

        try:
            f = float(value)
            if pd.isna(f) or not (float('-inf') < f < float('inf')):
                return default
            return int(f)
        except (TypeError, ValueError):
            return default

    def _index_candle_key(self, value) -> int | None:
        if value is None:
            return None
        try:
            ts = pd.Timestamp(value)
        except Exception:
            try:
                ts = pd.Timestamp(float(value), unit='s')
            except Exception:
                return None

        # ✅ 统一转成 UTC
        if ts.tzinfo is None:
            ts = ts.tz_localize('UTC')
        else:
            ts = ts.tz_convert('UTC')

        try:
            ts = ts.floor('min')
        except Exception:
            pass
        try:
            return int(ts.timestamp())
        except Exception:
            return None

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
        old = self._get(trade, key, None)

        if isinstance(value, float) and isinstance(old, float):
            if abs(value - old) < 1e-8:
                return

        if old == value:
            return

        if key in ('grid_anchor_price', 'grid_upper', 'grid_lower'):
            try:
                value = float(value)
            except (TypeError, ValueError):
                logger.error(f"_set 价格转换失败 key={key} value={value!r}")
                return

        try:
            trade.set_custom_data(key, value)
        except Exception:
            logger.error(
                f"_set 失败 key={key} value={value!r} type={type(value).__name__}\n"
                f"{traceback.format_exc()}"
            )

    def _get_candle_ts(self, obj):
        candle_key = None

        if isinstance(obj, pd.DataFrame):
            if 'date' in obj.columns:
                candle_key = self._index_candle_key(obj['date'].iloc[-1])
            if candle_key in (None, 0):
                candle_key = self._index_candle_key(obj.index[-1])

        elif isinstance(obj, pd.Series):
            if 'date' in obj.index:
                candle_key = self._index_candle_key(obj.get('date'))
            if candle_key in (None, 0):
                candle_key = self._index_candle_key(obj.name)

        else:
            return None

        if candle_key in (None, 0):
            return None
        return candle_key

    def _collateral_total(self) -> float:
        try:
            return float(self.wallets.get_total('USDT'))
        except Exception:
            return 0.0

    def _pair_position_exceeded(self, trade: Trade, current_rate: float = None) -> bool:
        """判断该交易对保证金是否超过单对持仓上限。

        返回 True 表示超限，应停止该交易对的 DCA 与网格加仓。
        """
        cfg = self.get_runtime_config()
        pm_cfg = self._cfg(cfg, "pair_max_position", default={}) or {}

        if not bool(pm_cfg.get("enable", False)):
            return False

        try:
            limit_percent = float(pm_cfg.get("percent", 30) or 30)
        except Exception:
            limit_percent = 30.0

        if limit_percent <= 0:
            return False

        collateral = self._collateral_total()
        if collateral <= 0:
            return False

        # ===== 当前该交易对实际占用保证金 =====
        try:
            qty = abs(float(trade.amount or 0.0))
        except Exception:
            qty = 0.0

        # 优先用传入的当前价
        if current_rate and float(current_rate) > 0:
            eval_price = float(current_rate)
        else:
            # 退回开仓均价
            try:
                eval_price = float(trade.open_rate or 0.0)
            except Exception:
                eval_price = 0.0

        try:
            lev = float(self.leverage(trade.pair) or 1.0)
        except Exception:
            lev = 1.0
        if lev <= 0:
            lev = 1.0

        margin = (qty * eval_price) / lev if eval_price > 0 else 0.0
        used_percent = margin / collateral * 100.0

        if used_percent >= limit_percent:
            # ⬇️ 日志去重：每个 trade 只打印一次，直到不再超限
            if trade.id not in self._pair_limit_logged:
                self._pair_limit_logged.add(trade.id)
                logger.info(
                    f"[{trade.pair}] {YELLOW}单交易对持仓超限{RESET} "
                    f"保证金={margin:.2f}, 总资金={collateral:.2f}, "
                    f"占比={used_percent:.2f}% >= 上限={limit_percent:.2f}%，"
                    f"停止逆势加仓（DCA / 网格 / 浮盈回补 / DCA止盈回补）"
                )
            return True

        # ⬇️ 不再超限 → 清掉去重标记，下次超限可再次打印
        self._pair_limit_logged.discard(trade.id)
        return False

    def _amount_mode(self):
        """全局金额模式：percent / amount"""
        try:
            cfg = self.get_runtime_config()
            mode = str(cfg.get("amount_mode", "percent")).lower()
            if mode not in ("percent", "amount"):
                return "percent"
            return mode
        except Exception:
            return "percent"

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

    def trend_add(self, trade, last, margin, collateral, current_time, current_profit, candle=None):

        cfg = self.get_runtime_config()
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

        if candle in (None, 0):
            candle = self._get_candle_ts(last)
            if candle in (None, 0):
                logger.warning(
                    f"[{trade.pair}] trend_add return: candle 无效, "
                    f"last.name={last.name!r}, last.date={last.get('date')!r}"
                )
                return None

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
        ema_fast = self._cfg_int(ema_cfg, "fast", 9)
        ema_mid = self._cfg_int(ema_cfg, "mid", 21)
        ema_slow = self._cfg_int(ema_cfg, "slow", 99)
        amount_mode = self._amount_mode()

        try:
            amount_pct = float(
                trend_cfg.get(
                    "amount_percent",
                    0.5
                )
            ) / 100

        except Exception:
            amount_pct = 0.005

        try:
            amount_amount = float(
                trend_cfg.get(
                    "amount_amount",
                    10.0
                )
            )
        except Exception:
            amount_amount = 10.0

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

        if bool(trend_cfg.get("kdj_enable", True)):
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
        # logger.info(
        #     f"[{trade.pair}] candle data:\n"
        #     f"{last.to_dict()}"
        # )
        # logger.info(
        #     f"""
        # [{trade.pair}] TREND DEBUG
        #
        # macd_tf={last.get('macd_tf')}
        # macdsig_tf={last.get('macdsig_tf')}
        #
        # k_tf={last.get('k_tf')}
        # d_tf={last.get('d_tf')}
        #
        # ema9_tf={last.get('ema9_tf')}
        # ema21_tf={last.get('ema21_tf')}
        # ema99_tf={last.get('ema99_tf')}
        #
        # columns={list(last.index)}
        # """
        # )

        def _add_trend_total_usdt(x):
            self._record_add_usdt(trade, 'trend_total_added_usdt', x)

        if (
                level == 0
                and not reset_needed
                and price is not None
                and is_bullish_trend
        ):
            self._set(trade, 'kdj_reduced', False)
            if amount_mode == "amount":
                # 固定保证金金额
                amt = min(
                    amount_amount,
                    self._available_stake() * 0.8
                )
            else:
                amt = min(
                    collateral * amount_pct,
                    self._available_stake() * 0.8
                )
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

            if amount_mode == "amount":
                logger.info(
                    f"[{trade.pair}] {GREEN}[多头趋势加仓 {amt:.2f} USDT]{RESET}, "
                    f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={price:.4f}, "
                    f"加仓={abs(amt):.4f} USDT, 新均价={new_avg:.4f}"
                )
            else:
                logger.info(
                    f"[{trade.pair}] {GREEN}[多头趋势加仓 {amount_pct * 100:.1f}%]{RESET}, "
                    f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={price:.4f}, "
                    f"加仓={abs(amt):.4f} USDT, 新均价={new_avg:.4f}"
                )

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
                if amount_mode == "amount":
                    try:
                        reduce_amount = float(
                            kdj_reduce_cfg.get("reduce_amount", 10.0) or 10.0
                        )
                    except Exception:
                        reduce_amount = 10.0
                    sell_usdt = min(reduce_amount, margin)
                    reduce_text = f"{sell_usdt:.2f} USDT"
                else:
                    reduce_percent = float(
                        kdj_reduce_cfg.get("reduce_percent", 50)
                    )
                    sell_usdt = min(
                        collateral * (reduce_percent / 100),
                        margin
                    )
                    reduce_text = f"{reduce_percent:.1f}%"

                amt = -float(sell_usdt)

                self._set(trade, 'trend_level', 0)
                self._set(trade, 'kdj_reduced', True)

                logger.info(
                    f"[{trade.pair}] {RED}[KDJ 减仓 {reduce_text}]{RESET}, "
                    f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={last.get('close'):.4f}, "
                    f"减仓={abs(amt):.4f} USDT"
                )
                return float(amt), 'kdj_reduce_by_trend_added'

    def dca_add(self, trade: Trade, df: DataFrame, last: dict, current_time: datetime, current_rate: float):
        cfg = self.get_runtime_config()
        dca_cfg = self._cfg(cfg, "dca", default={}) or {}
        if not bool(dca_cfg.get("enable", True)):
            return None

        # 单交易对持仓超限 → 停止 DCA
        if self._pair_position_exceeded(trade, current_rate):
            return None

        candle_key = self._get_candle_ts(df)
        if candle_key is None:
            return None
        candle_ts = pd.Timestamp(candle_key, unit='s').tz_localize(None).floor('min')

        last_rsi = df['rsi'].iat[-1] if 'rsi' in df.columns else None
        last_j = df['j_tf'].iat[-1] if 'j_tf' in df.columns else None

        u = self._get_int(trade, 'dca_count', 0)
        levels = dca_cfg.get("levels") or []
        level_cfg = levels[min(u, len(levels) - 1)] if levels else {}
        max_dca = self._cfg_int(dca_cfg, "max_count", 7)
        cooldown_minutes = self._cfg_int(dca_cfg, "cooldown_minutes", 60)
        last_dca = self._get_int(trade, 'last_dca_candle', 0)
        last_dca_ts = Timestamp(self._safe_int(last_dca), unit='s') if last_dca else None
        if last_dca_ts is None or last_dca_ts != candle_ts:
            self._set(trade, 'dca_done', False)
        dca_done = self._get_bool(trade, 'dca_done', False)

        within_dca_cooldown = False
        last_dca_time = self._get_int(trade, 'last_dca_time', 0)
        if last_dca_time:
            try:
                last_dca_dt = datetime.fromtimestamp(self._safe_int(last_dca_time))
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

        if cond_mode == "rsi":
            triggered_cond = cond_rsi
            triggered_label = f"RSI<{rsi_limit:g}"

        elif cond_mode == "j":
            triggered_cond = cond_j
            triggered_label = f"J<{j_limit:g}"

        elif cond_mode == "and":
            triggered_cond = cond_j and cond_rsi
            triggered_label = f"J<{j_limit:g} & RSI<{rsi_limit:g}"

        else:
            # 默认 or
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
                logger.info(f"{trade.pair} 无可用资金")
                return None

            try:
                margin = float(trade.stake_amount)
            except Exception:
                margin = 0.0

            dca_mode = str(dca_cfg.get("amount_mode", "auto")).lower()
            global_mode = self._amount_mode()  # percent / amount
            collateral = self._collateral_total()

            if dca_mode == "auto":
                amount_multiplier = float(dca_cfg.get("amount_multiplier", 1.0) or 1.0)

                if global_mode == "amount":
                    # 固定金额：base_amount 是保证金
                    base_amt = float(dca_cfg.get("base_amount", 10.0) or 10.0)
                    buy_amt = base_amt * (amount_multiplier ** u)
                    actual_pct = (buy_amt / collateral * 100) if collateral > 0 else 0.0
                    amount_text = f"模式：自动, 固定金额"
                    amount_label = f"{buy_amt:.2f} USDT"
                else:
                    # 百分比：base_percent 是总资金百分比
                    base_percent = float(dca_cfg.get("base_percent", 2) or 2)
                    base_amt = collateral * (base_percent / 100.0)
                    buy_amt = base_amt * (amount_multiplier ** u)
                    actual_pct = base_percent * (amount_multiplier ** u)
                    amount_text = f"模式：自动, 百分比"
                    amount_label = f"{actual_pct:.2f}%"

            else:
                # manual
                amount_multiplier = 1.0

                if global_mode == "amount":
                    # 固定金额：用 level.amount
                    base_amt = float(level_cfg.get("amount", 100) or 100)
                    buy_amt = base_amt
                    actual_pct = (buy_amt / collateral * 100) if collateral > 0 else 0.0
                    amount_text = f"模式：手动, 本层金额={base_amt}"
                    amount_label = f"{buy_amt:.2f} USDT"
                else:
                    # 百分比：用 level.percent
                    base_percent = float(level_cfg.get("percent", 2.0) or 2.0)
                    buy_amt = collateral * (base_percent / 100.0)
                    actual_pct = base_percent
                    amount_text = f"模式：手动, 本层百分比={base_percent}"
                    amount_label = f"{actual_pct:.2f}%"

            try:
                prev_qty = abs(trade.amount)
            except Exception:
                prev_qty = 0.0

            lev = float(self.leverage(trade.pair))
            added_qty = self._qty_from_usdt(buy_amt, candle_close, lev)

            prev_value = prev_qty * avg_entry
            added_value = added_qty * candle_close

            new_avg_entry = (prev_value + added_value) / (prev_qty + added_qty)

            self._set(trade, 'dca_count', u + 1)
            self._set(trade, 'dca_done', True)
            self._set(trade, 'last_dca_candle', self._safe_int(candle_ts.timestamp()))
            self._set(trade, 'last_dca_time', self._safe_int(current_time.timestamp()))
            self._set(trade, 'tp_count', 0)

            # 触发时的 RSI / J 实际值
            try:
                rsi_val_text = f"{float(last_rsi):.2f}" if last_rsi is not None else "None"
            except Exception:
                rsi_val_text = "None"

            try:
                j_val_text = f"{float(last_j):.2f}" if last_j is not None else "None"
            except Exception:
                j_val_text = "None"

            logger.info(
                f"[{trade.pair}] {RED}[浮亏 DCA 加仓 {amount_label} {RESET}"
                f"订单规模倍率：{amount_multiplier ** u:.2f})], u=({u}->{u + 1}), "
                f"{amount_text}, "
                f"触发条件={triggered_label}, "
                f"RSI={rsi_val_text}, J={j_val_text}, "
                f"触发价={threshold:.4f}, 收盘价={candle_close:.4f}, "
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
            current_qty = abs(float(trade.amount))
        except Exception:
            current_qty = 0.0

        current_value = (
                current_qty * price / lev
        ) if price else 0.0

        amount_mode = self._amount_mode()

        if amount_mode == "amount":
            try:
                target_value = float(tp_cfg.get("target_wallet_amount", 50.0) or 50.0)
            except Exception:
                target_value = 50.0
            target_text = f"{target_value:.2f} USDT"
        else:
            try:
                target_wallet_percent = float(tp_cfg.get("target_wallet_percent", 5) or 5)
            except Exception:
                target_wallet_percent = 5.0
            target_value = collateral * (target_wallet_percent / 100.0)
            target_text = f"{target_wallet_percent:.0f}%"

        buy_amt = target_value - current_value
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
            f"[{trade.pair}] {GREEN}[浮盈加仓至 {target_text}]{RESET}, n=({n}->{n + 1}), 当前价={price:.4f}, "
            f"{YELLOW}保证金={current_value:.4f}{RESET}, 加仓={buy_amt:.4f} USDT, 新均价={new_avg:.4f}"
        )
        if amount_mode == "amount":
            tag = "rebuy_to_amount"
        else:
            tag = f"rebuy_to_{target_wallet_percent:.0f}pct"

        return float(buy_amt), tag

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
        dca_tp_cfg = self._cfg(
            cfg,
            "loss_tp",
            default={}
        ) or {}

        if not bool(tp_cfg.get("enable", True)):
            return None

        amount_mode = self._amount_mode()

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
                self._safe_int(last_tp)
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
                        dca_tp_cfg.get(
                            "dca_tp_profit",
                            3
                        )
                    )
                    / 100
            )

        except Exception:
            dca_tp_profit = 0.008

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
            if not dca_tp_ready:
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
                logger.warning(...)
                return None

            margin_val = margin
            collateral_total = self._collateral_total()

            close_all = bool(dca_tp_cfg.get("close_all", False))

            if close_all:
                # 全平模式：目标仓位为 0
                target_usdt = 0.0
                target_wallet_percent = 0.0
            else:
                if amount_mode == "amount":
                    try:
                        target_usdt = float(dca_tp_cfg.get("target_wallet_amount", 50.0) or 50.0)
                    except Exception:
                        target_usdt = 50.0
                else:
                    try:
                        target_wallet_percent = float(dca_tp_cfg.get("target_wallet_percent", 5) or 5)
                    except Exception:
                        target_wallet_percent = 5.0
                    target_usdt = float(collateral_total) * (target_wallet_percent / 100.0)

            target_qty = (target_usdt * lev) / price
            sell_qty = max(0.0, current_qty_abs - target_qty)

            if sell_qty <= 0:
                # 全平模式下不会走这里，因为 target_qty = 0
                need_add_usdt = max(0.0, target_usdt - margin_val)
                if need_add_usdt > 0:
                    self._set(trade, 'dca_count', 0)
                    self._set(trade, 'dca_done', False)
                    self._set(trade, 'last_tp_time', self._safe_int(current_time.timestamp()))

                    if amount_mode == "amount":
                        target_text = f"{target_usdt:.2f} USDT"
                    else:
                        target_text = f"{target_wallet_percent:.0f}%"

                    logger.info(
                        f"[{trade.pair}] {GREEN}[当前仓位过小，浮亏DCA止盈加仓至 {target_text}]{RESET}, "
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
            self._set(trade, 'last_tp_time', self._safe_int(current_time.timestamp()))

            tp_reason = (
                f"DCA止盈目标收益率="
                f"{dca_tp_profit * 100:.2f}%"
            )

            if close_all:
                target_text = "全平"
            elif amount_mode == "amount":
                target_text = f"{target_usdt:.2f} USDT"
            else:
                target_text = f"{target_wallet_percent:.0f}%"

            logger.info(
                f"[{trade.pair}] {GREEN}[浮亏止盈减仓至 {target_text}]{RESET}, "
                f"DCA次数={u}, "
                f"{tp_reason}, "
                f"当前收益={account_profit * 100:.2f}%, "
                f"{YELLOW}保证金={margin:.2f} {RESET} USDT, "
                f"当前价={last.get('close'):.4f}, "
                f"减仓={sell_usdt_capped:.4f} USDT"
            )

            return float(-sell_usdt_capped), "tp_afterDCA_sell_keep_target"

        # -- 浮盈 TP 减仓 --
        amount_mode = self._amount_mode()
        rebuy_enable = bool(tp_cfg.get("rebuy_enable", True))
        reduce_percent = 100.0

        if not rebuy_enable:
            # 不补仓：一律全平，跟金额模式无关
            sell_amt = -margin
            reduce_text = f"全平 {margin:.2f} USDT"
        else:
            if amount_mode == "amount":
                try:
                    reduce_amount = float(tp_cfg.get("reduce_amount", 10.0) or 10.0)
                except Exception:
                    reduce_amount = 10.0
                sell_amt = -min(reduce_amount, margin)
                reduce_text = f"{abs(sell_amt):.2f} USDT"
            else:
                try:
                    reduce_percent = float(tp_cfg.get("reduce_percent", 30))
                except Exception:
                    reduce_percent = 30
                sell_amt = -(reduce_percent / 100.0) * margin
                reduce_text = f"{reduce_percent:.0f}%"

        self._set(trade, 'dca_done', False)
        self._set(trade, 'last_tp_time', self._safe_int(current_time.timestamp()))
        self._set(trade, 'last_tp_margin', float(margin))
        self._set(trade, 'need_rebuy', bool(tp_cfg.get("rebuy_enable", True)))

        logger.info(
            f"[{trade.pair}] {GREEN}[浮盈减仓 {reduce_text}]{RESET}, "
            f"持仓时间={elapsed:.0f}min, "
            f"ROI目标={roi_text}, "
            f"当前收益率={account_profit * 100:.2f}%, "
            f"{YELLOW}保证金={margin:.2f}{RESET}, "
            f"当前价={last.get('close'):.4f}, "
            f"减仓={abs(sell_amt):.4f}"
        )
        tp_tag = f"tp_{'amount' if amount_mode == 'amount' else reduce_percent}"
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
        grid_lower_pct = self._cfg_float(
            grid_cfg,
            "init_lower",
            self._cfg_float(grid_cfg, "grid_lower", -2.0)
        )
        grid_upper_pct = self._cfg_float(
            grid_cfg,
            "init_upper",
            self._cfg_float(grid_cfg, "grid_upper", 2.0)
        )
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
                last_dt = datetime.fromtimestamp(self._safe_int(last_grid_ts))
                cooldown_minutes = self._cfg_int(grid_cfg, "cooldown_minutes", 30)
                if (current_time - last_dt).total_seconds() < 60 * cooldown_minutes:
                    logger.debug(f"[{trade.pair}] 网格冷却中（{cooldown_minutes}min），上次动作 ts={last_grid_ts}")
                    return None
            except Exception:
                pass

        w = self._get_int(trade, 'grid_w', 0)

        max_w = self._cfg_int(grid_cfg, "max_count", 5)  # 网格加仓次数

        amount_mode = self._amount_mode()

        try:
            lev = float(self.leverage(trade.pair) or 1.0)
            if not (lev > 0):
                lev = 1.0
        except Exception:
            lev = 1.0
        price_source = "market" if current_rate is not None else "candle_close"

        if price <= grid_lower:

            if self._pair_position_exceeded(trade, price):
                return None

            if max_w > 0 and w >= max_w:
                logger.debug(f"[{trade.pair}] 网格加仓达到上限 w={w} >= {max_w}，跳过")
                return None

            # ==========================
            # 动态网格加仓数量
            # ==========================

            buy_percent = self._cfg_float(grid_cfg, "buy_percent", 2.0)
            buy_amount = self._cfg_float(grid_cfg, "buy_amount", 10.0)

            # 订单规模系数
            # 1 = 固定网格
            # >1 = 金字塔加仓
            # <1 = 倒金字塔
            order_scale = self._cfg_float(grid_cfg, "order_scale", 1.0)

            # 防止异常
            if order_scale <= 0:
                order_scale = 1.0

            # 第w层订单倍率
            # 第一次 w=0
            # 第二次 w=1
            # 第三次 w=2
            scale_factor = order_scale ** w

            if amount_mode == "amount":
                buy_usdt = min(
                    buy_amount * scale_factor,
                    self._available_stake() * 0.8
                )
                grid_frac = 0.0  # 仅用于日志
            else:
                grid_frac = (
                                    buy_percent / 100.0
                            ) * scale_factor

                grid_frac = max(0.01, grid_frac)

                buy_usdt = min(
                    collateral * grid_frac,
                    self._available_stake() * 0.8
                )

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
            self._set(trade, 'last_grid_action_time', self._safe_int(current_time.timestamp()))
            self._record_add_usdt(trade, 'grid_added_total_usdt', buy_usdt)
            self._record_add_qty(trade, 'grid_added_total_qty', added_qty)
            self._set(trade, 'grid_count', self._safe_int(self._get_int(trade, 'grid_count', 0) + 1))
            self._set(trade, 'grid_w', self._safe_int(new_w))

            if amount_mode == "amount":
                logger.info(
                    f"[{trade.pair}] {RED}[网格加仓 {buy_usdt:.2f} USDT {RESET}"
                    f"(订单规模倍率：{scale_factor:.2f})], 当前价={price:.4f}, 触发价={grid_lower:.4f}, "
                    f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 加仓={buy_usdt:.4f} USDT, 新均价={new_avg:.4f}, w={new_w}, "
                    f"下次网格 加仓价={next_buy:.4f}, 减仓价={next_sell:.4f}"
                )
            else:
                logger.info(
                    f"[{trade.pair}] {RED}[网格加仓 {grid_frac * 100:.2f}% {RESET}"
                    f"(订单规模倍率：{scale_factor:.2f})], 当前价={price:.4f}, 触发价={grid_lower:.4f}, "
                    f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 加仓={buy_usdt:.4f} USDT, 新均价={new_avg:.4f}, w={new_w}, "
                    f"下次网格 加仓价={next_buy:.4f}, 减仓价={next_sell:.4f}"
                )

            return float(buy_usdt), f"grid_add_{grid_frac:.3f}"

        if price >= grid_upper:

            sell_percent = self._cfg_float(grid_cfg, "sell_percent", 2.0)
            sell_amount = self._cfg_float(grid_cfg, "sell_amount", 10.0)

            if amount_mode == "amount":
                sell_usdt = min(sell_amount, cur_margin)
                grid_sell_frac = 0.0
            else:
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
            self._set(trade, 'last_grid_action_time', self._safe_int(current_time.timestamp()))
            self._set(trade, 'grid_count', self._safe_int(self._get_int(trade, 'grid_count', 0) + 1))
            self._set(trade, 'grid_w', self._safe_int(new_w))

            if amount_mode == "amount":
                logger.info(
                    f"[{trade.pair}] {GREEN}[网格减仓 {sell_usdt:.2f} USDT]{RESET} (triggered by {price_source}), 当前价={price:.4f}, 触发价={grid_upper:.4f}, "
                    f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 减仓={sell_usdt:.4f}, w={new_w}{RESET}, "
                    f"下次网格 加仓价={next_buy:.4f}, 减仓价={next_sell:.4f}"
                )
            else:
                logger.info(
                    f"[{trade.pair}] {GREEN}[网格减仓 {grid_sell_frac * 100:.1f}%]{RESET} (triggered by {price_source}), 当前价={price:.4f}, 触发价={grid_upper:.4f}, "
                    f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 减仓={sell_usdt:.4f}, w={new_w}{RESET}, "
                    f"下次网格 加仓价={next_buy:.4f}, 减仓价={next_sell:.4f}"
                )

            return float(-sell_usdt), "grid_sell_20pct"
        return None

    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            return self._adjust_trade_position_impl(
                trade, current_time, current_rate, current_profit, **kwargs
            )
        except Exception:
            logger.exception(f"[{trade.pair}] adjust_trade_position 异常")
            return None

    def _adjust_trade_position_impl(self, trade, current_time, current_rate, current_profit, **kwargs):

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

        collateral = self._collateral_total()
        if collateral <= 0:
            return None

        candle_ts = self._get_candle_ts(df)
        if candle_ts is None:
            logger.warning(f"[{trade.pair}] 无法获取有效 candle_ts，跳过")
            return None

        # 1) 趋势加仓
        res = self.trend_add(trade, last, margin, collateral, current_time, current_profit, candle_ts)
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

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        cfg = self.get_runtime_config()
        sl_cfg = self._cfg(cfg, "sl", default={}) or {}

        if not bool(sl_cfg.get("enable", True)):
            return None

        # ===== 1) 原有 ROI 止损 =====
        try:
            stoploss_roi = float(sl_cfg.get("stoploss", -50) or -50) / 100.0
        except Exception:
            stoploss_roi = -0.5

        if current_profit <= stoploss_roi:
            if trade.id not in self._stop_loss_logged:
                self._stop_loss_logged.add(trade.id)
                logger.info(
                    f"[{pair}] {RED}触发ROI止损{RESET} "
                    f"收益率={current_profit * 100:.2f}% "
                    f"持仓价={trade.open_rate:.4f} "
                    f"开仓价={current_rate:.4f}"
                )
                self._record_chart_marker(
                    event_type="stop_loss",
                    pair=pair,
                    trade_id=trade.id,
                    side="long",
                    price=current_rate,
                    amount=abs(float(trade.amount or 0)),
                    current_time=current_time,
                    message="ROI止损",
                    candle_time=self._index_candle_key(current_time)
                )
            return "stop_loss"

        # ===== 2) 新增：时间止损 =====
        if self._time_stop_triggered(trade, current_time, current_rate):
            return "time_stop"

        return None

    def custom_stoploss(self, *args, **kwargs) -> float | None:
        return None
