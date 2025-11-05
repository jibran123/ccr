"""
Integration tests for core API endpoints.

Tests health, search, stats, export functionality.
"""

import pytest
import json


class TestCoreEndpoints:
    """Test core API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
    
    def test_index_page_loads(self, client):
        """Test main index page loads."""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'API Search' in response.data or b'CCR' in response.data
    
    def test_search_endpoint_get_empty_query(self, client):
        """Test search endpoint with GET and empty query."""
        response = client.get('/api/search?q=&page=1&page_size=10')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert 'data' in data
        assert 'metadata' in data
        assert isinstance(data['data'], list)
    
    def test_search_endpoint_get_with_query(self, client):
        """Test search endpoint with GET and text query."""
        response = client.get('/api/search?q=test&page=1&page_size=10')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert isinstance(data['data'], list)
        assert 'total' in data['metadata']
        assert 'page' in data['metadata']
    
    def test_search_endpoint_post(self, client):
        """Test search endpoint with POST."""
        response = client.post('/api/search',
            json={'q': 'test', 'page': 1, 'page_size': 10}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'data' in data
    
    def test_search_validation_negative_page(self, client):
        """Test search with invalid page number."""
        response = client.get('/api/search?q=test&page=-1')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'page' in data['message'].lower()
    
    def test_search_validation_zero_page(self, client):
        """Test search with zero page number."""
        response = client.get('/api/search?q=test&page=0')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_search_validation_invalid_page_size(self, client):
        """Test search with invalid page size."""
        response = client.get('/api/search?q=test&page_size=0')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_search_pagination(self, client):
        """Test search pagination metadata."""
        response = client.get('/api/search?q=&page=1&page_size=5')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        metadata = data['metadata']
        assert metadata['page'] == 1
        assert metadata['page_size'] == 5
        assert 'total' in metadata
        assert 'total_pages' in metadata
    
    def test_stats_endpoint(self, client):
        """Test statistics endpoint."""
        response = client.get('/api/stats')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'total_documents' in data['data']
        assert isinstance(data['data']['total_documents'], int)
    
    def test_export_endpoint_json(self, client):
        """Test export endpoint with JSON format."""
        response = client.post('/api/export',
            json={'query': '', 'format': 'json'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'count' in data
        assert isinstance(data['data'], list)
    
    def test_export_endpoint_csv(self, client):
        """Test export endpoint with CSV format."""
        response = client.post('/api/export',
            json={'query': '', 'format': 'csv'}
        )
        
        assert response.status_code == 200
        assert response.content_type == 'text/csv'
        assert b'API Name' in response.data or b'PlatformID' in response.data
    
    def test_export_invalid_format(self, client):
        """Test export with invalid format."""
        response = client.post('/api/export',
            json={'query': '', 'format': 'invalid'}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_platforms_endpoint(self, client):
        """Test platforms list endpoint."""
        response = client.get('/api/platforms')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert isinstance(data['data'], list)
    
    def test_environments_endpoint(self, client):
        """Test environments list endpoint."""
        response = client.get('/api/environments')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert isinstance(data['data'], list)
    
    def test_suggestions_endpoint(self, client):
        """Test suggestions endpoint."""
        response = client.get('/api/suggestions/Platform?prefix=I')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert isinstance(data['data'], list)
