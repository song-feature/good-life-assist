"""股票模块 REST API"""
import asyncio
from functools import partial

from fastapi import APIRouter, Query

from server.modules.stock import service

router = APIRouter(tags=["stock"])


def _run_sync(fn, *args, **kwargs):
    """Run a blocking function in a thread pool."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, partial(fn, *args, **kwargs))


@router.get("/portfolio")
async def get_portfolio(market: str = Query(default=None), env: str = Query(default=None)):
    return await _run_sync(service.get_portfolio_data, market=market, env=env)


@router.get("/trend/{ticker}")
async def get_trend(ticker: str, period: str = Query(default="1mo"), market: str = Query(default=None)):
    return await _run_sync(service.get_stock_trend_data, ticker, market=market, period=period)


@router.get("/options/{ticker}/expiry-dates")
async def get_expiry_dates(ticker: str, market: str = Query(default=None)):
    dates = await _run_sync(service.get_options_expiry_dates, ticker, market=market)
    return {"ticker": ticker, "expiry_dates": dates}


@router.get("/options/{ticker}")
async def get_options(ticker: str, expiry: str = Query(default=None), market: str = Query(default=None)):
    data = await _run_sync(service.get_options_data, ticker, market=market, expiry_date=expiry)
    if data is None:
        return {"error": f"未找到 {ticker} 的期权数据"}
    return data


@router.get("/analysis")
async def get_analysis(market: str = Query(default=None), env: str = Query(default=None)):
    return await _run_sync(service.get_full_analysis, market=market, env=env)
