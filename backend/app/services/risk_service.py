import time

from app.core import runtime
from app.services.position_service import PositionService
from app.services.freqtrade_service import FreqtradeService


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

    @classmethod
    def force_exit_all(cls):

        positions = PositionService.get_all_positions()

        for pos in positions:

            try:

                PositionService.force_exit(
                    pos["trade_id"],
                    pos["side"]
                )

            except Exception as e:

                print(e)

    @classmethod
    def reset_round(cls):

        cls.init_round()

        print(
            "开始新一轮交易"
        )

    @classmethod
    def check_risk(cls):

        cls.calc_round_profit()

        risk = runtime.GLOBAL_RISK

        ratio = runtime.ROUND_INFO[
            "round_ratio"
        ]

        # TP

        if (
                risk["global_tp_enabled"]
                and
                ratio >= risk["global_tp_percent"]
        ):
            print(
                f"触发全局止盈 {ratio:.2f}%"
            )

            cls.force_exit_all()

            while True:

                positions = \
                    PositionService.get_all_positions()

                if len(positions) == 0:
                    break

                time.sleep(2)

            cls.reset_round()

            return

        # SL

        if (
                risk["global_sl_enabled"]
                and
                ratio <= risk["global_sl_percent"]
        ):
            print(
                f"触发全局止损 {ratio:.2f}%"
            )

            cls.force_exit_all()

            while True:

                positions = \
                    PositionService.get_all_positions()

                if len(positions) == 0:
                    break

                time.sleep(2)

            cls.reset_round()

    @classmethod
    def monitor(cls):

        print(
            "RiskService启动"
        )

        cls.init_round()

        while True:

            try:

                cls.check_risk()

            except Exception as e:

                print(
                    "风险监控错误:",
                    e
                )

            time.sleep(30)
