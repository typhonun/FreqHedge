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
def save_strategy(data:dict):

    result = StrategyService.save_config(data)

    return {
        "success":True,
        "message":"strategy saved",
        "data":result
    }