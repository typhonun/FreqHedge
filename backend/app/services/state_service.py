import json

from pathlib import Path
from app.core import runtime
from config.settings import FREQTRADE_DIR


class StateService:

    STATE_FILE = (
        Path(FREQTRADE_DIR).parent
        / "backend_state.json"
    )

    @classmethod
    def load(cls):

        if not cls.STATE_FILE.exists():
            return {
                "long": runtime.RUNNING["long"],
                "short": runtime.RUNNING["short"]
            }

        with open(
            cls.STATE_FILE,
            "r",
            encoding="utf8"
        ) as f:

            return json.load(f)

    @classmethod
    def save(
        cls,
        long_state,
        short_state
    ):

        state = {
            "long": long_state,
            "short": short_state
        }

        with open(
            cls.STATE_FILE,
            "w",
            encoding="utf8"
        ) as f:

            json.dump(
                state,
                f,
                indent=4,
                ensure_ascii=False
            )

        runtime.RUNNING["long"] = long_state
        runtime.RUNNING["short"] = short_state

        return state