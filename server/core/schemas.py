"""共享 Pydantic 数据模型"""
from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class UICommand(BaseModel):
    module: str
    action: str
    data: dict = Field(default_factory=dict)


class ModuleInfo(BaseModel):
    module_id: str
    display_name: str
    description: str
    enabled: bool
    config: dict = Field(default_factory=dict)
