from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parents[3]

class ConfigService:

    CONFIG_FILE = BASE_DIR / "config" / "runtime.json"

    @classmethod
    def get_config(cls):

        with open(cls.CONFIG_FILE, "r", encoding="utf8") as f:
            return json.load(f)

    @classmethod
    def save_config(cls, data):

        with open(cls.CONFIG_FILE, "w", encoding="utf8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        return {"success": True}