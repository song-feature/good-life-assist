"""交易枚举定义 - 封装富途 API 枚举"""
from futu import (
    TrdEnv, TrdMarket, TrdSide, OrderType, OrderStatus,
    ModifyOrderOp, TimeInForce, SecurityFirm
)

__all__ = [
    'TrdEnv', 'TrdMarket', 'TrdSide', 'OrderType', 'OrderStatus',
    'ModifyOrderOp', 'TimeInForce', 'SecurityFirm',
    'to_trd_env', 'to_trd_market',
]


def to_trd_env(value):
    if isinstance(value, str):
        value = value.upper()
        if value in ("REAL", "真实"):
            return TrdEnv.REAL
        elif value in ("SIMULATE", "SIM", "模拟"):
            return TrdEnv.SIMULATE
    return value if value in (TrdEnv.REAL, TrdEnv.SIMULATE) else TrdEnv.SIMULATE


def to_trd_market(value):
    if isinstance(value, str):
        value = value.upper()
        if value in ("US", "美股"):
            return TrdMarket.US
        elif value in ("HK", "港股"):
            return TrdMarket.HK
    return value if value in (TrdMarket.US, TrdMarket.HK) else TrdMarket.US
