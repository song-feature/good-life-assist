"""后台股价抓取守护线程"""
import time
import logging
import threading

logger = logging.getLogger("stock_store.fetcher")

# 每批抓取的 ticker 数量上限
_BATCH_SIZE = 8
# 批间等待秒数（避免 yfinance 限流）
_BATCH_SLEEP = 2.0


class StockPriceFetcher:
    """定时抓取 watchlist 中所有股票的最新报价和日线数据"""

    def __init__(self, interval_minutes: int = 30):
        self._interval_seconds = max(interval_minutes, 1) * 60
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        if self._thread and self._thread.is_alive():
            logger.warning("Fetcher 已在运行")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="stock-price-fetcher",
        )
        self._thread.start()
        logger.info(f"股价抓取线程已启动，间隔 {self._interval_seconds // 60} 分钟")

    def stop(self):
        if not self._thread:
            return
        self._stop_event.set()
        self._thread.join(timeout=5)
        self._thread = None
        logger.info("股价抓取线程已停止")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        """主循环：立即执行首次抓取，然后定时循环"""
        while not self._stop_event.is_set():
            try:
                self._fetch_cycle()
            except Exception as e:
                logger.error(f"抓取周期异常: {e}", exc_info=True)
            # 等待下一个周期或被中断
            self._stop_event.wait(self._interval_seconds)

    def _fetch_cycle(self):
        """单次抓取：最新报价 + 日线数据补全"""
        from server.modules.stock_store.service import get_stock_store_service
        from server.modules.stock.quote import fetch_quotes_batch, fetch_history_yfinance

        svc = get_stock_store_service()
        watchlist = svc.get_watchlist_tickers()
        if not watchlist:
            logger.debug("关注列表为空，跳过抓取")
            return

        # 按 market 分组
        by_market: dict[str, list[str]] = {}
        for item in watchlist:
            by_market.setdefault(item["market"], []).append(item["ticker"])

        for market, tickers in by_market.items():
            # 分批获取最新报价
            for i in range(0, len(tickers), _BATCH_SIZE):
                if self._stop_event.is_set():
                    return
                batch = tickers[i:i + _BATCH_SIZE]
                try:
                    quotes = fetch_quotes_batch(batch, market=market)
                    if quotes:
                        svc.save_latest_quotes(market, quotes)
                        logger.info(f"已更新 {len(quotes)} 只 {market} 股票报价")
                except Exception as e:
                    logger.error(f"批量报价抓取失败 ({market} batch {i}): {e}")
                if i + _BATCH_SIZE < len(tickers):
                    time.sleep(_BATCH_SLEEP)

            # 补充日线数据
            for ticker in tickers:
                if self._stop_event.is_set():
                    return
                try:
                    self._fill_daily_prices(svc, ticker, market)
                except Exception as e:
                    logger.error(f"日线数据补充失败 [{ticker}]: {e}")
                time.sleep(1.0)  # 每只股票间隔 1s

    @staticmethod
    def _fill_daily_prices(svc, ticker: str, market: str):
        """检查日线数据缺口并补充"""
        from server.modules.stock.quote import fetch_history_yfinance

        latest_date = svc.get_latest_stored_date(ticker, market)
        if latest_date:
            # 计算距今天数，决定是否需要补充
            from datetime import datetime, date
            try:
                last = datetime.strptime(latest_date, "%Y-%m-%d").date()
                gap_days = (date.today() - last).days
            except ValueError:
                gap_days = 999
            if gap_days <= 1:
                return  # 数据已是最新，无需补充
            period = "5d" if gap_days <= 5 else "1mo"
        else:
            # 首次抓取，拉取 3 个月数据
            period = "3mo"

        hist = fetch_history_yfinance(ticker, market=market, period=period, interval="1d")
        if hist and hist.get("close"):
            added = svc.save_daily_prices(ticker, market, hist)
            if added:
                logger.debug(f"[{ticker}] 补充 {added} 条日线数据 (period={period})")
