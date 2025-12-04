"""
Caching utilities for Common Configuration Repository (CCR)
Week 9-10: Performance optimization through intelligent caching
"""

from functools import wraps
from cachetools import TTLCache
import logging
import hashlib
import json
from typing import Callable, Any

logger = logging.getLogger(__name__)


# Cache Configuration
# TTLCache(maxsize, ttl) - maxsize: max items, ttl: time to live in seconds

# Audit statistics cache - 5 minute TTL (stats don't change frequently)
audit_stats_cache = TTLCache(maxsize=10, ttl=300)  # 5 minutes

# Search results cache - 2 minute TTL (balance freshness vs performance)
search_cache = TTLCache(maxsize=100, ttl=120)  # 2 minutes

# Config data cache - 30 minute TTL (rarely changes)
config_cache = TTLCache(maxsize=50, ttl=1800)  # 30 minutes

# Suggestions cache - 1 minute TTL (auto-complete needs to be responsive)
suggestions_cache = TTLCache(maxsize=200, ttl=60)  # 1 minute


def create_cache_key(*args, **kwargs) -> str:
    """
    Create a unique cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        str: MD5 hash of the arguments as cache key
    """
    # Convert args and kwargs to a stable string representation
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())  # Sort for consistency
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)

    # Create MD5 hash for compact key
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(cache: TTLCache, key_prefix: str = ""):
    """
    Decorator for caching function results with TTL.

    Args:
        cache: TTLCache instance to use
        key_prefix: Optional prefix for cache keys (for namespacing)

    Usage:
        @cached(audit_stats_cache, key_prefix="audit_stats")
        def get_audit_statistics():
            # Expensive operation
            return stats
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Create cache key
            cache_key = f"{key_prefix}:{create_cache_key(*args, **kwargs)}"

            # Try to get from cache
            if cache_key in cache:
                logger.debug(f"Cache HIT for {func.__name__}: {cache_key[:20]}...")
                return cache[cache_key]

            # Cache miss - call function
            logger.debug(f"Cache MISS for {func.__name__}: {cache_key[:20]}...")
            result = func(*args, **kwargs)

            # Store in cache
            cache[cache_key] = result
            logger.debug(f"Cached result for {func.__name__}: {cache_key[:20]}...")

            return result

        return wrapper
    return decorator


def cache_stats(cache: TTLCache, cache_name: str) -> dict:
    """
    Get statistics for a cache instance.

    Args:
        cache: TTLCache instance
        cache_name: Name for display

    Returns:
        dict: Cache statistics
    """
    return {
        'name': cache_name,
        'current_size': len(cache),
        'max_size': cache.maxsize,
        'ttl_seconds': cache.ttl,
        'utilization_percent': round((len(cache) / cache.maxsize) * 100, 1) if cache.maxsize > 0 else 0
    }


def get_all_cache_stats() -> dict:
    """
    Get statistics for all caches.

    Returns:
        dict: Statistics for all cache instances
    """
    return {
        'audit_stats': cache_stats(audit_stats_cache, 'Audit Statistics Cache'),
        'search': cache_stats(search_cache, 'Search Results Cache'),
        'config': cache_stats(config_cache, 'Config Data Cache'),
        'suggestions': cache_stats(suggestions_cache, 'Suggestions Cache'),
        'total_cached_items': (
            len(audit_stats_cache) +
            len(search_cache) +
            len(config_cache) +
            len(suggestions_cache)
        )
    }


def clear_cache(cache_name: str = None):
    """
    Clear one or all caches.

    Args:
        cache_name: Name of cache to clear ('audit_stats', 'search', 'config', 'suggestions')
                   If None, clears all caches
    """
    if cache_name == 'audit_stats':
        audit_stats_cache.clear()
        logger.info("Cleared audit_stats_cache")
    elif cache_name == 'search':
        search_cache.clear()
        logger.info("Cleared search_cache")
    elif cache_name == 'config':
        config_cache.clear()
        logger.info("Cleared config_cache")
    elif cache_name == 'suggestions':
        suggestions_cache.clear()
        logger.info("Cleared suggestions_cache")
    elif cache_name is None:
        # Clear all caches
        audit_stats_cache.clear()
        search_cache.clear()
        config_cache.clear()
        suggestions_cache.clear()
        logger.info("Cleared ALL caches")
    else:
        logger.warning(f"Unknown cache name: {cache_name}")


def invalidate_on_change(affected_caches: list):
    """
    Decorator to invalidate caches when data changes.

    Args:
        affected_caches: List of cache names to clear

    Usage:
        @invalidate_on_change(['audit_stats', 'search'])
        def create_deployment(...):
            # Creates new deployment
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Call the function
            result = func(*args, **kwargs)

            # Invalidate affected caches
            for cache_name in affected_caches:
                clear_cache(cache_name)
                logger.info(f"Invalidated {cache_name} cache due to {func.__name__}")

            return result

        return wrapper
    return decorator
