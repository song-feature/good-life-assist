"""管理 API - 模块启停、配置、LLM模型管理和日志"""
from fastapi import APIRouter, Query
from pydantic import BaseModel

from server.modules.registry import get_registry
from server.config import get_settings
from server.core.log_collector import get_log_handler
from server.db.service import get_llm_service

router = APIRouter(tags=["admin"])


# ==================== 模块管理 ====================

@router.get("/modules")
async def list_modules():
    registry = get_registry()
    return registry.get_all_module_info()


@router.put("/modules/{module_id}/toggle")
async def toggle_module(module_id: str, enabled: bool):
    registry = get_registry()
    if enabled:
        registry.enable_module(module_id)
    else:
        registry.disable_module(module_id)
    return {"module_id": module_id, "enabled": enabled}


@router.get("/modules/{module_id}/config")
async def get_module_config(module_id: str):
    registry = get_registry()
    return {
        "module_id": module_id,
        "config": registry.get_module_config(module_id),
    }


@router.put("/modules/{module_id}/config")
async def update_module_config(module_id: str, config: dict):
    registry = get_registry()
    registry.update_module_config(module_id, config)
    return {"module_id": module_id, "config": config}


@router.get("/llm/config")
async def get_llm_config():
    """兼容旧接口 - 返回当前生效的全局 LLM 配置"""
    svc = get_llm_service()
    resolved = svc.resolve_model_for_scope("global")
    return {
        "provider": resolved.provider,
        "model": resolved.model,
        "base_url": resolved.base_url or "",
        "has_api_key": bool(resolved.api_key),
        "source": resolved.source,
    }


# ==================== LLM 模型管理 ====================

class LLMModelCreate(BaseModel):
    name: str
    provider: str
    model: str
    api_key: str = ""
    base_url: str | None = None
    is_default: bool = False
    extra_params: str | None = None


class LLMModelUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    is_default: bool | None = None
    extra_params: str | None = None


class AssignmentBody(BaseModel):
    scope: str
    model_id: int
    temperature: float | None = None


@router.get("/llm/models")
async def list_llm_models():
    svc = get_llm_service()
    return svc.get_all_models()


@router.post("/llm/models")
async def create_llm_model(body: LLMModelCreate):
    svc = get_llm_service()
    return svc.create_model(**body.model_dump())


@router.put("/llm/models/{model_id}")
async def update_llm_model(model_id: int, body: LLMModelUpdate):
    svc = get_llm_service()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = svc.update_model(model_id, **updates)
    if not result:
        return {"error": "模型不存在"}
    return result


@router.delete("/llm/models/{model_id}")
async def delete_llm_model(model_id: int):
    svc = get_llm_service()
    ok = svc.delete_model(model_id)
    return {"success": ok}


# ==================== LLM Scope 分配 ====================

@router.get("/llm/assignments")
async def list_assignments():
    svc = get_llm_service()
    return svc.get_all_assignments()


@router.put("/llm/assignments")
async def set_assignment(body: AssignmentBody):
    svc = get_llm_service()
    return svc.set_assignment(body.scope, body.model_id, body.temperature)


@router.delete("/llm/assignments/{scope:path}")
async def delete_assignment(scope: str):
    svc = get_llm_service()
    ok = svc.delete_assignment(scope)
    return {"success": ok}


@router.get("/llm/scopes")
async def list_scopes():
    svc = get_llm_service()
    return svc.get_available_scopes()


# ==================== 日志 API ====================

@router.get("/logs")
async def get_logs(
    level: str | None = Query(default=None, description="按级别过滤: WARNING, ERROR, CRITICAL"),
    logger_name: str | None = Query(default=None, alias="logger", description="按 logger 名称过滤"),
    keyword: str | None = Query(default=None, description="按关键词搜索"),
    limit: int = Query(default=200, ge=1, le=500, description="返回条数"),
):
    handler = get_log_handler()
    logs = handler.get_logs(level=level, logger_name=logger_name, keyword=keyword, limit=limit)
    return {"total": len(logs), "logs": logs}


@router.delete("/logs")
async def clear_logs():
    handler = get_log_handler()
    handler.clear()
    return {"message": "日志已清空"}
