# freqtrade/user_data/strategies/GridBotBase.py
"""
网格机器人基类（动态锚点版 - 彻底修复滑点重启导致的网格脱节）
"""

import sys
import json
import time
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
    # Grid entries, adjustments, and exits are market orders and therefore
    # use the exchange taker tier in simulation.
    strategy_order_types = {
        "entry": "market",
        "exit": "market",
    }

    can_short = False
    use_exit_signal = True
    trailing_stop = False
    position_adjustment_enable = True
    use_custom_stoploss = False
    process_only_new_candles = False

    startup_candle_count = 500

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
        self._full_reduce_retry_after = {}  # {trade_id: unix timestamp}

    def bot_start(self, **kwargs) -> None:
        ft_cfg = self.config or {}
        dry_run_wallet = ft_cfg.get("dry_run_wallet", 0)
        leverage = ft_cfg.get("leverage", 1)

        # ★ 杠杆处理策略：
        # - dry_run：模拟撮合不受交易所真实限制约束，可修改本地 markets 字典 + set_leverage，
        #            让 Freqtrade 内部风控按目标杠杆计算，便于回测/模拟。
        # - 实盘：严禁修改本地 markets 字典，严禁强制 set_leverage。
        #         真实杠杆由交易所决定，策略层通过 leverage() 读取 max_leverage 自适应降级。
        #         篡改 markets 只会让 Freqtrade 内部风控与交易所实际脱节，导致保证金/清算价错误。
        is_dry_run = bool(ft_cfg.get("dry_run", False))
        try:
            logger.info(f"{GRID_TAG} 开始执行杠杆检查 | dry_run={is_dry_run}")

            if hasattr(self, 'dp') and self.dp and hasattr(self.dp, 'exchange') and self.dp.exchange:
                exchange = self.dp.exchange
                target_lev = float(ft_cfg.get("leverage", 5.0) or 5.0)
                logger.info(f"{GRID_TAG} 目标杠杆: {target_lev}x")

                if not is_dry_run:
                    # 实盘：只读检查白名单交易对的真实杠杆上限，不修改任何本地数据
                    whitelist = ft_cfg.get("exchange", {}).get("pair_whitelist", []) or []
                    logger.info(f"{GRID_TAG} 实盘模式：跳过本地 markets 杠杆上限修改，仅做只读检查")
                    for pair in whitelist:
                        try:
                            market = exchange.market(pair) if hasattr(exchange, "market") else None
                            real_max = None
                            if isinstance(market, dict):
                                real_max = (market.get("limits") or {}).get("leverage", {}).get("max")
                            if real_max is not None and target_lev > float(real_max):
                                logger.warning(
                                    f"{GRID_TAG} 实盘杠杆超限 | Pair={pair} | "
                                    f"目标={target_lev}x | 交易所最大={real_max}x | "
                                    f"将以交易所实际上限开仓，请检查账户是否已开通该交易对杠杆权限"
                                )
                            elif real_max is not None:
                                logger.info(
                                    f"{GRID_TAG} 实盘杠杆检查通过 | Pair={pair} | "
                                    f"目标={target_lev}x | 交易所最大={real_max}x"
                                )
                        except Exception as e:
                            logger.warning(f"{GRID_TAG} 实盘杠杆只读检查失败 | Pair={pair} | {e}")
                else:
                    # dry_run：修改本地 markets 字典，让 Freqtrade 内部风控按目标杠杆计算
                    modified_count = 0
                    for markets_attr in ['markets', '_markets']:
                        markets_dict = getattr(exchange, markets_attr, None)
                        if markets_dict and isinstance(markets_dict, dict):
                            for symbol, market in markets_dict.items():
                                if market and isinstance(market, dict):
                                    limits = market.setdefault('limits', {})
                                    lev_limits = limits.setdefault('leverage', {'min': 1, 'max': 75})
                                    if not lev_limits.get('max') or lev_limits['max'] < target_lev:
                                        old_max = lev_limits.get('max', 1)
                                        lev_limits['max'] = max(75.0, target_lev)
                                        modified_count += 1
                                        logger.info(
                                            f"{GRID_TAG} 干跑修改 {symbol} 杠杆上限: "
                                            f"{old_max}x -> {lev_limits['max']}x"
                                        )
                    logger.info(f"{GRID_TAG} 干跑模式共修改了 {modified_count} 个交易对的杠杆上限")

                    whitelist = ft_cfg.get("exchange", {}).get("pair_whitelist", []) or []
                    if whitelist:
                        logger.info(f"{GRID_TAG} 干跑模式：强制设置白名单交易对杠杆为 {target_lev}x")
                        for pair in whitelist:
                            try:
                                exchange.set_leverage(target_lev, pair)
                                logger.info(f"{GRID_TAG} ✅ 已设置 {pair} 杠杆为 {target_lev}x")
                            except Exception as e:
                                logger.warning(f"{GRID_TAG} 设置 {pair} 杠杆失败: {e}")
            else:
                logger.warning(f"{GRID_TAG} 无法获取 exchange 对象，跳过杠杆检查")
        except Exception as e:
            logger.exception(f"{GRID_TAG} 杠杆检查/修复失败: {e}")

        g = self._grid_cfg()

        # ★ 核心修改：如果是重启，尝试读取上次运行的动态区间
        runtime = self._get_bot_grid_runtime()
        if runtime:
            logger.info(
                f"{GRID_TAG} 检测到上次运行的动态网格区间 "
                f"[{runtime[0]:.4f}, {runtime[1]:.4f}]，已自动覆盖初始配置。"
            )
            # 覆盖当前配置字典中的值
            if "grid" in g:
                g["lower_price"] = runtime[0]
                g["upper_price"] = runtime[1]
            # 如果你在 custom_params 里保存的是扁平结构（如 cfg['lower_price']），也需要一并覆盖：
            elif "lower_price" in g:
                g["lower_price"] = runtime[0]
                g["upper_price"] = runtime[1]

        # 重新获取一遍最新的 g 用于打印日志
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

        # 启动时若网格边界缺失且启用 smart_range_mode，立即后台预取各币区间
        self._maybe_fetch_grid_bounds()

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        cfg = self.get_runtime_config() or {}
        grid_cfg = self._grid_cfg()
        target = max(1.0, float(grid_cfg.get("leverage", cfg.get("leverage", self.config.get("leverage", 1.0))) or 1.0))

        # ★ 核心修改：不管 dry_run 还是实盘，都以交易所真实上限为准
        if max_leverage is None or max_leverage <= 0:
            logger.warning(f"{GRID_TAG} 交易所未返回 {pair} 的有效杠杆限制，保守降级为 1x")
            return 1.0

        if target > max_leverage:
            logger.warning(
                f"{GRID_TAG} 杠杆降级 | Pair={pair} | 目标={target}x | 交易所上限={max_leverage}x | "
                f"实际应用={max_leverage}x（这会影响该交易对的保证金和最小名义价值计算）"
            )
            return float(max_leverage)

        logger.info(f"{GRID_TAG} 杠杆设置 | Pair={pair} | 目标={target}x | 交易所上限={max_leverage}x | 实际={target}x")
        return float(target)

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
        if isinstance(cfg, dict) and isinstance(cfg.get("grid"), dict):
            return cfg["grid"]
        return cfg if isinstance(cfg, dict) else {}

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

    def _prefetched_bounds_for_pair(self, pair):
        """动态白名单扫描预取的交易对专属网格区间（grid_prefetch_range kv）"""
        if not pair:
            return None
        try:
            from core.config_manager import ConfigManager
            raw = ConfigManager.get_bot_kv(f"grid_prefetch_range_{self._bot_id}_{self._side_str}")
            if isinstance(raw, dict):
                info = (raw.get("pairs") or {}).get(pair)
                if isinstance(info, dict):
                    lower = float(info.get("lower") or 0)
                    upper = float(info.get("upper") or 0)
                    if lower > 0 and upper > lower:
                        return lower, upper
        except Exception:
            pass
        return None

    def _maybe_fetch_grid_bounds(self):
        """边界缺失且启用 smart_range_mode 时，后台请求后端计算白名单各币的网格区间"""
        try:
            g = self._grid_cfg()
            mode = str(g.get("smart_range_mode", "") or "").lower()
            days_map = {"aggressive": 7, "moderate": 30, "conservative": 90}
            if mode not in days_map:
                return
            now = time.time()
            if now - getattr(self, "_bounds_fetch_ts", 0.0) < 60:
                return
            self._bounds_fetch_ts = now

            import os
            import threading
            import requests
            api_base = os.environ.get('DCATP_API_URL', 'http://localhost:9000')
            pairs = (self.config.get('exchange', {}) or {}).get('pair_whitelist', []) or []
            if not pairs:
                return
            payload = {
                "bot_id": self._bot_id,
                "side": self._side_str,
                "days": days_map[mode],
                "pairs": pairs,
                "persist": True,
            }

            def _fetch():
                try:
                    r = requests.post(f"{api_base}/api/scanner/range/bot", json=payload, timeout=60)
                    logger.info(f"{GRID_TAG} 网格区间预取完成 | status={r.status_code}")
                except Exception as e:
                    logger.warning(f"{GRID_TAG} 网格区间预取失败: {e}")

            threading.Thread(target=_fetch, daemon=True).start()
            logger.info(f"{GRID_TAG} 网格边界缺失，已触发区间预取 | mode={mode} | pairs={pairs}")
        except Exception as e:
            logger.warning(f"{GRID_TAG} 触发区间预取异常: {e}")

    def _runtime_grid_bounds(self, pair=None):
        # 动态白名单新币优先使用后端预取的专属区间
        if pair:
            pre = self._prefetched_bounds_for_pair(pair)
            if pre:
                return pre
        g = self._grid_cfg()
        runtime = self._get_bot_grid_runtime()
        if runtime:
            return runtime
        lower = self._cfg_float(g, "lower_price", 0.0)
        upper = self._cfg_float(g, "upper_price", 0.0)
        # 边界无效时尝试向后端请求计算（smart_range_mode 模式）
        if not (lower > 0 and upper > lower):
            self._maybe_fetch_grid_bounds()
        return lower, upper

    def _clear_full_reduce_retry(self, trade):
        """统一清理碎片平仓重试锁的内存与持久化字段，防止不一致。"""
        self._full_reduce_retry_after.pop(trade.id, None)
        self._set(trade, "grid_full_reduce_retry_until", None)

    def _dynamic_whitelist_enabled(self) -> bool:
        """网格策略：多因子模式下读取 grid.dynamic_whitelist（DCA 走 pair_switch 配置）"""
        if super()._dynamic_whitelist_enabled():
            return True
        return bool(self._grid_cfg().get("dynamic_whitelist", False))

    def _dynamic_whitelist_interval_hours(self) -> float:
        """网格策略：定时间隔读 grid.dynamic_whitelist_interval_hours（DCA 走 pair_switch 配置）"""
        try:
            v = float(self._grid_cfg().get("dynamic_whitelist_interval_hours", 2.0))
        except Exception:
            v = 4.0
        return max(0.0, v)

    def _build_grid_levels(self, lower=None, upper=None):
        g = self._grid_cfg()
        if lower is None or upper is None:
            lower, upper = self._runtime_grid_bounds()
        count = self._cfg_int(g, "grid_count", 0)
        algo = str(g.get("spacing_algo", "arithmetic")).lower()

        if upper <= 0 or lower <= 0 or count <= 0 or upper <= lower: return []
        if algo == "geometric":
            ratio = (upper / lower) ** (1.0 / count)
            return [lower * (ratio ** i) for i in range(count + 1)]
        step = (upper - lower) / count
        return [lower + step * i for i in range(count + 1)]

    # ★ 新增：动态获取网格步长
    def _get_grid_step_for_bounds(self, lower: float, upper: float) -> float:
        g = self._grid_cfg()
        count = self._cfg_int(g, "grid_count", 0)
        algo = str(g.get("spacing_algo", "arithmetic")).lower()
        if count <= 0 or upper <= lower or lower <= 0:
            return 0.0
        if algo == "geometric":
            # 等比取第一格间距作为近似基准
            ratio = (upper / lower) ** (1.0 / count)
            return lower * (ratio - 1.0)
        return (upper - lower) / count

    def _get_grid_step(self, pair=None) -> float:
        lower, upper = self._runtime_grid_bounds(pair)
        return self._get_grid_step_for_bounds(
            lower,
            upper,
        )

    def _trade_grid_step(self, trade) -> float:
        """按交易自身的动态网格边界计算步长（优先于全局共享边界）"""
        g = self._grid_cfg()
        dl = self._get_float(trade, "grid_dyn_lower", self._cfg_float(g, "lower_price", 0.0))
        du = self._get_float(trade, "grid_dyn_upper", self._cfg_float(g, "upper_price", 0.0))
        return self._get_grid_step_for_bounds(dl, du)

    def _shift_dynamic_grid(self, trade, direction: int) -> bool:
        """Move the live grid one spacing after the triggering order is filled."""
        g = self._grid_cfg()
        lower = self._get_float(trade, "grid_dyn_lower", self._cfg_float(g, "lower_price", 0.0))
        upper = self._get_float(trade, "grid_dyn_upper", self._cfg_float(g, "upper_price", 0.0))
        step = self._get_grid_step_for_bounds(lower, upper)
        if direction == 0 or step <= 0:
            return False
        lower += direction * step
        upper += direction * step
        self._set(trade, "grid_dyn_lower", lower)
        self._set(trade, "grid_dyn_upper", upper)
        self._set_bot_grid_runtime(lower, upper)
        logger.info(
            f"{GRID_TAG} 动态网格移动 | 方向={'上移' if direction > 0 else '下移'}"
            f" | 新区间=[{lower:.4f}, {upper:.4f}]"
        )
        return True

    def _check_and_apply_trailing(self, trade, close_price: float) -> bool:
        """
        检查收盘价是否越界，如果越界且开启了追踪，则主动平移网格。
        返回 True 表示发生了平移。
        """
        g = self._grid_cfg()
        trailing_up = bool(g.get("trailing_up", False))
        trailing_down = bool(g.get("trailing_down", False))

        if not trailing_up and not trailing_down:
            return False

        dyn_lower = self._get_float(trade, "grid_dyn_lower", self._cfg_float(g, "lower_price", 0.0))
        dyn_upper = self._get_float(trade, "grid_dyn_upper", self._cfg_float(g, "upper_price", 0.0))
        step = self._get_grid_step_for_bounds(dyn_lower, dyn_upper)

        if step <= 0:
            return False

        # ★ 新增：缓冲区防抖（要求越界至少 0.5 个 step 才触发，防止在边缘反复横跳）
        buffer = step * 0.5

        shifted = False
        # 向上追踪
        if trailing_up and close_price > (dyn_upper + buffer):
            # 计算需要平移几格才能包住当前价格
            shift_count = int((close_price - dyn_upper) / step) + 1
            shift_distance = shift_count * step
            dyn_upper += shift_distance
            dyn_lower += shift_distance
            shifted = True
            logger.info(
                f"{GRID_TAG} {CYAN}▲ 主动触发向上追踪{RESET} | 收盘价={close_price:.4f} | "
                f"突破缓冲带 | 平移{shift_count}格 | 新区间=[{dyn_lower:.4f}, {dyn_upper:.4f}]"
            )

        # 向下追踪
        elif trailing_down and close_price < (dyn_lower - buffer):
            # 计算需要平移几格才能包住当前价格
            shift_count = int((dyn_lower - close_price) / step) + 1
            shift_distance = shift_count * step
            dyn_upper -= shift_distance
            dyn_lower -= shift_distance
            shifted = True
            logger.info(
                f"{GRID_TAG} {CYAN}▼ 主动触发向下追踪{RESET} | 收盘价={close_price:.4f} | "
                f"突破缓冲带 | 平移{shift_count}格 | 新区间=[{dyn_lower:.4f}, {dyn_upper:.4f}]"
            )

        if shifted:
            self._set(trade, "grid_dyn_lower", dyn_lower)
            self._set(trade, "grid_dyn_upper", dyn_upper)

            # 锚定跟踪网格：平移后加/减仓价位统一由最近成交价 ± step 推导
            anchor_levels = self._grid_anchor_levels(trade, dyn_lower, dyn_upper)
            if anchor_levels:
                _, _, next_add_p, next_reduce_p = anchor_levels
                self._set(trade, "grid_next_add_price", next_add_p)
                self._set(trade, "grid_next_reduce_price", next_reduce_p)

            # ★ 修复：加入 fill_token 方便前端识别网格发生了平移
            self._set_bot_grid_runtime(
                dyn_lower,
                dyn_upper,
                last_fill_price=self._get_float(trade, "grid_last_fill_price", 0.0),
                next_add_price=self._get_float(trade, "grid_next_add_price", 0.0),
                fill_token=f"trail_{int(close_price * 10000)}",  # ★ 加入一个虚拟的 token
                **self._runtime_action_levels(trade, dyn_lower, dyn_upper)
            )
            return True
        return False

    def _grid_runtime_signature(self) -> str:
        g = self._grid_cfg()
        # ★ 核心修改：截取字符串的前半部分（比如网格数量和算法）作为唯一标识，
        # 不再把上下限价格包含在签名里，这样即使重启，也能认出是同一个机器人！
        return "|".join(
            str(g.get(key, ""))
            for key in ("grid_count", "spacing_algo")
        )

    def _get_bot_grid_runtime(self):
        try:
            from core.config_manager import ConfigManager
            if ConfigManager.get_bot_kv(self._grid_kv_key("runtime_signature")) != self._grid_runtime_signature():
                return None
            lower = float(ConfigManager.get_bot_kv(self._grid_kv_key("runtime_lower")) or 0)
            upper = float(ConfigManager.get_bot_kv(self._grid_kv_key("runtime_upper")) or 0)
            if lower > 0 and upper > lower:
                return lower, upper
        except (TypeError, ValueError):
            pass
        return None

    def _set_bot_grid_runtime(self, lower: float, upper: float, **state):
        try:
            from core.config_manager import ConfigManager
            ConfigManager.set_bot_kv(self._grid_kv_key("runtime_signature"), self._grid_runtime_signature())
            ConfigManager.set_bot_kv(self._grid_kv_key("runtime_lower"), float(lower))
            ConfigManager.set_bot_kv(self._grid_kv_key("runtime_upper"), float(upper))
            runtime = {
                "lower": float(lower),
                "upper": float(upper),
                "step": self._get_grid_step_for_bounds(lower, upper),
                "side": self._side_str,
                "signature": self._grid_runtime_signature(),
                "levels": self._build_grid_levels(lower, upper),
                **state,
            }
            ConfigManager.set_bot_kv(self._grid_kv_key("runtime_state"), runtime)
        except Exception:
            logger.exception(f"{GRID_TAG} 保存动态网格状态失败")

    def _grid_anchor_price(self, trade, positions=None) -> float:
        """锚点 = 最近一次成交价；缺失时兜底取最新建仓格（idx 为时间戳，越大越新）的 entry"""
        last_fill = self._get_float(trade, "grid_last_fill_price", 0.0)
        if last_fill > 0 and np.isfinite(last_fill):
            return float(last_fill)
        if positions is None:
            positions = self._get_grid_positions(trade)
        best_idx = None
        best_entry = 0.0
        for k, v in (positions or {}).items():
            try:
                idx = int(k)
                entry = float((v or {}).get("entry", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            if entry > 0 and (best_idx is None or idx > best_idx):
                best_idx = idx
                best_entry = entry
        if best_entry > 0:
            return best_entry
        try:
            return float(getattr(trade, "open_rate", 0.0) or 0.0)
        except Exception:
            return 0.0

    def _grid_anchor_levels(self, trade, lower=None, upper=None):
        """锚定跟踪网格：返回 (anchor, step, next_add, next_reduce)；数据不足返回 None。
        多头：加仓=anchor-step，减仓=anchor+step；空头镜像。"""
        g = self._grid_cfg()
        if lower is None or upper is None:
            lower = self._get_float(trade, "grid_dyn_lower", self._cfg_float(g, "lower_price", 0.0))
            upper = self._get_float(trade, "grid_dyn_upper", self._cfg_float(g, "upper_price", 0.0))
        step = self._get_grid_step_for_bounds(lower, upper)
        if step <= 0:
            return None
        positions = self._get_grid_positions(trade)
        anchor = self._grid_anchor_price(trade, positions)
        if anchor <= 0 or not np.isfinite(anchor):
            return None
        if self._is_short:
            next_add = anchor + step
            next_reduce = anchor - step
        else:
            next_add = anchor - step
            next_reduce = anchor + step
        return anchor, step, next_add, next_reduce

    def _anchor_level_chains(self, anchor, step, lower, upper):
        """从锚点向两侧生成预期加/减仓价位链（限制在动态区间内，最多 count+2 条）"""
        count = self._cfg_int(self._grid_cfg(), "grid_count", 20)
        lo = lower if lower and lower > 0 else 0.0
        hi = upper if upper and upper > 0 else float("inf")
        add_levels, reduce_levels = [], []
        if self._is_short:
            p = anchor + step
            while p <= hi and len(add_levels) < count + 2:
                add_levels.append(p)
                p += step
            p = anchor - step
            while p >= lo and len(reduce_levels) < count + 2:
                reduce_levels.append(p)
                p -= step
        else:
            p = anchor - step
            while p >= lo and len(add_levels) < count + 2:
                add_levels.append(p)
                p -= step
            p = anchor + step
            while p <= hi and len(reduce_levels) < count + 2:
                reduce_levels.append(p)
                p += step
        return (
            sorted(round(v, 8) for v in add_levels),
            sorted(round(v, 8) for v in reduce_levels),
        )

    def _select_lifo_reduce_slots(self, positions, target_qty: float):
        """最近加仓优先（idx 为时间戳，越大越新）凑满 target_qty 的减仓格位列表。
        整格选择不截断：保证成交回调按整格移除时账本扣减严格 LIFO。"""
        items = []
        for k, v in (positions or {}).items():
            if not isinstance(v, dict):
                continue
            try:
                idx = int(k)
            except (TypeError, ValueError):
                continue
            try:
                entry = float(v.get("entry", 0.0) or 0.0)
                qty = float(v.get("qty", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            if entry > 0 and qty > 0 and np.isfinite(entry) and np.isfinite(qty):
                items.append((idx, entry, v, qty))
        items.sort(key=lambda x: x[0], reverse=True)
        if not items:
            return []
        if target_qty <= 0 or not np.isfinite(target_qty):
            idx, entry, v, _ = items[0]
            return [(idx, entry, v)]
        selected = []
        acc = 0.0
        for idx, entry, v, qty in items:
            if acc >= target_qty:
                break
            selected.append((idx, entry, v))
            acc += qty
        return selected

    def _runtime_action_levels(self, trade, lower: float, upper: float) -> dict:
        levels = self._grid_anchor_levels(trade, lower, upper)
        if not levels:
            return {"add_levels": [], "reduce_levels": []}
        anchor, step, _, _ = levels
        add_levels, reduce_levels = self._anchor_level_chains(anchor, step, lower, upper)
        return {
            "add_levels": add_levels,
            "reduce_levels": reduce_levels,
        }

    # ★ 重写：基于动态开仓价计算止盈价
    def _grid_tp_price(self, entry_price: float, trade=None) -> float:
        step = self._trade_grid_step(trade) if trade is not None else self._get_grid_step()
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
        lower, upper = self._runtime_grid_bounds(metadata.get('pair'))
        start_mode = str(g.get("start_mode", "grid")).lower()
        trigger_price = self._cfg_float(g, "trigger_price", 0.0)

        if upper <= 0 or lower <= 0 or upper <= lower: return dataframe
        levels = self._build_grid_levels(lower, upper)
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
            g = self._grid_cfg()
            # ★ 门禁 1：动态白名单扫描/配置生效期间，禁止新开仓
            if self._dynamic_whitelist_enabled() and self._is_whitelist_scanning():
                logger.info(f"{GRID_TAG} [{pair}] 动态白名单扫描/生效中，暂缓新开仓")
                return False

            # ★ 门禁 2：开仓前校验交易对是否在最新白名单内
            if not self._is_pair_in_whitelist(pair):
                logger.info(f"{GRID_TAG} [{pair}] 不在当前有效白名单 {self._get_effective_whitelist()} 中，拒绝开仓")
                return False

            # 杠杆设置：dry_run 尝试设置，实盘以交易所真实限制为准
            try:
                if hasattr(self, 'dp') and self.dp and hasattr(self.dp, 'exchange') and self.dp.exchange:
                    exchange = self.dp.exchange
                    target_lev = float(self.config.get('leverage', 5.0) or 5.0)
                    is_dry_run = bool(self.config.get("dry_run", False))

                    if is_dry_run:
                        # dry_run 下尝试设置杠杆，失败不影响模拟撮合
                        try:
                            exchange.set_leverage(target_lev, pair)
                            logger.info(f"{GRID_TAG} confirm_trade_entry: 干跑设置 {pair} 杠杆 {target_lev}x")
                        except Exception as e:
                            logger.warning(f"{GRID_TAG} confirm_trade_entry: 干跑设置杠杆失败: {e}")

                        try:
                            for markets_attr in ['markets', '_markets']:
                                markets_dict = getattr(exchange, markets_attr, None)
                                if markets_dict and isinstance(markets_dict, dict):
                                    market = markets_dict.get(pair)
                                    if market and isinstance(market, dict):
                                        limits = market.setdefault('limits', {})
                                        lev_limits = limits.setdefault('leverage', {'min': 1, 'max': 75})
                                        old_max = lev_limits.get('max', 1)
                                        if old_max < target_lev:
                                            lev_limits['max'] = max(75.0, target_lev)
                                            logger.info(
                                                f"{GRID_TAG} confirm_trade_entry: 干跑修改 {pair} 杠杆上限 "
                                                f"{old_max}x -> {lev_limits['max']}x"
                                            )
                        except Exception as e:
                            logger.warning(f"{GRID_TAG} confirm_trade_entry: 干跑修改市场数据失败: {e}")
                    else:
                        # 实盘：不修改本地市场数据，不强制 set_leverage
                        # 真实杠杆由交易所决定，策略层通过 leverage() 读取 max_leverage 自适应
                        try:
                            market = exchange.market(pair) if hasattr(exchange, "market") else None
                            real_max = None
                            if isinstance(market, dict):
                                real_max = (market.get("limits") or {}).get("leverage", {}).get("max")
                            if real_max is not None and target_lev > float(real_max):
                                logger.warning(
                                    f"{GRID_TAG} confirm_trade_entry: 实盘目标杠杆 {target_lev}x "
                                    f"超过交易所上限 {real_max}x | Pair={pair} | 将以实际上限开仓"
                                )
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"{GRID_TAG} confirm_trade_entry: 杠杆检查失败: {e}")

            candle_str = self._get_candle_str(current_time)
            if self._last_candle_str.get(pair) == candle_str:
                return False

            lower, upper = self._runtime_grid_bounds(pair)
            if upper <= 0 or lower <= 0:
                return False

            try:
                open_count = len(list(Trade.get_trades_proxy(pair=pair, is_open=True)))
            except Exception:
                open_count = 0
            if open_count > 0:
                return False

            if rate < lower or rate > upper:
                return False

            # ★★★ 新增：最小名义价值预校验
            try:
                market = self.dp.market(pair) if hasattr(self, 'dp') else None

                # 1. 获取交易所对该交易对的真实杠杆上限（和 Freqtrade 内部调用 leverage() 时传的值一致）
                real_max_leverage = 100.0  # 默认兜底
                min_notional = 5.0
                if market:
                    lev_limits = (market.get("limits") or {}).get("leverage") or {}
                    if lev_limits.get("max") is not None:
                        real_max_leverage = float(lev_limits["max"])
                    cost_limits = (market.get("limits") or {}).get("cost") or {}
                    if cost_limits.get("min") is not None:
                        min_notional = float(cost_limits["min"])

                # 2. 用真实上限调用 leverage()，拿到真正会应用的杠杆（降级后的值）
                lev = float(self.leverage(
                    pair=pair,
                    current_time=current_time,
                    current_rate=rate,
                    proposed_leverage=1.0,
                    max_leverage=real_max_leverage,   # ★ 关键：传真实上限，而不是 100.0
                    entry_tag=entry_tag,
                    side=side,
                ) or 1.0)

                # 3. 计算单格保证金 × 真实杠杆 = 名义价值
                planned_stake = self._calc_grid_amount(trade=None, price=rate)
                planned_notional = planned_stake * lev

                # 4. 名义价值不足 → 直接拒绝开仓，避免污染全局 Wallets
                if planned_notional < min_notional:
                    logger.warning(
                        f"{GRID_TAG} [安全拦截] {pair} 计划保证金 {planned_stake:.2f} USDT "
                        f"× 真实杠杆 {lev:.2f}x（交易所上限 {real_max_leverage:.0f}x）"
                        f"= {planned_notional:.2f} 名义价值，低于交易所最低要求 {min_notional:.2f} USDT。"
                        f"已阻止该交易对开仓，避免污染全局资金账本。"
                    )
                    return False

                # 5. 杠杆被降级时，额外打一条 info，方便用户看到"为什么这个币的止盈/仓位跟预期不一样"
                target_lev = float(self.config.get("leverage", 1.0) or 1.0)
                if lev < target_lev - 0.01:
                    logger.warning(
                        f"{GRID_TAG} [杠杆降级提示] {pair} 配置杠杆 {target_lev}x，"
                        f"但交易所实际最大 {real_max_leverage:.0f}x，将使用 {lev:.2f}x 开仓。"
                        f"该交易对的保证金、止盈价、强平价都会按 {lev:.2f}x 重新计算。"
                    )

            except Exception as e:
                logger.exception(f"{GRID_TAG} [安全拦截] 名义价值校验异常: {e}，强制拒绝开仓以防崩坏")
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

            # A full fragment close can be rejected before an order exists
            # when the exchange rounds the exit quantity to zero. Back off
            # before trying again instead of requesting the same exit every
            # position-adjustment cycle.
            retry_until = self._full_reduce_retry_after.get(trade.id)
            if retry_until is None:
                retry_until = self._get_float(trade, "grid_full_reduce_retry_until", 0.0)
            try:
                if retry_until > 0 and float(getattr(trade, "amount", 0) or 0) <= 0:
                    logger.info(f"{GRID_TAG} 仓位已 flat，清理遗留碎片重试锁 | trade_id={trade.id}")
                    self._clear_full_reduce_retry(trade)
                    retry_until = 0.0
            except (TypeError, ValueError):
                pass
            if retry_until > current_time.timestamp():
                return None
            if retry_until > 0:
                self._clear_full_reduce_retry(trade)

            df, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            if df is None or df.empty: return None
            # The last dataframe row is the still-forming candle in live mode.
            # Tracking must react to the latest completed candle only.
            close_price = float(df.iloc[-2]['close'] if len(df) > 1 else df.iloc[-1]['close'])
            if close_price <= 0 or pd.isna(close_price) or np.isinf(close_price): return None
            try:
                executable_price = float(current_rate)
            except (TypeError, ValueError):
                executable_price = close_price
            if executable_price <= 0 or not np.isfinite(executable_price):
                executable_price = close_price
            action_price = max(close_price, executable_price) if not self._is_short else min(
                close_price, executable_price
            )

            entry_candle = self._get(trade, "grid_entry_candle", None)
            if entry_candle == candle_str:
                return None
            guard_until = self._get_int(trade, "grid_entry_guard_until", 0)
            if guard_until > 0 and current_time.timestamp() < guard_until:
                return None

            positions = self._get_grid_positions(trade)
            self._check_and_apply_trailing(trade, close_price)

            g = self._grid_cfg()

            # The live boundaries are the source of truth after the first fill.
            dyn_lower = self._get_float(trade, "grid_dyn_lower", self._cfg_float(g, "lower_price", 0.0))
            dyn_upper = self._get_float(trade, "grid_dyn_upper", self._cfg_float(g, "upper_price", 0.0))
            step = self._get_grid_step_for_bounds(dyn_lower, dyn_upper)

            try:
                actual_amount = float(getattr(trade, "amount", 0) or 0)
                if actual_amount <= 0:
                    self._set_grid_positions(trade, {})
                    self._pending_reduce.pop(trade.id, None)
            except (TypeError, ValueError):
                return None

            try:
                lev = float(getattr(trade, "leverage", 1.0) or 1.0)
            except (TypeError, ValueError):
                lev = 1.0
            if lev <= 0 or not np.isfinite(lev):
                try:
                    market = self.dp.market(trade.pair)
                    real_max = 100.0
                    if market:
                        real_max = float((market.get("limits") or {}).get("leverage", {}).get("max") or 100.0)
                    lev = float(self.leverage(
                        pair=trade.pair, current_time=current_time, current_rate=current_rate,
                        proposed_leverage=1.0, max_leverage=real_max,
                        entry_tag=None, side=self._side_str
                    ) or 1.0)
                except Exception:
                    lev = 1.0

            if not positions:
                trade_stake = float(getattr(trade, "stake_amount", 0) or 0)
                if actual_amount > 0 and trade_stake > 0 and np.isfinite(trade_stake):
                    self._last_candle_str[trade.pair] = candle_str
                    self._set(trade, "grid_pending_reduce", [])
                    self._set(trade, "grid_cleanup_pending", True)
                    return -trade_stake, "grid_reduce_cleanup"

                restart = bool(g.get("restart_after_all_tp", False))
                if restart:
                    if self._get_bool(trade, "grid_stopped", False):
                        return None

                    # ★ 修复：动态白名单扫描/生效期间禁止同 pair 重启，
                    # 否则会绕过 _trigger_dynamic_whitelist_scan 的门禁锁，
                    # 导致"平了又开"永远不换币。
                    if self._dynamic_whitelist_enabled() and self._is_whitelist_scanning():
                        logger.info(
                            f"{GRID_TAG} [{trade.pair}] 动态白名单扫描/生效中，暂缓网格重启"
                        )
                        return None

                    if actual_amount <= 0:
                        self._set(trade, "grid_allow_restart", True)

                    if not self._get_bool(trade, "grid_allow_restart", False):
                        return None

                    # ★ 修复：即使扫描锁已释放，也要校验当前 pair 是否仍在有效白名单内
                    if self._dynamic_whitelist_enabled() and not self._is_pair_in_whitelist(trade.pair):
                        logger.info(
                            f"{GRID_TAG} [{trade.pair}] 已不在有效白名单 "
                            f"{self._get_effective_whitelist()} 中，跳过重启"
                        )
                        return None

                    if self._last_candle_str.get(trade.pair) == candle_str:
                        return None
                    if getattr(trade, "has_open_orders", False):
                        return None

                    restart_price = action_price
                    buy_usdt = self._calc_grid_amount(trade, restart_price)
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

            # 使用 action_price 或 current_rate 来判断
            check_price = action_price

            # 锚定跟踪网格：减仓触发价 = 最近成交价 ± 一个步长（多头向上、空头向下）
            anchor_levels = self._grid_anchor_levels(trade, dyn_lower, dyn_upper)
            if anchor_levels:
                _, _, next_add_p, next_reduce_p = anchor_levels
                self._set(trade, "grid_next_add_price", next_add_p)
                self._set(trade, "grid_next_reduce_price", next_reduce_p)
                reduce_hit = (
                    (not self._is_short and check_price >= next_reduce_p)
                    or (self._is_short and check_price <= next_reduce_p)
                )
                if reduce_hit:
                    # 每次减仓一格量；账本按最近加仓优先（LIFO）扣减
                    cell_margin = self._calc_grid_amount(trade, check_price)
                    try:
                        cell_qty = (cell_margin * lev) / check_price if check_price > 0 else 0.0
                    except Exception:
                        cell_qty = 0.0
                    to_close = self._select_lifo_reduce_slots(positions, cell_qty)
            else:
                # 锚点数据缺失（如旧持仓未写 last_fill 且无有效边界），回退为不触发减仓
                pass

            if to_close:
                try:
                    actual_amount_chk = float(getattr(trade, "amount", 0) or 0)
                except (TypeError, ValueError):
                    actual_amount_chk = 0.0

                total_pos_qty = 0.0
                for _, v_all in positions.items():
                    try:
                        q_all = float(v_all.get("qty", 0.0) or 0.0)
                        if q_all > 0 and np.isfinite(q_all):
                            total_pos_qty += q_all
                    except (TypeError, ValueError):
                        pass

                if actual_amount_chk > 0 and total_pos_qty > actual_amount_chk * 1.015:
                    scale = actual_amount_chk / total_pos_qty
                    logger.warning(
                        f"{GRID_TAG} 检测到网格账本数量({total_pos_qty:.6f})大于实际持仓({actual_amount_chk:.6f})，"
                        f"按比例 {scale:.4f} 对齐各格数量（保留原建仓价与止盈价）"
                    )
                    scaled_positions = {}
                    for k_all, v_all in positions.items():
                        try:
                            e_all = float(v_all.get("entry", 0.0) or 0.0)
                            q_all = float(v_all.get("qty", 0.0) or 0.0)
                            if e_all > 0 and q_all > 0 and np.isfinite(e_all) and np.isfinite(q_all):
                                nv = dict(v_all)
                                nv["qty"] = q_all * scale
                                scaled_positions[k_all] = nv
                        except (TypeError, ValueError):
                            continue

                    if scaled_positions:
                        positions = scaled_positions
                        self._set_grid_positions(trade, positions)
                        refreshed_to_close = []
                        for idx_c, entry_c, _ in to_close:
                            slot = positions.get(str(int(idx_c)))
                            if slot:
                                refreshed_to_close.append((idx_c, entry_c, slot))
                        to_close = refreshed_to_close
                        if not to_close:
                            return None

                try:
                    actual_amount = float(getattr(trade, "amount", 0) or 0)
                    trade_stake = float(getattr(trade, "stake_amount", 0) or 0)
                except (TypeError, ValueError):
                    actual_amount = 0.0
                    trade_stake = 0.0

                # 减仓批次先做可成交性校验；无法形成有效订单时，优先把保证金
                # 最小的碎片格并入相邻格（只动账本，不提前卖出邻格仓位），
                # 全部并入后仍不可成交才回退到整仓平掉的兜底逻辑。
                total_margin = 0.0
                total_pnl = 0.0
                closed = []
                exec_info = None
                return_stake = 0.0
                merge_attempts = 0
                while True:
                    total_margin, total_pnl, closed = self._build_grid_reduce_closed(
                        to_close, lev, close_price
                    )
                    if total_margin <= 0 or not np.isfinite(total_margin):
                        return None

                    requested_qty = sum(item[2] for item in closed)
                    # 待减格覆盖全部实际持仓时直接整仓平仓，走统一的 flat 清理与扫描
                    if (
                            actual_amount > 0
                            and trade_stake > 0
                            and requested_qty >= actual_amount - 1e-9
                    ):
                        self._pending_reduce.pop(trade.id, None)
                        self._set(trade, "grid_pending_reduce", [])
                        self._set(trade, "grid_cleanup_pending", True)
                        return -float(trade_stake), "grid_reduce_full"

                    # Freqtrade 按 stake*amount/stake_amount 折算卖出数量。
                    # 按目标数量反推 stake，避免格子 entry 偏离混合成本时超卖/少卖。
                    if actual_amount > 0:
                        target_qty = min(requested_qty, actual_amount)
                    else:
                        target_qty = requested_qty
                    if trade_stake > 0 and actual_amount > 0:
                        return_stake = target_qty * trade_stake / actual_amount
                    else:
                        return_stake = total_margin
                    exec_info = self._eval_grid_reduce_executability(
                        trade,
                        return_stake,
                        closed,
                        lev,
                        close_price,
                        kwargs.get("min_exit_stake", 0.0),
                    )
                    if exec_info["ok"]:
                        break
                    merged_idx = self._merge_smallest_reduce_slot(trade, positions, to_close)
                    if merged_idx is None:
                        break
                    to_close = [item for item in to_close if int(item[0]) != merged_idx]
                    if not to_close:
                        # 可减格全部并入相邻格，本轮没有可成交的减仓单
                        return None
                    merge_attempts += 1
                    if merge_attempts > len(positions) + 1:
                        break

                if not exec_info["ok"]:
                    logger.warning(
                        f"{GRID_TAG} 减仓无法形成可成交数量 | "
                        f"网格数量={exec_info['requested_qty']:.6f} | 换算数量={exec_info['converted_qty']:.6f} | "
                        f"可成交数量={exec_info['executable_qty']:.6f} | 最小数量={exec_info['min_qty']:.6f} | "
                        f"精度后剩余数量={exec_info['remaining_qty']:.6f} | "
                        f"精度后剩余保证金={exec_info['remaining_stake_after_precision']:.6f} | "
                        f"剩余保证金={exec_info['remaining_stake']:.6f}，"
                        f"将整笔平掉剩余仓位，防止碎片订单锁死！"
                    )
                    # Do not clear local positions before the exchange confirms
                    # the close. order_filled() is the source of truth.
                    full_close_stake = exec_info["trade_stake"]
                    if full_close_stake <= 0 or not np.isfinite(full_close_stake):
                        return None

                    retry_seconds = min(
                        60,
                        max(
                            30,
                            self._cfg_int(self._grid_cfg(), "full_reduce_retry_seconds", 45),
                        ),
                    )
                    retry_until = current_time.timestamp() + retry_seconds
                    self._full_reduce_retry_after[trade.id] = retry_until
                    self._set(trade, "grid_full_reduce_retry_until", retry_until)
                    self._set(trade, "grid_cleanup_pending", True)
                    self._pending_reduce.pop(trade.id, None)
                    self._set(trade, "grid_pending_reduce", [])
                    return -full_close_stake, "grid_reduce_full"

                # 正常流程
                pending_reduce_set.update([idx for idx, _, _, _, _ in closed])
                self._pending_reduce[trade.id] = pending_reduce_set
                self._set(trade, "grid_pending_reduce", sorted(pending_reduce_set))
                self._log_reduce(trade, close_price, closed, total_margin, total_pnl)
                self._log_state_detail(trade, close_price)

                return -float(return_stake), f"grid_reduce_multi_{len(closed)}"

            # ---- 2) 检查加仓（动态运行网格）----
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
                # 提取时间戳（兼容字典和直接传递时间戳的情况）
                try:
                    if isinstance(pending_add, dict):
                        pending_ts = float(pending_add.get("timestamp", 0))
                    else:
                        pending_ts = float(pending_add)
                except (TypeError, ValueError):
                    pending_ts = 0.0

                elapsed = current_time.timestamp() - pending_ts if pending_ts > 0 else float("inf")

                # ★ 修复：不能仅凭时间超时释放 pending_add，否则在途订单成交后
                # 会与新一轮加仓叠加，导致同根 K 线双倍下单。
                # 释放条件收紧为：
                #   1) 时间戳无效（数据损坏）→ 直接释放，但记 error
                #   2) 超过硬上限（默认 300s）且交易所确认无在途订单 / 无持仓增量
                # 其余情况一律 return None 跳过本轮，继续等待。
                hard_timeout = max(120, self._cfg_int(g, "pending_add_hard_timeout_seconds", 300))

                if pending_ts <= 0:
                    # 时间戳损坏，无法判断，保守释放并打 error 便于排查
                    logger.error(
                        f"{GRID_TAG} pending_add 时间戳无效，强制释放 | trade_id={trade.id}"
                    )
                    self._pending_add.pop(trade.id, None)
                    self._set(trade, "grid_pending_add", None)
                    # 不 return，允许本轮继续走后续逻辑（但下面 should_add 可能再次触发，
                    # 这是极端异常路径，可接受）
                elif elapsed <= hard_timeout:
                    # 未到硬上限：无条件跳过，防止重复下单
                    return None
                else:
                    # 到达硬上限：先确认交易所侧是否还有在途订单
                    has_open = bool(getattr(trade, "has_open_orders", False))
                    if not has_open:
                        # 再尝试通过 trade.amount 与 positions 总和做一次对账，
                        # 若持仓数量明显大于本地记录，说明订单其实成交了但回调丢失，
                        # 此时释放 pending 会再次下单，必须放弃本轮并保留 pending 让
                        # order_filled 补记（或等下一轮 order_filled 补记后自然清理）。
                        positions_now = self._get_grid_positions(trade)
                        local_qty = sum(float(v.get("qty", 0) or 0) for v in positions_now.values())
                        try:
                            actual_qty = float(getattr(trade, "amount", 0) or 0)
                        except (TypeError, ValueError):
                            actual_qty = 0.0
                        # 允许 1% 误差（手续费/精度）
                        if actual_qty > local_qty * 1.01 + 1e-9:
                            logger.warning(
                                f"{GRID_TAG} pending_add 超时但持仓数量大于本地记录，"
                                f"疑似回调丢失，保留 pending 等待对账 | "
                                f"trade_id={trade.id} | actual_qty={actual_qty:.8f} | "
                                f"local_qty={local_qty:.8f}"
                            )
                            return None

                        logger.warning(
                            f"{GRID_TAG} pending_add 超时且交易所无在途订单、无持仓增量，释放 | "
                            f"trade_id={trade.id} | elapsed={elapsed:.1f}s"
                        )
                        self._pending_add.pop(trade.id, None)
                        self._set(trade, "grid_pending_add", None)
                        # 释放后不 return，允许本轮继续判断是否加仓
                    else:
                        # 仍有在途订单，继续等待
                        logger.info(
                            f"{GRID_TAG} pending_add 超时但仍有在途订单，继续等待 | "
                            f"trade_id={trade.id} | elapsed={elapsed:.1f}s"
                        )
                        return None

            grid_count = self._cfg_int(g, "grid_count", 20)

            # max_open_grids 是独立的持仓格数上限，不再被 grid_count 钳制。
            # 原因：trailing 平移后网格区间仍是 grid_count 格宽，但趋势行情中
            # 价格会走出原区间，若持仓上限锁死在 grid_count，会在下跌/上涨
            # 途中提前冻结加仓，网格退化为"固定 N 格后躺平"。
            max_grids = self._cfg_int(g, "max_open_grids", 0)
            if max_grids <= 0:
                # 未显式配置时才回落到 grid_count，保持旧默认行为
                max_grids = grid_count if grid_count > 0 else 20
            # 兜底：至少 1 格；不设上限钳制，允许用户配置大于 grid_count
            max_grids = max(1, max_grids)

            if len(positions) >= max_grids:
                return None

            # 锚定跟踪网格：加仓触发价 = 最近成交价 ∓ 一个步长（与减仓共用同一锚点）
            anchor_levels = self._grid_anchor_levels(trade, dyn_lower, dyn_upper)
            if not anchor_levels:
                return None
            _, step, next_add_price, _ = anchor_levels

            # 找出最边缘的 entry
            all_entries = [float(v.get("entry", 0)) for v in positions.values() if "entry" in v]
            if not all_entries: return None

            # Use the completed candle as the stable signal, but also accept
            # the current executable price. Otherwise a price can touch the
            # displayed grid and rebound before the candle closes, leaving
            # the existing position without an add order.
            add_price = min(close_price, executable_price) if not self._is_short else max(
                close_price, executable_price
            )
            trailing_ok = bool(g.get("trailing_up" if self._is_short else "trailing_down", False))
            should_add = trailing_ok and (
                (not self._is_short and add_price <= next_add_price)
                or (self._is_short and add_price >= next_add_price)
            )
            if not should_add:
                return None

            # ---- 极端行情防穿仓机制（仅记录跳空格数，不放大金额）----
            # 计算当前价格距离最边缘建仓价跨了多少格，仅用于日志/风控提示
            if not self._is_short:
                lowest_entry = min(all_entries)
                gap_count = max(0, int((lowest_entry - add_price) / step))
            else:
                highest_entry = max(all_entries)
                gap_count = max(0, int((add_price - highest_entry) / step))

            # 跳空时本根 K 线只加 1 格，金额固定 1 格，绝不放大
            # 成交后由 order_filled 以实际成交价重新锚定基准
            base_buy_usdt = self._calc_grid_amount(trade, close_price)
            if base_buy_usdt <= 0 or pd.isna(base_buy_usdt):
                return None

            buy_usdt_per = base_buy_usdt
            if gap_count > 1:
                logger.info(
                    f"{GRID_TAG} 检测到跳空 {gap_count} 格 | 本根K线仅加1格，"
                    f"金额={buy_usdt_per:.2f}，成交后按实际价重新锚定"
                )

            # 可用余额保护：绝不允许单次加仓超过总资金的 80%，防止爆仓
            available = self._available_stake()
            if available > 0 and buy_usdt_per > available * 0.5:
                logger.warning(
                    f"{GRID_TAG} 极端行情！加仓金额过大，强制缩水 | 需要={buy_usdt_per:.2f} | 可用={available:.2f}")
                buy_usdt_per = available * 0.5  # 强行砍半，保命要紧
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

        except Exception as e:
            logger.error(
                f"{GRID_TAG} [交易对异常隔离] {trade.pair} 加减仓发生底层异常: {e} | "
                f"已自动清理挂起状态，不影响其他交易对。"
            )
            # 清理挂起的减仓状态（避免下一根 K 线进入 pending 死循环）
            if trade.id in self._pending_reduce:
                self._pending_reduce.pop(trade.id, None)
            self._set(trade, "grid_pending_reduce", [])
            # 清理挂起的加仓状态
            if trade.id in self._pending_add:
                self._pending_add.pop(trade.id, None)
            self._set(trade, "grid_pending_add", None)
            # 清理碎片全平重试锁
            self._clear_full_reduce_retry(trade)
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
            if order.ft_order_side not in (self._entry_order_side, self._exit_order_side):
                return
            raw_reason = (
                    getattr(order, "ft_order_reason", None)
                    or getattr(order, "ft_order_tag", None)
                    or ""
            )
            reason = str(raw_reason).strip().lower()
            entry_price = float(getattr(order, "average", None) or trade.open_rate or 0.0)
            qty = self._order_filled_quantity(order)

            try:
                lev = float(getattr(trade, 'leverage', 1.0) or 1.0)
                if not np.isfinite(lev) or lev <= 0:
                    lev = 1.0
            except (TypeError, ValueError):
                lev = 1.0

            margin = (entry_price * qty) / lev

            logger.info(
                f"{GRID_TAG} 成交杠杆校验 | "
                f"Pair={trade.pair} | "
                f"实际杠杆={lev:.2f}x | "
                f"成交价={entry_price:.4f} | "
                f"成交数量={qty:.6f} | "
                f"保证金={margin:.4f} USDT"
            )
            candle_str = self._get_candle_str(current_time)
            is_manual_entry = reason.startswith("force_entry") or reason.startswith("forceenter")
            is_manual_exit = reason.startswith("force_exit") or reason.startswith("forceexit")

            # ---- A. 首仓成交 ----
            if not self._get_bool(trade, "grid_n_initialized", False) and order.ft_order_side == self._entry_order_side:
                target_leverage = float(self.config.get("leverage", 5.0) or 5.0)
                actual_leverage = float(getattr(trade, "leverage", 1.0) or 1.0)
                is_dry_run = bool(self.config.get("dry_run", False))

                if is_dry_run and abs(actual_leverage - target_leverage) > 0.01:
                    # dry_run 下模拟撮合不受交易所限制，强制对齐到目标杠杆
                    logger.warning(
                        f"{GRID_TAG} ⚠️ 干跑模式杠杆不一致，强制对齐 | "
                        f"Pair={trade.pair} | 目标={target_leverage}x | 原始={actual_leverage}x"
                    )
                    trade.leverage = target_leverage
                    try:
                        trade.save()
                    except Exception:
                        pass
                    lev = target_leverage
                elif not is_dry_run and abs(actual_leverage - target_leverage) > 0.01:
                    # 实盘：以交易所真实杠杆为准，不篡改 trade.leverage
                    logger.warning(
                        f"{GRID_TAG} ⚠️ 实盘杠杆与配置不一致，以交易所实际为准 | "
                        f"Pair={trade.pair} | 配置={target_leverage}x | 实际={actual_leverage}x | "
                        f"所有保证金/清算价计算将基于实际杠杆"
                    )
                    lev = actual_leverage
                else:
                    lev = actual_leverage
                    logger.info(
                        f"{GRID_TAG} ✅ 首仓杠杆正常 | {trade.pair} | {actual_leverage}x"
                    )

                margin = (entry_price * qty) / lev

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
                self._set(trade, "grid_trailing_candle", None)
                self._set(trade, "grid_realized_profit", 0.0)
                g = self._grid_cfg()
                # 动态白名单新币优先使用后端预取的专属区间
                runtime_lower, runtime_upper = self._runtime_grid_bounds(trade.pair)
                self._set(trade, "grid_dyn_lower", runtime_lower)
                self._set(trade, "grid_dyn_upper", runtime_upper)
                step = self._get_grid_step_for_bounds(runtime_lower, runtime_upper)
                next_add = (
                    (entry_price + step if self._is_short else entry_price - step)
                    if step > 0
                    else entry_price
                )
                self._set(trade, "grid_last_fill_price", entry_price)
                self._set(trade, "grid_next_add_price", next_add)
                self._set(
                    trade,
                    "grid_next_reduce_price",
                    (entry_price - step if self._is_short else entry_price + step)
                    if step > 0
                    else entry_price,
                )
                self._set_bot_grid_runtime(
                    runtime_lower,
                    runtime_upper,
                    last_fill_price=entry_price,
                    fill_token=f"{int(current_time.timestamp())}:{getattr(order, 'order_id', '')}",
                    next_add_price=next_add,
                    next_reduce_price=(
                        entry_price - step if self._is_short else entry_price + step
                    ),
                    **self._runtime_action_levels(trade, runtime_lower, runtime_upper),
                )

                self._record_chart_marker(
                    event_type="manual_entry" if is_manual_entry else "grid_entry",
                    pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time,
                    message=("手动开仓" if is_manual_entry else f"网格首仓 价格{entry_price:.4f}"),
                    candle_time=current_time
                )
                logger.info(f"[STRATEGY] [ENTRY] {GRID_TAG} ▶ 首仓成交 | 价格={entry_price:.4f} | 杠杆={lev}x")
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

                # ★ 必须先读取，再计算
                runtime_lower = self._get_float(
                    trade, "grid_dyn_lower",
                    self._cfg_float(self._grid_cfg(), "lower_price", 0.0),
                )
                runtime_upper = self._get_float(
                    trade, "grid_dyn_upper",
                    self._cfg_float(self._grid_cfg(), "upper_price", 0.0),
                )
                step = self._get_grid_step_for_bounds(runtime_lower, runtime_upper)

                if step > 0:
                    next_add = entry_price + step if self._is_short else entry_price - step
                else:
                    next_add = entry_price
                self._set(trade, "grid_last_fill_price", entry_price)
                self._set(trade, "grid_next_add_price", next_add)
                self._set(
                    trade,
                    "grid_next_reduce_price",
                    (entry_price - step if self._is_short else entry_price + step)
                    if step > 0
                    else entry_price,
                )

                self._set_bot_grid_runtime(
                    runtime_lower,
                    runtime_upper,
                    last_fill_price=entry_price,
                    fill_token=f"{int(current_time.timestamp())}:{getattr(order, 'order_id', '')}",
                    next_add_price=next_add,
                    next_reduce_price=(
                        entry_price - step if self._is_short else entry_price + step
                    ),
                    **self._runtime_action_levels(trade, runtime_lower, runtime_upper),
                )

                grid_str = ",".join([str(i) for i in idx_list])
                self._record_chart_marker(
                    event_type="grid_add",  # ✅ 改回加仓
                    pair=pair,
                    trade_id=trade.id,
                    side=self._side_str,
                    price=entry_price,  # ✅ 加仓用 entry_price
                    amount=margin,
                    current_time=current_time,
                    message=f"网格加仓 价格{entry_price:.2f}",  # ✅ 文案改回加仓
                    candle_time=current_time
                )
                logger.info(
                    f"[STRATEGY] [ADD] {GRID_TAG} ▲ 真实加仓成交 | 价格={entry_price:.4f} | "
                    f"金额={margin:.2f} | ID={idx_list} | 每格qty={per_qty:.6f}"
                )

            # ---- C. 减仓成交 ----
            elif reason.startswith("grid_reduce_full"):
                filled_price = entry_price
                self._clear_full_reduce_retry(trade)
                self._set(trade, "grid_pending_reduce", [])
                self._set_grid_positions(trade, {})

                actual_amount = float(getattr(trade, "amount", 0) or 0)
                remaining_after = max(0.0, actual_amount - float(qty))
                is_trade_closed = not bool(getattr(trade, "is_open", True))
                order_status = str(getattr(order, "status", "") or "").lower()
                is_order_closed = order_status in ("closed", "filled") and remaining_after <= 1e-8

                is_flat = (
                        actual_amount <= 1e-12
                        or remaining_after <= 1e-8
                        or is_trade_closed
                        or is_order_closed
                )

                self._set(trade, "grid_allow_restart", is_flat)
                self._set(trade, "grid_cleanup_pending", not is_flat)

                if is_flat:
                    _g = self._grid_cfg()
                    if self._dynamic_whitelist_enabled():
                        logger.info(
                            f"{GRID_TAG} 🏁 碎片尾仓整笔平仓后已 flat，触发动态白名单扫描 | "
                            f"closed_pair={trade.pair}"
                        )
                        self._trigger_dynamic_whitelist_scan(trade)
                else:
                    logger.warning(
                        f"{GRID_TAG} 碎片尾仓整笔平仓已提交，但暂未确认完全 flat | "
                        f"pair={trade.pair} | actual_amount={actual_amount:.8f} | "
                        f"qty={qty:.8f} | remaining_after={remaining_after:.8f} | "
                        f"is_open={getattr(trade, 'is_open', True)} | status={order_status}"
                    )

            elif reason.startswith("grid_reduce_multi"):
                self._clear_full_reduce_retry(trade)
                pending_reduce_set = self._pending_reduce.pop(trade.id, set())
                filled_price = entry_price

                positions = self._get_grid_positions(trade)
                # 在 grid_reduce_multi 分支中，遍历 pending_reduce_set 移除格位时同步累计已实现利润：
                batch_realized_pnl = 0.0
                fee_rate = float(getattr(trade, "fee_close", 0.0005) or 0.0005) + float(
                    getattr(trade, "fee_open", 0.0005) or 0.0005
                )

                # ★ 按实际成交数量占待平格子总数量的比例扣减。
                # 减仓数量由 stake→qty 换算并经交易所精度截断，通常与格子记账数量
                # 不完全一致；整格移除会造成账本数量漂移，比例扣减可保留残差格位。
                pending_slots = {}
                total_slot_qty = 0.0
                for idx in pending_reduce_set:
                    slot = positions.get(str(int(idx)))
                    if isinstance(slot, dict):
                        s_qty = float(slot.get("qty", 0.0) or 0.0)
                        if s_qty > 0 and np.isfinite(s_qty):
                            pending_slots[int(idx)] = slot
                            total_slot_qty += s_qty
                try:
                    filled_qty = float(qty)
                except (TypeError, ValueError):
                    filled_qty = 0.0
                if total_slot_qty > 0 and filled_qty > 0:
                    scale = min(filled_qty / total_slot_qty, 1.0)
                else:
                    scale = 1.0
                if not np.isfinite(scale) or scale <= 0:
                    scale = 1.0

                for idx, slot in pending_slots.items():
                    s_entry = float(slot.get("entry", 0.0) or 0.0)
                    s_qty = float(slot.get("qty", 0.0) or 0.0)
                    if s_entry <= 0 or s_qty <= 0:
                        positions.pop(str(idx), None)
                        continue
                    closed_qty = s_qty * scale
                    remaining_qty = s_qty - closed_qty
                    gross = (s_entry - filled_price) * closed_qty if self._is_short else (
                                                                                                    filled_price - s_entry) * closed_qty
                    est_fee = (s_entry + filled_price) * closed_qty * (fee_rate / 2.0)
                    batch_realized_pnl += (gross - est_fee)
                    if remaining_qty <= 1e-12:
                        positions.pop(str(idx), None)
                    else:
                        new_slot = dict(slot)
                        new_slot["qty"] = remaining_qty
                        positions[str(idx)] = new_slot

                prev_realized = self._get_float(trade, "grid_realized_profit", 0.0)
                self._set(trade, "grid_realized_profit", prev_realized + batch_realized_pnl)

                self._set_grid_positions(trade, positions)
                self._set(trade, "grid_pending_reduce", [])
                self._pending_reduce.pop(trade.id, None)

                if not positions:
                    actual_amount = float(getattr(trade, "amount", 0) or 0)
                    remaining_after = max(0.0, actual_amount - float(qty))
                    is_trade_closed = not bool(getattr(trade, "is_open", True))
                    order_status = str(getattr(order, "status", "") or "").lower()
                    is_order_closed = order_status in ("closed", "filled") and remaining_after <= 1e-8

                    if actual_amount <= 1e-12 or remaining_after <= 1e-8 or is_trade_closed or is_order_closed:
                        logger.info(f"{GRID_TAG} 🏁 当前所有网格已平仓，等待后续 K 线继续操作。")
                        self._set(trade, "grid_allow_restart", True)
                        self._set(trade, "grid_cleanup_pending", False)

                        _g = self._grid_cfg()
                        if self._dynamic_whitelist_enabled():
                            logger.info(
                                f"{GRID_TAG} 🏁 网格自动全平完成，触发动态白名单扫描 | "
                                f"closed_pair={trade.pair}"
                            )
                            self._trigger_dynamic_whitelist_scan(trade)
                        else:
                            logger.info(f"{GRID_TAG} 动态白名单未启用，网格全平后允许同 pair 重启")
                    else:
                        logger.warning(
                            f"{GRID_TAG} 网格记录已空，但交易实际剩余数量="
                            f"{actual_amount:.8f}，等待清理实际仓位。"
                        )
                        self._set(trade, "grid_allow_restart", False)
                        self._set(trade, "grid_cleanup_pending", True)
                else:
                    self._set(trade, "grid_allow_restart", False)

                runtime_lower = self._get_float(
                    trade, "grid_dyn_lower",
                    self._cfg_float(self._grid_cfg(), "lower_price", 0.0),
                )
                runtime_upper = self._get_float(
                    trade, "grid_dyn_upper",
                    self._cfg_float(self._grid_cfg(), "upper_price", 0.0),
                )
                self._set(trade, "grid_last_fill_price", filled_price)
                step_rt = self._get_grid_step_for_bounds(runtime_lower, runtime_upper)
                if step_rt > 0:
                    self._set(
                        trade, "grid_next_add_price",
                        filled_price + step_rt if self._is_short else filled_price - step_rt,
                    )
                    self._set(
                        trade, "grid_next_reduce_price",
                        filled_price - step_rt if self._is_short else filled_price + step_rt,
                    )
                self._set_bot_grid_runtime(
                    runtime_lower,
                    runtime_upper,
                    last_fill_price=filled_price,
                    fill_token=f"{int(current_time.timestamp())}:{getattr(order, 'order_id', '')}",
                    **self._runtime_action_levels(trade, runtime_lower, runtime_upper),
                )

                logger.info(
                    f"[STRATEGY] [REDUCE] {GRID_TAG} ▼ 真实减仓成交 | 价格={filled_price:.4f} | "
                    f"金额={margin:.2f} | 格位={sorted(pending_reduce_set)} | "
                    f"扣减比例={scale:.4f} | 已实现(分格口径)={batch_realized_pnl:+.4f} USDT"
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
                self._clear_full_reduce_retry(trade)
                self._pending_reduce.pop(trade.id, None)
                self._pending_add.pop(trade.id, None)
                self._set(trade, "grid_positions", "{}")
                self._set(trade, "grid_pending_reduce", [])
                self._set(trade, "grid_pending_add", None)
                actual_amount = float(getattr(trade, "amount", 0) or 0)
                is_flat = actual_amount <= 0
                self._set(trade, "grid_allow_restart", is_flat)
                self._set(trade, "grid_cleanup_pending", not is_flat)
                # ★ 新增：清理残余仓位后若已 flat，触发扫描
                if is_flat:
                    _g = self._grid_cfg()
                    if self._dynamic_whitelist_enabled():
                        logger.info(
                            f"{GRID_TAG} 🏁 清理残余仓位完成并已 flat，触发动态白名单扫描 | "
                            f"closed_pair={trade.pair}"
                        )
                        self._trigger_dynamic_whitelist_scan(trade)
                logger.info(
                    f"[STRATEGY] [REDUCE] {GRID_TAG} ▼ 清理残余实际仓位成交 | "
                    f"价格={entry_price:.4f} | 剩余数量={actual_amount:.8f}"
                )
                self._record_chart_marker(
                    event_type="exit_fill", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time, message="网格平仓",
                    candle_time=current_time
                )

                # ---- E1. 单交易对整体止盈全平 ----
            elif reason == "grid_pair_tp":
                self._clear_full_reduce_retry(trade)
                self._pending_reduce.pop(trade.id, None)
                self._pending_add.pop(trade.id, None)
                self._set(trade, "grid_pending_reduce", [])
                self._set(trade, "grid_pending_add", None)

                actual_amount = float(getattr(trade, "amount", 0) or 0)
                remaining_after = max(0.0, actual_amount - float(qty))
                is_trade_closed = not bool(getattr(trade, "is_open", True))
                order_status = str(getattr(order, "status", "") or "").lower()
                is_order_closed = order_status in ("closed", "filled") and remaining_after <= 1e-8
                is_flat = (
                        actual_amount <= 1e-12
                        or remaining_after <= 1e-8
                        or is_trade_closed
                        or is_order_closed
                )

                if is_flat:
                    self._set_grid_positions(trade, {})
                    self._set(trade, "grid_realized_profit", 0.0)
                    self._set(trade, "grid_allow_restart", True)
                    self._set(trade, "grid_cleanup_pending", False)
                else:
                    # 仅部分成交/未完全 flat 时：保留清理标记，不提前丢掉已实现利润统计
                    self._set(trade, "grid_allow_restart", False)
                    self._set(trade, "grid_cleanup_pending", True)

                self._record_chart_marker(
                    event_type="exit_fill",
                    pair=pair,
                    trade_id=trade.id,
                    side=self._side_str,
                    price=entry_price,
                    amount=margin,
                    current_time=current_time,
                    message=f"单币止盈全平 价格{entry_price:.4f}",
                    candle_time=current_time,
                )
                logger.info(
                    f"[STRATEGY] [PAIR_TP] {GRID_TAG} 🎯 单交易对止盈全平成交 | "
                    f"{trade.pair} | 价格={entry_price:.4f} | flat={is_flat} | status={order_status}"
                )

                if is_flat:
                    _g = self._grid_cfg()
                    if self._dynamic_whitelist_enabled():
                        logger.info(
                            f"{GRID_TAG} 🎯 单币止盈全平完成，触发动态白名单扫描 | closed_pair={trade.pair}"
                        )
                        self._trigger_dynamic_whitelist_scan(trade)

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
            elif is_manual_entry and order.ft_order_side == self._entry_order_side:
                self._record_chart_marker(
                    event_type="manual_add", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=entry_price, amount=margin,
                    current_time=current_time, message="手动加仓",
                    candle_time=current_time
                )
            elif is_manual_exit and order.ft_order_side == self._exit_order_side:
                trade_amount = float(getattr(trade, "amount", 0) or 0)
                positions_before = self._get_grid_positions(trade)
                grid_qty_before = sum(
                    float(v.get("qty", 0) or 0) for v in positions_before.values()
                )
                order_status = str(getattr(order, "status", "") or "").lower()
                is_trade_closed = not bool(getattr(trade, "is_open", True))

                # 全平判定：交易已关闭、剩余持仓接近 0，或本次成交量覆盖了原网格总数量
                remaining_after_fill = max(0.0, trade_amount - float(qty))
                is_full_exit = (
                        is_trade_closed
                        or trade_amount <= 1e-12
                        or (order_status in ("closed", "filled") and remaining_after_fill <= 1e-8)
                        or (grid_qty_before > 0 and qty >= grid_qty_before * 0.99)
                )

                self._record_chart_marker(
                    event_type="manual_exit" if is_full_exit else "manual_reduce",
                    pair=pair,
                    trade_id=trade.id,
                    side=self._side_str,
                    price=entry_price,
                    amount=margin,
                    current_time=current_time,
                    message="手动平仓" if is_full_exit else "手动减仓",
                    candle_time=current_time,
                )

                if is_full_exit:
                    logger.info(f"{GRID_TAG} 🏁 检测到手动全仓平仓完成，触发重启和动态白名单扫描")
                    self._set(trade, "grid_allow_restart", True)
                    self._set(trade, "grid_cleanup_pending", False)
                    self._set_grid_positions(trade, {})
                    self._set(trade, "grid_pending_reduce", [])
                    self._set(trade, "grid_pending_add", None)
                    self._pending_reduce.pop(trade.id, None)
                    self._pending_add.pop(trade.id, None)
                    self._clear_full_reduce_retry(trade)

                    g = self._grid_cfg()
                    if self._dynamic_whitelist_enabled():
                        self._trigger_dynamic_whitelist_scan(trade)
                    else:
                        logger.info(f"{GRID_TAG} 动态白名单未启用，手动平仓后等待下次信号")
                else:
                    # ★ 手动部分减仓：按 FIFO 扣减 grid_positions，保留剩余格位原 entry 以维持原网格止盈价
                    rem_to_deduct = max(0.0, float(qty))
                    positions = self._get_grid_positions(trade)
                    if positions and rem_to_deduct > 0:
                        sorted_keys = sorted(positions.keys(), key=lambda x: int(x))
                        updated_positions = {}
                        for k in sorted_keys:
                            v = positions[k]
                            try:
                                p_entry = float(v.get("entry", 0.0))
                                p_qty = float(v.get("qty", 0.0))
                            except (TypeError, ValueError):
                                continue
                            if p_entry <= 0 or p_qty <= 0:
                                continue

                            if rem_to_deduct <= 0:
                                new_v = dict(v)
                                new_v["entry"] = p_entry
                                new_v["qty"] = p_qty
                                updated_positions[k] = new_v
                            elif rem_to_deduct >= p_qty - 1e-12:
                                rem_to_deduct = max(0.0, rem_to_deduct - p_qty)
                                # 该格已扣完，移除
                            else:
                                left_qty = max(0.0, p_qty - rem_to_deduct)
                                rem_to_deduct = 0.0
                                if left_qty > 1e-12:
                                    new_v = dict(v)
                                    new_v["entry"] = p_entry
                                    new_v["qty"] = left_qty
                                    updated_positions[k] = new_v

                        # 若扣完后交易所实际持仓仍大于 0 但格位字典变空，兜底挂一个以当前均价/首格为锚点的格位，避免后续走进 empty positions 分支
                        # 如果 trade.amount 还没减掉本次成交的 qty（即 trade_amount 仍约等于扣减前总量），则剩余量应为 trade_amount - qty
                        raw_after = float(getattr(trade, "amount", 0) or 0)
                        total_before_deduct = sum(float(v.get("qty", 0) or 0) for v in positions.values())
                        if raw_after > 0 and total_before_deduct > 0 and abs(
                                raw_after - total_before_deduct) <= total_before_deduct * 0.02:
                            actual_after = max(0.0, raw_after - float(qty))
                        else:
                            actual_after = raw_after

                        if not updated_positions and actual_after > 0:
                            fallback_entry = (
                                entry_price
                                if entry_price > 0
                                else float(getattr(trade, "open_rate", 0.0) or 0.0)
                            )
                            if fallback_entry > 0:
                                updated_positions[str(int(current_time.timestamp()))] = {
                                    "entry": fallback_entry,
                                    "qty": actual_after,
                                }
                        self._set_grid_positions(trade, updated_positions)

                        # 清理可能残留的待减仓状态，让下一根 K 线按最新 positions 重新评估止盈
                        self._pending_reduce.pop(trade.id, None)
                        self._set(trade, "grid_pending_reduce", [])
                        self._clear_full_reduce_retry(trade)

                        runtime_lower = self._get_float(
                            trade,
                            "grid_dyn_lower",
                            self._cfg_float(self._grid_cfg(), "lower_price", 0.0),
                        )
                        runtime_upper = self._get_float(
                            trade,
                            "grid_dyn_upper",
                            self._cfg_float(self._grid_cfg(), "upper_price", 0.0),
                        )
                        self._set(trade, "grid_last_fill_price", entry_price)
                        step_rt = self._get_grid_step_for_bounds(runtime_lower, runtime_upper)
                        if step_rt > 0:
                            self._set(
                                trade, "grid_next_add_price",
                                entry_price + step_rt if self._is_short else entry_price - step_rt,
                            )
                            self._set(
                                trade, "grid_next_reduce_price",
                                entry_price - step_rt if self._is_short else entry_price + step_rt,
                            )
                        self._set_bot_grid_runtime(
                            runtime_lower,
                            runtime_upper,
                            last_fill_price=entry_price,
                            fill_token=f"{int(current_time.timestamp())}:{getattr(order, 'order_id', '')}",
                            **self._runtime_action_levels(trade, runtime_lower, runtime_upper),
                        )
                        logger.info(
                            f"{GRID_TAG} 手动部分减仓已同步网格账本 | 减仓数量={qty:.6f} | "
                            f"剩余格位数={len(updated_positions)} | 实际持仓={actual_after:.6f}"
                        )
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
        self._clear_full_reduce_retry(trade)
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
        self._clear_full_reduce_retry(trade)
        if trade.id in self._pending_add:
            self._pending_add.pop(trade.id, None)
            self._set(trade, "grid_pending_add", None)

    # ============================================================
    # 自定义止损
    # ============================================================
    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            g = self._grid_cfg()
            rate = float(current_rate or 0.0)
            if rate <= 0:
                return None

            # 1) 单交易对整体止盈检测（优先于区间止损）
            # 单币止盈仅多因子筛选模式可用：手动模式下 BotConfig.buildPayload
            # 会移除 smart_range_mode 字段，此处以此作为 scanner 模式判据，
            # 手动模式统一由机器人风控止盈兜底，避免两套止盈重复触发。
            is_scanner_mode = bool(g.get("smart_range_mode"))
            if (
                    is_scanner_mode
                    and bool(g.get("pair_tp_enabled", False))
                    and self._get_bool(trade, "grid_n_initialized", False)
            ):
                positions = self._get_grid_positions(trade)
                actual_amount = float(getattr(trade, "amount", 0) or 0)
                if positions and actual_amount > 0:
                    # 统一使用 Freqtrade 加权均价口径：
                    # realized_profit = 已平仓订单的真实累计盈亏(USDT，含手续费，
                    # 由 recalc_trade_from_orders 在每次成交后刷新)
                    # calculate_profit(rate) = 未实现盈亏，同样基于 trade.open_rate
                    # 两者相加才是该交易对的真实总盈亏，避免分格账本与均价账本混算。
                    realized_usdt = float(getattr(trade, "realized_profit", 0.0) or 0.0)
                    try:
                        prof = trade.calculate_profit(rate)
                        unrealized_usdt = float(prof.profit_abs or 0.0)
                        total_pair_profit_usdt = float(prof.total_profit or 0.0)
                    except Exception:
                        unrealized_usdt = 0.0
                        total_pair_profit_usdt = realized_usdt + float(
                            trade.calc_profit(rate) or 0.0
                        )

                    tp_mode = str(g.get("pair_tp_mode", "ratio")).lower()
                    if tp_mode == "amount":
                        target_usdt = self._cfg_float(g, "pair_tp_amount", 0.0)
                        if target_usdt > 0 and total_pair_profit_usdt >= target_usdt:
                            logger.info(
                                f"{GRID_TAG} 🎯 触发单币金额止盈 | {pair} | "
                                f"累计净利={total_pair_profit_usdt:.2f} USDT (已实现={realized_usdt:.2f}, "
                                f"浮盈={unrealized_usdt:.2f}) >= 目标={target_usdt:.2f} USDT"
                            )
                            return "grid_pair_tp"
                    else:
                        target_pct = self._cfg_float(g, "pair_tp_ratio", 0.0)
                        if target_pct > 0:
                            # 资金基准：取该交易对分配的网格总资金（单格保证金 * 网格数），兜底用当前保证金
                            grid_count = max(1, self._cfg_int(g, "grid_count", 20))
                            per_grid_stake = self._calc_grid_amount(trade, rate)
                            allocated_capital = per_grid_stake * grid_count
                            if allocated_capital <= 0:
                                allocated_capital = float(getattr(trade, "stake_amount", 0) or 0)

                            if allocated_capital > 0:
                                total_pair_profit_pct = (total_pair_profit_usdt / allocated_capital) * 100.0
                                if total_pair_profit_pct >= target_pct:
                                    logger.info(
                                        f"{GRID_TAG} 🎯 触发单币比例止盈 | {pair} | "
                                        f"累计收益率={total_pair_profit_pct:.2f}% "
                                        f"({total_pair_profit_usdt:.2f}/{allocated_capital:.2f} USDT) "
                                        f">= 目标={target_pct:.2f}%"
                                    )
                                    return "grid_pair_tp"

            # 2) 原有上下沿区间止损逻辑（优先读取动态区间，兜底配置区间）
            lower = self._get_float(trade, "grid_dyn_lower", self._cfg_float(g, "lower_price", 0.0))
            upper = self._get_float(trade, "grid_dyn_upper", self._cfg_float(g, "upper_price", 0.0))

            # 如果开启了追踪，默认禁用上下沿止损
            stop_below = bool(g.get("stop_below_lower", True)) and not bool(g.get("trailing_down", False))
            stop_above = bool(g.get("stop_above_upper", False)) and not bool(g.get("trailing_up", False))

            if not self._is_short:
                if stop_below and lower > 0 and rate <= lower:
                    return "grid_stop_lower"
            else:
                if stop_above and upper > 0 and rate >= upper:
                    return "grid_stop_upper"
            return None
        except Exception:
            logger.exception(f"{GRID_TAG} custom_exit 异常 | pair={pair}")
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
            per_grid = float((self.config or {}).get("stake_amount", 0) or 0)
            if per_grid <= 0 or pd.isna(per_grid):
                wallet = float((self.config or {}).get("dry_run_wallet", 0) or 0)
                grid_count = max(1, self._cfg_int(g, "grid_count", 20))
                per_grid = wallet / grid_count

        # ★ 修改：传交易所真实杠杆上限，避免 min_margin_needed 被低估
        pair = trade.pair if trade is not None else (
            (self.config.get("exchange", {}).get("pair_whitelist") or [""])[0]
        )
        real_max_leverage = 100.0
        try:
            market = self.dp.market(pair) if pair else None
            if market:
                lev_limits = (market.get("limits") or {}).get("leverage") or {}
                if lev_limits.get("max") is not None:
                    real_max_leverage = float(lev_limits["max"])
        except Exception:
            pass

        leverage = float(self.leverage(
            pair=pair,
            current_time=None,
            current_rate=price,
            proposed_leverage=1.0,
            max_leverage=real_max_leverage,
            entry_tag=None,
            side=self._side_str
        ) or 1.0)

        try:
            market = self.dp.market(pair) if pair else None
            min_notional = float(market["limits"]["cost"]["min"] or 5.0) if market else 5.0
        except Exception:
            min_notional = 5.0

        min_margin_needed = min_notional / leverage

        if per_grid < min_margin_needed:
            per_grid = min_margin_needed

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
                    # ★ 核心修改：保留 entry 和 qty，并把其他自定义字段原样保留
                    new_val = {"entry": entry, "qty": qty}
                    for k, v in value.items():
                        if k not in ("entry", "qty"):
                            # 确保额外字段可以被 JSON 序列化
                            if isinstance(v, (int, float, str, bool, type(None))):
                                new_val[k] = v
                            elif isinstance(v, dict):
                                new_val[k] = v
                    clean[idx] = new_val
            except (AttributeError, TypeError, ValueError):
                continue
        self._set(trade, "grid_positions", json.dumps(clean, allow_nan=False))

    def _add_grid_position(self, trade, idx: int, entry: float, qty: float):
        positions = self._get_grid_positions(trade)
        positions[str(int(idx))] = {"entry": float(entry), "qty": float(qty)}
        self._set_grid_positions(trade, positions)

    def _get_amount_limits(self, trade):
        """Return (min_qty, amount_step) for the pair's market limits."""
        min_qty = 0.001
        amount_step = min_qty
        try:
            market = self.dp.market(trade.pair)
            if market and market.get("limits", {}).get("amount", {}).get("min"):
                min_qty = float(market["limits"]["amount"]["min"])
            precision = (market or {}).get("precision", {}).get("amount")
            if precision is not None:
                precision = float(precision)
                # CCXT uses decimal places for DECIMAL_PLACES and a
                # step size for TICK_SIZE markets.
                amount_step = (
                    10.0 ** (-precision)
                    if precision >= 1 or precision == 0
                    else precision
                )
        except Exception:
            pass
        if not np.isfinite(amount_step) or amount_step <= 0:
            amount_step = min_qty
        return min_qty, amount_step

    def _build_grid_reduce_closed(self, to_close, lev, close_price):
        total_margin = 0.0
        total_pnl = 0.0
        closed = []
        for idx, entry, v in to_close:
            qty = float(v.get("qty", 0.0))
            margin = (entry * qty) / lev if lev > 0 else 0.0
            pnl = (entry - close_price) * qty if self._is_short else (close_price - entry) * qty
            if pd.isna(margin) or np.isinf(margin):
                margin = 0.0
            if pd.isna(pnl) or np.isinf(pnl):
                pnl = 0.0
            total_margin += margin
            total_pnl += pnl
            closed.append((idx, entry, qty, margin, pnl))
        return total_margin, total_pnl, closed

    def _eval_grid_reduce_executability(self, trade, close_stake, closed, lev, close_price, min_exit_stake):
        # Freqtrade converts the returned stake amount back to a position
        # quantity before applying exchange precision. Check that result,
        # not only the quantity stored in each grid slot.
        requested_qty = sum(item[2] for item in closed)
        min_qty, amount_step = self._get_amount_limits(trade)
        try:
            actual_amount = float(getattr(trade, "amount", 0) or 0)
            trade_stake = float(getattr(trade, "stake_amount", 0) or 0)
        except (TypeError, ValueError):
            actual_amount = 0.0
            trade_stake = 0.0

        # This is the same conversion used by Freqtrade when it handles
        # a negative adjustment. A tiny grid leg can otherwise become 0
        # after precision conversion and never create an exit order.
        converted_qty = (
            close_stake * actual_amount / trade_stake
            if trade_stake > 0 else 0.0
        )
        executable_qty = (
                np.floor((converted_qty + amount_step * 1e-9) / amount_step)
                * amount_step
        )
        try:
            min_exit_stake = float(min_exit_stake or 0.0)
        except (TypeError, ValueError):
            min_exit_stake = 0.0
        remaining_stake = max(trade_stake - close_stake, 0.0)
        would_leave_unexitable_remainder = (
                remaining_stake > 0
                and min_exit_stake > 0
                and remaining_stake < min_exit_stake
        )
        remaining_qty = max(actual_amount - executable_qty, 0.0)
        remaining_stake_after_precision = (
            remaining_qty * close_price / lev if lev > 0 else 0.0
        )
        would_leave_precision_remainder = (
                remaining_qty > 0
                and (
                        remaining_qty < min_qty
                        or (
                                min_exit_stake > 0
                                and remaining_stake_after_precision < min_exit_stake
                        )
                )
        )
        ok = not (
                requested_qty < min_qty
                or executable_qty < min_qty
                or executable_qty > actual_amount + amount_step
                or would_leave_unexitable_remainder
                or would_leave_precision_remainder
        )
        return {
            "ok": ok,
            "requested_qty": requested_qty,
            "min_qty": min_qty,
            "amount_step": amount_step,
            "converted_qty": converted_qty,
            "executable_qty": executable_qty,
            "actual_amount": actual_amount,
            "trade_stake": trade_stake,
            "remaining_stake": remaining_stake,
            "remaining_qty": remaining_qty,
            "remaining_stake_after_precision": remaining_stake_after_precision,
        }

    def _merge_smallest_reduce_slot(self, trade, positions, to_close):
        """Merge the smallest-margin slot in the reduce batch into its nearest
        non-batch neighbor. Ledger-only: the neighbor is NOT sold early."""
        try:
            to_close_idxs = {int(item[0]) for item in to_close}

            def _slot_margin(item):
                _, entry, v = item
                try:
                    q = float(v.get("qty", 0.0) or 0.0)
                except (TypeError, ValueError):
                    q = 0.0
                return abs(float(entry)) * max(q, 0.0)

            idx, _, _ = min(to_close, key=_slot_margin)
            idx = int(idx)
            src_key = str(idx)
            src = positions.get(src_key)
            if not isinstance(src, dict):
                return None
            try:
                src_entry = float(src.get("entry", 0.0) or 0.0)
                src_qty = float(src.get("qty", 0.0) or 0.0)
            except (TypeError, ValueError):
                return None
            if src_entry <= 0 or src_qty <= 0:
                return None

            best_key = None
            best_diff = None
            for k, v in positions.items():
                try:
                    n_idx = int(k)
                except (TypeError, ValueError):
                    continue
                if n_idx == idx or n_idx in to_close_idxs:
                    continue
                if not isinstance(v, dict):
                    continue
                try:
                    n_entry = float(v.get("entry", 0.0) or 0.0)
                    n_qty = float(v.get("qty", 0.0) or 0.0)
                except (TypeError, ValueError):
                    continue
                if n_entry <= 0 or n_qty <= 0:
                    continue
                diff = abs(n_entry - src_entry)
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_key = k
            if best_key is None:
                return None

            dst = positions[best_key]
            d_entry = float(dst.get("entry", 0.0) or 0.0)
            d_qty = float(dst.get("qty", 0.0) or 0.0)
            total_qty = src_qty + d_qty
            if total_qty <= 0 or not np.isfinite(total_qty):
                return None
            new_entry = (src_entry * src_qty + d_entry * d_qty) / total_qty
            if new_entry <= 0 or not np.isfinite(new_entry):
                return None
            new_dst = dict(dst)
            new_dst["entry"] = float(new_entry)
            new_dst["qty"] = float(total_qty)
            positions[best_key] = new_dst
            positions.pop(src_key, None)
            self._set_grid_positions(trade, positions)
            logger.info(
                f"{GRID_TAG} 碎片格并入相邻格 | {trade.pair} | "
                f"并入建仓={src_entry:.4f} 数量={src_qty:.6f} -> "
                f"邻格={best_key} 新建仓={new_entry:.4f} 新数量={total_qty:.6f}"
            )
            return idx
        except Exception as e:
            logger.warning(f"{GRID_TAG} 碎片格并入失败 | {trade.pair} | {e}")
            return None

    def _log_reduce(self, trade, price, closed, total_margin, total_pnl):
        try:
            if len(closed) == 1:
                idx, entry, qty, margin, pnl = closed[0]
                pnl_pct = (price - entry) / entry * 100 if entry > 0 else 0
                al = self._grid_anchor_levels(trade)
                tp_price = al[3] if al else self._grid_tp_price(entry, trade)
                logger.info(
                    f"[STRATEGY] [REDUCE] {GRID_TAG} {GREEN}▼ 减仓{RESET} | {trade.pair} | {entry:.4f} → {price:.4f}(减仓线={tp_price:.4f}) | pnl={pnl_pct:+.2f}% | pnl={pnl:+.2f} USDT | 数量={qty:.6f} | 释放={margin:.2f}"
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
            al = self._grid_anchor_levels(trade)
            anchor_desc = ""
            if al:
                anchor, _, na, nr = al
                anchor_desc = f" | 锚点={anchor:.4f} 下次加仓={na:.4f} 下次减仓={nr:.4f}"
            if positions:
                parts = []
                for k in sorted(positions.keys(), key=lambda x: int(x)):
                    v = positions[k]
                    entry = float(v.get("entry", 0.0))
                    parts.append(f"建仓={entry:.4f}")
                logger.info(f"{GRID_TAG}    └ 持仓: {' '.join(parts)} | 共{len(positions)}单{anchor_desc}")
            else:
                logger.info(f"{GRID_TAG}    └ 持仓: 无 | 共0单{anchor_desc}")
        except Exception:
            pass

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
