"""通道注册中心 - 管理通道生命周期"""
import logging
import threading

from server.channels.base import BaseChannel
from server.db.service import get_channel_config_service

logger = logging.getLogger("server.channels.registry")


class ChannelRegistry:
    def __init__(self):
        self.channels: dict[str, BaseChannel] = {}
        self._threads: dict[str, threading.Thread] = {}

    def register(self, channel: BaseChannel):
        """注册通道实例"""
        self.channels[channel.channel_id] = channel
        logger.info(f"通道已注册: {channel.channel_id} ({channel.display_name})")

        # 确保 DB 中有对应记录
        svc = get_channel_config_service()
        existing = svc.get_config(channel.channel_id)
        if existing is None:
            svc.upsert(channel.channel_id, channel.channel_type, enabled=False, config={})

    def discover_channels(self):
        """自动发现并注册所有内置通道"""
        from server.channels.feishu.channel import FeishuChannel
        self.register(FeishuChannel())

    def start_channel(self, channel_id: str) -> tuple[bool, str]:
        """启动单个通道"""
        channel = self.channels.get(channel_id)
        if not channel:
            return False, f"通道 {channel_id} 未注册"

        if channel.is_running:
            return True, "通道已在运行中"

        # 加载配置
        svc = get_channel_config_service()
        raw = svc.get_raw(channel_id)
        if raw:
            channel.configure(raw.get("config", {}))

        def _run():
            try:
                svc.update_status(channel_id, "running", "")
                channel.start()
            except Exception as e:
                logger.error(f"通道 {channel_id} 运行异常: {e}", exc_info=True)
                svc.update_status(channel_id, "error", str(e))

        t = threading.Thread(target=_run, name=f"channel-{channel_id}", daemon=True)
        t.start()
        self._threads[channel_id] = t
        return True, "通道启动中"

    def stop_channel(self, channel_id: str) -> tuple[bool, str]:
        """停止单个通道"""
        channel = self.channels.get(channel_id)
        if not channel:
            return False, f"通道 {channel_id} 未注册"

        try:
            channel.stop()
            svc = get_channel_config_service()
            svc.update_status(channel_id, "stopped", "")
            self._threads.pop(channel_id, None)
            return True, "通道已停止"
        except Exception as e:
            logger.error(f"停止通道 {channel_id} 失败: {e}")
            return False, str(e)

    def start_enabled_channels(self):
        """启动所有已启用的通道"""
        svc = get_channel_config_service()
        for channel_id, channel in self.channels.items():
            if svc.is_enabled(channel_id):
                ok, msg = self.start_channel(channel_id)
                if ok:
                    logger.info(f"通道 {channel_id} 启动成功")
                else:
                    logger.warning(f"通道 {channel_id} 启动失败: {msg}")

    def stop_all_channels(self):
        """停止所有运行中的通道"""
        for channel_id in list(self.channels.keys()):
            channel = self.channels[channel_id]
            if channel.is_running:
                self.stop_channel(channel_id)

    def get_all_channel_info(self) -> list[dict]:
        """获取所有通道信息（合并注册信息和 DB 状态）"""
        svc = get_channel_config_service()
        db_configs = {c["channel_id"]: c for c in svc.get_all()}
        result = []
        for cid, channel in self.channels.items():
            db_cfg = db_configs.get(cid, {})
            result.append({
                "channel_id": cid,
                "channel_type": channel.channel_type,
                "display_name": channel.display_name,
                "description": channel.description,
                "enabled": db_cfg.get("enabled", False),
                "status": db_cfg.get("status", "stopped"),
                "status_message": db_cfg.get("status_message", ""),
                "config": db_cfg.get("config", {}),
                "config_schema": channel.config_schema,
                "is_running": channel.is_running,
            })
        return result


_registry: ChannelRegistry | None = None


def get_channel_registry() -> ChannelRegistry:
    global _registry
    if _registry is None:
        _registry = ChannelRegistry()
    return _registry
