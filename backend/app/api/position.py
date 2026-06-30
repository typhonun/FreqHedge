from fastapi import APIRouter

from app.services.position_service import PositionService

router = APIRouter()


@router.get("/open")
def open_positions():
    return PositionService.get_open_positions()


@router.get("/count")
def count():
    return PositionService.get_position_count()


@router.get("/summary")
def summary():
    return PositionService.get_account_summary()


@router.get("/profit")
def profit():
    return PositionService.get_profit_summary()

@router.get("/floating")
def floating():

    return PositionService.get_floating_profit()
