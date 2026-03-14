"""SQLAlchemy ORM 模型"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, Text,
    ForeignKey, UniqueConstraint,
)
from server.db.session import Base


def _utcnow():
    return datetime.now(timezone.utc)


class LLMModel(Base):
    __tablename__ = "llm_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    provider = Column(String(50), nullable=False)  # deepseek/openai/anthropic/google/qwen
    model = Column(String(100), nullable=False)
    api_key = Column(Text, nullable=False, default="")  # 加密存储
    base_url = Column(String(500), nullable=True)
    is_default = Column(Boolean, default=False)
    extra_params = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class ModelAssignment(Base):
    __tablename__ = "model_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(String(200), unique=True, nullable=False)
    model_id = Column(Integer, ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False)
    temperature = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("scope", name="uq_assignment_scope"),
    )


class ModuleConfig(Base):
    __tablename__ = "module_configs"

    module_id = Column(String(100), primary_key=True)
    enabled = Column(Boolean, default=True)
    config_json = Column(Text, default="{}")
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
