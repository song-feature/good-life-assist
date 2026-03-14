"""数据迁移 - JSON 配置 -> SQLite"""
import json
import logging
from pathlib import Path

from server.config import get_settings
from server.db.session import get_session
from server.db.repositories import LLMModelRepository, ModuleConfigRepository

logger = logging.getLogger("server.db.migration")


def run_migration():
    """启动时自动迁移：JSON -> SQLite（仅在数据库为空时执行）"""
    _migrate_llm_from_env()
    _migrate_modules_from_json()


def _migrate_llm_from_env():
    """将 .env 中的 LLM 配置作为默认模型插入"""
    session = get_session()
    try:
        repo = LLMModelRepository(session)
        if repo.get_all():
            return  # 已有模型，跳过

        settings = get_settings()
        if not settings.llm_api_key:
            logger.info("未检测到 .env LLM 配置，跳过 LLM 迁移")
            return

        repo.create(
            name=f"{settings.llm_provider}-default",
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
            is_default=True,
        )
        logger.info(f"已从 .env 迁移 LLM 配置: {settings.llm_provider}/{settings.llm_model}")
    finally:
        session.close()


def _migrate_modules_from_json():
    """将 modules_config.json 迁移到 SQLite"""
    session = get_session()
    try:
        repo = ModuleConfigRepository(session)
        if repo.get_all():
            return  # 已有配置，跳过

        settings = get_settings()
        json_path = Path(settings.modules_config_path)
        if not json_path.exists():
            logger.info("未检测到 modules_config.json，跳过模块配置迁移")
            return

        data = json.loads(json_path.read_text(encoding="utf-8"))
        for module_id, module_data in data.items():
            enabled = module_data.get("enabled", True)
            config = module_data.get("config", {})
            repo.upsert(module_id, enabled=enabled, config=config)
            logger.info(f"已迁移模块配置: {module_id}")

        logger.info(f"模块配置迁移完成，共 {len(data)} 个模块")
    finally:
        session.close()
