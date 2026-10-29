from fastapi import APIRouter

from app.services.position_service import PositionService
from pydantic import BaseModel
from fastapi import Query

router = APIRouter()


class PositionAction(BaseModel):
    trade_id: int
    side: str
    action: str
    amount_usdt: float | None = None
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
        amount_usdt=data.amount_usdt,
        price=data.price,
        bot_id=data.bot_id,
    )


@router.get("/action_limits")
def action_limits(
    bot_id: int = Query(...),
    side: str = Query(...),
    pair: str = Query(...),
):
    return PositionService.get_action_limits(bot_id=bot_id, side=side, pair=pair)


# =========================================================
# 新增：手动开仓 / 全部平仓 / 可交易对
# =========================================================

class ForceEnterAction(BaseModel):
    bot_id: int
    side: str
    pair: str
    amount_usdt: float


class CloseAllAction(BaseModel):
    bot_id: int
    side: str            # "long" / "short"


@router.get("/available_pairs")
def get_available_pairs(
    side: str = Query(...),
    bot_id: int = Query(...),
):
    """获取该 bot 指定方向下、未被占用的可交易对"""
    return PositionService.get_available_pairs(side=side, bot_id=bot_id)


@router.post("/force_enter")
def force_enter(data: ForceEnterAction):
    """立即开仓（不传杠杆，Freqtrade 自动沿用 bot 配置）"""
    return PositionService.force_enter(
        side=data.side,
        pair=data.pair,
        amount_usdt=data.amount_usdt,
        bot_id=data.bot_id,
    )


@router.post("/close_all")
def close_all(data: CloseAllAction):
    """平掉该 bot 指定方向的所有持仓"""
    return PositionService.close_all(side=data.side, bot_id=data.bot_id)