"""关注列表与股价存储 LangChain Tools"""
import logging
from langchain_core.tools import tool

from server.agent.progress import get_channel
from server.modules.stock.config import get_stock_config

logger = logging.getLogger("stock.watchlist_tools")


def _get_default_market() -> str:
    return get_stock_config().get("watchlist_default_market",
                                  get_stock_config().get("market", "US"))


@tool
def list_watchlist() -> dict:
    """列举关注列表中所有股票及其最新价格（含盘前、盘后行情）。当用户想查看关注的股票时使用。"""
    from server.modules.stock_store.service import get_stock_store_service

    try:
        svc = get_stock_store_service()
        items = svc.get_watchlist()

        if not items:
            return {"message": "关注列表为空，可以使用 manage_watchlist 添加股票", "watchlist": []}

        # 构建摘要
        summary = []
        for item in items:
            q = item.get("quote")
            entry = {
                "ticker": item["ticker"],
                "market": item["market"],
                "display_name": item.get("display_name", ""),
            }
            if q:
                entry["regular_price"] = q.get("regular_price")
                entry["regular_change"] = q.get("regular_change")
                entry["regular_change_pct"] = q.get("regular_change_pct")
                entry["pre_price"] = q.get("pre_price")
                entry["pre_change"] = q.get("pre_change")
                entry["pre_change_pct"] = q.get("pre_change_pct")
                entry["post_price"] = q.get("post_price")
                entry["post_change"] = q.get("post_change")
                entry["post_change_pct"] = q.get("post_change_pct")
                entry["prev_close"] = q.get("prev_close")
                entry["session"] = q.get("session")
                entry["updated_at"] = q.get("updated_at")
            else:
                entry["session"] = "无报价数据"
            summary.append(entry)

        result = {"watchlist": summary, "count": len(summary)}

        channel = get_channel()
        if channel == "web":
            result["_ui_command"] = {
                "module": "stock",
                "action": "show_watchlist",
                "data": result,
            }
        return result
    except Exception as e:
        logger.error(f"list_watchlist 失败: {e}")
        return {"error": str(e)}


@tool
def manage_watchlist(action: str, ticker: str, market: str = "", display_name: str = "") -> dict:
    """添加或删除关注列表中的股票。参数: action-操作类型('add'添加/'remove'删除), ticker-股票代码(如AAPL), market-市场(默认US), display_name-显示名称(可选)。"""
    from server.modules.stock_store.service import get_stock_store_service

    if not market:
        market = _get_default_market()

    ticker = ticker.upper().strip()
    action = action.lower().strip()

    if action not in ("add", "remove"):
        return {"error": f"不支持的操作: {action}，请使用 'add' 或 'remove'"}

    try:
        svc = get_stock_store_service()

        if action == "add":
            result = svc.add_to_watchlist(ticker, market, display_name)
            # 添加后立即拉取历史数据回填 DB
            try:
                from server.modules.stock.quote import fetch_history_yfinance
                hist = fetch_history_yfinance(ticker, market=market, period="3mo", interval="1d")
                if hist and hist.get("close"):
                    svc.save_daily_prices(ticker, market, hist)
            except Exception as e:
                logger.warning(f"回填 {ticker} 历史数据失败: {e}")

            return {
                "message": f"已将 {ticker} ({market}) 添加到关注列表",
                "item": result,
            }
        else:
            ok = svc.remove_from_watchlist(ticker, market)
            if ok:
                return {"message": f"已将 {ticker} ({market}) 从关注列表移除"}
            else:
                return {"message": f"{ticker} ({market}) 不在关注列表中"}
    except Exception as e:
        logger.error(f"manage_watchlist 失败: {e}")
        return {"error": str(e)}


@tool
def analyze_stock_from_db(ticker: str, days: int = 30) -> dict:
    """基于数据库存储的历史数据分析股票走势，包含MA均线、RSI等技术指标。如果数据不足会自动从API补充。参数: ticker-股票代码(如AAPL), days-分析天数(默认30)。"""
    from server.modules.stock_store.service import get_stock_store_service
    from server.modules.stock.analysis import calc_rsi, calc_ma, calc_ma_series
    from server.modules.stock.config import get_default_market

    market = get_default_market()
    ticker = ticker.upper().strip()

    try:
        svc = get_stock_store_service()
        hist = svc.get_daily_prices_with_fallback(ticker, market, days=days)

        closes = hist.get("close", [])
        dates = hist.get("dates", [])

        if not closes:
            return {"error": f"未找到 {ticker} 的历史数据"}

        current_price = closes[-1] if closes else None
        price_5d_ago = closes[-6] if len(closes) >= 6 else closes[0]
        price_change_5d_pct = (
            round((current_price - price_5d_ago) / price_5d_ago * 100, 2)
            if current_price and price_5d_ago else None
        )

        data = {
            "ticker": ticker,
            "market": market,
            "data_source": "database",
            "data_points": len(closes),
            "current_price": current_price,
            "price_change_5d_pct": price_change_5d_pct,
            "ma5": calc_ma(closes, 5),
            "ma20": calc_ma(closes, 20),
            "rsi14": calc_rsi(closes, 14),
            "closes": closes,
            "dates": dates,
            "ma5_series": calc_ma_series(closes, 5),
            "ma20_series": calc_ma_series(closes, 20),
        }

        # MA 信号
        if data["ma5"] and data["ma20"]:
            if data["ma5"] > data["ma20"]:
                data["ma_signal"] = "golden_cross"
            elif data["ma5"] < data["ma20"]:
                data["ma_signal"] = "death_cross"
            else:
                data["ma_signal"] = "neutral"
        else:
            data["ma_signal"] = "insufficient_data"

        channel = get_channel()
        if channel == "web":
            data["_ui_command"] = {
                "module": "stock",
                "action": "show_trend",
                "data": data,
            }
        return data
    except Exception as e:
        logger.error(f"analyze_stock_from_db 失败: {e}")
        return {"error": str(e)}
