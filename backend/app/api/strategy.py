from fastapi import APIRouter

from app.services.strategy_service import (
    StrategyService
)

router = APIRouter()


@router.get("/")
def get_strategy():

    return StrategyService.get_config()


@router.post("/")
def save_strategy(data: dict):

    return StrategyService.save_config(
        data
    )