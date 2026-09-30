# backend/app/api/exchange.py
from fastapi import APIRouter, Query
from app.services.exchange_service import ExchangeService

router = APIRouter(tags=["exchange"])


@router.get("/pairs")
def get_pairs(
    exchange: str = Query("binance"),
    market: str = Query("futures"),
):
    if exchange == "binance" and market == "futures":
        return ExchangeService.get_binance_usdt_futures_pairs()
    return []