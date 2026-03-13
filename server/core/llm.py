"""LLM 工厂 - 按配置创建 LLM 实例"""
from langchain_openai import ChatOpenAI
from server.config import get_settings


def create_llm(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.7,
) -> ChatOpenAI:
    settings = get_settings()
    provider = provider or settings.llm_provider
    model = model or settings.llm_model
    api_key = api_key or settings.llm_api_key
    base_url = base_url or settings.llm_base_url

    if provider == "deepseek":
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )
    else:
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url if base_url != "https://api.deepseek.com" else None,
            temperature=temperature,
        )
