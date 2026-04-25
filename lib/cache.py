# Thread-safe in-memory cache with TTL and maxsize
import time
import threading
from typing import Optional, Any
from collections import OrderedDict


class TTLCache:
    """Thread-safe LRU cache with TTL expiration."""

    def __init__(self, maxsize: int = 1024, default_ttl: int = 300):
        self._cache: OrderedDict = OrderedDict()
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                data, expires = self._cache[key]
                if time.time() < expires:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    return data
                else:
                    del self._cache[key]
            return None

    def set(self, key: str, data: Any, ttl: int = None):
        if ttl is None:
            ttl = self._default_ttl
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (data, time.time() + ttl)
            # Evict oldest entries if over maxsize
            while len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def delete(self, key: str):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()

    def keys(self):
        """Return all keys in the cache."""
        with self._lock:
            return list(self._cache.keys())

    def cleanup_expired(self):
        """Remove all expired entries. Call periodically if desired."""
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
            for k in expired:
                del self._cache[k]


# Module-level singleton
_cache = TTLCache(maxsize=1024, default_ttl=300)


def cache_get(key: str) -> Optional[Any]:
    return _cache.get(key)


def cache_set(key: str, data: Any, ttl: int = 60):
    _cache.set(key, data, ttl=ttl)


def cache_delete(key: str):
    _cache.delete(key)


def cache_clear():
    _cache.clear()
