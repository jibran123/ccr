"""
Pytest fixtures for testing.

Provides common test fixtures like Flask app, test client, and mock database.
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime
from unittest.mock import Mock, patch

from app import create_app
from app.config import Config


class TestConfig(Config):
    """Test configuration with overrides."""
    
    # Use test database
    MONGO_URI = 'mongodb://mongo:27017/'
    MONGO_DB = 'ccr_test'
    MONGO_COLLECTION = 'apis_test'
    
    # Disable auth for easier testing
    AUTH_ENABLED = False
    
    # Use temp directory for backups
    BACKUP_DIR = None  # Will be set per test
    BACKUP_ENABLED = True
    
    # Testing flag
    TESTING = True


@pytest.fixture
def app():
    """
    Create Flask app for testing.
    
    Returns:
        Flask app instance configured for testing
    """
    app = create_app(TestConfig)
    app.config['TESTING'] = True
    
    yield app


@pytest.fixture
def client(app):
    """
    Create Flask test client.
    
    Args:
        app: Flask app fixture
        
    Returns:
        Flask test client
    """
    return app.test_client()


@pytest.fixture
def temp_backup_dir():
    """
    Create temporary directory for backup tests.
    
    Yields:
        Path to temporary directory
    """
    temp_dir = tempfile.mkdtemp(prefix='ccr_backup_test_')
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_mongodb():
    """
    Mock MongoDB collection for unit tests.
    
    Returns:
        Mock MongoDB collection object
    """
    mock_collection = Mock()
    
    # Mock common MongoDB operations
    mock_collection.find.return_value = []
    mock_collection.find_one.return_value = None
    mock_collection.insert_one.return_value = Mock(inserted_id='test-id')
    mock_collection.insert_many.return_value = Mock(inserted_ids=['id1', 'id2'])
    mock_collection.update_one.return_value = Mock(matched_count=1, modified_count=1)
    mock_collection.delete_one.return_value = Mock(deleted_count=1)
    mock_collection.count_documents.return_value = 0
    mock_collection.aggregate.return_value = []
    
    return mock_collection


@pytest.fixture
def sample_api_data():
    """
    Sample API deployment data for testing.
    
    Returns:
        Dictionary with sample API data
    """
    return {
        '_id': 'test-api',
        'API Name': 'test-api',
        'Platform': [
            {
                'PlatformID': 'IP4',
                'Environment': [
                    {
                        'environmentID': 'tst',
                        'version': '1.0.0',
                        'deploymentDate': datetime.utcnow().isoformat() + 'Z',
                        'lastUpdated': datetime.utcnow().isoformat() + 'Z',
                        'updatedBy': 'test-user',
                        'status': 'RUNNING',
                        'Properties': {
                            'api.name': 'test-api',
                            'api.version': '1.0.0',
                            'env': 'tst'
                        }
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_backup_data():
    """
    Sample backup data for testing.
    
    Returns:
        List of sample API documents
    """
    return [
        {
            '_id': 'api-1',
            'API Name': 'api-1',
            'Platform': [
                {
                    'PlatformID': 'IP4',
                    'Environment': [
                        {
                            'environmentID': 'tst',
                            'version': '1.0.0',
                            'status': 'RUNNING',
                            'Properties': {}
                        }
                    ]
                }
            ]
        },
        {
            '_id': 'api-2',
            'API Name': 'api-2',
            'Platform': [
                {
                    'PlatformID': 'IP3',
                    'Environment': [
                        {
                            'environmentID': 'prd',
                            'version': '2.0.0',
                            'status': 'RUNNING',
                            'Properties': {}
                        }
                    ]
                }
            ]
        }
    ]


@pytest.fixture
def auth_headers():
    """
    Generate authentication headers for protected endpoints.
    
    Returns:
        Dictionary with Authorization header
    """
    # If auth is disabled in tests, return empty headers
    return {}