from sqlalchemy import Column, Integer, String, Float, DateTime
from app.database import Base
from sqlalchemy import String

class TradeEvent(Base):
    __tablename__ = "trade_events"

    id = Column(
        Integer,
        primary_key=True
    )

    strategy = Column(String)

    pair = Column(String)

    trade_id = Column(Integer)

    event_type = Column(String)

    side = Column(String)

    price = Column(Float)

    amount = Column(Float)

    time = Column(String)

    candle_time = Column(String)

    message = Column(String)
