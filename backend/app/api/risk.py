from fastapi import APIRouter
from app.core import runtime
from app.services.position_service import PositionService

router = APIRouter()


@router.get("/direction")
def get_direction_state():
    """只返回多空持仓数（阈值由策略侧自己判断）"""

    return {
        "long_count": runtime.ROUND_INFO.get("long_count", 0),
        "short_count": runtime.ROUND_INFO.get("short_count", 0),
    }