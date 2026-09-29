from fastapi import APIRouter

from app.services.position_service import PositionService
from pydantic import BaseModel
from fastapi import Query

router = APIRouter()


class PositionAction(BaseModel):
    trade_id: int

    side: str

    action: str

    amount: float | None = None

    price: float | None = None

    bot_id: int | None = None


@router.get("/open")
def open_positions(bot_id: int | None = Query(None)):
    return PositionService.get_open_positions(bot_id=bot_id)


@router.get("/closed")
def closed_positions(bot_id: int | None = Query(None)):
    return PositionService.get_closed_positions(bot_id=bot_id)


@router.get("/count")
def count(bot_id: int | None = Query(None)):
    return PositionService.get_position_count(bot_id=bot_id)


@router.get("/summary")
def summary(bot_id: int | None = Query(None)):
    return PositionService.get_account_summary(bot_id=bot_id)


@router.get("/profit")
def profit(bot_id: int | None = Query(None)):
    return PositionService.get_profit_summary(bot_id=bot_id)


@router.get("/profit_all")
def profit_all(bot_id: int | None = Query(None)):
    return PositionService.get_closed_profit_summary(bot_id=bot_id)


@router.get("/closed_profit")
def closed_profit(bot_id: int | None = Query(None)):
    return PositionService.get_closed_profit_summary(bot_id=bot_id)


@router.get("/total_profit")
def total_profit(bot_id: int | None = Query(None)):
    return PositionService.get_total_profit_summary(bot_id=bot_id)


@router.get("/balance_curve")
def get_balance_curve(
    period: str = Query("1D"),
    bot_id: int | None = Query(None),
):
    return PositionService.get_balance_curve(period, bot_id=bot_id)


@router.get("/profit_curve")
def get_profit_curve(
    period: str = Query("1D"),
    bot_id: int | None = Query(None),
):
    return PositionService.get_profit_curve(period, bot_id=bot_id)


@router.get("/floating")
def floating(bot_id: int | None = Query(None)):
    return PositionService.get_floating_profit(bot_id=bot_id)


@router.post("/action")
def position_action(data: PositionAction):
    return PositionService.trade_action(
        trade_id=data.trade_id,
        side=data.side,
        action=data.action,
        amount=data.amount,
        price=data.price,
        bot_id=data.bot_id,
    )
