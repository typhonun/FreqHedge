from sqlalchemy import Boolean, Column, Float, Integer, String

from app.database import Base


class ArchivedProfit(Base):
    __tablename__ = "archived_profit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(Integer, nullable=False, unique=True, index=True)
    account_id = Column(String, nullable=True, index=True)
    dry_run = Column(Boolean, nullable=False, index=True)
    total_profit = Column(Float, nullable=False, default=0)
    long_profit = Column(Float, nullable=False, default=0)
    short_profit = Column(Float, nullable=False, default=0)
    timestamp = Column(Integer, nullable=False)
