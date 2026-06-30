from fastapi import APIRouter

from app.services.bot_manager import BotManager

router = APIRouter()


@router.get("/status")
def status():

    return BotManager.get_all_status()


@router.get("/balance")
def balance():

    return BotManager.get_all_balance()


@router.post("/start")
def start():

    return BotManager.start_all()


@router.post("/stop")
def stop():

    return BotManager.stop_all()