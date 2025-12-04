"""
Unit tests for cache utility functions.

Tests caching utilities including TTL caches, cache decorators, cache key generation,
cache statistics, and cache invalidation.

Week 13-14: Testing & Quality Assurance - Phase 1 Quick Wins (Pure Functions)
"""

import pytest
import time
from unittest.mock import Mock, patch, call
from cachetools import TTLCache

from app.utils.cache import (
    create_cache_key,
    cached,
    cache_stats,
    get_all_cache_stats,
    clear_cache,
    invalidate_on_change,
    audit_stats_cache,
    search_cache,
    config_cache,
    suggestions_cache
)


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_create_cache_key_no_args(self):
        """Test cache key generation with no arguments."""
        key1 = create_cache_key()
        key2 = create_cache_key()

        # Same input should produce same key
        assert key1 == key2
        # Should be MD5 hash (32 hex chars)
        assert len(key1) == 32
        assert all(c in '0123456789abcdef' for c in key1)

    def test_create_cache_key_with_args(self):
        """Test cache key generation with positional arguments."""
        key1 = create_cache_key('arg1', 'arg2', 123)
        key2 = create_cache_key('arg1', 'arg2', 123)
        key3 = create_cache_key('arg1', 'different', 123)

        # Same args should produce same key
        assert key1 == key2
        # Different args should produce different key
        assert key1 != key3

    def test_create_cache_key_with_kwargs(self):
        """Test cache key generation with keyword arguments."""
        key1 = create_cache_key(a=1, b=2, c=3)
        key2 = create_cache_key(c=3, a=1, b=2)  # Different order
        key3 = create_cache_key(a=1, b=2, c=4)  # Different value

        # Same kwargs should produce same key regardless of order
        assert key1 == key2
        # Different kwargs should produce different key
        assert key1 != key3

    def test_create_cache_key_with_mixed_args(self):
        """Test cache key generation with both args and kwargs."""
        key1 = create_cache_key('pos1', 'pos2', kw1='val1', kw2='val2')
        key2 = create_cache_key('pos1', 'pos2', kw2='val2', kw1='val1')
        key3 = create_cache_key('pos1', 'different', kw1='val1', kw2='val2')

        # Same arguments should produce same key
        assert key1 == key2
        # Different arguments should produce different key
        assert key1 != key3

    def test_create_cache_key_with_complex_types(self):
        """Test cache key generation with complex types."""
        key1 = create_cache_key(['list', 'items'], {'dict': 'value'})
        key2 = create_cache_key(['list', 'items'], {'dict': 'value'})

        # Should handle complex types
        assert key1 == key2
        assert len(key1) == 32

    def test_create_cache_key_is_deterministic(self):
        """Test that cache key generation is deterministic."""
        keys = [create_cache_key('test', x=123) for _ in range(5)]

        # All keys should be identical
        assert all(k == keys[0] for k in keys)


class TestCacheDecorator:
    """Test the @cached decorator."""

    def test_cached_decorator_basic(self):
        """Test basic caching with decorator."""
        test_cache = TTLCache(maxsize=10, ttl=60)
        call_count = 0

        @cached(test_cache, key_prefix="test")
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - cache miss
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - cache hit
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment

        # Different args - cache miss
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    def test_cached_decorator_with_kwargs(self):
        """Test caching with keyword arguments."""
        test_cache = TTLCache(maxsize=10, ttl=60)
        call_count = 0

        @cached(test_cache, key_prefix="test")
        def function_with_kwargs(a, b=10):
            nonlocal call_count
            call_count += 1
            return a + b

        # First call
        result1 = function_with_kwargs(5, b=15)
        assert result1 == 20
        assert call_count == 1

        # Same args - cache hit
        result2 = function_with_kwargs(5, b=15)
        assert result2 == 20
        assert call_count == 1

        # Different kwargs - cache miss
        result3 = function_with_kwargs(5, b=20)
        assert result3 == 25
        assert call_count == 2

    def test_cached_decorator_ttl_expiration(self):
        """Test that cache expires after TTL."""
        test_cache = TTLCache(maxsize=10, ttl=1)  # 1 second TTL
        call_count = 0

        @cached(test_cache, key_prefix="test")
        def function_with_short_ttl(x):
            nonlocal call_count
            call_count += 1
            return x * 3

        # First call
        result1 = function_with_short_ttl(5)
        assert result1 == 15
        assert call_count == 1

        # Immediate second call - cache hit
        result2 = function_with_short_ttl(5)
        assert result2 == 15
        assert call_count == 1

        # Wait for TTL to expire
        time.sleep(1.5)

        # Call again - cache should be expired
        result3 = function_with_short_ttl(5)
        assert result3 == 15
        assert call_count == 2  # Should increment

    def test_cached_decorator_max_size(self):
        """Test that cache respects max size."""
        test_cache = TTLCache(maxsize=2, ttl=60)  # Only 2 items
        call_count = 0

        @cached(test_cache, key_prefix="test")
        def function_with_small_cache(x):
            nonlocal call_count
            call_count += 1
            return x * 4

        # Fill cache
        function_with_small_cache(1)  # call_count = 1
        function_with_small_cache(2)  # call_count = 2
        function_with_small_cache(3)  # call_count = 3, evicts oldest

        # First call should be evicted
        function_with_small_cache(1)  # Should be cache miss
        assert call_count == 4

    def test_cached_decorator_without_prefix(self):
        """Test caching without key prefix."""
        test_cache = TTLCache(maxsize=10, ttl=60)

        @cached(test_cache)  # No prefix
        def function_no_prefix(x):
            return x * 5

        result1 = function_no_prefix(5)
        result2 = function_no_prefix(5)

        assert result1 == 25
        assert result2 == 25
        assert len(test_cache) == 1

    @patch('app.utils.cache.logger')
    def test_cached_decorator_logging(self, mock_logger):
        """Test that cache decorator logs hits and misses."""
        test_cache = TTLCache(maxsize=10, ttl=60)

        @cached(test_cache, key_prefix="test")
        def logged_function(x):
            return x * 6

        # First call - should log MISS
        logged_function(5)
        assert any(
            'Cache MISS' in str(call)
            for call in mock_logger.debug.call_args_list
        )

        # Second call - should log HIT
        mock_logger.reset_mock()
        logged_function(5)
        assert any(
            'Cache HIT' in str(call)
            for call in mock_logger.debug.call_args_list
        )


class TestCacheStats:
    """Test cache statistics functions."""

    def test_cache_stats_empty_cache(self):
        """Test stats for empty cache."""
        test_cache = TTLCache(maxsize=10, ttl=300)

        stats = cache_stats(test_cache, 'Test Cache')

        assert stats['name'] == 'Test Cache'
        assert stats['current_size'] == 0
        assert stats['max_size'] == 10
        assert stats['ttl_seconds'] == 300
        assert stats['utilization_percent'] == 0.0

    def test_cache_stats_partially_filled(self):
        """Test stats for partially filled cache."""
        test_cache = TTLCache(maxsize=10, ttl=300)
        test_cache['key1'] = 'value1'
        test_cache['key2'] = 'value2'
        test_cache['key3'] = 'value3'

        stats = cache_stats(test_cache, 'Test Cache')

        assert stats['name'] == 'Test Cache'
        assert stats['current_size'] == 3
        assert stats['max_size'] == 10
        assert stats['ttl_seconds'] == 300
        assert stats['utilization_percent'] == 30.0

    def test_cache_stats_full_cache(self):
        """Test stats for full cache."""
        test_cache = TTLCache(maxsize=5, ttl=300)
        for i in range(5):
            test_cache[f'key{i}'] = f'value{i}'

        stats = cache_stats(test_cache, 'Full Cache')

        assert stats['current_size'] == 5
        assert stats['max_size'] == 5
        assert stats['utilization_percent'] == 100.0

    def test_get_all_cache_stats_structure(self):
        """Test that get_all_cache_stats returns correct structure."""
        stats = get_all_cache_stats()

        # Check structure
        assert 'audit_stats' in stats
        assert 'search' in stats
        assert 'config' in stats
        assert 'suggestions' in stats
        assert 'total_cached_items' in stats

        # Each cache should have required fields
        for cache_name in ['audit_stats', 'search', 'config', 'suggestions']:
            cache_stat = stats[cache_name]
            assert 'name' in cache_stat
            assert 'current_size' in cache_stat
            assert 'max_size' in cache_stat
            assert 'ttl_seconds' in cache_stat
            assert 'utilization_percent' in cache_stat

    def test_get_all_cache_stats_values(self):
        """Test that get_all_cache_stats returns correct values."""
        # Clear all caches first
        clear_cache()

        stats = get_all_cache_stats()

        # Check audit_stats cache config
        assert stats['audit_stats']['max_size'] == 10
        assert stats['audit_stats']['ttl_seconds'] == 300

        # Check search cache config
        assert stats['search']['max_size'] == 100
        assert stats['search']['ttl_seconds'] == 120

        # Check config cache config
        assert stats['config']['max_size'] == 50
        assert stats['config']['ttl_seconds'] == 1800

        # Check suggestions cache config
        assert stats['suggestions']['max_size'] == 200
        assert stats['suggestions']['ttl_seconds'] == 60

        # Total should be sum of all
        assert stats['total_cached_items'] == 0  # All empty after clear

    def test_get_all_cache_stats_with_data(self):
        """Test stats with data in caches."""
        # Clear all caches first
        clear_cache()

        # Add some items to caches
        audit_stats_cache['test1'] = 'value1'
        search_cache['test2'] = 'value2'
        search_cache['test3'] = 'value3'
        config_cache['test4'] = 'value4'

        stats = get_all_cache_stats()

        assert stats['audit_stats']['current_size'] == 1
        assert stats['search']['current_size'] == 2
        assert stats['config']['current_size'] == 1
        assert stats['suggestions']['current_size'] == 0
        assert stats['total_cached_items'] == 4


class TestCacheClear:
    """Test cache clearing functionality."""

    def setup_method(self):
        """Clear all caches before each test."""
        clear_cache()

    def test_clear_specific_cache(self):
        """Test clearing a specific cache."""
        # Add items to all caches
        audit_stats_cache['key1'] = 'value1'
        search_cache['key2'] = 'value2'
        config_cache['key3'] = 'value3'
        suggestions_cache['key4'] = 'value4'

        # Clear only search cache
        clear_cache('search')

        # Verify only search cache is cleared
        assert len(audit_stats_cache) == 1
        assert len(search_cache) == 0
        assert len(config_cache) == 1
        assert len(suggestions_cache) == 1

    def test_clear_all_caches(self):
        """Test clearing all caches."""
        # Add items to all caches
        audit_stats_cache['key1'] = 'value1'
        search_cache['key2'] = 'value2'
        config_cache['key3'] = 'value3'
        suggestions_cache['key4'] = 'value4'

        # Clear all caches
        clear_cache(None)

        # Verify all caches are cleared
        assert len(audit_stats_cache) == 0
        assert len(search_cache) == 0
        assert len(config_cache) == 0
        assert len(suggestions_cache) == 0

    def test_clear_audit_stats_cache(self):
        """Test clearing audit stats cache."""
        audit_stats_cache['key1'] = 'value1'
        clear_cache('audit_stats')
        assert len(audit_stats_cache) == 0

    def test_clear_config_cache(self):
        """Test clearing config cache."""
        config_cache['key1'] = 'value1'
        clear_cache('config')
        assert len(config_cache) == 0

    def test_clear_suggestions_cache(self):
        """Test clearing suggestions cache."""
        suggestions_cache['key1'] = 'value1'
        clear_cache('suggestions')
        assert len(suggestions_cache) == 0

    @patch('app.utils.cache.logger')
    def test_clear_unknown_cache(self, mock_logger):
        """Test clearing with unknown cache name."""
        clear_cache('nonexistent_cache')

        # Should log warning
        mock_logger.warning.assert_called_once()
        assert 'Unknown cache name' in str(mock_logger.warning.call_args)

    @patch('app.utils.cache.logger')
    def test_clear_cache_logging(self, mock_logger):
        """Test that cache clearing logs appropriately."""
        clear_cache('search')
        mock_logger.info.assert_called_once_with("Cleared search_cache")

        mock_logger.reset_mock()
        clear_cache(None)
        mock_logger.info.assert_called_once_with("Cleared ALL caches")


class TestInvalidateOnChange:
    """Test cache invalidation decorator."""

    def setup_method(self):
        """Clear all caches before each test."""
        clear_cache()

    def test_invalidate_single_cache(self):
        """Test invalidating a single cache."""
        # Add items to caches
        search_cache['key1'] = 'value1'
        config_cache['key2'] = 'value2'

        @invalidate_on_change(['search'])
        def modify_data():
            return 'modified'

        result = modify_data()

        assert result == 'modified'
        assert len(search_cache) == 0  # Should be cleared
        assert len(config_cache) == 1  # Should not be cleared

    def test_invalidate_multiple_caches(self):
        """Test invalidating multiple caches."""
        # Add items to all caches
        audit_stats_cache['key1'] = 'value1'
        search_cache['key2'] = 'value2'
        config_cache['key3'] = 'value3'
        suggestions_cache['key4'] = 'value4'

        @invalidate_on_change(['search', 'audit_stats'])
        def modify_data():
            return 'modified'

        modify_data()

        # Only specified caches should be cleared
        assert len(audit_stats_cache) == 0
        assert len(search_cache) == 0
        assert len(config_cache) == 1
        assert len(suggestions_cache) == 1

    def test_invalidate_preserves_return_value(self):
        """Test that decorator preserves function return value."""
        @invalidate_on_change(['search'])
        def function_with_return():
            return {'status': 'success', 'data': [1, 2, 3]}

        result = function_with_return()

        assert result == {'status': 'success', 'data': [1, 2, 3]}

    def test_invalidate_with_function_args(self):
        """Test invalidation with function arguments."""
        @invalidate_on_change(['search'])
        def function_with_args(a, b, c=10):
            return a + b + c

        result = function_with_args(5, 10, c=15)

        assert result == 30

    @patch('app.utils.cache.logger')
    def test_invalidate_logging(self, mock_logger):
        """Test that invalidation logs appropriately."""
        search_cache['key1'] = 'value1'

        @invalidate_on_change(['search'])
        def modify_function():
            return 'result'

        modify_function()

        # Should log cache invalidation
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any('Invalidated search cache' in call for call in info_calls)


class TestCacheIntegration:
    """Test integration scenarios with caches."""

    def setup_method(self):
        """Clear all caches before each test."""
        clear_cache()

    def test_multiple_functions_same_cache(self):
        """Test multiple functions using the same cache."""
        shared_cache = TTLCache(maxsize=10, ttl=60)

        @cached(shared_cache, key_prefix="func1")
        def function1(x):
            return x * 2

        @cached(shared_cache, key_prefix="func2")
        def function2(x):
            return x * 3

        # Both functions should store in same cache
        function1(5)
        function2(5)

        # Cache should have 2 items (different prefixes)
        assert len(shared_cache) == 2

    def test_cache_with_invalidation_workflow(self):
        """Test realistic workflow with caching and invalidation."""
        test_cache = TTLCache(maxsize=10, ttl=60)
        call_count = 0

        @cached(test_cache, key_prefix="data")
        def get_data():
            nonlocal call_count
            call_count += 1
            return {'count': call_count}

        @invalidate_on_change(['search'])
        def update_data():
            return 'updated'

        # Get data - cache miss
        result1 = get_data()
        assert result1 == {'count': 1}
        assert call_count == 1

        # Get data again - cache hit
        result2 = get_data()
        assert result2 == {'count': 1}
        assert call_count == 1

        # Add to search cache
        search_cache['test'] = 'value'
        assert len(search_cache) == 1

        # Update data - should invalidate search cache
        update_data()
        assert len(search_cache) == 0

        # Our test_cache should not be affected
        result3 = get_data()
        assert result3 == {'count': 1}  # Still cached
        assert call_count == 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_cache_with_none_value(self):
        """Test caching None values."""
        test_cache = TTLCache(maxsize=10, ttl=60)

        @cached(test_cache, key_prefix="test")
        def function_returns_none(x):
            return None

        result1 = function_returns_none(5)
        result2 = function_returns_none(5)

        assert result1 is None
        assert result2 is None
        assert len(test_cache) == 1

    def test_cache_with_empty_collections(self):
        """Test caching empty collections."""
        test_cache = TTLCache(maxsize=10, ttl=60)
        call_count = 0

        @cached(test_cache, key_prefix="test")
        def function_returns_empty(x):
            nonlocal call_count
            call_count += 1
            return []

        result1 = function_returns_empty(5)
        result2 = function_returns_empty(5)

        assert result1 == []
        assert result2 == []
        assert call_count == 1  # Should be cached

    def test_cache_key_with_unicode(self):
        """Test cache key generation with unicode characters."""
        key1 = create_cache_key('café', '日本語', 'مرحبا')
        key2 = create_cache_key('café', '日本語', 'مرحبا')

        assert key1 == key2
        assert len(key1) == 32

    def test_cache_key_with_special_chars(self):
        """Test cache key generation with special characters."""
        key1 = create_cache_key('key!@#$%^&*()', x='value<>?":{}')
        key2 = create_cache_key('key!@#$%^&*()', x='value<>?":{}')

        assert key1 == key2

    def test_concurrent_cache_access(self):
        """Test that cache handles concurrent-style access."""
        test_cache = TTLCache(maxsize=100, ttl=60)

        @cached(test_cache, key_prefix="test")
        def concurrent_function(x):
            return x * 2

        # Simulate multiple "concurrent" calls
        results = [concurrent_function(i) for i in range(50)]

        assert len(results) == 50
        assert len(test_cache) == 50
        assert all(results[i] == i * 2 for i in range(50))

    def test_cache_stats_with_zero_maxsize(self):
        """Test cache stats with maxsize of 1 (effectively minimal)."""
        # Test with minimal cache size
        test_cache = TTLCache(maxsize=1, ttl=60)
        test_cache['item'] = 'value'

        stats = cache_stats(test_cache, 'Minimal Cache')

        # Should handle small cache correctly
        assert stats['current_size'] == 1
        assert stats['max_size'] == 1
        assert stats['utilization_percent'] == 100.0
