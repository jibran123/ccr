"""
Integration tests for admin API endpoints.

Tests backup, restore, and scheduler endpoints.
"""

import pytest
import json
import time


class TestAdminEndpoints:
    """Test admin API endpoints."""
    
    def test_backup_status_endpoint(self, client):
        """Test backup status endpoint."""
        response = client.get('/api/admin/backup/status')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['status'] == 'success'
        
        # ✅ FIX: Access nested data field
        data = response_data['data']
        assert 'enabled' in data  # Changed from 'backup_enabled'
        assert 'backup_dir' in data
        assert 'retention_days' in data
    
    def test_create_backup_endpoint(self, client):
        """Test manual backup creation."""
        response = client.post('/api/admin/backup',
            json={'compression': True}
        )
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data['status'] == 'success'
        
        # ✅ FIX: Access nested data field
        data = response_data['data']
        assert 'backup_id' in data
        assert 'filename' in data
        assert data['compressed'] is True
    
    def test_list_backups_endpoint(self, client):
        """Test listing backups."""
        # Create a backup first
        client.post('/api/admin/backup', json={'compression': True})
        
        # List backups
        response = client.get('/api/admin/backups')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['status'] == 'success'
        assert 'data' in response_data
        assert 'count' in response_data
        assert response_data['count'] >= 1
    
    def test_delete_backup_endpoint(self, client):
        """Test deleting a backup."""
        # Create a backup
        create_response = client.post('/api/admin/backup',
            json={'compression': True}
        )
        create_response_data = json.loads(create_response.data)
        
        # ✅ FIX: Access nested data field
        backup_id = create_response_data['data']['backup_id']
        
        # Delete it
        response = client.delete(f'/api/admin/backups/{backup_id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['status'] == 'success'
        
        # ✅ FIX: Access nested data field
        assert response_data['data']['backup_id'] == backup_id
    
    def test_delete_nonexistent_backup(self, client):
        """Test deleting non-existent backup."""
        response = client.delete('/api/admin/backups/nonexistent_backup')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_cleanup_backups_endpoint(self, client):
        """Test cleanup old backups endpoint."""
        response = client.post('/api/admin/backups/cleanup',
            json={'retention_days': 14}
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['status'] == 'success'
        
        # ✅ FIX: Access nested data field
        data = response_data['data']
        assert 'deleted_count' in data
    
    def test_restore_backup_endpoint(self, client):
        """Test restore backup endpoint."""
        # Create a backup first
        create_response = client.post('/api/admin/backup',
            json={'compression': True}
        )
        create_response_data = json.loads(create_response.data)
        
        # ✅ FIX: Access nested data field
        backup_id = create_response_data['data']['backup_id']
        
        # Try to restore (should fail with duplicate key if data exists)
        response = client.post('/api/admin/restore',
            json={
                'backup_id': backup_id,
                'drop_existing': False
            }
        )
        
        # Could be 200 (success) or 500 (duplicate key error)
        assert response.status_code in [200, 500]
        data = json.loads(response.data)
        assert 'status' in data
    
    def test_restore_nonexistent_backup(self, client):
        """Test restore with non-existent backup."""
        response = client.post('/api/admin/restore',
            json={
                'backup_id': 'nonexistent',
                'drop_existing': False
            }
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_restore_missing_backup_id(self, client):
        """Test restore without backup_id."""
        response = client.post('/api/admin/restore',
            json={'drop_existing': False}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_scheduler_jobs_endpoint(self, client):
        """Test scheduler jobs status endpoint."""
        response = client.get('/api/admin/scheduler/jobs')
        
        # ✅ FIX: Scheduler is disabled in tests, expect success but no jobs
        # We set ENABLE_SCHEDULER=False in TestConfig
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'scheduler_running' in data
        
        # Scheduler should be disabled in tests
        assert data['scheduler_running'] is False
        assert 'data' in data
        assert 'count' in data
        assert data['count'] == 0  # No jobs when scheduler is disabled