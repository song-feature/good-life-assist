"""股票模块配置"""
import os
from server.modules.registry import get_registry


def get_stock_config() -> dict:
    """获取股票模块配置，优先从 registry 读，兜底用环境变量"""
    try:
        registry = get_registry()
        cfg = registry.get_module_config("stock")
        if cfg:
            return cfg
    except Exception:
        pass

    return {
        "futu_host": os.getenv("FUTU_HOST", "127.0.0.1"),
        "futu_port": int(os.getenv("FUTU_TRADE_PORT", "11111")),
        "market": os.getenv("DEFAULT_TRD_MARKET", "US"),
        "env": os.getenv("DEFAULT_TRD_ENV", "SIMULATE"),
    }


# Convenience accessors
def get_futu_host() -> str:
    return get_stock_config().get("futu_host", "127.0.0.1")


def get_futu_port() -> int:
    return int(get_stock_config().get("futu_port", 11111))


def get_default_market() -> str:
    return get_stock_config().get("market", "US")


def get_default_env() -> str:
    return get_stock_config().get("env", "SIMULATE")
