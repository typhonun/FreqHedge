import time
import traceback

from app.core import runtime
from app.services.position_service import PositionService
from app.services.freqtrade_service import FreqtradeService
from app.services.position_service import snapshot_cache


class RiskService:

    @classmethod
    def init_round(cls):

        closed = PositionService.get_closed_profit_summary()

        runtime.ROUND_INFO["start_profit"] = closed["total_closed_profit"] or 0.0
        runtime.ROUND_INFO["start_long_closed"] = closed["long_closed_profit"] or 0.0
        runtime.ROUND_INFO["start_short_closed"] = closed["short_closed_profit"] or 0.0

        start_balance = PositionService.get_account_summary().get("total_balance")
        runtime.ROUND_INFO["start_balance"] = start_balance or 0.0

        runtime.ROUND_INFO["round_profit"] = 0.0
        runtime.ROUND_INFO["round_ratio"] = 0.0
        runtime.ROUND_INFO["last_tp_time"] = 0.0

        runtime.ROUND_INFO["peak_profit"] = 0.0
        runtime.ROUND_INFO["peak_ratio"] = 0.0
        runtime.ROUND_INFO["trough_profit"] = 0.0
        runtime.ROUND_INFO["trough_ratio"] = 0.0
        runtime.ROUND_INFO["trail_active"] = False

        print(
            f"新一轮开始 "
            f"start_profit={runtime.ROUND_INFO['start_profit']}, "
            f"start_long_closed={runtime.ROUND_INFO['start_long_closed']}, "
            f"start_short_closed={runtime.ROUND_INFO['start_short_closed']}, "
            f"start_balance={runtime.ROUND_INFO['start_balance']}, "
            f"累计止盈次数={runtime.ROUND_INFO.get('global_tp_count', 0)}, "
            f"累计止损次数={runtime.ROUND_INFO.get('global_sl_count', 0)}"
        )

    @classmethod
    def calc_round_profit(cls):

        try:
            closed = PositionService.get_closed_profit_summary()
        except Exception as e:
            print(f"[Risk] get_closed_profit_summary 失败: {e}")
            closed = {
                "long_closed_profit": 0.0,
                "short_closed_profit": 0.0,
                "total_closed_profit": 0.0
            }

        try:
            floating = PositionService.get_floating_profit()
        except Exception as e:
            print(f"[Risk] get_floating_profit 失败: {e}")
            floating = {
                "long_float": 0.0,
                "short_float": 0.0,
                "total_float": 0.0
            }

        start_long_closed = runtime.ROUND_INFO.get("start_long_closed") or 0.0
        start_short_closed = runtime.ROUND_INFO.get("start_short_closed") or 0.0
        start_balance = runtime.ROUND_INFO.get("start_balance") or 0.0

        long_closed_round = closed["long_closed_profit"] - start_long_closed
        short_closed_round = closed["short_closed_profit"] - start_short_closed

        long_round = long_closed_round + floating["long_float"]
        short_round = short_closed_round + floating["short_float"]

        round_profit = long_round + short_round

        if start_balance:
            round_ratio = round_profit / start_balance * 100
        else:
            round_ratio = 0.0

        runtime.ROUND_INFO["round_profit"] = round_profit
        runtime.ROUND_INFO["round_ratio"] = round(round_ratio, 2)

        # 更新峰值 / 谷值（用于追踪止损）
        if round_profit > runtime.ROUND_INFO.get("peak_profit", 0.0):
            runtime.ROUND_INFO["peak_profit"] = round_profit

        if round_ratio > runtime.ROUND_INFO.get("peak_ratio", 0.0):
            runtime.ROUND_INFO["peak_ratio"] = round_ratio

        if round_profit < runtime.ROUND_INFO.get("trough_profit", 0.0):
            runtime.ROUND_INFO["trough_profit"] = round_profit

        if round_ratio < runtime.ROUND_INFO.get("trough_ratio", 0.0):
            runtime.ROUND_INFO["trough_ratio"] = round_ratio

        print(
            f"[Risk] calc "
            f"多单本轮已平仓={long_closed_round:.2f}, "
            f"多单浮盈={floating['long_float']:.2f}, "
            f"多单收益={long_round:.2f}, "
            f"空单本轮已平仓={short_closed_round:.2f}, "
            f"空单浮盈={floating['short_float']:.2f}, "
            f"空单收益={short_round:.2f}, "
            f"本轮总收益={round_profit:.2f}, "
            f"全局止盈次数={runtime.ROUND_INFO['global_tp_count']}, "
            f"全局止损次数={runtime.ROUND_INFO['global_sl_count']}, "
            f"收益率={round_ratio:.2f}%"
        )

    @classmethod
    def force_exit_all(cls, reason: str = None):
        """全部平仓

        reason: 可选，全局平仓原因
        """

        snapshot_cache["time"] = 0
        positions = PositionService.get_all_positions()

        # 如果传了 reason，记录一下
        if reason:
            for pos in positions:
                trade_id = pos.get("trade_id")
                if trade_id is not None:
                    runtime.GLOBAL_EXIT_REASONS[trade_id] = reason

            # 限制大小
            if len(runtime.GLOBAL_EXIT_REASONS) > 1000:
                keys = list(runtime.GLOBAL_EXIT_REASONS.keys())
                for k in keys[:len(keys) - 1000]:
                    del runtime.GLOBAL_EXIT_REASONS[k]

        for pos in positions:
            for attempt in range(3):
                try:
                    PositionService.force_exit(pos["trade_id"], pos["side"])
                    break
                except Exception as e:
                    print(
                        f"force_exit 失败 "
                        f"trade_id={pos.get('trade_id')} "
                        f"pair={pos.get('pair')} "
                        f"attempt={attempt + 1} "
                        f"error={e}"
                    )
                    time.sleep(1)

    @classmethod
    def wait_positions_closed(cls, timeout=60):
        start = time.time()
        while time.time() - start < timeout:
            snapshot_cache["time"] = 0
            positions = PositionService.get_all_positions()
            if len(positions) == 0:
                return True
            time.sleep(2)
        return False

    @classmethod
    def reset_round(cls):
        cls.init_round()
        print("开始新一轮交易")

    @classmethod
    def check_risk(cls):

        last_tp = runtime.ROUND_INFO.get("last_tp_time", 0) or 0
        if time.time() - last_tp < 60:
            return

        cls.calc_round_profit()

        # 无持仓不判断，避免 0 收益误触发
        position_count = PositionService.get_position_count()
        if position_count["total"] == 0:
            return

        risk = runtime.GLOBAL_RISK
        profit = runtime.ROUND_INFO.get("round_profit", 0.0) or 0.0
        ratio = runtime.ROUND_INFO.get("round_ratio", 0.0) or 0.0

        # ---------- 止盈 ----------
        if risk["global_tp_enabled"]:

            tp_mode = risk.get("global_tp_mode", "amount")

            if tp_mode == "ratio":
                tp_ratio = float(risk.get("global_tp_ratio", 0.0) or 0.0)
                # 阈值必须 > 0 才判断
                if tp_ratio > 0 and ratio >= tp_ratio:
                    tp_hit = True
                    tp_desc = f"{ratio:.2f}% >= {tp_ratio}%"
                else:
                    tp_hit = False
                    tp_desc = ""
            else:
                tp_amount = float(risk.get("global_tp_amount", 0.0) or 0.0)
                if tp_amount > 0 and profit >= tp_amount:
                    tp_hit = True
                    tp_desc = f"{profit:.2f} >= {tp_amount} USDT"
                else:
                    tp_hit = False
                    tp_desc = ""

            if tp_hit:
                print(f"触发全局止盈 {tp_desc}")
                runtime.ROUND_INFO["last_tp_time"] = time.time()

                runtime.ROUND_INFO["global_tp_count"] = (
                        runtime.ROUND_INFO.get("global_tp_count", 0) + 1
                )

                cls.record_global_exit_events("global_tp", "全局止盈")

                cls.force_exit_all(reason="全局止盈")
                cls.wait_positions_closed(timeout=60)
                cls.reset_round()
                return

        # ---------- 止损 ----------
        if risk["global_sl_enabled"]:

            sl_mode = risk.get("global_sl_mode", "amount")

            if sl_mode == "ratio":
                sl_ratio = float(risk.get("global_sl_ratio", 0.0) or 0.0)
                # 阈值必须 > 0 才判断
                if sl_ratio > 0 and ratio <= -sl_ratio:
                    sl_hit = True
                    sl_desc = f"{ratio:.2f}% <= -{sl_ratio}%"
                else:
                    sl_hit = False
                    sl_desc = ""
            else:
                sl_amount = float(risk.get("global_sl_amount", 0.0) or 0.0)
                if sl_amount > 0 and profit <= -sl_amount:
                    sl_hit = True
                    sl_desc = f"{profit:.2f} <= -{sl_amount} USDT"
                else:
                    sl_hit = False
                    sl_desc = ""

            if sl_hit:
                print(f"触发全局止损 {sl_desc}")
                runtime.ROUND_INFO["last_tp_time"] = time.time()

                runtime.ROUND_INFO["global_sl_count"] = (
                        runtime.ROUND_INFO.get("global_sl_count", 0) + 1
                )

                cls.record_global_exit_events("global_sl", "全局止损")

                cls.force_exit_all(reason="全局止损")
                cls.wait_positions_closed(timeout=60)
                cls.reset_round()
                return

        # ---------- 追踪止损 ----------
        if risk.get("global_trail_enabled"):

            trail_mode = risk.get("global_trail_mode", "ratio")

            if trail_mode == "ratio":
                activate = float(risk.get("global_trail_activate_ratio", 0.0) or 0.0)
                drawdown = float(risk.get("global_trail_drawdown_ratio", 0.0) or 0.0)
                current = ratio
                peak = runtime.ROUND_INFO.get("peak_ratio", 0.0)
                trough = runtime.ROUND_INFO.get("trough_ratio", 0.0)
            else:
                activate = float(risk.get("global_trail_activate_amount", 0.0) or 0.0)
                drawdown = float(risk.get("global_trail_drawdown_amount", 0.0) or 0.0)
                current = profit
                peak = runtime.ROUND_INFO.get("peak_profit", 0.0)
                trough = runtime.ROUND_INFO.get("trough_profit", 0.0)

            # 参数合法性：回撤必须 > 0
            if drawdown > 0 and activate != 0:

                # 激活判断
                if not runtime.ROUND_INFO.get("trail_active"):
                    if activate > 0 and peak >= activate:
                        runtime.ROUND_INFO["trail_active"] = True
                        runtime.ROUND_INFO["trail_direction"] = "profit"

                        # 启用起算：把 peak 重置为当前值
                        runtime.ROUND_INFO["peak_profit"] = profit
                        runtime.ROUND_INFO["peak_ratio"] = ratio

                        print(
                            f"[Risk] 追踪止盈已激活 "
                            f"peak={profit:.2f}/{ratio:.2f}（启用起算）"
                        )

                    elif activate < 0 and trough <= activate:
                        runtime.ROUND_INFO["trail_active"] = True
                        runtime.ROUND_INFO["trail_direction"] = "loss"

                        # 启用起算：把 trough 重置为当前值
                        runtime.ROUND_INFO["trough_profit"] = profit
                        runtime.ROUND_INFO["trough_ratio"] = ratio

                        print(
                            f"[Risk] 追踪止损已激活 "
                            f"trough={profit:.2f}/{ratio:.2f}（启用起算）"
                        )

                # 触发判断
                if runtime.ROUND_INFO.get("trail_active"):

                    direction = runtime.ROUND_INFO.get("trail_direction", "profit")

                    if direction == "profit":
                        # 盈利区：从峰值回撤
                        trigger_line = peak - drawdown
                        hit = current <= trigger_line
                        desc = f"{current:.2f} <= {trigger_line:.2f} (peak={peak:.2f}, dd={drawdown})"
                    else:
                        # 亏损区：从谷值反弹
                        trigger_line = trough + drawdown
                        hit = current >= trigger_line
                        desc = f"{current:.2f} >= {trigger_line:.2f} (trough={trough:.2f}, dd={drawdown})"

                    if hit:
                        print(f"触发追踪止损 [{direction}] {desc}")
                        runtime.ROUND_INFO["last_tp_time"] = time.time()

                        runtime.ROUND_INFO["global_trail_count"] = (
                                runtime.ROUND_INFO.get("global_trail_count", 0) + 1
                        )

                        cls.record_global_exit_events("global_trail", "追踪止损")

                        cls.force_exit_all(reason="追踪止损")
                        cls.wait_positions_closed(timeout=60)
                        cls.reset_round()
                        return

    @classmethod
    def record_global_exit_events(cls, event_type: str, message: str):
        """记录全局平仓事件到图表"""

        import sys
        from pathlib import Path
        from datetime import datetime

        EVENT_LOGGER_DIR = (
                Path(__file__).resolve().parents[3]
                / "freqtrade"
                / "user_data"
                / "strategies"
        )

        if str(EVENT_LOGGER_DIR) not in sys.path:
            sys.path.insert(0, str(EVENT_LOGGER_DIR))

        try:
            from event_logger import record_event
        except Exception as e:
            print(f"[Risk] event_logger 导入失败，跳过事件记录: {e}")
            return

        positions = PositionService.get_all_positions()

        current_time = datetime.utcnow()

        for pos in positions:

            trade_id = pos.get("trade_id")
            pair = pos.get("pair")
            price = pos.get("current_rate") or pos.get("close_rate") or 0
            amount = pos.get("amount") or 0
            side = pos.get("side", "long").lower()

            if trade_id is None or not pair:
                continue

            # 根据 side 判断策略名
            strategy_name = "DcaTpShort" if side == "short" else "DcaTpLong"

            try:
                record_event(
                    strategy=strategy_name,
                    pair=pair,
                    trade_id=trade_id,
                    event_type=event_type,
                    side=side,
                    price=float(price),
                    amount=float(amount),
                    message=message,
                    current_time=current_time
                )
            except Exception as e:
                print(f"[Risk] record_event 失败: {e}")

    @classmethod
    def monitor(cls):
        print("RiskService启动")
        cls.init_round()
        while True:
            try:
                risk = runtime.GLOBAL_RISK
                print(
                    f"[Risk] profit={runtime.ROUND_INFO.get('round_profit')}, "
                    f"ratio={runtime.ROUND_INFO.get('round_ratio')}, "
                    f"tp={risk.get('global_tp_enabled')}"
                    f"/{risk.get('global_tp_mode')}"
                    f"/{risk.get('global_tp_amount')}"
                    f"/{risk.get('global_tp_ratio')}, "
                    f"sl={risk.get('global_sl_enabled')}"
                    f"/{risk.get('global_sl_mode')}"
                    f"/{risk.get('global_sl_amount')}"
                    f"/{risk.get('global_sl_ratio')}"
                    f", trail={risk.get('global_trail_enabled')}"
                    f"/{risk.get('global_trail_mode')}"
                    f"/{risk.get('global_trail_activate_amount')}"
                    f"/{risk.get('global_trail_activate_ratio')}"
                    f"/{risk.get('global_trail_drawdown_amount')}"
                    f"/{risk.get('global_trail_drawdown_ratio')}"
                    f", peak={runtime.ROUND_INFO.get('peak_profit'):.2f}"
                    f"/{runtime.ROUND_INFO.get('peak_ratio'):.2f}"
                    f", trough={runtime.ROUND_INFO.get('trough_profit'):.2f}"
                    f"/{runtime.ROUND_INFO.get('trough_ratio'):.2f}"
                    f", active={runtime.ROUND_INFO.get('trail_active')}"
                )
                cls.check_risk()
            except Exception as e:
                print("风险监控错误:", e)
                print(traceback.format_exc())
            time.sleep(5)