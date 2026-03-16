"""股价存储 Repository - DB CRUD 封装"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from server.modules.stock_store.models import WatchlistItem, StockDailyPrice, StockLatestQuote

logger = logging.getLogger("stock_store.repository")


# ==================== Watchlist ====================

class WatchlistRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[WatchlistItem]:
        return self.session.query(WatchlistItem).order_by(WatchlistItem.ticker).all()

    def get_by_ticker(self, ticker: str, market: str = "US") -> WatchlistItem | None:
        return self.session.query(WatchlistItem).filter(
            WatchlistItem.ticker == ticker,
            WatchlistItem.market == market,
        ).first()

    def add(self, ticker: str, market: str = "US", display_name: str = "") -> WatchlistItem:
        existing = self.get_by_ticker(ticker, market)
        if existing:
            if display_name and not existing.display_name:
                existing.display_name = display_name
                self.session.commit()
            return existing
        obj = WatchlistItem(
            ticker=ticker.upper(),
            market=market.upper(),
            display_name=display_name or None,
        )
        self.session.add(obj)
        self.session.commit()
        return obj

    def remove(self, ticker: str, market: str = "US") -> bool:
        obj = self.get_by_ticker(ticker, market)
        if not obj:
            return False
        self.session.delete(obj)
        self.session.commit()
        return True

    @staticmethod
    def to_dict(obj: WatchlistItem) -> dict:
        return {
            "id": obj.id,
            "ticker": obj.ticker,
            "market": obj.market,
            "display_name": obj.display_name or "",
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }


# ==================== Stock Daily Price ====================

class StockDailyPriceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_latest(self, ticker: str, market: str = "US", limit: int = 30) -> list[StockDailyPrice]:
        return (
            self.session.query(StockDailyPrice)
            .filter(StockDailyPrice.ticker == ticker, StockDailyPrice.market == market)
            .order_by(StockDailyPrice.date.desc())
            .limit(limit)
            .all()
        )

    def get_latest_date(self, ticker: str, market: str = "US") -> str | None:
        row = (
            self.session.query(StockDailyPrice.date)
            .filter(StockDailyPrice.ticker == ticker, StockDailyPrice.market == market)
            .order_by(StockDailyPrice.date.desc())
            .first()
        )
        return row[0] if row else None

    def bulk_upsert(self, records: list[dict]) -> int:
        """批量写入日线数据，跳过已存在的 (ticker, market, date)。返回新增行数。"""
        added = 0
        for rec in records:
            existing = self.session.query(StockDailyPrice).filter(
                StockDailyPrice.ticker == rec["ticker"],
                StockDailyPrice.market == rec["market"],
                StockDailyPrice.date == rec["date"],
            ).first()
            if existing:
                continue
            obj = StockDailyPrice(**rec)
            self.session.add(obj)
            added += 1
        if added:
            self.session.commit()
        return added

    @staticmethod
    def to_dict(obj: StockDailyPrice) -> dict:
        return {
            "ticker": obj.ticker,
            "market": obj.market,
            "date": obj.date,
            "open": obj.open,
            "high": obj.high,
            "low": obj.low,
            "close": obj.close,
            "volume": obj.volume,
        }


# ==================== Stock Latest Quote ====================

class StockLatestQuoteRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, ticker: str, market: str = "US") -> StockLatestQuote | None:
        return self.session.query(StockLatestQuote).filter(
            StockLatestQuote.ticker == ticker,
            StockLatestQuote.market == market,
        ).first()

    def get_for_tickers(self, tickers: list[str], market: str = "US") -> list[StockLatestQuote]:
        if not tickers:
            return []
        return self.session.query(StockLatestQuote).filter(
            StockLatestQuote.ticker.in_(tickers),
            StockLatestQuote.market == market,
        ).all()

    def upsert(self, ticker: str, market: str = "US", **fields) -> StockLatestQuote:
        obj = self.get(ticker, market)
        if obj:
            for k, v in fields.items():
                if hasattr(obj, k):
                    setattr(obj, k, v)
            obj.updated_at = datetime.now(timezone.utc)
        else:
            obj = StockLatestQuote(ticker=ticker, market=market, **fields)
            self.session.add(obj)
        self.session.commit()
        return obj

    def bulk_upsert(self, market: str, quotes_dict: dict[str, dict]) -> int:
        """批量更新最新报价。quotes_dict = {ticker: {field: value, ...}}"""
        count = 0
        for ticker, fields in quotes_dict.items():
            self.upsert(ticker, market, **fields)
            count += 1
        return count

    @staticmethod
    def to_dict(obj: StockLatestQuote) -> dict:
        return {
            "ticker": obj.ticker,
            "market": obj.market,
            "regular_price": obj.regular_price,
            "regular_change": obj.regular_change,
            "regular_change_pct": obj.regular_change_pct,
            "pre_price": obj.pre_price,
            "pre_change": obj.pre_change,
            "pre_change_pct": obj.pre_change_pct,
            "post_price": obj.post_price,
            "post_change": obj.post_change,
            "post_change_pct": obj.post_change_pct,
            "prev_close": obj.prev_close,
            "session": obj.session,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }
