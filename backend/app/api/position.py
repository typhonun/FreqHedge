from fastapi import APIRouter

from app.services.position_service import PositionService
from pydantic import BaseModel

router = APIRouter()


class PositionAction(BaseModel):
    trade_id: int

    side: str

    action: str

    amount: float | None = None

    price: float | None = None


@router.get("/open")
def open_positions():
    return PositionService.get_open_positions()


@router.get("/closed")
def closed_positions():
    return PositionService.get_closed_positions()


@router.get("/count")
def count():
    return PositionService.get_position_count()


@router.get("/summary")
def summary():
    return PositionService.get_account_summary()


@router.get("/profit")
def profit():
    return PositionService.get_profit_summary()


@router.get("/profit_all")
def profit_all():
    return PositionService.get_closed_profit_summary()


@router.get("/closed_profit")
def closed_profit():
    return PositionService.get_closed_profit_summary()


@router.get("/floating")
def floating():
    return PositionService.get_floating_profit()


@router.post("/action")
def position_action(
        data: PositionAction
):
    return PositionService.trade_action(

        trade_id=data.trade_id,

        side=data.side,

        action=data.action,

        amount=data.amount,

        price=data.price
    )
