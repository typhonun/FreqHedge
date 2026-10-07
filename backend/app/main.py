# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from threading import Thread
import threading

from contextlib import asynccontextmanager
from app.models import user as _user_model  # noqa 确保建表
from app.api import auth
from app.models import user as _user_model
from app.api.chart import cache_refresh_loop
from app.services.risk_service import RiskService
from app.services.risk_config_service import RiskConfigService
from app.api.risk import router as risk_router
from app.api.position import router as position_router
from app.api.chart import router as chart_router
from app.api import exchange
from app.api import logs
from app.api import bots, backtest
from app.services.health_monitor import (
    start_health_monitor,
    stop_health_monitor,
)
from app.database import Base, engine

from app.scheduler.equity_scheduler import (
    start_scheduler,
    stop_scheduler
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    Base.metadata.create_all(bind=engine)
    print("Database tables initialized.")

    RiskConfigService.load()

    start_scheduler()

    threading.Thread(
        target=RiskService.monitor,
        daemon=True
    ).start()

    Thread(
        target=cache_refresh_loop,
        daemon=True
    ).start()

    start_health_monitor()

    print("Application started.")

    yield

    stop_health_monitor()
    stop_scheduler()

    print("Application stopped.")


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return "ok"


# =========================================================
# Routers —— 保留的
# =========================================================

app.include_router(position_router, prefix="/position", tags=["position"])
app.include_router(chart_router,    prefix="/chart", tags=["chart"])
app.include_router(bots.router,     prefix="/bots", tags=["bots"])
app.include_router(backtest.router, prefix="/bots", tags=["backtest"])
app.include_router(risk_router,     prefix="/api/risk", tags=["risk"])
app.include_router(logs.router,     prefix="/logs", tags=["logs"])
app.include_router(exchange.router, prefix="/exchange", tags=["exchange"])
app.include_router(auth.router,     prefix="/auth", tags=["auth"])