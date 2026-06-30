from fastapi import APIRouter

from app.services.process_service import ProcessService

router = APIRouter()


@router.post("/docker/start")
def start():

    return ProcessService.start_all()


@router.post("/docker/stop")
def stop():

    return ProcessService.stop_all()


@router.post("/docker/restart")
def restart():

    return ProcessService.restart_all()