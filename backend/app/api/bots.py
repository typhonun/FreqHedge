# backend/app/api/bots.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.bot_manager import BotManager
from app.services.config_service import ConfigService

router = APIRouter(tags=["bots"])       # ← 去掉 prefix


class BotBaseInfo(BaseModel):
    
    name: str
    pair: list[str]              # ← 从 str 改为 list
    capital: float
    stakeAmount: float = 30
    leverage: int = 10
    dryRun: bool = True
    enableLong: bool
    enableShort: bool


class BotPayload(BaseModel):
    base: BotBaseInfo
    longConfig: Optional[dict] = None
    shortConfig: Optional[dict] = None


@router.get("")
async def list_bots():
    return BotManager.list_all()


@router.get("/{bot_id}")
async def get_bot(bot_id: int):
    bot = BotManager.get(bot_id)
    if not bot:
        raise HTTPException(404, "bot not found")
    return bot


@router.post("")
async def create_bot(payload: BotPayload):
    data = payload.model_dump()
    bot = BotManager.create(data)
    ConfigService.generate_configs(bot["id"], data)
    return bot


@router.put("/{bot_id}")
async def update_bot(bot_id: int, payload: BotPayload):
    data = payload.model_dump()
    bot = BotManager.update(bot_id, data)
    if not bot:
        raise HTTPException(404, "bot not found")
    ConfigService.generate_configs(bot_id, data)
    return bot


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