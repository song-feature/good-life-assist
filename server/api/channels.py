"""通道管理 API"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.channels.registry import get_channel_registry
from server.db.service import get_channel_config_service

logger = logging.getLogger("server.api.channels")
router = APIRouter(tags=["channels"])


class ToggleRequest(BaseModel):
    enabled: bool


class ConfigUpdateRequest(BaseModel):
    config: dict


class TestRequest(BaseModel):
    config: dict


@router.get("/channels")
async def list_channels():
    """获取所有通道列表"""
    registry = get_channel_registry()
    return registry.get_all_channel_info()


@router.get("/channels/{channel_id}/config")
async def get_channel_config(channel_id: str):
    """获取通道配置（含 schema）"""
    registry = get_channel_registry()
    channel = registry.channels.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail=f"通道 {channel_id} 不存在")

    svc = get_channel_config_service()
    db_all = {c["channel_id"]: c for c in svc.get_all()}
    db_cfg = db_all.get(channel_id, {})

    return {
        "channel_id": channel_id,
        "display_name": channel.display_name,
        "description": channel.description,
        "channel_type": channel.channel_type,
        "config_schema": channel.config_schema,
        "config": db_cfg.get("config", {}),
        "enabled": db_cfg.get("enabled", False),
        "status": db_cfg.get("status", "stopped"),
        "status_message": db_cfg.get("status_message", ""),
    }


@router.put("/channels/{channel_id}/config")
async def update_channel_config(channel_id: str, body: ConfigUpdateRequest):
    """更新通道配置"""
    registry = get_channel_registry()
    if channel_id not in registry.channels:
        raise HTTPException(status_code=404, detail=f"通道 {channel_id} 不存在")

    svc = get_channel_config_service()

    # 合并配置：保留已有的 secret 字段（如果前端传来脱敏值则不覆盖）
    existing = svc.get_config(channel_id) or {}
    new_config = dict(body.config)
    for key, val in new_config.items():
        if val == "••••••••" and key in existing:
            new_config[key] = existing[key]

    svc.update_config(channel_id, new_config)
    return {"ok": True}


@router.put("/channels/{channel_id}/toggle")
async def toggle_channel(channel_id: str, body: ToggleRequest):
    """启用/禁用通道"""
    registry = get_channel_registry()
    if channel_id not in registry.channels:
        raise HTTPException(status_code=404, detail=f"通道 {channel_id} 不存在")

    svc = get_channel_config_service()
    svc.update_enabled(channel_id, body.enabled)

    if body.enabled:
        ok, msg = registry.start_channel(channel_id)
        return {"ok": ok, "message": msg}
    else:
        ok, msg = registry.stop_channel(channel_id)
        return {"ok": ok, "message": msg}


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: str, body: TestRequest):
    """测试通道连接"""
    registry = get_channel_registry()
    channel = registry.channels.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail=f"通道 {channel_id} 不存在")

    # 合并脱敏字段
    svc = get_channel_config_service()
    existing = svc.get_config(channel_id) or {}
    test_config = dict(body.config)
    for key, val in test_config.items():
        if val == "••••••••" and key in existing:
            test_config[key] = existing[key]

    success, message = channel.test_connection(test_config)
    return {"success": success, "message": message}
