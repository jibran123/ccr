"""
Integration tests for deployment API.

Tests POST /api/deploy endpoint.
"""

import pytest
import json
from datetime import datetime


class TestDeployEndpoint:
    """Test deployment API endpoint."""
    
    def test_deploy_new_api_minimal(self, client):
        """Test deploying new API with minimal required fields."""
        deploy_data = {
            'api_name': f'test-deploy-{datetime.now().timestamp()}',
            'platform': 'IP4',
            'environment': 'tst',
            'version': '1.0.0',
            'status': 'RUNNING',
            'updated_by': 'pytest'
        }
        
        response = client.post('/api/deploy',
            json=deploy_data,
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'api_name' in data
        assert data['api_name'] == deploy_data['api_name']
    
    def test_deploy_with_properties(self, client):
        """Test deploying API with properties."""
        deploy_data = {
            'api_name': f'test-props-{datetime.now().timestamp()}',
            'platform': 'IP4',
            'environment': 'tst',
            'version': '1.0.0',
            'status': 'RUNNING',
            'updated_by': 'pytest',
            'properties': {
                'api.id': '12345',
                'api.port': '8080',
                'feature.flag': 'enabled'
            }
        }
        
        response = client.post('/api/deploy',
            json=deploy_data,
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['status'] == 'success'
    
    def test_deploy_update_existing(self, client):
        """Test updating existing deployment (upsert behavior)."""
        api_name = f'test-upsert-{datetime.now().timestamp()}'
        
        # First deployment
        deploy_data_v1 = {
            'api_name': api_name,
            'platform': 'IP4',
            'environment': 'tst',
            'version': '1.0.0',
            'status': 'RUNNING',
            'updated_by': 'pytest'
        }
        
        response1 = client.post('/api/deploy', json=deploy_data_v1)
        assert response1.status_code == 201
        
        # Update with new version
        deploy_data_v2 = {
            'api_name': api_name,
            'platform': 'IP4',
            'environment': 'tst',
            'version': '2.0.0',  # Changed
            'status': 'RUNNING',
            'updated_by': 'pytest'
        }
        
        response2 = client.post('/api/deploy', json=deploy_data_v2)
        assert response2.status_code in [200, 201]  # Could be update or insert
        
        data = json.loads(response2.data)
        assert data['status'] == 'success'
    
    def test_deploy_missing_required_field(self, client):
        """Test deploy with missing required field."""
        deploy_data = {
            'api_name': 'test-missing',
            'platform': 'IP4',
            # Missing 'environment'
            'version': '1.0.0',
            'status': 'RUNNING',
            'updated_by': 'pytest'
        }
        
        response = client.post('/api/deploy', json=deploy_data)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'environment' in data['message'].lower()
    
    def test_deploy_invalid_platform(self, client):
        """Test deploy with invalid platform."""
        deploy_data = {
            'api_name': 'test-invalid',
            'platform': 'INVALID_PLATFORM',
            'environment': 'tst',
            'version': '1.0.0',
            'status': 'RUNNING',
            'updated_by': 'pytest'
        }
        
        response = client.post('/api/deploy', json=deploy_data)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_deploy_invalid_status(self, client):
        """Test deploy with invalid status."""
        deploy_data = {
            'api_name': 'test-invalid-status',
            'platform': 'IP4',
            'environment': 'tst',
            'version': '1.0.0',
            'status': 'INVALID_STATUS',
            'updated_by': 'pytest'
        }
        
        response = client.post('/api/deploy', json=deploy_data)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_deploy_multiple_platforms(self, client):
        """Test deploying same API to different platforms."""
        api_name = f'test-multi-platform-{datetime.now().timestamp()}'
        
        # Deploy to IP4
        deploy_ip4 = {
            'api_name': api_name,
            'platform': 'IP4',
            'environment': 'tst',
            'version': '1.0.0',
            'status': 'RUNNING',
            'updated_by': 'pytest'
        }
        
        response1 = client.post('/api/deploy', json=deploy_ip4)
        assert response1.status_code == 201
        
        # Deploy same API to IP3
        deploy_ip3 = {
            'api_name': api_name,
            'platform': 'IP3',
            'environment': 'tst',
            'version': '1.0.0',
            'status': 'RUNNING',
            'updated_by': 'pytest'
        }
        
        response2 = client.post('/api/deploy', json=deploy_ip3)
        assert response2.status_code in [200, 201]
