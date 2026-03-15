"""股票分析子 Agent 节点"""
import json
import logging
from langchain_core.messages import AIMessage, SystemMessage

from server.core.llm import create_llm_for_scope, resolve_model_info
from server.modules.registry import get_registry
from server.agent.state import AgentState
from server.agent.progress import emit_progress, emit_token, emit_usage, get_channel

logger = logging.getLogger("server.agent.nodes.stock")

_IM_SYSTEM_SUFFIX = (
    "\n\n【重要】当前是 IM 通道，无法展示图表和页面。"
    "请用文字详细描述所有数据和分析结果，确保用户不看图表也能完整理解。"
    "对于持仓数据，请列出每只股票的代码、名称、数量、成本价、当前价、盈亏等关键信息。"
    "对于技术分析，请用文字说明均线、RSI等指标的具体数值和含义。"
)


def stock_agent_node(state: AgentState) -> dict:
    """股票分析 Agent - 使用 ReAct 模式调用 tools"""
    registry = get_registry()
    module = registry.get_module("stock")
    if not module:
        return {
            "messages": [AIMessage(content="股票分析模块未启用")],
            "current_module": "stock",
        }

    tools = module.get_tools()
    system_prompt = module.get_system_prompt()
    if get_channel() == "im":
        system_prompt += _IM_SYSTEM_SUFFIX
    scope = "module.stock.agent"
    llm = create_llm_for_scope(scope, temperature=0.3)
    provider, model_name = resolve_model_info(scope)
    llm_with_tools = llm.bind_tools(tools)

    messages = state.get("messages", [])
    full_messages = [SystemMessage(content=system_prompt)] + messages

    ui_commands = list(state.get("ui_commands", []))
    total_input_tokens = 0
    total_output_tokens = 0

    # ReAct loop: let the LLM decide which tools to call
    max_iterations = 5
    for _ in range(max_iterations):
        response = llm_with_tools.invoke(full_messages)
        full_messages.append(response)

        # Accumulate usage from invoke calls
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            total_input_tokens += response.usage_metadata.get('input_tokens', 0)
            total_output_tokens += response.usage_metadata.get('output_tokens', 0)

        if not response.tool_calls:
            break

        # Execute tool calls
        from langchain_core.messages import ToolMessage
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            logger.info(f"调用工具: {tool_name}({tool_args})")
            emit_progress("tool_call", f"正在调用 {tool_name}...")

            tool_fn = next((t for t in tools if t.name == tool_name), None)
            if tool_fn is None:
                result = json.dumps({"error": f"未知工具: {tool_name}"})
            else:
                try:
                    raw_result = tool_fn.invoke(tool_args)
                    if isinstance(raw_result, dict):
                        # Check if tool returned a ui_command
                        if "_ui_command" in raw_result:
                            ui_commands.append(raw_result.pop("_ui_command"))
                        result = json.dumps(raw_result, ensure_ascii=False, default=str)
                    else:
                        result = str(raw_result)
                except Exception as e:
                    logger.error(f"工具调用失败 {tool_name}: {e}")
                    result = json.dumps({"error": str(e)})

            full_messages.append(ToolMessage(
                content=result,
                tool_call_id=tool_call["id"],
            ))

    # Stream the final response
    final_response = full_messages[-1]
    if not isinstance(final_response, AIMessage):
        # Last message is a ToolMessage — stream a new summary call
        emit_progress("generating", "正在生成分析报告...")
    else:
        # Last message is a pre-generated AIMessage — discard it and re-stream
        full_messages.pop()
        emit_progress("generating", "正在生成分析报告...")

    full_content = ""
    stream_usage = None
    for chunk in llm.stream(full_messages):
        if chunk.content:
            emit_token(chunk.content)
            full_content += chunk.content
        if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
            stream_usage = chunk.usage_metadata
    if stream_usage:
        total_input_tokens += stream_usage.get('input_tokens', 0)
        total_output_tokens += stream_usage.get('output_tokens', 0)
    usage = {
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
    } if (total_input_tokens or total_output_tokens) else None
    emit_usage(provider, model_name, usage)
    final_response = AIMessage(content=full_content)

    return {
        "messages": [final_response],
        "current_module": "stock",
        "ui_commands": ui_commands,
    }
