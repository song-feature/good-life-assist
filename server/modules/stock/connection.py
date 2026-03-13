"""连接管理器 - 管理富途交易上下文"""
import threading
import logging
from futu import (
    OpenSecTradeContext, OpenHKTradeContext,
    TrdMarket, TrdEnv, SecurityFirm, RET_OK
)
from .enums import to_trd_env, to_trd_market
from .config import get_futu_host, get_futu_port

logger = logging.getLogger("stock.connection")


class ConnectionManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._contexts = {}
        self._acc_cache = {}
        self._lock = threading.Lock()
        self._initialized = True

    def get_trade_context(self, market="US", env="SIMULATE", host=None, port=None):
        market = to_trd_market(market)
        env = to_trd_env(env)
        host = host or get_futu_host()
        port = port or get_futu_port()

        key = (market, env)

        with self._lock:
            if key in self._contexts:
                ctx = self._contexts[key]
                try:
                    ret, _ = ctx.get_acc_list()
                    if ret == RET_OK:
                        return ctx
                except Exception:
                    pass
                try:
                    ctx.close()
                except Exception:
                    pass
                del self._contexts[key]

            if market == TrdMarket.HK:
                ctx = OpenHKTradeContext(host=host, port=port)
            else:
                ctx = OpenSecTradeContext(
                    filter_trdmarket=market,
                    host=host,
                    port=port,
                    security_firm=SecurityFirm.FUTUSECURITIES
                )

            self._contexts[key] = ctx
            return ctx

    def get_acc_id(self, market="US", env="SIMULATE", sim_acc_type="STOCK"):
        market = to_trd_market(market)
        env = to_trd_env(env)

        key = (market, env, sim_acc_type)
        if key in self._acc_cache:
            return self._acc_cache[key]

        ctx = self.get_trade_context(market, env)
        ret, acc_data = ctx.get_acc_list()

        if ret != RET_OK or acc_data is None or acc_data.empty:
            return 0

        market_str = "US" if market == TrdMarket.US else "HK"
        env_str = str(env)

        for _, row in acc_data.iterrows():
            if row["trd_env"] != env_str:
                continue
            if row.get("acc_status") != "ACTIVE":
                continue
            markets = row.get("trdmarket_auth", [])
            if market_str not in markets:
                continue
            if env == TrdEnv.SIMULATE:
                acc_type = row.get("sim_acc_type", "N/A")
                if acc_type not in (sim_acc_type, "N/A"):
                    continue
            acc_id = row["acc_id"]
            self._acc_cache[key] = acc_id
            return acc_id

        return 0

    def close_all(self):
        with self._lock:
            for ctx in self._contexts.values():
                try:
                    ctx.close()
                except Exception:
                    pass
            self._contexts.clear()
            self._acc_cache.clear()


_connection_manager = None


def get_connection_manager():
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
