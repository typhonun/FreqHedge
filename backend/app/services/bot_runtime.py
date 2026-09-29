# backend/app/services/bot_runtime.py
"""
多实例 bot 的运行时信息统一入口。

所有需要访问"某个 bot 的 API / DB / 日志"的地方，都通过这里取，
避免在多个文件里重复计算端口和路径。
"""
from pathlib import Path

from config.settings import FREQTRADE_DIR
from app.services.bot_manager import BotManager


def get_bot_or_raise(bot_id: int) -> dict:
    bot = BotManager.get(bot_id)
    if not bot:
        raise ValueError(f"bot {bot_id} not found")
    return bot


def get_bot_port(bot_id: int, side: str) -> int:
    """
    端口规则必须与 ConfigService._get_port 保持一致。
    long : 8011 + bot_id * 2
    short: 8011 + bot_id * 2 + 1
    """
    base_port = 8011 + bot_id * 2
    return base_port if side == "long" else base_port + 1


def get_bot_url(bot_id: int, side: str) -> str:
    return f"http://127.0.0.1:{get_bot_port(bot_id, side)}"


def get_bot_db_path(bot_id: int, side: str) -> Path:
    return (
        Path(FREQTRADE_DIR)
        / "user_data"
        / "bots"
        / str(bot_id)
        / f"tradesv3_{side}.sqlite"
    )


def get_bot_log_path(bot_id: int, side: str) -> Path:
    return (
        Path(FREQTRADE_DIR)
        / "user_data"
        / "bots"
        / str(bot_id)
        / "logs"
        / f"{side}.log"
    )


def get_enabled_sides(bot: dict) -> list[str]:
    sides = []
    if bot.get("enableLong"):
        sides.append("long")
    if bot.get("enableShort"):
        sides.append("short")
    return sides


def list_running_bots() -> list[dict]:
    """返回所有 status=running 的 bot"""
    return [b for b in BotManager.list_all() if b.get("status") == "running"]


def list_all_bots() -> list[dict]:
    return BotManager.list_all()