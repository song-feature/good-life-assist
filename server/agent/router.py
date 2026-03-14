"""意图分类路由节点"""
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from server.core.llm import create_llm_for_scope
from server.modules.registry import get_registry
from server.agent.state import AgentState
from server.agent.progress import emit_progress

logger = logging.getLogger("server.agent.router")

ROUTER_PROMPT = """你是一个意图分类器。根据用户的最新消息，判断用户想使用哪个功能模块。

可用模块列表:
{modules_desc}

规则：
1. 只回复模块的 ID（如 "stock"），不要回复其他内容
2. 如果用户意图不属于任何模块，回复 "general"
3. 如果用户的消息是对之前话题的延续，且当前模块是 "{current_module}"，倾向于保持当前模块

只回复模块 ID，不要有任何解释。"""


def router_node(state: AgentState) -> dict:
    registry = get_registry()
    enabled = registry.get_enabled_modules()

    if not enabled:
        return {"intent": "general"}

    modules_desc = "\n".join(
        f"- {m.module_id}: {m.description}" for m in enabled
    )

    current = state.get("current_module") or "none"
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "general"}

    last_msg = messages[-1].content if messages else ""

    llm = create_llm_for_scope("agent.router", temperature=0)
    prompt = ROUTER_PROMPT.format(modules_desc=modules_desc, current_module=current)

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=last_msg),
    ])

    intent = response.content.strip().lower().strip('"').strip("'")
    valid_ids = {m.module_id for m in enabled} | {"general"}
    if intent not in valid_ids:
        intent = "general"

    module_names = {m.module_id: m.display_name for m in enabled}
    display = module_names.get(intent, "通用对话")
    emit_progress("routed", f"路由到{display}模块")

    logger.info(f"路由意图: '{last_msg[:30]}...' -> {intent}")
    return {"intent": intent}
