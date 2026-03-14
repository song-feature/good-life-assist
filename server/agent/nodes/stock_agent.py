"""股票分析子 Agent 节点"""
import json
import logging
from langchain_core.messages import AIMessage, SystemMessage

from server.core.llm import create_llm_for_scope
from server.modules.registry import get_registry
from server.agent.state import AgentState
from server.agent.progress import emit_progress

logger = logging.getLogger("server.agent.nodes.stock")


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
    llm = create_llm_for_scope("module.stock.agent", temperature=0.3)
    llm_with_tools = llm.bind_tools(tools)

    messages = state.get("messages", [])
    full_messages = [SystemMessage(content=system_prompt)] + messages

    ui_commands = list(state.get("ui_commands", []))

    # ReAct loop: let the LLM decide which tools to call
    max_iterations = 5
    for _ in range(max_iterations):
        response = llm_with_tools.invoke(full_messages)
        full_messages.append(response)

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

    # The last AI message (after all tool calls) is the final response
    final_response = full_messages[-1]
    if not isinstance(final_response, AIMessage):
        # If the last message is a ToolMessage, invoke LLM once more for summary
        emit_progress("generating", "正在生成分析报告...")
        final_response = llm.invoke(full_messages)

    return {
        "messages": [final_response],
        "current_module": "stock",
        "ui_commands": ui_commands,
    }
