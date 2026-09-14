import time

from app.core import runtime
from app.services.position_service import PositionService
from app.services.freqtrade_service import FreqtradeService
from app.services.position_service import snapshot_cache


class RiskService:

    @classmethod
    def init_round(cls):

        runtime.ROUND_INFO["start_profit"] = \
            PositionService.get_closed_profit()

        runtime.ROUND_INFO["start_balance"] = \
            PositionService.get_account_summary()[
                "total_balance"
            ]

        runtime.ROUND_INFO["round_profit"] = 0

        runtime.ROUND_INFO["round_ratio"] = 0

        print(
            f"新一轮开始 "
            f"start_profit="
            f"{runtime.ROUND_INFO['start_profit']}, "
            f"start_balance="
            f"{runtime.ROUND_INFO['start_balance']}"
        )

    @classmethod
    def calc_round_profit(cls):

        current_profit = \
            PositionService.get_closed_profit()

        floating_profit = \
            PositionService.get_floating_profit()[
                "total_float"
            ]

        start_profit = \
            runtime.ROUND_INFO["start_profit"]

        start_balance = \
            runtime.ROUND_INFO["start_balance"]

        if start_profit is None:
            cls.init_round()

            return

        round_profit = (

                current_profit
                - start_profit

                + floating_profit

        )

        if not start_balance:
            runtime.ROUND_INFO[
                "round_ratio"
            ] = 0

            return

        round_ratio = (

                              round_profit
                              / start_balance

                      ) * 100

        runtime.ROUND_INFO[
            "round_profit"
        ] = round_profit

        runtime.ROUND_INFO[
            "round_ratio"
        ] = round(
            round_ratio,
            2
        )

        print(
            f"[Risk] calc "
            f"当前已平仓累计利润={current_profit}, "
            f"本轮开始时已平仓累计利润={start_profit}, "
            f"当前浮动利润={floating_profit}, "
            f"本轮新增利润={round_profit if 'round_profit' in dir() else None}"
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

        print(
            "开始新一轮交易"
        )

    @classmethod
    def check_risk(cls):

        # 冷却：止盈/止损触发后 60 秒内不再检查
        last_tp = runtime.ROUND_INFO.get("last_tp_time", 0)
        if time.time() - last_tp < 60:
            return

        cls.calc_round_profit()

        risk = runtime.GLOBAL_RISK
        profit = runtime.ROUND_INFO["round_profit"]

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

            cls.force_exit_all()
            cls.wait_positions_closed(timeout=60)
            cls.reset_round()
            return

        if risk["global_sl_enabled"] and profit <= -risk["global_sl_amount"]:
            print(f"触发全局止损 {profit:.2f} USDT")
            runtime.ROUND_INFO["last_tp_time"] = time.time()

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
                import traceback
                print("风险监控错误:", e)
                print(traceback.format_exc())
            time.sleep(5)
