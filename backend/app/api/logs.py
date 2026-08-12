from fastapi import APIRouter

from app.services.log_service import LogService

router = APIRouter()


@router.get("/all/list")
def get_all():
    return {
        "data":
            LogService.all()
    }


@router.get("/{source}")
def get_logs(source: str):
    return {

        "data":
            LogService.read(source)

    }
