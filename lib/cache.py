# Simple in-memory cache with TTL
import time
from typing import Optional, Any

_cache: dict = {}


def cache_get(key: str) -> Optional[Any]:
    if key in _cache:
        data, expires = _cache[key]
        if time.time() < expires:
            return data
        del _cache[key]
    return None


def cache_set(key: str, data: Any, ttl: int = 60):
    _cache[key] = (data, time.time() + ttl)


def cache_delete(key: str):
    if key in _cache:
        del _cache[key]


def cache_clear():
    _cache.clear()
