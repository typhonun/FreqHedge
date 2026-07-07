from fastapi import APIRouter
import json

from app.services.strategy_service import (
    StrategyService
)

router = APIRouter()


@router.get("/")
def get_strategy():

    return StrategyService.get_config()


@router.post("/")
def save_strategy(data: dict):

    print("\n========== 收到前端请求 ==========")
    print(data)
    print("=================================\n")

    return StrategyService.save_config(
        data
    )