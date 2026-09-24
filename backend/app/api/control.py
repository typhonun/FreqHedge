from fastapi import APIRouter

from app.core import runtime
from app.services.freqtrade_service import FreqtradeService
from app.services.config_service import ConfigService
from pydantic import BaseModel
from app.services.position_service import PositionService
from app.services.risk_config_service import RiskConfigService
from app.services.event_service import record_event
from requests.exceptions import Timeout, ConnectionError
import requests
from datetime import datetime, timezone

from app.services.freqtrade_client import FreqtradeClient
from app.services.delete_service import DeleteService

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

    print("============================")
    print("DELETE TRADE API CALLED")

    print(
        "LONG PROCESS:",
        runtime.LONG_PROCESS
    )

    print(
        "SHORT PROCESS:",
        runtime.SHORT_PROCESS
    )

    result = DeleteService.delete_trade()


    print(
        "DELETE RESULT:",
        result
    )

    return result


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
def force_enter(data: ForceEnterRequest):
    try:
        result = PositionService.force_enter(
            side=data.side,
            pair=data.pair,
            stakeamount=data.stakeamount
        )
    except Timeout:
        return {
            "success": False,
            "rejected": False,
            "reason": "Freqtrade 响应超时，可能网络或交易所不可用",
            "message": "开仓超时，请检查网络后重试",
        }
    except ConnectionError:
        return {
            "success": False,
            "rejected": False,
            "reason": "无法连接 Freqtrade",
            "message": "Freqtrade 离线，请先启动机器人",
        }
    except requests.exceptions.HTTPError as e:
        err_msg = str(e)
        return {
            "success": False,
            "rejected": True,
            "reason": err_msg,
            "message": f"开仓被拒绝: {err_msg}",
        }
    except Exception as e:
        return {
            "success": False,
            "rejected": False,
            "reason": str(e),
            "message": f"开仓异常: {e}",
        }

    # ===== 成功，记录事件 =====
    try:
        strategy = (
            "DcaTpLong"
            if data.side == "long"
            else "DcaTpShort"
        )

        from config.settings import LONG_URL, SHORT_URL

        url = (
            LONG_URL
            if data.side == "long"
            else SHORT_URL
        )

        trade = None

        try:
            trades = FreqtradeClient.get_status(url)

            if isinstance(trades, dict):
                trades = trades.get("trades", []) or []
            elif not isinstance(trades, list):
                trades = []

            trade = next(
                (
                    t
                    for t in trades
                    if isinstance(t, dict) and t.get("pair") == data.pair
                ),
                None
            )
        except Exception as e:
            print(f"[force_enter] 查询 trade 失败: {e}")

        record_event(
            strategy=strategy,
            pair=data.pair,
            trade_id=trade.get("trade_id", 0) if trade else 0,
            event_type="manual_entry",
            side=data.side,
            price=trade.get("open_rate") if trade else None,
            amount=data.stakeamount,
            message="手动开仓",
            current_time=datetime.now(timezone.utc)
        )

    except Exception as e:
        print("manual entry event error:", e)

    return {
        "success": True,
        "rejected": False,
        "result": result,
    }


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
