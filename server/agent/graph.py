"""LangGraph 图定义 - 主 Agent 系统"""
import logging
from langchain_core.messages import AIMessage

from langgraph.graph import StateGraph, START, END

from server.agent.state import AgentState
from server.agent.router import router_node
from server.agent.nodes.stock_agent import stock_agent_node
from server.core.llm import create_llm

logger = logging.getLogger("server.agent.graph")


def chat_agent_node(state: AgentState) -> dict:
    """通用聊天节点 - 直接调用 LLM"""
    llm = create_llm()
    messages = state.get("messages", [])
    response = llm.invoke(messages)
    return {
        "messages": [response],
        "current_module": None,
    }


def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "general")
    if intent == "stock":
        return "stock_agent"
    return "chat_agent"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("stock_agent", stock_agent_node)
    graph.add_node("chat_agent", chat_agent_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", route_by_intent, {
        "stock_agent": "stock_agent",
        "chat_agent": "chat_agent",
    })
    graph.add_edge("stock_agent", END)
    graph.add_edge("chat_agent", END)

    return graph.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
