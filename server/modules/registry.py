"""模块注册中心 - 管理所有可插拔模块"""
import json
import logging
from pathlib import Path

from server.config import get_settings
from server.modules.base import BaseModule

logger = logging.getLogger("server.registry")


def _get_config_service():
    """延迟导入避免循环依赖"""
    from server.db.service import get_module_config_service
    return get_module_config_service()


class ModuleRegistry:
    def __init__(self):
        self.modules: dict[str, BaseModule] = {}
        self._config: dict[str, dict] = {}
        self._db_ready = False

    def _ensure_db(self):
        """尝试从数据库加载配置，失败时回退到 JSON"""
        if self._db_ready:
            return
        try:
            svc = _get_config_service()
            all_configs = svc.get_all()
            for item in all_configs:
                self._config[item["module_id"]] = {
                    "enabled": item.get("enabled", True),
                    "config": item.get("config", {}),
                }
            self._db_ready = True
        except Exception:
            # 数据库尚未初始化，回退 JSON
            self._load_config_from_json()

    def _load_config_from_json(self):
        settings = get_settings()
        path = Path(settings.modules_config_path)
        if path.exists():
            self._config = json.loads(path.read_text(encoding="utf-8"))

    def _save_to_db(self, module_id: str):
        """持久化单个模块配置到数据库"""
        try:
            svc = _get_config_service()
            cfg = self._config.get(module_id, {})
            svc.upsert(
                module_id,
                enabled=cfg.get("enabled", True),
                config=cfg.get("config", {}),
            )
        except Exception as e:
            logger.warning(f"保存模块配置到数据库失败 ({module_id}): {e}")

    def register(self, module: BaseModule):
        self.modules[module.module_id] = module
        self._ensure_db()
        if module.module_id not in self._config:
            self._config[module.module_id] = {
                "enabled": True,
                "config": dict(module.default_config),
            }
            self._save_to_db(module.module_id)
        else:
            # 合并新增的 default_config 字段到已保存的配置中
            saved = self._config[module.module_id].get("config", {})
            merged = {**module.default_config, **saved}
            if merged != saved:
                self._config[module.module_id]["config"] = merged
                self._save_to_db(module.module_id)
        logger.info(f"模块已注册: {module.module_id} ({module.display_name})")

    def discover_modules(self):
        from server.modules.stock.module import StockModule
        self.register(StockModule())

    def get_enabled_modules(self) -> list[BaseModule]:
        self._ensure_db()
        return [
            m for mid, m in self.modules.items()
            if self._config.get(mid, {}).get("enabled", True)
        ]

    def get_module(self, module_id: str) -> BaseModule | None:
        return self.modules.get(module_id)

    def is_enabled(self, module_id: str) -> bool:
        self._ensure_db()
        return self._config.get(module_id, {}).get("enabled", True)

    def enable_module(self, module_id: str):
        self._ensure_db()
        if module_id in self._config:
            self._config[module_id]["enabled"] = True
            self._save_to_db(module_id)
            module = self.modules.get(module_id)
            if module:
                module.on_enable()

    def disable_module(self, module_id: str):
        self._ensure_db()
        if module_id in self._config:
            self._config[module_id]["enabled"] = False
            self._save_to_db(module_id)
            module = self.modules.get(module_id)
            if module:
                module.on_disable()

    def get_module_config(self, module_id: str) -> dict:
        self._ensure_db()
        saved = self._config.get(module_id, {}).get("config", {})
        module = self.modules.get(module_id)
        if module and hasattr(module, "default_config"):
            return {**module.default_config, **saved}
        return saved

    def update_module_config(self, module_id: str, config: dict):
        self._ensure_db()
        if module_id not in self._config:
            self._config[module_id] = {"enabled": True, "config": {}}
        self._config[module_id]["config"] = config
        self._save_to_db(module_id)

    def get_all_module_info(self) -> list[dict]:
        self._ensure_db()
        result = []
        for mid, module in self.modules.items():
            cfg = self._config.get(mid, {})
            saved_config = cfg.get("config", {})
            merged_config = {**module.default_config, **saved_config} if module.default_config else saved_config
            result.append({
                "module_id": mid,
                "display_name": module.display_name,
                "description": module.description,
                "enabled": cfg.get("enabled", True),
                "config": merged_config,
            })
        return result


_registry: ModuleRegistry | None = None


def get_registry() -> ModuleRegistry:
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry
