from sqlalchemy import Column, Integer, Float

from app.database import Base


class EquityHistory(Base):

    __tablename__ = "equity_history"

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

    equity = Column(
        Float,
        nullable=False
    )

    wallet = Column(
        Float,
        nullable=False
    )

    profit = Column(
        Float,
        nullable=False
    )