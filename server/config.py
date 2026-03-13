"""全局配置 - 从 .env 加载"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "deepseek"
    llm_model: str = "deepseek-chat"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"

    # Server
    server_port: int = 8000

    # Futu OpenD
    futu_host: str = "127.0.0.1"
    futu_trade_port: int = 11111
    default_trd_env: str = "SIMULATE"
    default_trd_market: str = "US"

    # Paths
    modules_config_path: str = "data/modules_config.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
