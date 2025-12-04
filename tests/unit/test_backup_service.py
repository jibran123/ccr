"""
Unit tests for BackupService.

Tests backup creation, listing, deletion, cleanup, and restore functionality.
"""

import pytest
import os
import json
import gzip
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.backup_service import BackupService


class TestBackupService:
    """Test BackupService functionality."""
    
    @pytest.fixture
    def backup_service(self, temp_backup_dir):
        """Create BackupService instance for testing without MongoDB connection."""
        service = BackupService(
            mongo_uri='mongodb://test:27017',
            db_name='test_db',
            backup_dir=temp_backup_dir
        )
        return service
    
    def test_backup_service_initialization(self, temp_backup_dir):
        """Test BackupService initializes correctly."""
        service = BackupService(
            mongo_uri='mongodb://test:27017',
            db_name='test_db',
            backup_dir=temp_backup_dir
        )
        
        # Compare Path objects or convert to string
        assert str(service.backup_dir) == str(temp_backup_dir)
        assert os.path.exists(temp_backup_dir)
    
    def test_create_backup_directory_creation(self):
        """Test backup directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = os.path.join(temp_dir, 'nonexistent', 'backups')
            
            service = BackupService(
                mongo_uri='mongodb://test:27017',
                db_name='test_db',
                backup_dir=backup_dir
            )
            
            assert os.path.exists(backup_dir)
    
    @patch('app.services.backup_service.MongoClient')
    def test_create_backup_success(self, mock_client, backup_service, sample_backup_data):
        """Test successful backup creation."""
        # Mock the MongoClient that's created inside create_backup()
        mock_collection = MagicMock()
        mock_collection.find.return_value = sample_backup_data
        
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ['test_collection']
        mock_db.__getitem__.return_value = mock_collection
        
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client.return_value = mock_client_instance
        
        result = backup_service.create_backup(compression=True)
        
        assert result['success'] is True
        assert 'backup_id' in result
        assert 'filename' in result
        assert result['compressed'] is True
        assert result['total_documents'] == len(sample_backup_data)
        assert result['size_mb'] >= 0
        
        # Verify backup file exists
        backup_path = backup_service.backup_dir / result['filename']
        assert os.path.exists(backup_path)
        assert str(backup_path).endswith('.json.gz')
    
    @patch('app.services.backup_service.MongoClient')
    def test_create_backup_uncompressed(self, mock_client, backup_service, sample_backup_data):
        """Test uncompressed backup creation."""
        # Mock the MongoClient
        mock_collection = MagicMock()
        mock_collection.find.return_value = sample_backup_data
        
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ['test_collection']
        mock_db.__getitem__.return_value = mock_collection
        
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client.return_value = mock_client_instance
        
        result = backup_service.create_backup(compression=False)
        
        assert result['success'] is True
        assert result['compressed'] is False
        assert result['filename'].endswith('.json')
        
        # Verify file is readable JSON
        backup_path = backup_service.backup_dir / result['filename']
        with open(backup_path, 'r') as f:
            data = json.load(f)
            assert 'metadata' in data
            assert 'collections' in data
    
    def test_list_backups_empty(self, backup_service):
        """Test listing backups when directory is empty."""
        result = backup_service.list_backups()
        
        # list_backups() returns a list, not dict
        assert isinstance(result, list)
        assert len(result) == 0
    
    @patch('app.services.backup_service.MongoClient')
    def test_list_backups_with_files(self, mock_client, backup_service, sample_backup_data):
        """Test listing backups with multiple backup files."""
        # Mock the MongoClient
        mock_collection = MagicMock()
        mock_collection.find.return_value = sample_backup_data
        
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ['test_collection']
        mock_db.__getitem__.return_value = mock_collection
        
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client.return_value = mock_client_instance
        
        # Add delays between backups to avoid timestamp collision
        backup_service.create_backup(compression=True)
        time.sleep(1.1)  # Ensure different timestamps
        backup_service.create_backup(compression=True)
        time.sleep(1.1)
        backup_service.create_backup(compression=False)
        
        result = backup_service.list_backups()
        
        # list_backups() returns a list
        assert isinstance(result, list)
        assert len(result) == 3
        
        # Verify backup metadata
        for backup in result:
            assert 'backup_id' in backup
            assert 'filename' in backup
            assert 'timestamp' in backup
            assert 'size_bytes' in backup
            assert 'size_mb' in backup
            assert 'compressed' in backup
            assert 'age_days' in backup
    
    @patch('app.services.backup_service.MongoClient')
    def test_delete_backup_success(self, mock_client, backup_service, sample_backup_data):
        """Test successful backup deletion."""
        # Mock the MongoClient
        mock_collection = MagicMock()
        mock_collection.find.return_value = sample_backup_data
        
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ['test_collection']
        mock_db.__getitem__.return_value = mock_collection
        
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client.return_value = mock_client_instance
        
        # Create a backup
        create_result = backup_service.create_backup(compression=True)
        backup_id = create_result['backup_id']
        
        # Delete it - delete_backup() returns True, not a dict
        result = backup_service.delete_backup(backup_id)
        assert result is True
        
        # Verify file is gone
        list_result = backup_service.list_backups()
        assert len(list_result) == 0
    
    def test_delete_backup_not_found(self, backup_service):
        """Test deleting non-existent backup."""
        # delete_backup() raises FileNotFoundError, not returning dict
        with pytest.raises(FileNotFoundError) as exc_info:
            backup_service.delete_backup('nonexistent_backup')
        
        assert 'not found' in str(exc_info.value).lower()
    
    @patch('app.services.backup_service.MongoClient')
    def test_cleanup_old_backups(self, mock_client, backup_service, sample_backup_data):
        """Test cleanup of old backups based on retention policy."""
        # Mock the MongoClient
        mock_collection = MagicMock()
        mock_collection.find.return_value = sample_backup_data
        
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ['test_collection']
        mock_db.__getitem__.return_value = mock_collection
        
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client.return_value = mock_client_instance
        
        # Create a new backup
        backup2 = backup_service.create_backup(compression=True)
        
        # ✅ FIX: Manually create an old backup file with old timestamp in filename
        old_date = datetime.now() - timedelta(days=20)
        old_timestamp_str = old_date.strftime('%Y%m%d_%H%M%S')
        old_filename = f"backup_test_db_{old_timestamp_str}.json.gz"
        old_backup_path = backup_service.backup_dir / old_filename
        
        # Create a minimal valid backup file
        from bson import json_util
        old_backup_data = {
            'metadata': {
                'database': 'test_db',
                'timestamp': old_date.isoformat() + 'Z',
                'collections': 1,
                'compression': True
            },
            'collections': {
                'test_collection': []
            }
        }
        
        # Write the old backup file
        with gzip.open(old_backup_path, 'wt', encoding='utf-8') as f:
            f.write(json_util.dumps(old_backup_data))
        
        # Verify we have 2 backups before cleanup
        backups_before = backup_service.list_backups()
        assert len(backups_before) == 2, f"Expected 2 backups, got {len(backups_before)}"
        
        # Cleanup backups older than 14 days
        result = backup_service.cleanup_old_backups(retention_days=14)
        
        # Check cleanup result
        assert result['success'] is True
        assert result['deleted_count'] == 1, f"Expected 1 deleted, got {result['deleted_count']}"
        
        # Verify only new backup remains
        list_result = backup_service.list_backups()
        assert len(list_result) == 1, f"Expected 1 backup remaining, got {len(list_result)}"
    
    @patch('app.services.backup_service.MongoClient')
    def test_get_backup_info_success(self, mock_client, backup_service, sample_backup_data):
        """Test getting backup information."""
        # Mock the MongoClient
        mock_collection = MagicMock()
        mock_collection.find.return_value = sample_backup_data
        
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ['test_collection']
        mock_db.__getitem__.return_value = mock_collection
        
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client.return_value = mock_client_instance
        
        # Create a backup
        create_result = backup_service.create_backup(compression=True)
        backup_id = create_result['backup_id']
        
        # Get its info from list_backups
        backups = backup_service.list_backups()
        info = next((b for b in backups if b['backup_id'] == backup_id), None)
        
        assert info is not None
        assert info['backup_id'] == backup_id
        assert 'filename' in info
        assert 'size_bytes' in info
        assert 'compressed' in info
    
    def test_get_backup_info_not_found(self, backup_service):
        """Test getting info for non-existent backup."""
        backups = backup_service.list_backups()
        info = next((b for b in backups if b['backup_id'] == 'nonexistent'), None)
        
        assert info is None
    
    @patch('app.services.backup_service.MongoClient')
    def test_restore_backup_basic(self, mock_client, backup_service, sample_backup_data):
        """Test basic restore functionality (without drop_existing)."""
        # Mock the MongoClient for create_backup
        mock_collection = MagicMock()
        mock_collection.find.return_value = sample_backup_data
        mock_collection.insert_many.return_value = MagicMock(inserted_ids=['id1', 'id2'])
        
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ['test_collection']
        mock_db.__getitem__.return_value = mock_collection
        
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client.return_value = mock_client_instance
        
        # Create a backup first
        create_result = backup_service.create_backup(compression=True)
        backup_id = create_result['backup_id']
        
        # Restore it
        result = backup_service.restore_backup(backup_id, drop_existing=False)
        
        assert result['success'] is True
        assert result['backup_id'] == backup_id
        assert 'total_documents' in result
        
        # Verify insert_many was called
        mock_collection.insert_many.assert_called()
    
    def test_restore_backup_not_found(self, backup_service):
        """Test restore with non-existent backup."""
        with pytest.raises(Exception) as exc_info:
            backup_service.restore_backup('nonexistent', drop_existing=False)
        
        assert 'not found' in str(exc_info.value).lower()