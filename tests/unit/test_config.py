"""
Unit tests for configuration module.

Tests configuration helper functions, mappings, and endpoint validation.

Week 13-14: Testing & Quality Assurance - Phase 1 Quick Wins (Pure Functions)
"""

import pytest
from app.config import (
    Config,
    get_valid_platforms,
    get_valid_environments,
    get_valid_statuses,
    is_valid_platform,
    is_valid_environment,
    is_valid_status,
    get_platform_display_name,
    get_environment_display_name,
    is_public_endpoint,
    PLATFORM_MAPPING,
    ENVIRONMENT_MAPPING,
    STATUS_OPTIONS
)


class TestConfigMappings:
    """Test configuration mappings and constants."""

    def test_platform_mapping_structure(self):
        """Test platform mapping has correct structure."""
        assert isinstance(PLATFORM_MAPPING, dict)
        assert len(PLATFORM_MAPPING) > 0

    def test_platform_mapping_contains_key_platforms(self):
        """Test platform mapping contains expected platforms."""
        expected_platforms = ['IP2', 'IP3', 'IP4', 'IP5', 'IP6', 'IP7', 'OpenShift', 'Kubernetes']
        for platform in expected_platforms:
            assert platform in PLATFORM_MAPPING

    def test_environment_mapping_structure(self):
        """Test environment mapping has correct structure."""
        assert isinstance(ENVIRONMENT_MAPPING, dict)
        assert len(ENVIRONMENT_MAPPING) > 0

    def test_environment_mapping_contains_key_environments(self):
        """Test environment mapping contains expected environments."""
        expected_envs = ['dev', 'tst', 'acc', 'prd']
        for env in expected_envs:
            assert env in ENVIRONMENT_MAPPING

    def test_status_options_structure(self):
        """Test status options has correct structure."""
        assert isinstance(STATUS_OPTIONS, list)
        assert len(STATUS_OPTIONS) > 0

    def test_status_options_contains_key_statuses(self):
        """Test status options contains expected statuses."""
        expected_statuses = ['RUNNING', 'STOPPED', 'DEPLOYING', 'FAILED']
        for status in expected_statuses:
            assert status in STATUS_OPTIONS


class TestGetValidLists:
    """Test functions that return valid lists."""

    def test_get_valid_platforms_returns_list(self):
        """Test get_valid_platforms returns a list."""
        platforms = get_valid_platforms()
        assert isinstance(platforms, list)
        assert len(platforms) > 0

    def test_get_valid_platforms_content(self):
        """Test get_valid_platforms returns correct platforms."""
        platforms = get_valid_platforms()
        assert 'IP4' in platforms
        assert 'OpenShift' in platforms
        assert 'AWS' in platforms

    def test_get_valid_platforms_matches_mapping(self):
        """Test get_valid_platforms matches mapping keys."""
        platforms = get_valid_platforms()
        assert set(platforms) == set(PLATFORM_MAPPING.keys())

    def test_get_valid_environments_returns_list(self):
        """Test get_valid_environments returns a list."""
        environments = get_valid_environments()
        assert isinstance(environments, list)
        assert len(environments) > 0

    def test_get_valid_environments_content(self):
        """Test get_valid_environments returns correct environments."""
        environments = get_valid_environments()
        assert 'dev' in environments
        assert 'tst' in environments
        assert 'prd' in environments

    def test_get_valid_environments_matches_mapping(self):
        """Test get_valid_environments matches mapping keys."""
        environments = get_valid_environments()
        assert set(environments) == set(ENVIRONMENT_MAPPING.keys())

    def test_get_valid_statuses_returns_list(self):
        """Test get_valid_statuses returns a list."""
        statuses = get_valid_statuses()
        assert isinstance(statuses, list)
        assert len(statuses) > 0

    def test_get_valid_statuses_content(self):
        """Test get_valid_statuses returns correct statuses."""
        statuses = get_valid_statuses()
        assert 'RUNNING' in statuses
        assert 'STOPPED' in statuses
        assert 'FAILED' in statuses

    def test_get_valid_statuses_matches_config(self):
        """Test get_valid_statuses matches STATUS_OPTIONS."""
        statuses = get_valid_statuses()
        assert statuses == STATUS_OPTIONS


class TestValidationFunctions:
    """Test validation helper functions."""

    def test_is_valid_platform_with_valid_platforms(self):
        """Test is_valid_platform returns True for valid platforms."""
        valid_platforms = ['IP4', 'IP5', 'OpenShift', 'AWS', 'Azure']
        for platform in valid_platforms:
            assert is_valid_platform(platform) is True

    def test_is_valid_platform_with_invalid_platforms(self):
        """Test is_valid_platform returns False for invalid platforms."""
        invalid_platforms = ['invalid', 'IP99', 'unknown', '']
        for platform in invalid_platforms:
            assert is_valid_platform(platform) is False

    def test_is_valid_platform_case_sensitive(self):
        """Test is_valid_platform is case-sensitive."""
        assert is_valid_platform('IP4') is True
        assert is_valid_platform('ip4') is False
        assert is_valid_platform('openshift') is False

    def test_is_valid_environment_with_valid_environments(self):
        """Test is_valid_environment returns True for valid environments."""
        valid_envs = ['dev', 'tst', 'acc', 'prd', 'uat']
        for env in valid_envs:
            assert is_valid_environment(env) is True

    def test_is_valid_environment_with_invalid_environments(self):
        """Test is_valid_environment returns False for invalid environments."""
        invalid_envs = ['invalid', 'prod', 'development', '']
        for env in invalid_envs:
            assert is_valid_environment(env) is False

    def test_is_valid_environment_case_sensitive(self):
        """Test is_valid_environment is case-sensitive."""
        assert is_valid_environment('dev') is True
        assert is_valid_environment('DEV') is False
        assert is_valid_environment('Dev') is False

    def test_is_valid_status_with_valid_statuses(self):
        """Test is_valid_status returns True for valid statuses."""
        valid_statuses = ['RUNNING', 'STOPPED', 'DEPLOYING', 'FAILED']
        for status in valid_statuses:
            assert is_valid_status(status) is True

    def test_is_valid_status_with_invalid_statuses(self):
        """Test is_valid_status returns False for invalid statuses."""
        invalid_statuses = ['invalid', 'running', 'active', '']
        for status in invalid_statuses:
            assert is_valid_status(status) is False

    def test_is_valid_status_case_sensitive(self):
        """Test is_valid_status is case-sensitive."""
        assert is_valid_status('RUNNING') is True
        assert is_valid_status('running') is False
        assert is_valid_status('Running') is False


class TestDisplayNameFunctions:
    """Test display name helper functions."""

    def test_get_platform_display_name_with_valid_platform(self):
        """Test get_platform_display_name with valid platforms."""
        assert get_platform_display_name('IP4') == 'IP4 Platform'
        assert get_platform_display_name('OpenShift') == 'OpenShift Container Platform'
        assert get_platform_display_name('AWS') == 'Amazon Web Services'

    def test_get_platform_display_name_with_invalid_platform(self):
        """Test get_platform_display_name returns input for invalid platform."""
        assert get_platform_display_name('invalid') == 'invalid'
        assert get_platform_display_name('') == ''
        assert get_platform_display_name('unknown-platform') == 'unknown-platform'

    def test_get_platform_display_name_preserves_case(self):
        """Test get_platform_display_name preserves case for unknown platforms."""
        assert get_platform_display_name('MyPlatform') == 'MyPlatform'

    def test_get_environment_display_name_with_valid_environment(self):
        """Test get_environment_display_name with valid environments."""
        assert get_environment_display_name('dev') == 'Development'
        assert get_environment_display_name('tst') == 'Test'
        assert get_environment_display_name('prd') == 'Production'
        assert get_environment_display_name('acc') == 'Acceptance'

    def test_get_environment_display_name_with_invalid_environment(self):
        """Test get_environment_display_name returns input for invalid environment."""
        assert get_environment_display_name('invalid') == 'invalid'
        assert get_environment_display_name('') == ''
        assert get_environment_display_name('unknown-env') == 'unknown-env'

    def test_get_environment_display_name_preserves_case(self):
        """Test get_environment_display_name preserves case for unknown environments."""
        assert get_environment_display_name('MyEnv') == 'MyEnv'


class TestPublicEndpointValidation:
    """Test public endpoint validation."""

    def test_is_public_endpoint_root_path(self):
        """Test is_public_endpoint recognizes root path."""
        assert is_public_endpoint('/') is True

    def test_is_public_endpoint_search_path(self):
        """Test is_public_endpoint recognizes search path."""
        assert is_public_endpoint('/search') is True

    def test_is_public_endpoint_health_endpoints(self):
        """Test is_public_endpoint recognizes health endpoints."""
        assert is_public_endpoint('/health') is True
        assert is_public_endpoint('/health/ready') is True
        assert is_public_endpoint('/health/live') is True
        assert is_public_endpoint('/health/metrics') is True

    def test_is_public_endpoint_auth_endpoints(self):
        """Test is_public_endpoint recognizes auth endpoints."""
        assert is_public_endpoint('/api/auth/token') is True
        assert is_public_endpoint('/api/auth/verify') is True
        assert is_public_endpoint('/api/auth/refresh') is True
        assert is_public_endpoint('/api/auth/revoke') is True
        assert is_public_endpoint('/api/auth/logout') is True

    def test_is_public_endpoint_static_files(self):
        """Test is_public_endpoint recognizes static file paths."""
        assert is_public_endpoint('/static/') is True
        assert is_public_endpoint('/static/css/main.css') is True
        assert is_public_endpoint('/static/js/app.js') is True

    def test_is_public_endpoint_non_public_paths(self):
        """Test is_public_endpoint rejects non-public paths."""
        assert is_public_endpoint('/api/deploy') is False
        assert is_public_endpoint('/api/search') is False
        assert is_public_endpoint('/audit') is False
        assert is_public_endpoint('/admin') is False

    def test_is_public_endpoint_case_sensitive(self):
        """Test is_public_endpoint is case-sensitive."""
        assert is_public_endpoint('/health') is True
        assert is_public_endpoint('/Health') is False
        assert is_public_endpoint('/HEALTH') is False

    def test_is_public_endpoint_partial_matches(self):
        """Test is_public_endpoint handles partial matches correctly."""
        # Should match - starts with public path
        assert is_public_endpoint('/health/custom') is True

        # Should not match - doesn't start with public path
        assert is_public_endpoint('/not-health') is False
        assert is_public_endpoint('/api/health') is False

    def test_is_public_endpoint_with_query_params(self):
        """Test is_public_endpoint with query parameters."""
        assert is_public_endpoint('/health?check=db') is True
        assert is_public_endpoint('/api/auth/token?grant_type=password') is True

    def test_is_public_endpoint_with_trailing_slash(self):
        """Test is_public_endpoint with trailing slash."""
        assert is_public_endpoint('/health/') is True
        assert is_public_endpoint('/static/css/') is True

    def test_is_public_endpoint_module_level_function(self):
        """Test module-level is_public_endpoint function."""
        # Module-level function should behave same as class method
        from app.config import is_public_endpoint as module_func
        assert module_func('/health') is True
        assert module_func('/api/deploy') is False

    def test_config_class_is_public_endpoint(self):
        """Test Config class static method."""
        assert Config.is_public_endpoint('/health') is True
        assert Config.is_public_endpoint('/api/deploy') is False


class TestConfigConstants:
    """Test configuration constants."""

    def test_public_endpoints_list_exists(self):
        """Test PUBLIC_ENDPOINTS list exists and has content."""
        from app.config import PUBLIC_ENDPOINTS
        assert isinstance(PUBLIC_ENDPOINTS, list)
        assert len(PUBLIC_ENDPOINTS) > 0

    def test_public_endpoints_contains_expected_paths(self):
        """Test PUBLIC_ENDPOINTS contains expected paths."""
        from app.config import PUBLIC_ENDPOINTS
        expected_paths = ['/health', '/api/auth/token', '/', '/static/']
        for path in expected_paths:
            assert path in PUBLIC_ENDPOINTS

    def test_platform_mapping_all_values_are_strings(self):
        """Test all platform mapping values are strings."""
        for key, value in PLATFORM_MAPPING.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert len(key) > 0
            assert len(value) > 0

    def test_environment_mapping_all_values_are_strings(self):
        """Test all environment mapping values are strings."""
        for key, value in ENVIRONMENT_MAPPING.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert len(key) > 0
            assert len(value) > 0

    def test_status_options_all_values_are_strings(self):
        """Test all status options are strings."""
        for status in STATUS_OPTIONS:
            assert isinstance(status, str)
            assert len(status) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_validation_with_none_input(self):
        """Test validation functions handle None gracefully."""
        # These should not crash, but return False
        assert is_valid_platform(None) is False
        assert is_valid_environment(None) is False
        assert is_valid_status(None) is False

    def test_validation_with_empty_string(self):
        """Test validation functions handle empty string."""
        assert is_valid_platform('') is False
        assert is_valid_environment('') is False
        assert is_valid_status('') is False

    def test_validation_with_whitespace(self):
        """Test validation functions handle whitespace."""
        assert is_valid_platform(' ') is False
        assert is_valid_platform('  IP4  ') is False
        assert is_valid_environment(' dev ') is False
        assert is_valid_status(' RUNNING ') is False

    def test_display_name_with_none_input(self):
        """Test display name functions handle None."""
        # Should return None or empty string without crashing
        result_platform = get_platform_display_name(None)
        result_env = get_environment_display_name(None)
        assert result_platform in [None, '']
        assert result_env in [None, '']

    def test_is_public_endpoint_with_none(self):
        """Test is_public_endpoint handles None."""
        # Should not crash
        try:
            result = is_public_endpoint(None)
            assert result is False
        except (TypeError, AttributeError):
            # Acceptable to raise error for None
            pass

    def test_is_public_endpoint_empty_string(self):
        """Test is_public_endpoint with empty string."""
        assert is_public_endpoint('') is False

    def test_all_platforms_have_unique_keys(self):
        """Test all platform keys are unique."""
        keys = list(PLATFORM_MAPPING.keys())
        assert len(keys) == len(set(keys))

    def test_all_environments_have_unique_keys(self):
        """Test all environment keys are unique."""
        keys = list(ENVIRONMENT_MAPPING.keys())
        assert len(keys) == len(set(keys))

    def test_all_statuses_are_unique(self):
        """Test all status options are unique."""
        assert len(STATUS_OPTIONS) == len(set(STATUS_OPTIONS))
