"""模块注册中心 - 管理所有可插拔模块"""
import json
import logging
from pathlib import Path

from server.config import get_settings
from server.modules.base import BaseModule

logger = logging.getLogger("server.registry")


class ModuleRegistry:
    def __init__(self):
        self.modules: dict[str, BaseModule] = {}
        self._config: dict[str, dict] = {}
        self._load_config()

    def _config_path(self) -> Path:
        settings = get_settings()
        return Path(settings.modules_config_path)

    def _load_config(self):
        path = self._config_path()
        if path.exists():
            self._config = json.loads(path.read_text(encoding="utf-8"))
        else:
            self._config = {}

    def _save_config(self):
        path = self._config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._config, ensure_ascii=False, indent=2), encoding="utf-8")

    def register(self, module: BaseModule):
        self.modules[module.module_id] = module
        if module.module_id not in self._config:
            self._config[module.module_id] = {
                "enabled": True,
                "config": dict(module.default_config),
            }
            self._save_config()
        logger.info(f"模块已注册: {module.module_id} ({module.display_name})")

    def discover_modules(self):
        from server.modules.stock.module import StockModule
        self.register(StockModule())

    def get_enabled_modules(self) -> list[BaseModule]:
        return [
            m for mid, m in self.modules.items()
            if self._config.get(mid, {}).get("enabled", True)
        ]

    def get_module(self, module_id: str) -> BaseModule | None:
        return self.modules.get(module_id)

    def is_enabled(self, module_id: str) -> bool:
        return self._config.get(module_id, {}).get("enabled", True)

    def enable_module(self, module_id: str):
        if module_id in self._config:
            self._config[module_id]["enabled"] = True
            self._save_config()
            module = self.modules.get(module_id)
            if module:
                module.on_enable()

    def disable_module(self, module_id: str):
        if module_id in self._config:
            self._config[module_id]["enabled"] = False
            self._save_config()
            module = self.modules.get(module_id)
            if module:
                module.on_disable()

    def get_module_config(self, module_id: str) -> dict:
        return self._config.get(module_id, {}).get("config", {})

    def update_module_config(self, module_id: str, config: dict):
        if module_id not in self._config:
            self._config[module_id] = {"enabled": True, "config": {}}
        self._config[module_id]["config"] = config
        self._save_config()

    def get_all_module_info(self) -> list[dict]:
        result = []
        for mid, module in self.modules.items():
            cfg = self._config.get(mid, {})
            result.append({
                "module_id": mid,
                "display_name": module.display_name,
                "description": module.description,
                "enabled": cfg.get("enabled", True),
                "config": cfg.get("config", {}),
            })
        return result


_registry: ModuleRegistry | None = None


def get_registry() -> ModuleRegistry:
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry
