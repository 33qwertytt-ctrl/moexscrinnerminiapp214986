"""Caching helpers for MOEX data."""

from aiocache import Cache


def build_cache(cache_dir: str) -> Cache:
    """Create cache instance. Filesystem cache can be swapped later."""
    return Cache(Cache.MEMORY, namespace=cache_dir)
