from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from threading import Thread
import threading

from contextlib import asynccontextmanager

from app.api.chart import cache_refresh_loop
from app.services.risk_service import RiskService
from app.services.risk_config_service import RiskConfigService
from app.api.risk import router as risk_router
from app.api.trade import router as trade_router
from app.api.control import router as control_router
from app.api.system import router as system_router
from app.api.position import router as position_router
from app.api.config import router as config_router
from app.api.chart import router as chart_router
from app.api import logs
from app.api import strategy

from app.database import Base, engine

# 重要：确保模型被导入
from app.models import trade_event
from app.models.equity_history import EquityHistory
from app.models.profit_history import ProfitHistory

from app.scheduler.equity_scheduler import (
    start_scheduler,
    stop_scheduler
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    # =====================================================
    # 1. 创建数据库表
    # =====================================================

    Base.metadata.create_all(bind=engine)

    print("Database tables initialized.")

    # =====================================================
    # 2. 加载风险配置
    # =====================================================

    RiskConfigService.load()

    # =====================================================
    # 3. 启动 Equity 定时任务
    # =====================================================

    start_scheduler()

    # =====================================================
    # 4. 启动风险监控
    # =====================================================

    threading.Thread(
        target=RiskService.monitor,
        daemon=True
    ).start()

    # =====================================================
    # 5. 启动缓存刷新
    # =====================================================

    Thread(
        target=cache_refresh_loop,
        daemon=True
    ).start()

    print("Application started.")

    yield

    # =====================================================
    # 6. 关闭 scheduler
    # =====================================================

    stop_scheduler()

    print("Application stopped.")


app = FastAPI(
    lifespan=lifespan
)


# =========================================================
# CORS
# =========================================================

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
# Routers
# =========================================================

app.include_router(
    trade_router,
    prefix="/trade",
    tags=["trade"]
)

app.include_router(
    system_router,
    prefix="/system",
    tags=["system"]
)

app.include_router(
    position_router,
    prefix="/position",
    tags=["position"]
)

app.include_router(
    config_router,
    prefix="/config",
    tags=["config"]
)

app.include_router(
    chart_router,
    prefix="/chart",
    tags=["chart"]
)

app.include_router(
    control_router,
    prefix="/control",
    tags=["control"]
)

app.include_router(
    strategy.router,
    prefix="/strategy",
    tags=["strategy"]
)

app.include_router(
    risk_router,
    prefix="/api/risk",
    tags=["risk"]
)

app.include_router(
    logs.router,
    prefix="/logs"
)