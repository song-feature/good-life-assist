"""Agent 状态定义"""
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    current_module: str | None
    ui_commands: list[dict]
    intent: str | None
