"""管理 API - 模块启停、配置和日志"""
from fastapi import APIRouter, Query

from server.modules.registry import get_registry
from server.config import get_settings
from server.core.log_collector import get_log_handler

router = APIRouter(tags=["admin"])


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
    settings = get_settings()
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "base_url": settings.llm_base_url,
        "has_api_key": bool(settings.llm_api_key),
    }


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
