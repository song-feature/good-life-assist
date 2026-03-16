"""股价存储 ORM 模型"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, BigInteger, DateTime, Index, UniqueConstraint,
)
from server.db.session import Base


def _utcnow():
    return datetime.now(timezone.utc)


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    market = Column(String(10), nullable=False, default="US")
    display_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("ticker", "market", name="uq_watchlist_ticker_market"),
    )


class StockDailyPrice(Base):
    __tablename__ = "stock_daily_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    market = Column(String(10), nullable=False)
    date = Column(String(10), nullable=False)  # "2024-01-15"
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    volume = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("ticker", "market", "date", name="uq_daily_ticker_market_date"),
        Index("ix_daily_ticker_market_date", "ticker", "market", "date"),
    )


class StockLatestQuote(Base):
    __tablename__ = "stock_latest_quotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    market = Column(String(10), nullable=False)
    regular_price = Column(Float, nullable=True)
    regular_change = Column(Float, nullable=True)
    regular_change_pct = Column(Float, nullable=True)
    pre_price = Column(Float, nullable=True)
    pre_change = Column(Float, nullable=True)
    pre_change_pct = Column(Float, nullable=True)
    post_price = Column(Float, nullable=True)
    post_change = Column(Float, nullable=True)
    post_change_pct = Column(Float, nullable=True)
    prev_close = Column(Float, nullable=True)
    session = Column(String(20), nullable=True)  # "盘前"/"盘中"/"盘后"/"休市"
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("ticker", "market", name="uq_quote_ticker_market"),
    )
