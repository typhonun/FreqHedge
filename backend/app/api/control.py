from fastapi import APIRouter

from app.core import runtime
from app.services.freqtrade_service import FreqtradeService
from app.services.config_service import ConfigService
from pydantic import BaseModel
from app.services.position_service import PositionService
from app.services.risk_config_service import RiskConfigService
from app.services.event_service import record_event

from datetime import datetime, timezone

router = APIRouter()


class ForceEnterRequest(BaseModel):
    side: str

    pair: str

    stakeamount: float


class CloseAllRequest(BaseModel):
    side: str


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


@router.get("/stopentry")
def get_stopentry():
    return FreqtradeService.get_stop_entry_status()


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
    result = PositionService.force_enter(
        side=data.side,
        pair=data.pair,
        stakeamount=data.stakeamount
    )

    try:

        strategy = (
            "DcaTpLong"
            if data.side == "long"
            else
            "DcaTpShort"
        )

        from config.settings import (
            LONG_URL,
            SHORT_URL
        )

        url = (
            LONG_URL
            if data.side == "long"
            else SHORT_URL
        )

        trades = FreqtradeService.get_status(
            url
        )

        trade = next(
            (
                t
                for t in trades
                if t["pair"] == data.pair
            ),
            None
        )

        record_event(

            strategy=strategy,

            pair=data.pair,

            trade_id=
            trade["trade_id"]
            if trade else 0,

            event_type="manual_entry",

            side=data.side,

            price=
            trade["open_rate"]
            if trade else None,

            amount=data.stakeamount,

            message="手动开仓",

            current_time=datetime.now(
                timezone.utc
            )
        )


    except Exception as e:

        print(
            "manual entry event error:",
            e
        )

    return result


@router.post("/close_all")
def close_all(
        data: CloseAllRequest
):
    result = PositionService.close_all(
        data.side
    )

    try:

        record_event(

            strategy=
            "DcaTpLong"
            if data.side == "long"
            else
            "DcaTpShort",

            pair="ALL",

            trade_id=0,

            event_type="manual_exit",

            side=data.side,

            price=None,

            amount=0,

            message="手动全部平仓",

            current_time=datetime.now(
                timezone.utc
            )

        )


    except Exception as e:

        print(
            "close all event error:",
            e
        )

    return result


@router.get("/round-info")
def get_round_info():
    return runtime.ROUND_INFO


@router.get("/risk-config")
def get_risk_config():
    return runtime.GLOBAL_RISK


@router.post("/risk-config")
def save_risk_config(data: dict):
    runtime.GLOBAL_RISK.update(data)

    RiskConfigService.save(
        runtime.GLOBAL_RISK
    )

    return {
        "success": True
    }
