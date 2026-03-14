"""业务逻辑服务层"""
import json
import logging
from dataclasses import dataclass

from server.db.session import get_session
from server.db.repositories import (
    LLMModelRepository, ModelAssignmentRepository, ModuleConfigRepository,
)
from server.db.crypto import decrypt_api_key
from server.config import get_settings

logger = logging.getLogger("server.db.service")


# ==================== LLM Service ====================

@dataclass
class ResolvedLLMConfig:
    provider: str
    model: str
    api_key: str
    base_url: str | None
    temperature: float | None
    extra_params: dict | None
    source: str  # 说明从哪里解析到的, e.g. "scope:agent.router", "global", "env_fallback"


class LLMService:
    """LLM 模型管理和 scope 解析"""

    # 所有可配置的 scope 定义
    AVAILABLE_SCOPES = [
        {"scope": "global", "label": "全局默认", "description": "所有未指定模型的地方使用"},
        {"scope": "agent.router", "label": "意图路由", "description": "Agent 意图分类使用的模型"},
        {"scope": "agent.chat", "label": "通用对话", "description": "通用聊天回复使用的模型"},
        {"scope": "module.stock", "label": "股票模块默认", "description": "股票模块的默认模型"},
        {"scope": "module.stock.agent", "label": "股票分析 Agent", "description": "股票分析 ReAct Agent"},
        {"scope": "module.stock.options_wall", "label": "期权墙分析", "description": "期权墙 AI 摘要"},
        {"scope": "module.stock.recommendations", "label": "投资建议", "description": "AI 投资建议生成"},
    ]

    def resolve_model_for_scope(self, scope: str) -> ResolvedLLMConfig:
        """按优先级解析模型: 精确scope -> 上级scope -> global -> .env 回退"""
        session = get_session()
        try:
            assignment_repo = ModelAssignmentRepository(session)
            model_repo = LLMModelRepository(session)

            # 1. 逐级向上查找 scope 分配
            scopes_to_try = self._build_scope_chain(scope)
            for s in scopes_to_try:
                assignment = assignment_repo.get_by_scope(s)
                if assignment:
                    llm_model = model_repo.get_by_id(assignment.model_id)
                    if llm_model:
                        extra = json.loads(llm_model.extra_params) if llm_model.extra_params else None
                        return ResolvedLLMConfig(
                            provider=llm_model.provider,
                            model=llm_model.model,
                            api_key=decrypt_api_key(llm_model.api_key),
                            base_url=llm_model.base_url,
                            temperature=assignment.temperature,
                            extra_params=extra,
                            source=f"scope:{s}",
                        )

            # 2. 查找 is_default 模型
            default_model = model_repo.get_default()
            if default_model:
                extra = json.loads(default_model.extra_params) if default_model.extra_params else None
                return ResolvedLLMConfig(
                    provider=default_model.provider,
                    model=default_model.model,
                    api_key=decrypt_api_key(default_model.api_key),
                    base_url=default_model.base_url,
                    temperature=None,
                    extra_params=extra,
                    source="default_model",
                )

            # 3. .env 回退
            return self._env_fallback()
        finally:
            session.close()

    @staticmethod
    def _build_scope_chain(scope: str) -> list[str]:
        """构建 scope 查找链, e.g. "module.stock.recommendations" -> ["module.stock.recommendations", "module.stock", "global"]"""
        parts = scope.split(".")
        chain = []
        for i in range(len(parts), 0, -1):
            chain.append(".".join(parts[:i]))
        if "global" not in chain:
            chain.append("global")
        return chain

    @staticmethod
    def _env_fallback() -> ResolvedLLMConfig:
        settings = get_settings()
        return ResolvedLLMConfig(
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=None,
            extra_params=None,
            source="env_fallback",
        )

    # --- CRUD ---

    def get_all_models(self) -> list[dict]:
        session = get_session()
        try:
            repo = LLMModelRepository(session)
            return [repo.to_dict(m) for m in repo.get_all()]
        finally:
            session.close()

    def create_model(self, **kwargs) -> dict:
        session = get_session()
        try:
            repo = LLMModelRepository(session)
            obj = repo.create(**kwargs)
            return repo.to_dict(obj)
        finally:
            session.close()

    def update_model(self, model_id: int, **kwargs) -> dict | None:
        session = get_session()
        try:
            repo = LLMModelRepository(session)
            obj = repo.update(model_id, **kwargs)
            return repo.to_dict(obj) if obj else None
        finally:
            session.close()

    def delete_model(self, model_id: int) -> bool:
        session = get_session()
        try:
            repo = LLMModelRepository(session)
            return repo.delete(model_id)
        finally:
            session.close()

    def get_all_assignments(self) -> list[dict]:
        session = get_session()
        try:
            repo = ModelAssignmentRepository(session)
            return [repo.to_dict(a) for a in repo.get_all()]
        finally:
            session.close()

    def set_assignment(self, scope: str, model_id: int, temperature: float | None = None) -> dict:
        session = get_session()
        try:
            repo = ModelAssignmentRepository(session)
            obj = repo.set_assignment(scope, model_id, temperature)
            return repo.to_dict(obj)
        finally:
            session.close()

    def delete_assignment(self, scope: str) -> bool:
        session = get_session()
        try:
            repo = ModelAssignmentRepository(session)
            return repo.delete_by_scope(scope)
        finally:
            session.close()

    def get_available_scopes(self) -> list[dict]:
        return self.AVAILABLE_SCOPES


# ==================== Module Config Service ====================

class ModuleConfigService:
    """模块配置服务"""

    def get_config(self, module_id: str) -> dict | None:
        session = get_session()
        try:
            repo = ModuleConfigRepository(session)
            obj = repo.get(module_id)
            if obj:
                return json.loads(obj.config_json) if obj.config_json else {}
            return None
        finally:
            session.close()

    def is_enabled(self, module_id: str) -> bool | None:
        session = get_session()
        try:
            repo = ModuleConfigRepository(session)
            obj = repo.get(module_id)
            if obj:
                return obj.enabled
            return None
        finally:
            session.close()

    def upsert(self, module_id: str, enabled: bool = True, config: dict | None = None):
        session = get_session()
        try:
            repo = ModuleConfigRepository(session)
            repo.upsert(module_id, enabled, config)
        finally:
            session.close()

    def update_enabled(self, module_id: str, enabled: bool):
        session = get_session()
        try:
            repo = ModuleConfigRepository(session)
            repo.update_enabled(module_id, enabled)
        finally:
            session.close()

    def update_config(self, module_id: str, config: dict):
        session = get_session()
        try:
            repo = ModuleConfigRepository(session)
            repo.update_config(module_id, config)
        finally:
            session.close()

    def get_all(self) -> list[dict]:
        session = get_session()
        try:
            repo = ModuleConfigRepository(session)
            return [repo.to_dict(c) for c in repo.get_all()]
        finally:
            session.close()


# 单例
_llm_service: LLMService | None = None
_module_config_service: ModuleConfigService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def get_module_config_service() -> ModuleConfigService:
    global _module_config_service
    if _module_config_service is None:
        _module_config_service = ModuleConfigService()
    return _module_config_service
