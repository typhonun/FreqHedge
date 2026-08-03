from pydantic import BaseModel
from datetime import datetime


class TradeEventCreate(BaseModel):

    strategy: str

    pair: str

    trade_id: int

    event_type: str

    side: str

    price: float

    amount: float

    # 真实事件时间
    time: datetime

    # 对应K线时间
    candle_time: datetime | None = None

    message: str = ""


class TradeEventOut(BaseModel):

    id: int

    strategy: str

    pair: str

    trade_id: int

    event_type: str

    side: str

    price: float

    amount: float

    time: datetime

    candle_time: datetime | None = None

    message: str


    class Config:
        from_attributes = True