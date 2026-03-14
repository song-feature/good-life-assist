"""数据仓库 - 封装数据库 CRUD"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from server.db.models import LLMModel, ModelAssignment, ModuleConfig
from server.db.crypto import encrypt_api_key, decrypt_api_key

logger = logging.getLogger("server.db.repositories")


# ==================== LLM Model ====================

class LLMModelRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[LLMModel]:
        return self.session.query(LLMModel).order_by(LLMModel.id).all()

    def get_by_id(self, model_id: int) -> LLMModel | None:
        return self.session.get(LLMModel, model_id)

    def get_by_name(self, name: str) -> LLMModel | None:
        return self.session.query(LLMModel).filter(LLMModel.name == name).first()

    def get_default(self) -> LLMModel | None:
        return self.session.query(LLMModel).filter(LLMModel.is_default == True).first()  # noqa: E712

    def create(self, *, name: str, provider: str, model: str, api_key: str,
               base_url: str | None = None, is_default: bool = False,
               extra_params: str | None = None) -> LLMModel:
        # 如果设为默认，取消其他默认
        if is_default:
            self._clear_default()
        obj = LLMModel(
            name=name,
            provider=provider,
            model=model,
            api_key=encrypt_api_key(api_key),
            base_url=base_url or None,
            is_default=is_default,
            extra_params=extra_params,
        )
        self.session.add(obj)
        self.session.commit()
        return obj

    def update(self, model_id: int, **kwargs) -> LLMModel | None:
        obj = self.get_by_id(model_id)
        if not obj:
            return None
        if "api_key" in kwargs and kwargs["api_key"]:
            kwargs["api_key"] = encrypt_api_key(kwargs["api_key"])
        if kwargs.get("is_default"):
            self._clear_default()
        for k, v in kwargs.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        obj.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return obj

    def delete(self, model_id: int) -> bool:
        obj = self.get_by_id(model_id)
        if not obj:
            return False
        self.session.delete(obj)
        self.session.commit()
        return True

    def _clear_default(self):
        self.session.query(LLMModel).filter(
            LLMModel.is_default == True  # noqa: E712
        ).update({"is_default": False})

    @staticmethod
    def to_dict(obj: LLMModel, include_key: bool = False) -> dict:
        d = {
            "id": obj.id,
            "name": obj.name,
            "provider": obj.provider,
            "model": obj.model,
            "base_url": obj.base_url or "",
            "is_default": obj.is_default,
            "extra_params": obj.extra_params,
            "has_api_key": bool(obj.api_key),
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }
        if include_key:
            d["api_key"] = decrypt_api_key(obj.api_key)
        return d


# ==================== Model Assignment ====================

class ModelAssignmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[ModelAssignment]:
        return self.session.query(ModelAssignment).order_by(ModelAssignment.scope).all()

    def get_by_scope(self, scope: str) -> ModelAssignment | None:
        return self.session.query(ModelAssignment).filter(
            ModelAssignment.scope == scope
        ).first()

    def set_assignment(self, scope: str, model_id: int, temperature: float | None = None) -> ModelAssignment:
        obj = self.get_by_scope(scope)
        if obj:
            obj.model_id = model_id
            obj.temperature = temperature
            obj.updated_at = datetime.now(timezone.utc)
        else:
            obj = ModelAssignment(scope=scope, model_id=model_id, temperature=temperature)
            self.session.add(obj)
        self.session.commit()
        return obj

    def delete_by_scope(self, scope: str) -> bool:
        obj = self.get_by_scope(scope)
        if not obj:
            return False
        self.session.delete(obj)
        self.session.commit()
        return True

    @staticmethod
    def to_dict(obj: ModelAssignment) -> dict:
        return {
            "id": obj.id,
            "scope": obj.scope,
            "model_id": obj.model_id,
            "temperature": obj.temperature,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }


# ==================== Module Config ====================

class ModuleConfigRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, module_id: str) -> ModuleConfig | None:
        return self.session.get(ModuleConfig, module_id)

    def get_all(self) -> list[ModuleConfig]:
        return self.session.query(ModuleConfig).order_by(ModuleConfig.module_id).all()

    def upsert(self, module_id: str, enabled: bool = True, config: dict | None = None) -> ModuleConfig:
        obj = self.get(module_id)
        if obj:
            obj.enabled = enabled
            if config is not None:
                obj.config_json = json.dumps(config, ensure_ascii=False)
            obj.updated_at = datetime.now(timezone.utc)
        else:
            obj = ModuleConfig(
                module_id=module_id,
                enabled=enabled,
                config_json=json.dumps(config or {}, ensure_ascii=False),
            )
            self.session.add(obj)
        self.session.commit()
        return obj

    def update_enabled(self, module_id: str, enabled: bool) -> ModuleConfig | None:
        obj = self.get(module_id)
        if not obj:
            return None
        obj.enabled = enabled
        obj.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return obj

    def update_config(self, module_id: str, config: dict) -> ModuleConfig | None:
        obj = self.get(module_id)
        if not obj:
            return None
        obj.config_json = json.dumps(config, ensure_ascii=False)
        obj.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return obj

    @staticmethod
    def to_dict(obj: ModuleConfig) -> dict:
        return {
            "module_id": obj.module_id,
            "enabled": obj.enabled,
            "config": json.loads(obj.config_json) if obj.config_json else {},
        }
