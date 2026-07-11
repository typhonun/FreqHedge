import json
import os

from app.core import runtime

CONFIG_FILE = "config/risk_config.json"


class RiskConfigService:

    @staticmethod
    def load():

        if not os.path.exists(CONFIG_FILE):
            RiskConfigService.save(
                runtime.GLOBAL_RISK
            )

            return

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        runtime.GLOBAL_RISK.update(data)

    @staticmethod
    def save(data):

        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )