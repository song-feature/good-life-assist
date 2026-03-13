"""股票模块 LangChain Tools"""
import json
import logging
from langchain_core.tools import tool

from . import service

logger = logging.getLogger("stock.tools")


@tool
def get_portfolio() -> dict:
    """查询当前股票持仓和账户资金概览。返回持仓列表（每只股票的代码、名称、数量、成本价、现价、盈亏）和资金信息（总资产、现金、浮动盈亏）。"""
    try:
        data = service.get_portfolio_data()
        data["_ui_command"] = {
            "module": "stock",
            "action": "show_portfolio",
            "data": data,
        }
        return data
    except Exception as e:
        logger.error(f"get_portfolio 失败: {e}")
        return {"error": str(e)}


@tool
def get_stock_trend(ticker: str, period: str = "1mo") -> dict:
    """获取指定股票的价格走势和技术指标。包括收盘价历史、MA5/MA20均线、RSI14、5日涨跌幅。参数: ticker-股票代码(如AAPL), period-时间范围(默认1mo)。"""
    try:
        data = service.get_stock_trend_data(ticker, period=period)
        data["_ui_command"] = {
            "module": "stock",
            "action": "show_trend",
            "data": data,
        }
        return data
    except Exception as e:
        logger.error(f"get_stock_trend 失败: {e}")
        return {"error": str(e)}


@tool
def get_options_chain(ticker: str, expiry_date: str = "") -> dict:
    """获取指定股票的期权链数据。包括看涨/看跌期权列表、行权价、未平仓量、隐含波动率等。参数: ticker-股票代码(如AAPL), expiry_date-到期日(可选,如2025-03-21)。"""
    try:
        expiry = expiry_date if expiry_date else None
        data = service.get_options_data(ticker, expiry_date=expiry)
        if data is None:
            return {"error": f"未找到 {ticker} 的期权数据"}
        result = dict(data)
        result["_ui_command"] = {
            "module": "stock",
            "action": "show_options",
            "data": data,
        }
        return result
    except Exception as e:
        logger.error(f"get_options_chain 失败: {e}")
        return {"error": str(e)}


@tool
def get_portfolio_analysis() -> dict:
    """获取完整的持仓分析报告。包括每只持仓的技术指标（MA交叉、RSI、5日涨跌）、期权情绪分析、以及综合操作建议。"""
    try:
        data = service.get_full_analysis()
        if "error" in data:
            return data
        data["_ui_command"] = {
            "module": "stock",
            "action": "show_analysis",
            "data": data,
        }
        return data
    except Exception as e:
        logger.error(f"get_portfolio_analysis 失败: {e}")
        return {"error": str(e)}
