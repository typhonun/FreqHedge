from fastapi import APIRouter
from app.core import runtime
from app.services.position_service import PositionService

router = APIRouter()


@router.get("/direction")
def get_direction_state():
    return {
        "long_count": runtime.ROUND_INFO.get("long_count", 0),
        "short_count": runtime.ROUND_INFO.get("short_count", 0),
        "direction_diff": runtime.ROUND_INFO.get("direction_diff", 0),
        "block_long": runtime.ROUND_INFO.get("block_long", False),
        "block_short": runtime.ROUND_INFO.get("block_short", False),
        "imbalance_long_enable": bool(runtime.GLOBAL_RISK.get("imbalance_long_enable", False)),
        "imbalance_short_enable": bool(runtime.GLOBAL_RISK.get("imbalance_short_enable", False)),
    }