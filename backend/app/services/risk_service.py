# backend/app/services/risk_service.py
import time
import traceback
import logging
import json
from pathlib import Path

from app.core import runtime
from app.services.position_service import PositionService
from app.core.defaults import RISK_DEFAULTS
from app.services.bot_runtime import list_running_bots

# 使用日志替代 print，避免同步阻塞
logger = logging.getLogger(__name__)
COMBO_CONFIG_PATH = Path("config/combo_profit.json")

class RiskService:
    # 缓存 _get_bot_risk 的结果，避免高频查库
    _bot_risk_cache = {}
    _bot_risk_cache_time = {}
    RISK_CACHE_TTL = 30  # 30秒缓存
    _combo_cooldown_time = 0

    # ====== 每个 bot 独立的 ROUND_INFO ======
    @classmethod
    def _round_info(cls, bot_id: int) -> dict:
        return runtime.ROUND_INFO_BY_BOT.setdefault(bot_id, {
            "start_profit": None,
            "start_long_closed": None,
            "start_short_closed": None,
            "start_balance": None,
            "round_profit": 0, "round_ratio": 0,
            "global_tp_count": 0, "global_sl_count": 0,
            "global_trail_count": 0,
            "last_tp_time": 0,
            "peak_profit": 0.0, "peak_ratio": 0.0,
            "trough_profit": 0.0, "trough_ratio": 0.0,
            "trail_active": False,
            "exiting": False,
        })

    @classmethod
    def init_round(cls, bot_id: int):
        info = cls._round_info(bot_id)
        closed = PositionService.get_closed_profit_summary(bot_id=bot_id)
        info["start_profit"] = closed["total_closed_profit"] or 0.0
        info["start_long_closed"] = closed["long_closed_profit"] or 0.0
        info["start_short_closed"] = closed["short_closed_profit"] or 0.0
        info["start_balance"] = PositionService.get_account_summary(bot_id=bot_id).get("total_balance") or 0.0

        info["round_profit"] = 0.0
        info["round_ratio"] = 0.0
        info["last_tp_time"] = time.time()
        info["peak_profit"] = 0.0
        info["peak_ratio"] = 0.0
        info["trough_profit"] = 0.0
        info["trough_ratio"] = 0.0
        info["trail_active"] = False
        info["exiting"] = False

    @classmethod
    def calc_round_profit(cls, bot_id: int):
        info = cls._round_info(bot_id)

        # ★ 优化：PositionService 内部有 5 秒缓存，这里直接拿快照即可
        snapshot = PositionService.get_snapshot(bot_id=bot_id)
        long_positions = PositionService._extract_trades(snapshot["long_status"])
        short_positions = PositionService._extract_trades(snapshot["short_status"])
        long_trades = PositionService._extract_trades(snapshot["long_trades"])
        short_trades = PositionService._extract_trades(snapshot["short_trades"])

        try:
            closed = PositionService.get_closed_profit_summary(
                snapshot, long_trades=long_trades, short_trades=short_trades,
                long_status=long_positions, short_status=short_positions,
            )
        except Exception as e:
            logger.error(f"[Risk] closed summary error bot={bot_id}: {e}")
            closed = {"long_closed_profit": 0, "short_closed_profit": 0, "total_closed_profit": 0}

        try:
            floating = PositionService.get_floating_profit(
                snapshot, long_positions=long_positions, short_positions=short_positions
            )
        except Exception as e:
            logger.error(f"[Risk] floating error bot={bot_id}: {e}")
            floating = {"long_float": 0, "short_float": 0, "total_float": 0}

        start_long_closed = info.get("start_long_closed") or 0.0
        start_short_closed = info.get("start_short_closed") or 0.0
        start_balance = info.get("start_balance") or 0.0

        long_round = (closed["long_closed_profit"] - start_long_closed) + floating["long_float"]
        short_round = (closed["short_closed_profit"] - start_short_closed) + floating["short_float"]
        round_profit = long_round + short_round
        round_ratio = round_profit / start_balance * 100 if start_balance else 0.0

        info["round_profit"] = round_profit
        info["round_ratio"] = round(round_ratio, 2)

        if round_profit > info.get("peak_profit", 0.0):
            info["peak_profit"] = round_profit
        if round_ratio > info.get("peak_ratio", 0.0):
            info["peak_ratio"] = round_ratio
        if round_profit < info.get("trough_profit", 0.0):
            info["trough_profit"] = round_profit
        if round_ratio < info.get("trough_ratio", 0.0):
            info["trough_ratio"] = round_ratio

    @classmethod
    def calc_direction_imbalance(cls):
        # ★ 优化：改成拿当前全局缓存中的所有持仓数量，避免高频全量拉取
        # 复用 PositionService 的全局快照缓存
        try:
            snapshot = PositionService.get_snapshot()
            long_count = len(PositionService._extract_trades(snapshot.get("long_status", [])))
            short_count = len(PositionService._extract_trades(snapshot.get("short_status", [])))
            runtime.ROUND_INFO["long_count"] = long_count
            runtime.ROUND_INFO["short_count"] = short_count
        except Exception as e:
            logger.error(f"[Risk] calc_direction_imbalance error: {e}")

    @classmethod
    def force_exit_all(cls, bot_id: int, reason: str = None):
        positions = PositionService.get_all_positions(bot_id=bot_id)
        if reason:
            for pos in positions:
                tid = pos.get("trade_id")
                if tid is not None:
                    runtime.set_exit_reason(bot_id, tid, reason)

        failed = []
        for pos in positions:
            tid = pos.get("trade_id")
            side = pos.get("side")
            ok = False
            for _ in range(3):
                try:
                    PositionService.force_exit(tid, side, bot_id=bot_id)
                    ok = True
                    break
                except Exception as e:
                    logger.error(f"force_exit fail bot={bot_id} tid={tid}: {e}")
                    time.sleep(1)
            if not ok:
                failed.append(tid)
        return failed

    @classmethod
    def wait_positions_closed(cls, bot_id: int, timeout=60, stable_count=3, interval=2):
        start = time.time()
        empty = 0
        while time.time() - start < timeout:
            try:
                positions = PositionService.get_all_positions(bot_id=bot_id)
            except Exception:
                positions = None

            if positions is not None and len(positions) == 0:
                empty += 1
                if empty >= stable_count:
                    return True
            else:
                empty = 0
            time.sleep(interval)
        return False

    @classmethod
    def _get_bot_risk(cls, bot_id: int) -> dict:
        # ★ 优化：增加 30 秒缓存，避免每 5 秒就去查一遍数据库
        now = time.time()
        if bot_id in cls._bot_risk_cache:
            if now - cls._bot_risk_cache_time.get(bot_id, 0) < cls.RISK_CACHE_TTL:
                return cls._bot_risk_cache[bot_id]

        from app.services.bot_manager import BotManager
        bot = BotManager.get(bot_id)
        if not bot:
            return {}

        risk = {
            "tp_enabled": bot.get("tp_enabled"),
            "tp_mode": bot.get("tp_mode", "amount"),
            "tp_amount": bot.get("tp_amount", 0),
            "tp_ratio": bot.get("tp_ratio", 0),

            "sl_enabled": bot.get("sl_enabled"),
            "sl_mode": bot.get("sl_mode", "amount"),
            "sl_amount": bot.get("sl_amount", 0),
            "sl_ratio": bot.get("sl_ratio", 0),

            "trail_enabled": bot.get("trail_enabled"),
            "trail_mode": bot.get("trail_mode", "ratio"),
            "trail_activate_amount": bot.get("trail_activate_amount", 0),
            "trail_activate_ratio": bot.get("trail_activate_ratio", 0),
            "trail_drawdown_amount": bot.get("trail_drawdown_amount", 0),
            "trail_drawdown_ratio": bot.get("trail_drawdown_ratio", 0),

            "auto_stop_on_tp": bot.get("auto_stop_on_tp", True),
            "auto_stop_on_sl": bot.get("auto_stop_on_sl", True),
            "auto_stop_on_trail": bot.get("auto_stop_on_trail", True),
        }

        cls._bot_risk_cache[bot_id] = risk
        cls._bot_risk_cache_time[bot_id] = now
        return risk

    @classmethod
    def check_risk(cls, bot_id: int):
        info = cls._round_info(bot_id)
        if info.get("exiting"):
            return

        position_count = PositionService.get_position_count(bot_id=bot_id)
        # logger.debug(f"[Risk] bot={bot_id} position_count={position_count}") # 降低日志级别

        if position_count["total"] == 0:
            return
        if time.time() - (info.get("last_tp_time", 0) or 0) < 60:
            return

        cls.calc_round_profit(bot_id)

        risk = cls._get_bot_risk(bot_id)
        profit = info.get("round_profit", 0.0) or 0.0
        ratio = info.get("round_ratio", 0.0) or 0.0

        # ---- 止盈 ----
        if risk.get("tp_enabled"):
            mode = risk.get("tp_mode", RISK_DEFAULTS["tp_mode"])
            hit = False
            if mode == "ratio":
                th = float(risk.get("tp_ratio", 0) or 0)
                hit = th > 0 and ratio >= th
            else:
                th = float(risk.get("tp_amount", 0) or 0)
                hit = th > 0 and profit >= th

            if hit:
                cls._handle_exit(
                    bot_id, "bot_tp", "单bot止盈", "单bot止盈",
                    auto_stop=risk.get("auto_stop_on_tp", RISK_DEFAULTS["auto_stop_on_tp"]),
                )
                info["global_tp_count"] += 1
                return

        # ---- 止损 ----
        if risk.get("sl_enabled"):
            mode = risk.get("sl_mode", RISK_DEFAULTS["sl_mode"])
            hit = False
            if mode == "ratio":
                th = float(risk.get("sl_ratio", 0) or 0)
                hit = th > 0 and ratio <= -th
            else:
                th = float(risk.get("sl_amount", 0) or 0)
                hit = th > 0 and profit <= -th

            if hit:
                cls._handle_exit(
                    bot_id, "bot_sl", "单bot止损", "单bot止损",
                    auto_stop=risk.get("auto_stop_on_sl", RISK_DEFAULTS["auto_stop_on_sl"]),
                )
                info["global_sl_count"] += 1
                return

        # ---- 追踪止损 ----
        if risk.get("trail_enabled"):
            mode = risk.get("trail_mode", RISK_DEFAULTS["trail_mode"])
            if mode == "ratio":
                activate = float(risk.get("trail_activate_ratio", RISK_DEFAULTS["trail_activate_ratio"]) or 0)
                drawdown = float(risk.get("trail_drawdown_ratio", RISK_DEFAULTS["trail_drawdown_ratio"]) or 0)
                current, peak, trough = ratio, info["peak_ratio"], info["trough_ratio"]
            else:
                activate = float(risk.get("trail_activate_amount", RISK_DEFAULTS["trail_activate_amount"]) or 0)
                drawdown = float(risk.get("trail_drawdown_amount", RISK_DEFAULTS["trail_drawdown_amount"]) or 0)
                current, peak, trough = profit, info["peak_profit"], info["trough_profit"]

            if drawdown > 0 and activate != 0:
                if not info.get("trail_active"):
                    if activate > 0 and peak >= activate:
                        info["trail_active"] = True
                        info["trail_direction"] = "profit"
                        info["peak_profit"] = profit
                        info["peak_ratio"] = ratio
                    elif activate < 0 and trough <= activate:
                        info["trail_active"] = True
                        info["trail_direction"] = "loss"
                        info["trough_profit"] = profit
                        info["trough_ratio"] = ratio

                if info.get("trail_active"):
                    direction = info.get("trail_direction", "profit")
                    if direction == "profit":
                        hit = current <= peak - drawdown
                    else:
                        hit = current >= trough + drawdown

                    if hit:
                        info["global_trail_count"] = info.get("global_trail_count", 0) + 1
                        cls._handle_exit(
                            bot_id, "bot_trail", "单bot追踪止损", "单bot追踪止损",
                            auto_stop=risk.get("auto_stop_on_trail", RISK_DEFAULTS["auto_stop_on_trail"]),
                        )
                        return

    @classmethod
    def _handle_exit(cls, bot_id, event_type, message, reason, auto_stop: bool = False):
        info = cls._round_info(bot_id)
        if info.get("exiting"):
            return
        info["exiting"] = True
        info["last_tp_time"] = time.time()
        try:
            cls.record_exit_events(bot_id, event_type, message)
            failed = cls.force_exit_all(bot_id, reason=reason)
            if failed:
                logger.error(f"[Risk] bot={bot_id} 以下 trade_id 平仓失败: {failed}")

            if not cls.wait_positions_closed(bot_id):
                return

            if auto_stop:
                try:
                    from app.services.bot_manager import BotManager
                    BotManager.stop(bot_id)
                    logger.info(f"[Risk] bot={bot_id} 已自动停止（触发 {event_type}）")
                except Exception as e:
                    logger.error(f"[Risk] bot={bot_id} 自动停止失败: {e}")

            cls.init_round(bot_id)
        finally:
            info["exiting"] = False

    @classmethod
    def record_exit_events(cls, bot_id: int, event_type: str, message: str):
        import sys
        from pathlib import Path
        from datetime import datetime
        EVENT_LOGGER_DIR = Path(__file__).resolve().parents[3] / "freqtrade" / "user_data" / "strategies"
        if str(EVENT_LOGGER_DIR) not in sys.path:
            sys.path.insert(0, str(EVENT_LOGGER_DIR))
        try:
            from event_logger import record_event
        except Exception as e:
            logger.error(f"[Risk] event_logger 导入失败: {e}")
            return

        positions = PositionService.get_all_positions(bot_id=bot_id)
        current_time = datetime.utcnow()
        for pos in positions:
            tid = pos.get("trade_id")
            pair = pos.get("pair")
            price = pos.get("current_rate") or pos.get("close_rate") or 0
            amount = pos.get("amount") or 0
            side = pos.get("side", "long").lower()
            if tid is None or not pair:
                continue
            strategy = "DcaTpShort" if side == "short" else "DcaTpLong"
            try:
                record_event(strategy=strategy, pair=pair, trade_id=tid,
                             event_type=event_type, side=side, price=float(price),
                             amount=float(amount), message=message, current_time=current_time)
            except Exception as e:
                logger.error(f"[Risk] record_event 失败: {e}")


    @classmethod
    def check_combo_profit(cls):
        if not COMBO_CONFIG_PATH.exists():
            return

        try:
            cfg_data = json.loads(COMBO_CONFIG_PATH.read_text())
        except Exception as e:
            logger.error(f"[Combo] 读取配置文件失败: {e}")
            return

        groups = cfg_data.get("groups", [])
        if not groups:
            return

        now = time.time()
        # 冷却时间记录 (可以为每个组单独记录，这里简化为全局)
        if now - cls._combo_cooldown_time < 60:
            return

        for group in groups:
            if not group.get("enabled") or not group.get("bot_ids"):
                continue

            total_profit = 0.0
            for bid in group.get("bot_ids"):
                try:
                    summary = PositionService.get_total_profit_summary(bot_id=bid)
                    total_profit += summary.get("total_profit", 0.0)
                except Exception as e:
                    logger.warning(f"[Combo] 获取 bot={bid} 收益失败: {e}")

            if total_profit >= group.get("target_profit", 5):
                logger.info(f"[Combo] 🎯 触发组合【{group.get('name')}】联合止盈！当前利润={total_profit:.2f}")

                for bid in group.get("bot_ids"):
                    cls.force_exit_all(bid, reason=f"combo_{group.get('name')}")

                for bid in group.get("bot_ids"):
                    cls.wait_positions_closed(bid, timeout=10)

                if group.get("auto_stop"):
                    from app.services.bot_manager import BotManager
                    for bid in group.get("bot_ids"):
                        try:
                            BotManager.stop(bid)
                        except Exception:
                            pass

                # 触发后关闭这个组的开关
                group["enabled"] = False
                try:
                    COMBO_CONFIG_PATH.write_text(json.dumps(cfg_data, indent=2))
                except Exception as e:
                    logger.error(f"[Combo] 更新配置失败: {e}")

                cls._combo_cooldown_time = time.time()

    @classmethod
    def monitor(cls):
        logger.info("RiskService 启动（多实例）")
        for bot in list_running_bots():
            cls.init_round(bot["id"])

        while True:
            try:
                cls.calc_direction_imbalance()

                # 1. 单机器人风控巡检
                for bot in list_running_bots():
                    try:
                        if PositionService.get_position_count(bot_id=bot["id"])["total"] == 0:
                            continue
                        cls.check_risk(bot["id"])
                    except Exception as e:
                        logger.error(f"[Risk] bot={bot['id']} 检查失败: {e}")
                        traceback.print_exc()

                # 2. ★ 新增：联合风控巡检
                try:
                    cls.check_combo_profit()
                except Exception as e:
                    logger.error(f"[Risk] 联合风控检查失败: {e}")

            except Exception as e:
                logger.error(f"风险监控错误: {e}")
                traceback.print_exc()

            time.sleep(15)