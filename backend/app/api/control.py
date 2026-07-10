from fastapi import APIRouter

from app.services.freqtrade_service import FreqtradeService
from app.services.config_service import ConfigService
from pydantic import BaseModel
from app.services.position_service import PositionService

router = APIRouter()


class ForceEnterRequest(BaseModel):
    side: str

    pair: str

    stakeamount: float


@router.post("/start")
def start_bot(data: dict):
    return FreqtradeService.start_bot_service(data)


@router.post("/stop")
def stop_bot(data: dict):
    return FreqtradeService.stop_bot_service(data)


@router.get("/status")
def status():
    return FreqtradeService.get_status_service()


@router.post("/reload")
def reload():
    return FreqtradeService.reload_service()


@router.post("/stopentry")
def stopentry(data: dict):
    return FreqtradeService.stop_entry(data)


@router.post("/delete_trade")
def delete_trade():
    return FreqtradeService.delete_trade()


@router.get("/config")
def get_config():
    return ConfigService.get_config()


@router.post("/config")
def save_config(data: dict):
    return ConfigService.save_config(data)


@router.get("/available_pairs/{side}")
def available_pairs(side: str):
    return PositionService.get_available_pairs(
        side
    )


@router.post("/force_enter")
def force_enter(
        data: ForceEnterRequest
):
    return PositionService.force_enter(

        side=data.side,

        pair=data.pair,

        stakeamount=data.stakeamount
    )
