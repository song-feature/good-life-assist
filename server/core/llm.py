"""LLM 工厂 - 支持多 Provider 和 scope 解析"""
import logging
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from server.config import get_settings

logger = logging.getLogger("server.core.llm")

# OpenAI 兼容的 provider 列表
_OPENAI_COMPATIBLE = {"deepseek", "openai", "qwen"}


def _create_by_provider(
    provider: str,
    model: str,
    api_key: str,
    base_url: str | None,
    temperature: float,
) -> BaseChatModel:
    """根据 provider 创建对应 LangChain Chat Model"""

    if provider in _OPENAI_COMPATIBLE:
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url or None,
            temperature=temperature,
            stream_usage=True,
        )

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("请安装 langchain-anthropic: pip install langchain-anthropic")
        return ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=4096,
        )

    if provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("请安装 langchain-google-genai: pip install langchain-google-genai")
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
        )

    # 未知 provider，尝试 OpenAI 兼容
    logger.warning(f"未知 provider '{provider}'，尝试 OpenAI 兼容模式")
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url or None,
        temperature=temperature,
    )


def resolve_model_info(scope: str) -> tuple[str, str]:
    """返回 (provider, model) 用于展示"""
    from server.db.service import get_llm_service
    service = get_llm_service()
    resolved = service.resolve_model_for_scope(scope)
    return resolved.provider, resolved.model


def create_llm_for_scope(
    scope: str,
    temperature: float | None = None,
    **overrides,
) -> BaseChatModel:
    """通过 scope 解析链创建 LLM 实例"""
    from server.db.service import get_llm_service

    service = get_llm_service()
    resolved = service.resolve_model_for_scope(scope)

    final_temp = temperature if temperature is not None else (resolved.temperature or 0.7)

    logger.debug(f"LLM scope={scope} -> provider={resolved.provider}, model={resolved.model}, source={resolved.source}")

    return _create_by_provider(
        provider=overrides.get("provider", resolved.provider),
        model=overrides.get("model", resolved.model),
        api_key=overrides.get("api_key", resolved.api_key),
        base_url=overrides.get("base_url", resolved.base_url),
        temperature=final_temp,
    )


def create_llm(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.7,
) -> BaseChatModel:
    """兼容入口 - 无显式参数时走 scope 解析"""
    if any([provider, model, api_key, base_url]):
        # 有显式参数，直接构造
        settings = get_settings()
        return _create_by_provider(
            provider=provider or settings.llm_provider,
            model=model or settings.llm_model,
            api_key=api_key or settings.llm_api_key,
            base_url=base_url or settings.llm_base_url,
            temperature=temperature,
        )
    # 无显式参数，走 scope 解析
    return create_llm_for_scope("global", temperature=temperature)

