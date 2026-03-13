"""交易模块工具函数"""
import math
import logging

logger = logging.getLogger("stock.utils")


def safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def safe_int(val, default=0):
    f = safe_float(val, float(default))
    return int(f)
