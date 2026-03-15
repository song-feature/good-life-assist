"""富途股票模块声明"""
import logging

from server.modules.base import BaseModule
from langchain_core.tools import BaseTool

logger = logging.getLogger("stock.module")

OPTIONS_WALL_PROMPT_DEFAULT = """你是一位专业的美股期权分析师。请根据以下期权持仓量数据分析关键支撑位和阻力位。

{data}

请用中文简洁回答（150字以内，不使用 markdown）：
1) 短期关键支撑和阻力在哪里
2) Max Pain 暗示的收盘磁吸方向
3) 做市商对冲可能如何影响股价"""

RECOMMENDATIONS_PROMPT_DEFAULT = """你是一位专业的股票投资顾问。请根据以下持仓技术分析和期权数据给出操作建议。

{data}

要求：
- 每只股票一条建议（一句话）
- 最后给整体组合判断
- 总字数300字以内，使用 markdown **加粗** 强调
- 末尾加风险提示"""


class StockModule(BaseModule):
    module_id = "stock"
    display_name = "富途股票"
    description = "股票持仓分析模块。支持查询持仓、查看股票走势、期权链分析、生成操作建议、管理关注列表、股价存储与分析。关键词：持仓、股票、期权、走势、分析、建议、关注、添加、删除"
    default_config = {
        "futu_host": "127.0.0.1",
        "futu_port": 11111,
        "market": "US",
        "env": "SIMULATE",
        "prompt_options_wall": OPTIONS_WALL_PROMPT_DEFAULT,
        "prompt_recommendations": RECOMMENDATIONS_PROMPT_DEFAULT,
        "fetch_interval_minutes": 30,
        "watchlist_default_market": "US",
    }

    _fetcher = None

    def get_tools(self) -> list[BaseTool]:
        from .tools import get_portfolio, get_stock_trend, get_options_chain, get_portfolio_analysis
        from .watchlist_tools import list_watchlist, manage_watchlist, analyze_stock_from_db
        return [
            get_portfolio, get_stock_trend, get_options_chain, get_portfolio_analysis,
            list_watchlist, manage_watchlist, analyze_stock_from_db,
        ]

    def get_system_prompt(self) -> str:
        return """你是一个专业的股票持仓分析助手。你可以：

1. 查询用户的股票持仓和账户资金 - 使用 get_portfolio 工具
2. 查看某只股票的价格走势和技术指标 - 使用 get_stock_trend 工具
3. 查看某只股票的期权链数据 - 使用 get_options_chain 工具
4. 生成完整的持仓分析报告和操作建议 - 使用 get_portfolio_analysis 工具
5. 查看关注列表及最新价格（含盘前/盘后） - 使用 list_watchlist 工具
6. 添加/删除关注的股票 - 使用 manage_watchlist 工具
7. 基于存储数据分析股票走势 - 使用 analyze_stock_from_db 工具

规则：
- 当用户想看持仓时，调用 get_portfolio
- 当用户问某只股票走势时，调用 get_stock_trend
- 当用户问期权时，调用 get_options_chain
- 当用户要分析或建议时，调用 get_portfolio_analysis
- 当用户想看关注的股票时，调用 list_watchlist
- 当用户要添加或删除关注股票时，调用 manage_watchlist
- 当用户要分析某只股票的历史走势时，优先用 analyze_stock_from_db（使用存储数据，减少API调用）
- 工具返回后，用中文简要总结关键信息
- 给出建议时要说明分析依据（技术指标、期权情绪等）
- 始终提醒"以上分析仅供参考，请结合基本面综合判断"

分析框架：
- MA5 > MA20 = 金叉（看多），MA5 < MA20 = 死叉（看空）
- RSI > 70 = 超买区，RSI < 30 = 超卖区
- Put/Call Ratio > 1.0 = 看跌情绪，< 0.7 = 看涨情绪"""

    def on_enable(self) -> None:
        """启动后台价格抓取线程"""
        from .config import get_stock_config
        from server.modules.stock_store.fetcher import StockPriceFetcher

        if self._fetcher and self._fetcher.is_running:
            return
        config = get_stock_config()
        interval = config.get("fetch_interval_minutes", 30)
        self._fetcher = StockPriceFetcher(interval_minutes=interval)
        self._fetcher.start()
        logger.info(f"股价抓取线程已启动 (间隔 {interval} 分钟)")

    def on_disable(self) -> None:
        """停止后台抓取线程"""
        if self._fetcher:
            self._fetcher.stop()
            self._fetcher = None
            logger.info("股价抓取线程已停止")
