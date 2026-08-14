from sqlalchemy import Column, Integer, Float

from app.database import Base


class ProfitHistory(Base):

    __tablename__ = "profit_history"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    timestamp = Column(
        Integer,
        index=True,
        nullable=False
    )

    total_profit = Column(
        Float,
        nullable=False
    )

    long_profit = Column(
        Float,
        nullable=False
    )

    short_profit = Column(
        Float,
        nullable=False
    )