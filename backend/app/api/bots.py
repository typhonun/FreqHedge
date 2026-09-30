# backend/app/api/bots.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from app.services.bot_manager import BotManager
from app.services.position_service import PositionService   # ★ 新增
from app.services.config_service import ConfigService

router = APIRouter(tags=["bots"])       # ← 去掉 prefix


class BotBaseInfo(BaseModel):
    name: str
    pair: list[str]
    capital: float
    stakeAmount: float = 30
    leverage: int = 10
    dryRun: bool = True
    enableLong: bool
    enableShort: bool


class BotRiskConfig(BaseModel):
    tp_enabled: bool = False
    tp_mode: str = "amount"
    tp_amount: float = 0
    tp_ratio: float = 0

    sl_enabled: bool = False
    sl_mode: str = "amount"
    sl_amount: float = 0
    sl_ratio: float = 0

    trail_enabled: bool = False
    trail_mode: str = "ratio"
    trail_activate_amount: float = 0
    trail_activate_ratio: float = 0
    trail_drawdown_amount: float = 0
    trail_drawdown_ratio: float = 0

    auto_stop_on_tp: bool = True
    auto_stop_on_sl: bool = True
    auto_stop_on_trail: bool = True


class BotPayload(BaseModel):
    base: BotBaseInfo
    risk: Optional[BotRiskConfig] = None
    longConfig: Optional[dict] = None
    shortConfig: Optional[dict] = None


# =========================================================
# ★ 给单个 bot 补上收益字段（累计 / 多头 / 空头）
# =========================================================
def _attach_profit(bot: dict) -> dict:
    bot_id = bot.get("id")
    try:
        summary = PositionService.get_total_profit_summary(bot_id=bot_id)
        bot["total_profit"] = round(float(summary.get("total_profit", 0.0) or 0.0), 2)
        bot["long_profit"]  = round(float(summary.get("long_total_profit", 0.0) or 0.0), 2)
        bot["short_profit"] = round(float(summary.get("short_total_profit", 0.0) or 0.0), 2)
    except Exception as e:
        print(f"[bots] attach profit failed bot={bot_id}: {e}")
        bot["total_profit"] = 0.0
        bot["long_profit"]  = 0.0
        bot["short_profit"] = 0.0
    return bot


def _attach_profit_batch(bots: list[dict]) -> list[dict]:
    """并行给一批 bot 补收益，最多 8 个并发"""
    if not bots:
        return bots
    with ThreadPoolExecutor(max_workers=8) as executor:
        return list(executor.map(_attach_profit, bots))


# =========================================================
# 路由
# =========================================================

@router.get("")
async def list_bots():
    bots = BotManager.list_all()
    return _attach_profit_batch(bots)


@router.get("/{bot_id}")
async def get_bot(bot_id: int):
    bot = BotManager.get(bot_id)
    if not bot:
        raise HTTPException(404, "bot not found")
    return _attach_profit(bot)


@router.post("")
async def create_bot(payload: BotPayload):
    data = payload.model_dump()
    bot = BotManager.create(data)
    ConfigService.generate_configs(bot["id"], data)
    return _attach_profit(bot)


@router.put("/{bot_id}")
async def update_bot(bot_id: int, payload: BotPayload):
    data = payload.model_dump()
    bot = BotManager.update(bot_id, data)
    if not bot:
        raise HTTPException(404, "bot not found")
    ConfigService.generate_configs(bot_id, data)
    return _attach_profit(bot)


@router.delete("/{bot_id}")
async def delete_bot(bot_id: int):
    BotManager.stop(bot_id)
    ConfigService.remove_bot_dir(bot_id)
    BotManager.delete(bot_id)
    return {"success": True}


@router.post("/{bot_id}/start")
async def start_bot(bot_id: int):
    return BotManager.start(bot_id)


@router.post("/{bot_id}/stop")
async def stop_bot(bot_id: int):
    return BotManager.stop(bot_id)


@router.get("/{bot_id}/status")
async def bot_status(bot_id: int):
    return BotManager.status(bot_id)