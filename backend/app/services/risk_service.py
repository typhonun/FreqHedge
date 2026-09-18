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

        print(
            f"新一轮开始 "
            f"start_profit={runtime.ROUND_INFO['start_profit']}, "
            f"start_long_closed={runtime.ROUND_INFO['start_long_closed']}, "
            f"start_short_closed={runtime.ROUND_INFO['start_short_closed']}, "
            f"start_balance={runtime.ROUND_INFO['start_balance']}"
            f"累计止盈次数={runtime.ROUND_INFO.get('global_tp_count', 0)}, "
            f"累计止损次数={runtime.ROUND_INFO.get('global_sl_count', 0)}"
        )

    @classmethod
    def calc_round_profit(cls):

        # ---------- 取值，全部兜底 ----------
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

        # ---------- 本轮基准 ----------
        start_long_closed = runtime.ROUND_INFO.get("start_long_closed") or 0.0
        start_short_closed = runtime.ROUND_INFO.get("start_short_closed") or 0.0
        start_balance = runtime.ROUND_INFO.get("start_balance") or 0.0

        # ---------- 本轮多单已平仓 ----------
        long_closed_round = (
                closed["long_closed_profit"] - start_long_closed
        )
        short_closed_round = (
                closed["short_closed_profit"] - start_short_closed
        )

        # ---------- 本轮多单收益 = 多单本轮已平仓 + 多单浮盈 ----------
        long_round = long_closed_round + floating["long_float"]
        short_round = short_closed_round + floating["short_float"]

        # ---------- 本轮总收益 ----------
        round_profit = long_round + short_round

        # ---------- 本轮收益率 ----------
        if start_balance:
            round_ratio = round_profit / start_balance * 100
        else:
            round_ratio = 0.0

        # ---------- 写回 ROUND_INFO ----------
        runtime.ROUND_INFO["round_profit"] = round_profit
        runtime.ROUND_INFO["round_ratio"] = round(round_ratio, 2)

        # ---------- 日志 ----------
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
    def force_exit_all(cls):
        snapshot_cache["time"] = 0
        positions = PositionService.get_all_positions()
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
            snapshot_cache["time"] = 0  # 强制刷新
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

        # 冷却：止盈/止损触发后 60 秒内不再检查
        last_tp = runtime.ROUND_INFO.get("last_tp_time", 0) or 0
        if time.time() - last_tp < 60:
            return

        cls.calc_round_profit()

        risk = runtime.GLOBAL_RISK
        profit = runtime.ROUND_INFO.get("round_profit", 0.0) or 0.0

        print(
            f"[Risk] check "
            f"profit={profit}, "
            f"tp_enabled={risk['global_tp_enabled']}, "
            f"tp_amount={risk['global_tp_amount']}, "
            f"last_tp={runtime.ROUND_INFO.get('last_tp_time')}"
        )

        if risk["global_tp_enabled"] and profit >= risk["global_tp_amount"]:
            print(f"触发全局止盈 {profit:.2f} USDT")
            runtime.ROUND_INFO["last_tp_time"] = time.time()

            runtime.ROUND_INFO["global_tp_count"] = (
                    runtime.ROUND_INFO.get("global_tp_count", 0) + 1
            )

            cls.force_exit_all()
            cls.wait_positions_closed(timeout=60)
            cls.reset_round()
            return

        if risk["global_sl_enabled"] and profit <= -risk["global_sl_amount"]:
            print(f"触发全局止损 {profit:.2f} USDT")
            runtime.ROUND_INFO["last_tp_time"] = time.time()

            runtime.ROUND_INFO["global_sl_count"] = (
                    runtime.ROUND_INFO.get("global_sl_count", 0) + 1
            )

            cls.force_exit_all()
            cls.wait_positions_closed(timeout=60)
            cls.reset_round()
            return

    @classmethod
    def monitor(cls):
        print("RiskService启动")
        cls.init_round()
        while True:
            try:
                risk = runtime.GLOBAL_RISK
                print(
                    f"[Risk] profit={runtime.ROUND_INFO.get('round_profit')}, "
                    f"tp={risk.get('global_tp_enabled')}/{risk.get('global_tp_amount')}, "
                    f"sl={risk.get('global_sl_enabled')}/{risk.get('global_sl_amount')}"
                )
                cls.check_risk()
            except Exception as e:
                print("风险监控错误:", e)
                print(traceback.format_exc())
            time.sleep(5)