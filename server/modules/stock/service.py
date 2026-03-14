"""股票模块业务逻辑编排层"""
import logging
import time
from datetime import datetime

from .account import get_positions_and_funds
from .quote import fetch_quotes_batch, fetch_history_yfinance, fetch_option_chain, fetch_option_expiry_dates
from .analysis import analyze_ticker, calc_rsi, calc_ma, calc_ma_series
from .options_wall import get_options_wall_for_ticker
from .llm_summary import generate_options_wall_summary, generate_portfolio_recommendations
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
            pos["prev_close"] = safe_float(quote.get("prev_close"))
            pos["price_change"] = safe_float(quote.get("regular_change"))
            pos["price_change_pct"] = safe_float(quote.get("regular_change_pct"))

            # 盘前/盘后使用对应的变动数据
            session = quote.get("session", "")
            if session == "盘前" and quote.get("pre_change") is not None:
                pos["price_change"] = safe_float(quote["pre_change"])
                pos["price_change_pct"] = safe_float(quote["pre_change_pct"])
            elif session == "盘后" and quote.get("post_change") is not None:
                pos["price_change"] = safe_float(quote["post_change"])
                pos["price_change_pct"] = safe_float(quote["post_change_pct"])
        elif "current_price" not in pos:
            qty = pos.get("qty", 0)
            mval = pos.get("market_val", 0)
            pos["current_price"] = round(mval / qty, 2) if qty > 0 else pos.get("cost_price", 0)

    return {
        "positions": positions,
        "funds": pf.get("funds"),
        "today_pl_total": pf.get("today_pl_total", 0),
    }


PERIOD_INTERVAL_MAP = {
    "1d": "5m",
    "5d": "15m",
    "1mo": "1d",
    "3mo": "1d",
    "6mo": "1d",
    "1y": "1wk",
    "ytd": "1d",
}


def get_stock_trend_data(ticker, market=None, period="1mo"):
    """获取单只股票走势+技术指标"""
    market = market or get_default_market()
    interval = PERIOD_INTERVAL_MAP.get(period, "1d")
    analysis = analyze_ticker(ticker, market=market, period=period, interval=interval)
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


def get_options_wall(ticker, market=None):
    """返回期权墙结构化数据（快速）"""
    market = market or get_default_market()
    return get_options_wall_for_ticker(ticker, market=market)


def get_options_wall_summary(ticker, market=None):
    """返回期权墙结构化数据 + LLM 摘要"""
    market = market or get_default_market()
    wall_data = get_options_wall_for_ticker(ticker, market=market)
    summary = generate_options_wall_summary(wall_data)
    return {"ticker": ticker, "wall_data": wall_data, "summary": summary}


def get_analysis_recommendations(market=None, env=None):
    """返回 LLM 组合投资建议"""
    analysis_data = get_full_analysis(market=market, env=env)
    if "error" in analysis_data:
        return analysis_data
    recommendations = generate_portfolio_recommendations(analysis_data)
    return {
        "recommendations": recommendations,
        "generated_at": datetime.now().isoformat(),
    }
