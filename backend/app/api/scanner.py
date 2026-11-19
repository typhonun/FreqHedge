# backend/app/api/scanner.py
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.grid_scanner import GridScanner
import asyncio
import time

router = APIRouter()
scanner = GridScanner()

class BotBoundsRequest(BaseModel):
    bot_id: int
    side: str = "long"
    days: int = 30
    pairs: Optional[list] = None
    persist: bool = True

@router.get("/grid")
async def scan_grid_pairs(
    long_count: int = Query(3, ge=0, le=10),
    short_count: int = Query(0, ge=0, le=10)
):
    # 放到线程池执行，防止阻塞 FastAPI 主事件循环
    result = await asyncio.to_thread(scanner.scan, long_count, short_count)
    return result


@router.post("/range/bot")
async def get_bot_range(req: BotBoundsRequest):
    if req.days not in (7, 30, 90):
        raise HTTPException(400, "days 只支持 7 / 30 / 90")

    pairs = req.pairs
    if not pairs:
        try:
            from app.services.bot_manager import BotManager
            bot = BotManager.get(req.bot_id) or {}
            pairs = bot.get("pair") or []
        except Exception:
            pairs = []

    if not pairs:
        raise HTTPException(400, "白名单为空")

    results = await asyncio.to_thread(scanner.get_all_ranges, pairs, req.days)

    if req.persist:
        try:
            from app.core.config_manager import ConfigManager
            key = f"grid_prefetch_range_{req.bot_id}_{req.side}"
            # ★ 按 pair 逐个写入或者写个整体字典，这里写整体
            ConfigManager.set_bot_kv(key, {
                "days": req.days,
                "generated_at": time.time(),
                "pairs": results
            })
        except Exception:
            pass

    return {"success": True, "results": results}
