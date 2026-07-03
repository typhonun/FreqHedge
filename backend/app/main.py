from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.trade import router as trade_router
from app.api.control import router as control_router
from app.api.system import router as system_router
from app.api.position import router as position_router
from app.api.config import router as config_router
from app.api.chart import router as chart_router

app = FastAPI()

# 允许前端访问
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