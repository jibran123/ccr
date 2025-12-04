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
    
    # Use localhost instead of 'mongo' hostname
    # Tests run on host machine, MongoDB port is mapped to localhost:27017
    MONGO_URI = 'mongodb://localhost:27017/'
    MONGO_DB = 'ccr_test'
    MONGO_COLLECTION = 'apis_test'
    
    # Also set the component values to ensure consistency
    MONGO_HOST = 'localhost'
    MONGO_PORT = 27017
    
    # Disable auth for easier testing
    AUTH_ENABLED = False
    
    # ✅ FIX: Set a valid backup directory for tests
    BACKUP_DIR = '/tmp/ccr_test_backups'
    BACKUP_ENABLED = True
    
    # Disable scheduler for tests
    ENABLE_SCHEDULER = False
    
    # Testing flag
    TESTING = True
    
    # Test secrets
    SECRET_KEY = 'test-secret-key-for-testing-only'
    JWT_SECRET_KEY = 'test-jwt-secret-key-for-testing-only'
    JWT_ADMIN_KEY = 'dev-admin-key-ONLY-FOR-DEVELOPMENT'

    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False

    # Disable brute force lockout for tests (or set high limits)
    AUTH_LOCKOUT_ENABLED = False


@pytest.fixture
def app():
    """
    Create Flask app for testing.
    
    Returns:
        Flask app instance configured for testing
    """
    # Create test backup directory if it doesn't exist
    test_backup_dir = '/tmp/ccr_test_backups'
    os.makedirs(test_backup_dir, exist_ok=True)
    
    # Set environment variables BEFORE creating app to ensure they're picked up
    os.environ['MONGO_HOST'] = 'localhost'
    os.environ['MONGO_PORT'] = '27017'
    os.environ['MONGO_DB'] = 'ccr_test'
    os.environ['MONGO_COLLECTION'] = 'apis_test'
    os.environ['AUTH_ENABLED'] = 'false'
    os.environ['BACKUP_ENABLED'] = 'true'
    os.environ['BACKUP_DIR'] = test_backup_dir  # ✅ FIX: Set backup directory
    os.environ['ENABLE_SCHEDULER'] = 'false'
    
    # Create app with TestConfig
    app = create_app(TestConfig)
    app.config['TESTING'] = True
    
    # Ensure config values are set correctly
    app.config['MONGO_DB'] = 'ccr_test'
    app.config['MONGO_COLLECTION'] = 'apis_test'
    app.config['BACKUP_DIR'] = test_backup_dir  # ✅ FIX: Ensure backup dir is set
    
    yield app
    
    # Cleanup: Remove test backup directory after tests
    if os.path.exists(test_backup_dir):
        shutil.rmtree(test_backup_dir, ignore_errors=True)
    
    # Cleanup environment variables after test
    for key in ['MONGO_HOST', 'MONGO_PORT', 'MONGO_DB', 'MONGO_COLLECTION', 
                'AUTH_ENABLED', 'BACKUP_ENABLED', 'BACKUP_DIR', 'ENABLE_SCHEDULER']:
        os.environ.pop(key, None)


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
        'API Name': 'test-api',
        'Platform': [
            {
                'PlatformID': 'IP4',
                'Environment': [
                    {
                        'environmentID': 'dev',
                        'version': '1.0.0',
                        'status': 'RUNNING',
                        'deploymentDate': datetime.utcnow().isoformat() + 'Z',
                        'lastUpdated': datetime.utcnow().isoformat() + 'Z',
                        'updatedBy': 'test-user',
                        'Properties': {
                            'api.id': '12345',
                            'api.endpoint': 'https://api.test.com'
                        }
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_backup_data():
    """
    Sample backup/restore data for testing.
    
    Returns:
        List of sample API documents
    """
    return [
        {
            '_id': 'test-api-1',
            'API Name': 'test-api-1',
            'Platform': [
                {
                    'PlatformID': 'IP4',
                    'Environment': [
                        {
                            'environmentID': 'dev',
                            'version': '1.0.0',
                            'status': 'RUNNING',
                            'deploymentDate': datetime.utcnow().isoformat() + 'Z',
                            'lastUpdated': datetime.utcnow().isoformat() + 'Z',
                            'updatedBy': 'test-user',
                            'Properties': {}
                        }
                    ]
                }
            ]
        },
        {
            '_id': 'test-api-2',
            'API Name': 'test-api-2',
            'Platform': [
                {
                    'PlatformID': 'IP5',
                    'Environment': [
                        {
                            'environmentID': 'prd',
                            'version': '2.0.0',
                            'status': 'STOPPED',
                            'deploymentDate': datetime.utcnow().isoformat() + 'Z',
                            'lastUpdated': datetime.utcnow().isoformat() + 'Z',
                            'updatedBy': 'admin',
                            'Properties': {}
                        }
                    ]
                }
            ]
        }
    ]


@pytest.fixture
def admin_headers():
    """
    Headers for admin API requests.

    Returns:
        Dictionary with admin headers
    """
    return {
        'Content-Type': 'application/json',
        'X-Admin-Key': 'dev-admin-key-ONLY-FOR-DEVELOPMENT'
    }


@pytest.fixture
def auth_token(client):
    """
    Get a valid JWT authentication token for testing.

    Args:
        client: Flask test client

    Returns:
        Valid JWT token string
    """
    # If auth is disabled in tests, return empty string
    return ''


@pytest.fixture
def live_auth_tokens(base_url, admin_headers):
    """
    Generate authentication tokens from the live server for integration tests.

    This fixture generates both user and admin tokens by calling the live server's
    /api/auth/token endpoint. Use this for integration tests that need real tokens.

    Args:
        base_url: Base URL of the live server
        admin_headers: Admin headers fixture with X-Admin-Key

    Returns:
        Dictionary with 'user' and 'admin' token objects
    """
    import requests

    # Generate user token
    user_response = requests.post(
        f"{base_url}/api/auth/token",
        headers=admin_headers,
        json={"username": "test_integration_user", "role": "user"}
    )

    # Generate admin token
    admin_response = requests.post(
        f"{base_url}/api/auth/token",
        headers=admin_headers,
        json={"username": "test_integration_admin", "role": "admin"}
    )

    if user_response.status_code != 200 or admin_response.status_code != 200:
        pytest.fail(f"Failed to generate auth tokens. User: {user_response.status_code}, Admin: {admin_response.status_code}")

    return {
        'user': user_response.json()['data'],
        'admin': admin_response.json()['data']
    }


@pytest.fixture
def user_auth_headers(live_auth_tokens):
    """
    Get authorization headers with a valid user token.

    Args:
        live_auth_tokens: Fixture that generates tokens from live server

    Returns:
        Dictionary with Authorization header containing user token
    """
    return {
        'Authorization': f"Bearer {live_auth_tokens['user']['access_token']}",
        'Content-Type': 'application/json'
    }


@pytest.fixture
def admin_auth_headers(live_auth_tokens):
    """
    Get authorization headers with a valid admin token.

    Args:
        live_auth_tokens: Fixture that generates tokens from live server

    Returns:
        Dictionary with Authorization header containing admin token
    """
    return {
        'Authorization': f"Bearer {live_auth_tokens['admin']['access_token']}",
        'Content-Type': 'application/json'
    }


# ========== Security Testing Fixtures ==========

@pytest.fixture
def base_url():
    """
    Base URL for API testing.

    Returns:
        Base URL string (default: http://localhost:5000)
    """
    return os.getenv('TEST_BASE_URL', 'http://localhost:5000')


@pytest.fixture
def valid_admin_key():
    """
    Valid admin key for authentication tests.

    Returns:
        Admin key string
    """
    return 'dev-admin-key-ONLY-FOR-DEVELOPMENT'


@pytest.fixture
def invalid_admin_key():
    """
    Invalid admin key for negative testing.

    Returns:
        Invalid admin key string
    """
    return 'wrong-admin-key-invalid'


@pytest.fixture
def security_headers():
    """
    Common security headers for testing.

    Returns:
        Dictionary of security headers
    """
    return {
        'Content-Type': 'application/json',
        'X-Admin-Key': 'dev-admin-key-ONLY-FOR-DEVELOPMENT'
    }


@pytest.fixture
def test_user_credentials():
    """
    Test user credentials for authentication tests.

    Returns:
        Dictionary with username and role
    """
    return {
        'username': 'test_user',
        'role': 'user'
    }


@pytest.fixture
def test_admin_credentials():
    """
    Test admin credentials for authentication tests.

    Returns:
        Dictionary with username and role
    """
    return {
        'username': 'test_admin',
        'role': 'admin'
    }


# ========== Command-line Options ==========

def pytest_addoption(parser):
    """Add custom command-line options to pytest."""
    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="Skip slow tests"
    )
    parser.addoption(
        "--run-load-tests",
        action="store_true",
        default=False,
        help="Run load tests (requires Locust)"
    )
    parser.addoption(
        "--base-url",
        action="store",
        default="http://localhost:5000",
        help="Base URL for API testing"
    )


def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "slow: mark test as slow to run"
    )
    config.addinivalue_line(
        "markers", "load: mark test as load/stress test"
    )


@pytest.fixture(autouse=True, scope='function')
def cleanup_auth_state(app):
    """
    Clean up authentication state between tests.

    Clears rate limiters and auth lockouts to prevent test pollution.
    """
    yield

    # Clean up after each test
    try:
        # Clear rate limiter storage if it exists
        if hasattr(app, 'limiter') and hasattr(app.limiter, 'storage'):
            app.limiter.reset()
    except Exception:
        pass  # Ignore errors in cleanup

    try:
        # Clear auth lockouts from database
        if hasattr(app, 'db_service') and app.db_service:
            db = app.db_service.db
            if db is not None:
                db['auth_lockouts'].delete_many({})
                db['token_blacklist'].delete_many({})
    except Exception:
        pass  # Ignore errors in cleanup