"""
Integration tests for update API endpoints.

Tests PUT/PATCH/DELETE operations on deployments.
"""

import pytest
import json
from datetime import datetime


class TestUpdateEndpoints:
    """Test API update endpoints."""
    
    @pytest.fixture
    def deployed_api(self, client):
        """Deploy a test API for update tests."""
        api_name = f'test-update-{datetime.now().timestamp()}'
        
        deploy_data = {
            'api_name': api_name,
            'platform': 'IP4',
            'environment': 'tst',
            'version': '1.0.0',
            'status': 'RUNNING',
            'updated_by': 'pytest',
            'properties': {
                'initial': 'value'
            }
        }
        
        response = client.post('/api/deploy', json=deploy_data)
        assert response.status_code == 201
        
        return api_name
    
    def test_full_update_put(self, client, deployed_api):
        """Test full update with PUT."""
        update_data = {
            'version': '2.0.0',
            'status': 'STOPPED',
            'updated_by': 'pytest-update',
            'properties': {
                'updated': 'value',
                'new_key': 'new_value'
            }
        }
        
        response = client.put(
            f'/api/apis/{deployed_api}/platforms/IP4/environments/tst',
            json=update_data
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
    
    def test_partial_update_patch(self, client, deployed_api):
        """Test partial update with PATCH."""
        update_data = {
            'version': '1.1.0',
            'updated_by': 'pytest-patch'
        }
        
        response = client.patch(
            f'/api/apis/{deployed_api}/platforms/IP4/environments/tst',
            json=update_data
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
    
    def test_status_only_update(self, client, deployed_api):
        """Test status-only update endpoint."""
        update_data = {
            'status': 'DEPLOYING',
            'updated_by': 'pytest-status'
        }
        
        response = client.patch(
            f'/api/apis/{deployed_api}/platforms/IP4/environments/tst/status',
            json=update_data
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
    
    def test_properties_only_update(self, client, deployed_api):
        """Test properties-only update endpoint."""
        update_data = {
            'updated_by': 'pytest-props',
            'properties': {
                'new_property': 'new_value',
                'another_key': 'another_value'
            }
        }
        
        response = client.patch(
            f'/api/apis/{deployed_api}/platforms/IP4/environments/tst/properties',
            json=update_data
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
    
    def test_update_nonexistent_deployment(self, client):
        """Test updating deployment that doesn't exist."""
        update_data = {
            'version': '1.0.0',
            'status': 'RUNNING',
            'updated_by': 'pytest'
        }
        
        response = client.patch(
            '/api/apis/nonexistent-api/platforms/IP4/environments/tst',
            json=update_data
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_get_deployment_details(self, client, deployed_api):
        """Test getting deployment details."""
        response = client.get(
            f'/api/apis/{deployed_api}/platforms/IP4/environments/tst'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'deployment' in data
    
    def test_delete_deployment(self, client, deployed_api):
        """Test deleting a deployment."""
        response = client.delete(
            f'/api/apis/{deployed_api}/platforms/IP4/environments/tst'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        
        # Verify it's gone
        get_response = client.get(
            f'/api/apis/{deployed_api}/platforms/IP4/environments/tst'
        )
        assert get_response.status_code == 404
