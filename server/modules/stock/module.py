"""富途股票模块声明"""
from server.modules.base import BaseModule
from langchain_core.tools import BaseTool


class StockModule(BaseModule):
    module_id = "stock"
    display_name = "富途股票"
    description = "股票持仓分析模块。支持查询持仓、查看股票走势、期权链分析、生成操作建议。关键词：持仓、股票、期权、走势、分析、建议"
    default_config = {
        "futu_host": "127.0.0.1",
        "futu_port": 11111,
        "market": "US",
        "env": "SIMULATE",
    }

    def get_tools(self) -> list[BaseTool]:
        from .tools import get_portfolio, get_stock_trend, get_options_chain, get_portfolio_analysis
        return [get_portfolio, get_stock_trend, get_options_chain, get_portfolio_analysis]

    def get_system_prompt(self) -> str:
        return """你是一个专业的股票持仓分析助手。你可以：

1. 查询用户的股票持仓和账户资金 - 使用 get_portfolio 工具
2. 查看某只股票的价格走势和技术指标 - 使用 get_stock_trend 工具
3. 查看某只股票的期权链数据 - 使用 get_options_chain 工具
4. 生成完整的持仓分析报告和操作建议 - 使用 get_portfolio_analysis 工具

规则：
- 当用户想看持仓时，调用 get_portfolio
- 当用户问某只股票走势时，调用 get_stock_trend
- 当用户问期权时，调用 get_options_chain
- 当用户要分析或建议时，调用 get_portfolio_analysis
- 工具返回后，用中文简要总结关键信息
- 给出建议时要说明分析依据（技术指标、期权情绪等）
- 始终提醒"以上分析仅供参考，请结合基本面综合判断"

分析框架：
- MA5 > MA20 = 金叉（看多），MA5 < MA20 = 死叉（看空）
- RSI > 70 = 超买区，RSI < 30 = 超卖区
- Put/Call Ratio > 1.0 = 看跌情绪，< 0.7 = 看涨情绪"""
