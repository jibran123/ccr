"""Integration tests for API endpoints."""

import pytest
import json


class TestAPIEndpoints:
    """Test API endpoints integration."""
    
    def test_index_route(self, client):
        """Test index page loads."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'API Search' in response.data
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
    
    def test_search_endpoint_get(self, client):
        """Test search endpoint with GET."""
        response = client.get('/api/search?q=test&page=1&page_size=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert 'data' in data
        assert 'metadata' in data
    
    def test_search_endpoint_post(self, client):
        """Test search endpoint with POST."""
        response = client.post('/api/search', 
            json={'q': 'test', 'page': 1, 'page_size': 10}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
    
    def test_search_validation_error(self, client):
        """Test search with invalid parameters."""
        response = client.get('/api/search?q=test&page=-1')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_suggestions_endpoint(self, client):
        """Test suggestions endpoint."""
        response = client.get('/api/suggestions/Platform?prefix=A')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert isinstance(data['data'], list)
    
    def test_stats_endpoint(self, client):
        """Test statistics endpoint."""
        response = client.get('/api/stats')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'total_documents' in data['data']
    
    def test_export_endpoint_json(self, client):
        """Test export endpoint with JSON format."""
        response = client.post('/api/export', 
            json={'query': 'test', 'format': 'json'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'count' in data
    
    def test_export_endpoint_csv(self, client):
        """Test export endpoint with CSV format."""
        response = client.post('/api/export', 
            json={'query': 'test', 'format': 'csv'}
        )
        assert response.status_code == 200
        assert response.content_type == 'text/csv'
    
    def test_readiness_probe(self, client):
        """Test readiness probe endpoint."""
        response = client.get('/health/ready')
        # May fail if DB not connected, but should return valid response
        assert response.status_code in [200, 503]
        data = json.loads(response.data)
        assert 'status' in data
    
    def test_liveness_probe(self, client):
        """Test liveness probe endpoint."""
        response = client.get('/health/live')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'alive'
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get('/health/metrics')
        assert response.status_code in [200, 500]
        assert 'api_manager_documents_total' in response.data.decode()
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Resource not found'