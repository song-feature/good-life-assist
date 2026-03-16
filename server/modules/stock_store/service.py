"""股价存储 Service - 业务逻辑层"""
import logging
from datetime import datetime, timezone, timedelta

from server.db.session import get_session
from server.modules.stock_store.repository import (
    WatchlistRepository,
    StockDailyPriceRepository,
    StockLatestQuoteRepository,
)

logger = logging.getLogger("stock_store.service")


class StockStoreService:
    """股价存储业务逻辑，管理 session 生命周期"""

    # ── Watchlist ──────────────────────────────────────

    def get_watchlist(self) -> list[dict]:
        """获取关注列表，含最新报价"""
        session = get_session()
        try:
            wl_repo = WatchlistRepository(session)
            quote_repo = StockLatestQuoteRepository(session)
            items = wl_repo.get_all()
            result = []
            for item in items:
                d = wl_repo.to_dict(item)
                quote = quote_repo.get(item.ticker, item.market)
                if quote:
                    d["quote"] = quote_repo.to_dict(quote)
                else:
                    d["quote"] = None
                result.append(d)
            return result
        finally:
            session.close()

    def add_to_watchlist(self, ticker: str, market: str = "US",
                         display_name: str = "") -> dict:
        """添加股票到关注列表"""
        session = get_session()
        try:
            repo = WatchlistRepository(session)
            obj = repo.add(ticker.upper(), market.upper(), display_name)
            return repo.to_dict(obj)
        finally:
            session.close()

    def remove_from_watchlist(self, ticker: str, market: str = "US") -> bool:
        """从关注列表移除"""
        session = get_session()
        try:
            repo = WatchlistRepository(session)
            return repo.remove(ticker.upper(), market.upper())
        finally:
            session.close()

    def get_watchlist_tickers(self) -> list[dict]:
        """获取关注列表的 ticker 和 market（供 fetcher 使用）"""
        session = get_session()
        try:
            repo = WatchlistRepository(session)
            items = repo.get_all()
            return [{"ticker": i.ticker, "market": i.market} for i in items]
        finally:
            session.close()

    # ── 最新报价查询 ──────────────────────────────────

    def get_latest_quotes(self, tickers: list[str], market: str = "US") -> dict[str, dict]:
        """从 DB 查询最新报价，返回 {ticker: quote_dict}"""
        session = get_session()
        try:
            repo = StockLatestQuoteRepository(session)
            rows = repo.get_for_tickers(tickers, market)
            return {row.ticker: repo.to_dict(row) for row in rows}
        finally:
            session.close()

    def get_fresh_quotes(self, tickers: list[str], market: str = "US",
                         max_age_minutes: int = 30) -> tuple[dict[str, dict], list[str]]:
        """从 DB 查询未过期的报价。返回 (fresh_quotes, stale_tickers)"""
        session = get_session()
        try:
            repo = StockLatestQuoteRepository(session)
            rows = repo.get_for_tickers(tickers, market)
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
            fresh = {}
            found_tickers = set()
            for row in rows:
                found_tickers.add(row.ticker)
                if row.updated_at and row.updated_at.replace(tzinfo=timezone.utc) >= cutoff:
                    fresh[row.ticker] = repo.to_dict(row)
            stale = [t for t in tickers if t not in fresh]
            return fresh, stale
        finally:
            session.close()

    # ── 日线数据查询 ──────────────────────────────────

    def get_daily_prices(self, ticker: str, market: str = "US",
                         days: int = 30) -> list[dict]:
        """查询日线数据，按 date DESC"""
        session = get_session()
        try:
            repo = StockDailyPriceRepository(session)
            rows = repo.get_latest(ticker.upper(), market.upper(), limit=days)
            return [repo.to_dict(r) for r in reversed(rows)]  # 按 date ASC 返回
        finally:
            session.close()

    def get_latest_stored_date(self, ticker: str, market: str = "US") -> str | None:
        """获取某 ticker 在 DB 中最新的日线日期"""
        session = get_session()
        try:
            repo = StockDailyPriceRepository(session)
            return repo.get_latest_date(ticker.upper(), market.upper())
        finally:
            session.close()

    # ── 数据写入 ──────────────────────────────────────

    def save_latest_quotes(self, market: str, quotes_dict: dict[str, dict]):
        """将 fetch_quotes_batch 返回的 dict 写入 stock_latest_quotes"""
        session = get_session()
        try:
            repo = StockLatestQuoteRepository(session)
            for ticker, q in quotes_dict.items():
                fields = {
                    "regular_price": q.get("regular_price") or q.get("current_price"),
                    "regular_change": q.get("regular_change"),
                    "regular_change_pct": q.get("regular_change_pct"),
                    "pre_price": q.get("pre_price"),
                    "pre_change": q.get("pre_change"),
                    "pre_change_pct": q.get("pre_change_pct"),
                    "post_price": q.get("post_price"),
                    "post_change": q.get("post_change"),
                    "post_change_pct": q.get("post_change_pct"),
                    "prev_close": q.get("prev_close"),
                    "session": q.get("session"),
                }
                repo.upsert(ticker, market, **fields)
            logger.debug(f"保存 {len(quotes_dict)} 条最新报价到 DB")
        except Exception as e:
            logger.error(f"保存最新报价失败: {e}")
        finally:
            session.close()

    def save_daily_prices(self, ticker: str, market: str, history_data: dict) -> int:
        """将 yfinance history 数据写入 stock_daily_prices。
        history_data 格式: {"dates": [...], "close": [...], "high": [...], "low": [...]}
        返回新增行数。
        """
        session = get_session()
        try:
            repo = StockDailyPriceRepository(session)
            dates = history_data.get("dates", [])
            closes = history_data.get("close", [])
            highs = history_data.get("high", [])
            lows = history_data.get("low", [])
            records = []
            for i, date_str in enumerate(dates):
                # 只处理日线格式 (YYYY-MM-DD)
                if len(date_str) > 10:
                    continue
                records.append({
                    "ticker": ticker.upper(),
                    "market": market.upper(),
                    "date": date_str,
                    "close": closes[i] if i < len(closes) else None,
                    "high": highs[i] if i < len(highs) else None,
                    "low": lows[i] if i < len(lows) else None,
                    "open": None,  # yfinance history_data 可能不含 open
                    "volume": None,
                })
            added = repo.bulk_upsert(records) if records else 0
            if added:
                logger.info(f"保存 {ticker} {added} 条日线数据")
            return added
        except Exception as e:
            logger.error(f"保存 {ticker} 日线数据失败: {e}")
            return 0
        finally:
            session.close()

    # ── DB-first + fallback（核心方法）──────────────────

    def get_quotes_with_fallback(self, tickers: list[str], market: str = "US",
                                 max_age_minutes: int = 30) -> dict[str, dict]:
        """DB 优先获取报价，过期/缺失的回退到 yfinance 并回填 DB"""
        fresh, stale = self.get_fresh_quotes(tickers, market, max_age_minutes)
        if not stale:
            return fresh

        # 延迟导入避免循环依赖
        from server.modules.stock.quote import fetch_quotes_batch
        try:
            yf_quotes = fetch_quotes_batch(stale, market=market)
            if yf_quotes:
                self.save_latest_quotes(market, yf_quotes)
                # 转换为与 to_dict 一致的格式
                for ticker, q in yf_quotes.items():
                    fresh[ticker] = {
                        "ticker": ticker,
                        "market": market,
                        "regular_price": q.get("regular_price") or q.get("current_price"),
                        "regular_change": q.get("regular_change"),
                        "regular_change_pct": q.get("regular_change_pct"),
                        "pre_price": q.get("pre_price"),
                        "pre_change": q.get("pre_change"),
                        "pre_change_pct": q.get("pre_change_pct"),
                        "post_price": q.get("post_price"),
                        "post_change": q.get("post_change"),
                        "post_change_pct": q.get("post_change_pct"),
                        "prev_close": q.get("prev_close"),
                        "session": q.get("session"),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
        except Exception as e:
            logger.error(f"yfinance fallback 失败: {e}")

        return fresh

    def get_daily_prices_with_fallback(self, ticker: str, market: str = "US",
                                       days: int = 30) -> dict:
        """DB 优先获取日线数据，不足时补充 yfinance 并回填 DB。
        返回与 fetch_history_yfinance 兼容的格式: {"dates": [], "close": [], "high": [], "low": []}
        """
        db_prices = self.get_daily_prices(ticker, market, days)

        if len(db_prices) >= days:
            # DB 数据充足
            return {
                "dates": [p["date"] for p in db_prices],
                "close": [p["close"] for p in db_prices],
                "high": [p["high"] for p in db_prices],
                "low": [p["low"] for p in db_prices],
            }

        # DB 数据不足，从 yfinance 补充
        from server.modules.stock.quote import fetch_history_yfinance
        try:
            period = "3mo" if days > 30 else "1mo"
            hist = fetch_history_yfinance(ticker, market=market, period=period, interval="1d")
            if hist and hist.get("close"):
                self.save_daily_prices(ticker, market, hist)
                return hist
        except Exception as e:
            logger.error(f"yfinance 日线 fallback 失败 [{ticker}]: {e}")

        # yfinance 也失败，返回 DB 中已有的数据
        if db_prices:
            return {
                "dates": [p["date"] for p in db_prices],
                "close": [p["close"] for p in db_prices],
                "high": [p["high"] for p in db_prices],
                "low": [p["low"] for p in db_prices],
            }
        return {"dates": [], "close": [], "high": [], "low": []}


# 单例
_stock_store_service: StockStoreService | None = None


def get_stock_store_service() -> StockStoreService:
    global _stock_store_service
    if _stock_store_service is None:
        _stock_store_service = StockStoreService()
    return _stock_store_service
