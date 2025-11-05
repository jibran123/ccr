"""
Unit tests for BackupService.

Tests backup creation, listing, deletion, cleanup, and restore functionality.
"""

import pytest
import os
import json
import gzip
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.services.backup_service import BackupService


class TestBackupService:
    """Test BackupService functionality."""
    
    @pytest.fixture
    def backup_service(self, temp_backup_dir, mock_mongodb):
        """Create BackupService instance for testing."""
        with patch('app.services.backup_service.MongoClient') as mock_client:
            mock_client.return_value.__getitem__.return_value.__getitem__.return_value = mock_mongodb
            
            service = BackupService(
                mongo_uri='mongodb://test:27017',
                db_name='test_db',
                backup_dir=temp_backup_dir
            )
            service.collection = mock_mongodb
            
            return service
    
    def test_backup_service_initialization(self, temp_backup_dir):
        """Test BackupService initializes correctly."""
        with patch('app.services.backup_service.MongoClient'):
            service = BackupService(
                mongo_uri='mongodb://test:27017',
                db_name='test_db',
                backup_dir=temp_backup_dir
            )
            
            assert service.backup_dir == temp_backup_dir
            assert os.path.exists(temp_backup_dir)
    
    def test_create_backup_directory_creation(self, mock_mongodb):
        """Test backup directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = os.path.join(temp_dir, 'nonexistent', 'backups')
            
            with patch('app.services.backup_service.MongoClient') as mock_client:
                mock_client.return_value.__getitem__.return_value.__getitem__.return_value = mock_mongodb
                mock_mongodb.find.return_value = []
                
                service = BackupService(
                    mongo_uri='mongodb://test:27017',
                    db_name='test_db',
                    backup_dir=backup_dir
                )
                
                assert os.path.exists(backup_dir)
    
    def test_create_backup_success(self, backup_service, mock_mongodb, sample_backup_data):
        """Test successful backup creation."""
        # Mock MongoDB find to return sample data
        mock_mongodb.find.return_value = sample_backup_data
        
        result = backup_service.create_backup(compression=True)
        
        assert result['status'] == 'success'
        assert 'backup_id' in result
        assert 'filename' in result
        assert result['compressed'] is True
        assert result['total_documents'] == len(sample_backup_data)
        assert result['size_mb'] > 0
        
        # Verify backup file exists
        backup_path = os.path.join(backup_service.backup_dir, result['filename'])
        assert os.path.exists(backup_path)
        assert backup_path.endswith('.json.gz')
    
    def test_create_backup_uncompressed(self, backup_service, mock_mongodb, sample_backup_data):
        """Test uncompressed backup creation."""
        mock_mongodb.find.return_value = sample_backup_data
        
        result = backup_service.create_backup(compression=False)
        
        assert result['status'] == 'success'
        assert result['compressed'] is False
        assert result['filename'].endswith('.json')
        
        # Verify file is readable JSON
        backup_path = os.path.join(backup_service.backup_dir, result['filename'])
        with open(backup_path, 'r') as f:
            data = json.load(f)
            assert len(data) == len(sample_backup_data)
    
    def test_list_backups_empty(self, backup_service):
        """Test listing backups when directory is empty."""
        result = backup_service.list_backups()
        
        assert result['status'] == 'success'
        assert result['count'] == 0
        assert result['data'] == []
    
    def test_list_backups_with_files(self, backup_service, mock_mongodb, sample_backup_data):
        """Test listing backups with multiple backup files."""
        mock_mongodb.find.return_value = sample_backup_data
        
        # Create 3 backups
        backup_service.create_backup(compression=True)
        backup_service.create_backup(compression=True)
        backup_service.create_backup(compression=False)
        
        result = backup_service.list_backups()
        
        assert result['status'] == 'success'
        assert result['count'] == 3
        assert len(result['data']) == 3
        
        # Verify backup metadata
        for backup in result['data']:
            assert 'backup_id' in backup
            assert 'filename' in backup
            assert 'timestamp' in backup
            assert 'size_bytes' in backup
            assert 'size_mb' in backup
            assert 'compressed' in backup
            assert 'age_days' in backup
    
    def test_delete_backup_success(self, backup_service, mock_mongodb, sample_backup_data):
        """Test successful backup deletion."""
        mock_mongodb.find.return_value = sample_backup_data
        
        # Create a backup
        create_result = backup_service.create_backup(compression=True)
        backup_id = create_result['backup_id']
        
        # Delete it
        delete_result = backup_service.delete_backup(backup_id)
        
        assert delete_result['status'] == 'success'
        assert delete_result['backup_id'] == backup_id
        
        # Verify file is gone
        list_result = backup_service.list_backups()
        assert list_result['count'] == 0
    
    def test_delete_backup_not_found(self, backup_service):
        """Test deleting non-existent backup."""
        result = backup_service.delete_backup('nonexistent_backup')
        
        assert result['status'] == 'error'
        assert 'not found' in result['message'].lower()
    
    def test_cleanup_old_backups(self, backup_service, mock_mongodb, sample_backup_data):
        """Test cleanup of old backups based on retention policy."""
        mock_mongodb.find.return_value = sample_backup_data
        
        # Create backups
        backup1 = backup_service.create_backup(compression=True)
        backup2 = backup_service.create_backup(compression=True)
        
        # Make one backup look old by modifying its timestamp
        old_backup_path = os.path.join(backup_service.backup_dir, backup1['filename'])
        old_time = (datetime.now() - timedelta(days=20)).timestamp()
        os.utime(old_backup_path, (old_time, old_time))
        
        # Cleanup backups older than 14 days
        result = backup_service.cleanup_old_backups(retention_days=14)
        
        assert result['status'] == 'success'
        assert result['deleted_count'] == 1
        assert len(result['deleted_backups']) == 1
        
        # Verify only new backup remains
        list_result = backup_service.list_backups()
        assert list_result['count'] == 1
    
    def test_get_backup_info_success(self, backup_service, mock_mongodb, sample_backup_data):
        """Test getting backup information."""
        mock_mongodb.find.return_value = sample_backup_data
        
        # Create a backup
        create_result = backup_service.create_backup(compression=True)
        backup_id = create_result['backup_id']
        
        # Get its info
        info = backup_service.get_backup_info(backup_id)
        
        assert info is not None
        assert info['backup_id'] == backup_id
        assert 'filename' in info
        assert 'size_bytes' in info
        assert 'compressed' in info
    
    def test_get_backup_info_not_found(self, backup_service):
        """Test getting info for non-existent backup."""
        info = backup_service.get_backup_info('nonexistent')
        
        assert info is None
    
    def test_restore_backup_basic(self, backup_service, mock_mongodb, sample_backup_data):
        """Test basic restore functionality (without drop_existing)."""
        # Create a backup first
        mock_mongodb.find.return_value = sample_backup_data
        create_result = backup_service.create_backup(compression=True)
        backup_id = create_result['backup_id']
        
        # Mock insert_many for restore
        mock_mongodb.insert_many.return_value = Mock(inserted_ids=['id1', 'id2'])
        
        # Restore it
        result = backup_service.restore_backup(backup_id, drop_existing=False)
        
        assert result['status'] == 'success'
        assert result['backup_id'] == backup_id
        assert result['total_documents'] == len(sample_backup_data)
        
        # Verify insert_many was called
        mock_mongodb.insert_many.assert_called_once()
    
    def test_restore_backup_not_found(self, backup_service):
        """Test restore with non-existent backup."""
        with pytest.raises(Exception) as exc_info:
            backup_service.restore_backup('nonexistent', drop_existing=False)
        
        assert 'not found' in str(exc_info.value).lower()
