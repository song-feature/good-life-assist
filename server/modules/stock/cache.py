"""轻量级 TTL 缓存 — 供 stock 模块内多个子模块共享"""
import time
from threading import Lock

_store: dict[str, tuple[float, object, int]] = {}
_lock = Lock()

DEFAULT_TTL = 120  # seconds


def cache_get(key: str):
    """读取缓存，过期返回 None"""
    with _lock:
        entry = _store.get(key)
        if entry and (time.time() - entry[0]) < entry[2]:
            return entry[1]
    return None


def cache_set(key: str, value: object, ttl: int = DEFAULT_TTL):
    """写入缓存"""
    with _lock:
        _store[key] = (time.time(), value, ttl)


def cache_clear():
    """清空全部缓存"""
    with _lock:
        _store.clear()
