"""
API cache. Because hitting GitHub 50 times for the same data is silly.

Simple in-memory cache that lasts for the duration of a single run.
Nothing fancy, just a dict with a wrapper.
"""

from typing import Any, Callable, TypeVar
from functools import wraps
import hashlib
import json

T = TypeVar("T")


class APICache:
    """Session-scoped cache for API calls. Lives and dies with the process."""

    _cache: dict[str, Any] = {}
    _enabled: bool = True

    @classmethod
    def get(cls, key: str) -> Any | None:
        """Get from cache. Returns None if not found or disabled."""
        if not cls._enabled:
            return None
        return cls._cache.get(key)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Store in cache."""
        if cls._enabled:
            cls._cache[key] = value

    @classmethod
    def get_or_fetch(cls, key: str, fetcher: Callable[[], T]) -> T:
        """Get from cache or call fetcher. The bread and butter."""
        cached = cls.get(key)
        if cached is not None:
            return cached

        result = fetcher()
        cls.set(key, result)
        return result

    @classmethod
    def clear(cls) -> None:
        """Nuke the cache. Fresh start."""
        cls._cache.clear()

    @classmethod
    def disable(cls) -> None:
        """Turn off caching. For when you want fresh data."""
        cls._enabled = False

    @classmethod
    def enable(cls) -> None:
        """Turn caching back on."""
        cls._enabled = True

    @classmethod
    def is_cached(cls, key: str) -> bool:
        """Check if something is in the cache."""
        return key in cls._cache


def make_cache_key(*args, **kwargs) -> str:
    """Turn args into a cache key. Deterministic hashing."""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(prefix: str = ""):
    """
    Decorator for caching function results.

    Usage:
        @cached("github_repos")
        def get_github_repos(limit=1000, filter_forks=False):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            key = f"{prefix}:{make_cache_key(*args, **kwargs)}"
            return APICache.get_or_fetch(key, lambda: func(*args, **kwargs))

        return wrapper

    return decorator
