from fastapi import APIRouter, Query
from typing import Optional
from app.services.log_service import LogService

router = APIRouter()


@router.get("/all/list")
def get_all(dry_run: bool | None = Query(None)):
    return {"data": LogService.all(dry_run=dry_run)}


@router.get("/{source}")
def get_logs(source: str, bot_id: Optional[int] = Query(None),
             dry_run: bool | None = Query(None)):
    return {"data": LogService.read(source, bot_id=bot_id, dry_run=dry_run)}