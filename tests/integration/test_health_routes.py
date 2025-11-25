"""
Comprehensive tests for health check routes.

Coverage target: health_routes.py 50% → 75%
Missing lines: 18-20, 32-34, 44-54, 65, 74-98
"""
import pytest
from unittest.mock import Mock
from datetime import datetime


class TestHealthCheckEndpoint:
    """Test /health endpoint with various scenarios."""

    def test_health_check_success(self, client, app):
        """Test health check with healthy database."""
        response = client.get('/health')

        assert response.status_code == 200
        data = response.get_json()

        assert data['status'] == 'healthy'
        assert data['service'] == 'CCR API Manager'
        assert 'timestamp' in data
        assert data['database']['status'] == 'healthy'
        assert data['database']['message'] == 'Connected'

    def test_health_check_db_unhealthy(self, client, app):
        """Test health check when database ping fails."""
        with app.app_context():
            # Mock database ping to raise exception
            original_client = app.db_service.client
            mock_client = Mock()
            mock_admin = Mock()
            mock_admin.command.side_effect = Exception("Connection timeout")
            mock_client.admin = mock_admin
            app.db_service.client = mock_client

            try:
                response = client.get('/health')

                assert response.status_code == 503
                data = response.get_json()

                assert data['status'] == 'unhealthy'
                assert data['service'] == 'CCR API Manager'
                assert data['database']['status'] == 'unhealthy'
                assert 'Connection timeout' in data['database']['message']

            finally:
                # Restore original client
                app.db_service.client = original_client

    def test_health_check_unexpected_error(self, client, app):
        """Test health check when unexpected error occurs in db access."""
        with app.app_context():
            # Mock db_service.client to be None to trigger AttributeError
            original_client = app.db_service.client
            app.db_service.client = None

            try:
                response = client.get('/health')

                assert response.status_code == 503
                data = response.get_json()

                assert data['status'] == 'unhealthy'
                assert 'timestamp' in data
                # This error is caught in inner try/catch, so it shows as db unhealthy
                assert data['database']['status'] == 'unhealthy'
                assert 'NoneType' in data['database']['message'] or 'client' in data['database']['message']

            finally:
                # Restore original client
                app.db_service.client = original_client

    def test_health_check_response_format(self, client, app):
        """Test health check response has correct format."""
        response = client.get('/health')
        data = response.get_json()

        # Verify all required fields present
        assert 'status' in data
        assert 'timestamp' in data
        assert 'service' in data
        assert 'database' in data
        assert 'status' in data['database']
        assert 'message' in data['database']

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(data['timestamp'])
        except ValueError:
            pytest.fail("Invalid timestamp format")


class TestReadinessCheckEndpoint:
    """Test /health/ready endpoint for Kubernetes readiness."""

    def test_readiness_check_ready(self, client, app):
        """Test readiness check when service is ready."""
        response = client.get('/health/ready')

        assert response.status_code == 200
        data = response.get_json()

        assert data['status'] == 'ready'
        assert 'timestamp' in data

    def test_readiness_check_not_ready_db_down(self, client, app):
        """Test readiness check when database is not accessible."""
        with app.app_context():
            # Mock database ping to raise exception
            original_client = app.db_service.client
            mock_client = Mock()
            mock_admin = Mock()
            mock_admin.command.side_effect = Exception("Database connection failed")
            mock_client.admin = mock_admin
            app.db_service.client = mock_client

            try:
                response = client.get('/health/ready')

                assert response.status_code == 503
                data = response.get_json()

                assert data['status'] == 'not ready'
                assert 'timestamp' in data
                assert 'error' in data
                assert 'Database connection failed' in data['error']

            finally:
                # Restore original client
                app.db_service.client = original_client

    def test_readiness_check_response_format(self, client, app):
        """Test readiness check response format."""
        response = client.get('/health/ready')
        data = response.get_json()

        assert 'status' in data
        assert 'timestamp' in data

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(data['timestamp'])
        except ValueError:
            pytest.fail("Invalid timestamp format")


class TestLivenessCheckEndpoint:
    """Test /health/live endpoint for Kubernetes liveness."""

    def test_liveness_check_alive(self, client, app):
        """Test liveness check always returns alive."""
        response = client.get('/health/live')

        assert response.status_code == 200
        data = response.get_json()

        assert data['status'] == 'alive'
        assert 'timestamp' in data

    def test_liveness_check_response_format(self, client, app):
        """Test liveness check response format."""
        response = client.get('/health/live')
        data = response.get_json()

        assert 'status' in data
        assert 'timestamp' in data

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(data['timestamp'])
        except ValueError:
            pytest.fail("Invalid timestamp format")


class TestMetricsEndpoint:
    """Test /health/metrics endpoint for Prometheus metrics."""

    def test_metrics_success(self, client, app):
        """Test metrics endpoint returns Prometheus format."""
        with app.app_context():
            # Mock get_stats to return test data
            original_get_stats = app.db_service.get_stats
            app.db_service.get_stats = Mock(return_value={
                'total_apis': 42,
                'unique_platforms': 5,
                'unique_environments': 8,
                'total_deployments': 156
            })

            try:
                response = client.get('/health/metrics')

                assert response.status_code == 200
                assert response.content_type == 'text/plain; charset=utf-8'

                metrics_text = response.data.decode('utf-8')

                # Verify Prometheus format
                assert '# HELP api_manager_documents_total' in metrics_text
                assert '# TYPE api_manager_documents_total gauge' in metrics_text
                assert 'api_manager_documents_total 42' in metrics_text

                assert '# HELP api_manager_platforms_total' in metrics_text
                assert 'api_manager_platforms_total 5' in metrics_text

                assert '# HELP api_manager_environments_total' in metrics_text
                assert 'api_manager_environments_total 8' in metrics_text

                assert '# HELP api_manager_deployments_total' in metrics_text
                assert 'api_manager_deployments_total 156' in metrics_text

            finally:
                # Restore original method
                app.db_service.get_stats = original_get_stats

    def test_metrics_with_zero_values(self, client, app):
        """Test metrics endpoint with zero values."""
        with app.app_context():
            # Mock get_stats to return zeros
            original_get_stats = app.db_service.get_stats
            app.db_service.get_stats = Mock(return_value={
                'total_apis': 0,
                'unique_platforms': 0,
                'unique_environments': 0,
                'total_deployments': 0
            })

            try:
                response = client.get('/health/metrics')

                assert response.status_code == 200
                metrics_text = response.data.decode('utf-8')

                assert 'api_manager_documents_total 0' in metrics_text
                assert 'api_manager_platforms_total 0' in metrics_text
                assert 'api_manager_environments_total 0' in metrics_text
                assert 'api_manager_deployments_total 0' in metrics_text

            finally:
                app.db_service.get_stats = original_get_stats

    def test_metrics_with_missing_stats(self, client, app):
        """Test metrics endpoint when stats has missing keys."""
        with app.app_context():
            # Mock get_stats to return partial data
            original_get_stats = app.db_service.get_stats
            app.db_service.get_stats = Mock(return_value={
                'total_apis': 10
                # Missing other keys
            })

            try:
                response = client.get('/health/metrics')

                assert response.status_code == 200
                metrics_text = response.data.decode('utf-8')

                # Should default to 0 for missing keys
                assert 'api_manager_documents_total 10' in metrics_text
                assert 'api_manager_platforms_total 0' in metrics_text
                assert 'api_manager_environments_total 0' in metrics_text
                assert 'api_manager_deployments_total 0' in metrics_text

            finally:
                app.db_service.get_stats = original_get_stats

    def test_metrics_error_handling(self, client, app):
        """Test metrics endpoint when get_stats raises exception."""
        with app.app_context():
            # Mock get_stats to raise exception
            original_get_stats = app.db_service.get_stats
            app.db_service.get_stats = Mock(side_effect=Exception("Database error"))

            try:
                response = client.get('/health/metrics')

                assert response.status_code == 500
                assert response.content_type == 'text/plain'

                metrics_text = response.data.decode('utf-8')
                assert '# Error generating metrics' in metrics_text
                assert 'Database error' in metrics_text

            finally:
                app.db_service.get_stats = original_get_stats


class TestHealthRoutesIntegration:
    """Integration tests for health routes."""

    def test_all_health_endpoints_accessible(self, client, app):
        """Test all health endpoints are accessible."""
        endpoints = [
            '/health',
            '/health/ready',
            '/health/live',
            '/health/metrics'
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 503], \
                f"Endpoint {endpoint} returned unexpected status {response.status_code}"

    def test_health_endpoints_return_json_or_text(self, client, app):
        """Test health endpoints return appropriate content types."""
        # JSON endpoints
        json_endpoints = ['/health', '/health/ready', '/health/live']
        for endpoint in json_endpoints:
            response = client.get(endpoint)
            assert 'application/json' in response.content_type, \
                f"Endpoint {endpoint} did not return JSON"

        # Text endpoint
        response = client.get('/health/metrics')
        assert 'text/plain' in response.content_type, \
            "Metrics endpoint did not return text/plain"

    def test_health_endpoints_no_authentication_required(self, client, app):
        """Test health endpoints are accessible without authentication."""
        # Health endpoints should not require authentication
        endpoints = [
            '/health',
            '/health/ready',
            '/health/live',
            '/health/metrics'
        ]

        for endpoint in endpoints:
            # Call without any auth headers
            response = client.get(endpoint)
            # Should not return 401 Unauthorized
            assert response.status_code != 401, \
                f"Endpoint {endpoint} requires authentication"
