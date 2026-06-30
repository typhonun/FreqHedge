from fastapi import APIRouter, Body
from app.services.config_service import ConfigService

router = APIRouter()


@router.get("/")
def get_config():

    return ConfigService.get_config()


@router.post("/")
def save_config(
        data: dict = Body(...)
):

    return ConfigService.save_config(data)