"""股票模块业务逻辑编排层"""
import logging
import time
from datetime import datetime

from .account import get_positions_and_funds
from .quote import fetch_quotes_batch, fetch_history_yfinance, fetch_option_chain, fetch_option_expiry_dates
from .analysis import analyze_ticker, calc_rsi, calc_ma, calc_ma_series
from .config import get_default_market, get_default_env
from .utils import safe_float

logger = logging.getLogger("stock.service")


def get_portfolio_data(market=None, env=None):
    """获取持仓+资金+实时报价"""
    market = market or get_default_market()
    env = env or get_default_env()

    pf = get_positions_and_funds(market=market, env=env, include_zero=False)
    if not pf.get("success"):
        return pf

    positions = pf.get("positions", [])
    tickers = [p["ticker"] for p in positions]
    quotes = fetch_quotes_batch(tickers, market=market) if tickers else {}

    for pos in positions:
        quote = quotes.get(pos["ticker"], {})
        if quote.get("current_price"):
            pos["current_price"] = safe_float(quote["current_price"])
            pos["session"] = quote.get("session", "unknown")

    return {
        "positions": positions,
        "funds": pf.get("funds"),
        "today_pl_total": pf.get("today_pl_total", 0),
    }


def get_stock_trend_data(ticker, market=None, period="1mo"):
    """获取单只股票走势+技术指标"""
    market = market or get_default_market()
    analysis = analyze_ticker(ticker, market=market)
    return {
        "ticker": ticker,
        "closes": analysis.get("closes", []),
        "dates": analysis.get("dates", []),
        "ma5": analysis.get("ma5_series", []),
        "ma20": analysis.get("ma20_series", []),
        "rsi14": analysis.get("rsi14"),
        "current_price": analysis.get("current_price"),
        "price_change_5d_pct": analysis.get("price_change_5d_pct"),
        "ma_signal": analysis.get("ma_signal"),
    }


def get_options_data(ticker, market=None, expiry_date=None):
    """获取期权链"""
    market = market or get_default_market()
    return fetch_option_chain(ticker, market=market, expiry_date=expiry_date)


def get_options_expiry_dates(ticker, market=None):
    """获取期权到期日列表"""
    market = market or get_default_market()
    return fetch_option_expiry_dates(ticker, market=market)


def get_full_analysis(market=None, env=None):
    """完整持仓分析"""
    market = market or get_default_market()
    env = env or get_default_env()

    pf = get_positions_and_funds(market=market, env=env, include_zero=False)
    if not pf.get("success"):
        return {"error": pf.get("error_msg", "获取持仓失败")}

    positions = pf.get("positions", [])
    tickers = [p["ticker"] for p in positions]
    quotes = fetch_quotes_batch(tickers, market=market) if tickers else {}

    holdings = []
    for i, pos in enumerate(positions):
        ticker = pos["ticker"]
        quote = quotes.get(ticker, {})

        holding = {
            "ticker": ticker,
            "name": pos.get("name", ""),
            "qty": pos["qty"],
            "cost_price": pos["cost_price"],
            "current_price": safe_float(quote.get("current_price")),
            "market_val": pos.get("market_val", 0),
            "pl_val": pos.get("pl_val", 0),
            "pl_ratio": pos.get("pl_ratio", 0),
            "today_pl_val": pos.get("today_pl_val", 0),
            "session": quote.get("session", "unknown"),
        }

        # Small delay between tickers to avoid yfinance rate limiting
        if i > 0:
            time.sleep(1.0)

        analysis = analyze_ticker(ticker, market=market)
        holding["ma5"] = analysis.get("ma5")
        holding["ma20"] = analysis.get("ma20")
        holding["rsi14"] = analysis.get("rsi14")
        holding["ma_signal"] = analysis.get("ma_signal")
        holding["price_change_5d_pct"] = analysis.get("price_change_5d_pct")
        holding["options"] = analysis.get("options")
        holding["options_sentiment"] = analysis.get("options_sentiment")

        holdings.append(holding)

    return {
        "generated_at": datetime.now().isoformat(),
        "funds": pf.get("funds"),
        "today_pl_total": pf.get("today_pl_total", 0),
        "holdings": holdings,
    }
