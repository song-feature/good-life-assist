"""LLM 摘要生成 - 从 registry 读取可配置 prompt，调用 LLM 生成文本"""
import logging
import time
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from server.core.llm import create_llm_for_scope
from server.modules.registry import get_registry

logger = logging.getLogger("stock.llm_summary")

# ---------- 内存缓存（TTL 300s）----------

_cache: dict[str, tuple[float, str]] = {}
_CACHE_TTL = 300


def _cache_get(key: str) -> str | None:
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: str):
    _cache[key] = (time.time(), value)


# ---------- prompt 读取 ----------

# 默认值（与 module.py 中的 default_config 保持一致）
_DEFAULT_OPTIONS_WALL_PROMPT = """你是一位专业的美股期权分析师。请根据以下期权持仓量数据分析关键支撑位和阻力位。

{data}

请用中文简洁回答（150字以内，不使用 markdown）：
1) 短期关键支撑和阻力在哪里
2) Max Pain 暗示的收盘磁吸方向
3) 做市商对冲可能如何影响股价"""

_DEFAULT_RECOMMENDATIONS_PROMPT = """你是一位专业的股票投资顾问。请根据以下持仓技术分析和期权数据给出操作建议。

{data}

要求：
- 每只股票一条建议（一句话）
- 最后给整体组合判断
- 总字数300字以内，使用 markdown **加粗** 强调
- 末尾加风险提示"""


def _get_prompt(key: str) -> str:
    """从 registry 配置中读取 prompt，未配置则用默认值"""
    try:
        config = get_registry().get_module_config("stock")
        val = config.get(key)
        if val and isinstance(val, str) and val.strip():
            return val
    except Exception:
        pass
    defaults = {
        "prompt_options_wall": _DEFAULT_OPTIONS_WALL_PROMPT,
        "prompt_recommendations": _DEFAULT_RECOMMENDATIONS_PROMPT,
    }
    return defaults.get(key, "")


# ---------- 数据格式化 ----------

def _format_wall_data(wall_data: dict) -> str:
    """将期权墙结构化数据格式化为 LLM 可读文本"""
    ticker = wall_data.get("ticker", "")
    price = wall_data.get("current_price", 0)
    lines = [f"股票：{ticker}，当前股价：${price}"]

    for label, key in [("本周五", "this_friday"), ("下周五", "next_friday")]:
        wall = wall_data.get(key)
        if not wall:
            lines.append(f"\n【{label}】无数据")
            continue
        lines.append(f"\n【{label}到期 ({wall['expiry_date']})】")

        call_walls = wall.get("call_walls", [])
        if call_walls:
            items = ", ".join(f"${w['strike']}(OI:{w['openInterest']:,})" for w in call_walls)
            lines.append(f"Call Wall（阻力）：{items}")

        put_walls = wall.get("put_walls", [])
        if put_walls:
            items = ", ".join(f"${w['strike']}(OI:{w['openInterest']:,})" for w in put_walls)
            lines.append(f"Put Wall（支撑）：{items}")

        mp = wall.get("max_pain")
        pc = wall.get("put_call_ratio", 0)
        lines.append(f"Max Pain：${mp}  P/C Ratio：{pc}")

    return "\n".join(lines)


def _format_analysis_data(analysis_data: dict) -> str:
    """将持仓分析数据格式化为 LLM 可读文本"""
    holdings = analysis_data.get("holdings", [])
    lines = []
    for h in holdings:
        ticker = h.get("ticker", "")
        name = h.get("name", "")
        qty = h.get("qty", 0)
        cost = h.get("cost_price", 0)
        current = h.get("current_price", 0)
        pl_ratio = h.get("pl_ratio", 0)
        ma_signal = h.get("ma_signal", "无数据")
        rsi14 = h.get("rsi14", "无数据")
        pct_5d = h.get("price_change_5d_pct", "无数据")
        sentiment = h.get("options_sentiment", "无数据")
        opts = h.get("options") or {}
        pc = opts.get("put_call_ratio", "N/A")

        lines.append(
            f"**{ticker}** ({name}) - {qty}股，成本${cost}，现价${current}，盈亏{pl_ratio}%\n"
            f"MA信号：{ma_signal}，RSI(14)：{rsi14}，5日涨跌：{pct_5d}%\n"
            f"期权情绪：{sentiment}（P/C={pc}）"
        )
    return "\n\n".join(lines)


# ---------- LLM 调用 ----------

def generate_options_wall_summary(wall_data: dict) -> str:
    """用 LLM 生成单只股票的期权墙摘要"""
    ticker = wall_data.get("ticker", "unknown")
    cache_key = f"wall_summary:{ticker}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    prompt_template = _get_prompt("prompt_options_wall")
    data_text = _format_wall_data(wall_data)
    prompt_filled = prompt_template.replace("{data}", data_text)

    try:
        llm = create_llm(temperature=0.3)
        resp = llm.invoke([
            SystemMessage(content="你是一位专业的美股期权分析师。"),
            HumanMessage(content=prompt_filled),
        ])
        result = resp.content.strip()
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"LLM 生成期权墙摘要失败 ({ticker}): {e}")
        return f"AI 分析暂不可用: {e}"


def generate_portfolio_recommendations(analysis_data: dict) -> str:
    """用 LLM 生成组合投资建议"""
    cache_key = "portfolio_recommendations"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    prompt_template = _get_prompt("prompt_recommendations")
    data_text = _format_analysis_data(analysis_data)
    prompt_filled = prompt_template.replace("{data}", data_text)

    try:
        llm = create_llm_for_scope("module.stock.recommendations", temperature=0.4)
        resp = llm.invoke([
            SystemMessage(content="你是一位专业的股票投资顾问。"),
            HumanMessage(content=prompt_filled),
        ])
        result = resp.content.strip()
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"LLM 生成投资建议失败: {e}")
        return f"AI 建议暂不可用: {e}"
