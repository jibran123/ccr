"""
Unit Tests: TokenService
Tests for JWT token management service
Week 13-14: Testing & Quality Assurance

These tests use proper Flask app context with the `app` fixture from conftest.py.
Unit tests focus on testing TokenService logic in isolation with mocked database.
Integration tests (test_auth_integration.py) test the full workflow.
"""

import pytest
import jwt
import secrets
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from freezegun import freeze_time

from app.services.token_service import TokenService


class TestTokenServiceInitialization:
    """Test TokenService initialization."""

    def test_init_creates_collections(self, app):
        """Test that initialization creates collection references."""
        with app.app_context():
            # Arrange
            mock_db_service = Mock()
            mock_db_service.db_name = 'test_db'

            # Create proper mock client with __getitem__ support
            mock_client = MagicMock()
            mock_db_service.client = mock_client

            # Mock collections
            mock_refresh_collection = MagicMock()
            mock_blacklist_collection = MagicMock()

            # Configure mock client to return collections
            mock_db = MagicMock()
            mock_db.__getitem__.side_effect = lambda col: (
                mock_refresh_collection if col == 'refresh_tokens'
                else mock_blacklist_collection if col == 'token_blacklist'
                else MagicMock()
            )
            mock_client.__getitem__.return_value = mock_db

            # Act
            service = TokenService(mock_db_service)

            # Assert
            assert service.db == mock_db_service
            assert service.db_client == mock_client
            assert service.db_name == 'test_db'
            assert service.refresh_tokens_collection is not None
            assert service.blacklist_collection is not None

    def test_init_creates_indexes(self, app):
        """Test that initialization creates database indexes."""
        with app.app_context():
            # Arrange
            mock_db_service = Mock()
            mock_db_service.db_name = 'test_db'

            # Create proper mock client
            mock_client = MagicMock()
            mock_db_service.client = mock_client

            mock_refresh_collection = MagicMock()
            mock_blacklist_collection = MagicMock()

            # Configure mock to return specific collections
            mock_db = MagicMock()
            mock_db.__getitem__.side_effect = lambda col: (
                mock_refresh_collection if col == 'refresh_tokens'
                else mock_blacklist_collection if col == 'token_blacklist'
                else MagicMock()
            )
            mock_client.__getitem__.return_value = mock_db

            # Act
            service = TokenService(mock_db_service)

            # Assert
            assert mock_refresh_collection.create_index.called
            assert mock_blacklist_collection.create_index.called


class TestAccessTokenGeneration:
    """Test access token generation."""

    @pytest.fixture
    def token_service(self, app):
        """Create TokenService with mocked dependencies."""
        with app.app_context():
            mock_db_service = Mock()
            mock_db_service.client = MagicMock()
            mock_db_service.db_name = 'test_db'

            # Mock collections
            mock_collection = Mock()
            mock_collection.create_index = Mock()

            mock_db = MagicMock()
            mock_db.__getitem__.return_value = mock_collection
            mock_db_service.client.__getitem__.return_value = mock_db

            service = TokenService(mock_db_service)
            return service

    @freeze_time("2025-01-01 12:00:00")
    def test_generate_access_token_success(self, app, token_service):
        """Test successful access token generation."""
        with app.app_context():
            # Arrange
            username = 'test_user'
            role = 'user'

            # Act
            result = token_service.generate_access_token(username, role)

            # Assert
            assert 'token' in result
            assert result['token_type'] == 'access'
            assert result['username'] == username
            assert result['role'] == role
            assert 'expires_at' in result
            assert result['expires_in'] == 15 * 60  # 15 minutes in seconds

            # Verify token can be decoded
            decoded = jwt.decode(
                result['token'],
                app.config['JWT_SECRET_KEY'],
                algorithms=[app.config['JWT_ALGORITHM']]
            )
            assert decoded['username'] == username
            assert decoded['role'] == role
            assert decoded['token_type'] == 'access'
            assert 'jti' in decoded
            assert decoded['iss'] == 'ccr-api-manager'

    def test_generate_access_token_admin_role(self, app, token_service):
        """Test access token generation with admin role."""
        with app.app_context():
            # Arrange
            username = 'admin_user'
            role = 'admin'

            # Act
            result = token_service.generate_access_token(username, role)

            # Assert
            decoded = jwt.decode(
                result['token'],
                app.config['JWT_SECRET_KEY'],
                algorithms=[app.config['JWT_ALGORITHM']]
            )
            assert decoded['role'] == 'admin'

    def test_generate_access_token_contains_jti(self, app, token_service):
        """Test that access token contains unique JTI."""
        with app.app_context():
            # Arrange
            username = 'test_user'

            # Act
            result1 = token_service.generate_access_token(username)
            result2 = token_service.generate_access_token(username)

            # Assert - JTIs should be different
            decoded1 = jwt.decode(
                result1['token'],
                app.config['JWT_SECRET_KEY'],
                algorithms=[app.config['JWT_ALGORITHM']]
            )
            decoded2 = jwt.decode(
                result2['token'],
                app.config['JWT_SECRET_KEY'],
                algorithms=[app.config['JWT_ALGORITHM']]
            )
            assert decoded1['jti'] != decoded2['jti']

    @freeze_time("2025-01-01 12:00:00")
    def test_generate_access_token_expiration(self, app, token_service):
        """Test that access token has correct expiration time."""
        with app.app_context():
            # Arrange
            username = 'test_user'
            expected_expiration = datetime(2025, 1, 1, 12, 15, 0)  # 15 minutes later

            # Act
            result = token_service.generate_access_token(username)

            # Assert
            decoded = jwt.decode(
                result['token'],
                app.config['JWT_SECRET_KEY'],
                algorithms=[app.config['JWT_ALGORITHM']]
            )
            token_exp = datetime.utcfromtimestamp(decoded['exp'])
            assert token_exp == expected_expiration


class TestRefreshTokenGeneration:
    """Test refresh token generation."""

    @pytest.fixture
    def token_service(self, app):
        """Create TokenService with mocked MongoDB."""
        with app.app_context():
            mock_db_service = Mock()
            mock_db_service.client = MagicMock()
            mock_db_service.db_name = 'test_db'

            # Mock collections
            mock_refresh_collection = Mock()
            mock_refresh_collection.create_index = Mock()
            mock_refresh_collection.insert_one = Mock(return_value=Mock(inserted_id='mock_id'))

            mock_blacklist_collection = Mock()
            mock_blacklist_collection.create_index = Mock()

            def get_collection(db_name):
                db_mock = MagicMock()
                db_mock.__getitem__.side_effect = lambda col: (
                    mock_refresh_collection if col == 'refresh_tokens'
                    else mock_blacklist_collection if col == 'token_blacklist'
                    else Mock()
                )
                return db_mock

            mock_db_service.client.__getitem__.side_effect = get_collection

            service = TokenService(mock_db_service)
            service.refresh_tokens_collection = mock_refresh_collection
            service.blacklist_collection = mock_blacklist_collection
            return service

    @freeze_time("2025-01-01 12:00:00")
    def test_generate_refresh_token_success(self, app, token_service):
        """Test successful refresh token generation."""
        with app.app_context():
            # Arrange
            username = 'test_user'
            role = 'user'

            # Act
            result = token_service.generate_refresh_token(username, role)

            # Assert
            assert 'token' in result
            assert result['token_type'] == 'refresh'
            assert result['username'] == username
            assert result['role'] == role
            assert 'token_id' in result
            assert 'expires_at' in result
            assert result['expires_in'] == 7 * 24 * 60 * 60  # 7 days in seconds

            # Verify token stored in MongoDB
            assert token_service.refresh_tokens_collection.insert_one.called
            stored_doc = token_service.refresh_tokens_collection.insert_one.call_args[0][0]
            assert stored_doc['username'] == username
            assert stored_doc['role'] == role
            assert stored_doc['revoked'] == False
            assert stored_doc['used_at'] is None

    def test_generate_refresh_token_stores_in_db(self, app, token_service):
        """Test that refresh token is stored in MongoDB."""
        with app.app_context():
            # Arrange
            username = 'test_user'

            # Act
            result = token_service.generate_refresh_token(username)

            # Assert
            token_service.refresh_tokens_collection.insert_one.assert_called_once()
            stored_doc = token_service.refresh_tokens_collection.insert_one.call_args[0][0]
            assert stored_doc['token_id'] == result['token_id']


class TestTokenPairGeneration:
    """Test token pair generation."""

    @pytest.fixture
    def token_service(self, app):
        """Create TokenService with mocked dependencies."""
        with app.app_context():
            mock_db_service = Mock()
            mock_db_service.client = MagicMock()
            mock_db_service.db_name = 'test_db'

            mock_collection = Mock()
            mock_collection.create_index = Mock()
            mock_collection.insert_one = Mock()

            mock_db = MagicMock()
            mock_db.__getitem__.return_value = mock_collection
            mock_db_service.client.__getitem__.return_value = mock_db

            service = TokenService(mock_db_service)
            service.refresh_tokens_collection = mock_collection
            service.blacklist_collection = mock_collection
            return service

    def test_generate_token_pair_success(self, app, token_service):
        """Test generation of access and refresh token pair."""
        with app.app_context():
            # Arrange
            username = 'test_user'
            role = 'user'

            with patch.object(token_service, 'generate_access_token') as mock_access:
                with patch.object(token_service, 'generate_refresh_token') as mock_refresh:
                    mock_access.return_value = {
                        'token': 'access_token',
                        'expires_in': 900
                    }
                    mock_refresh.return_value = {
                        'token': 'refresh_token',
                        'expires_in': 604800
                    }

                    # Act
                    result = token_service.generate_token_pair(username, role)

            # Assert
            assert result['access_token'] == 'access_token'
            assert result['refresh_token'] == 'refresh_token'
            assert result['token_type'] == 'Bearer'
            assert result['username'] == username
            assert result['role'] == role
            mock_access.assert_called_once_with(username, role)
            mock_refresh.assert_called_once_with(username, role)


class TestTokenRefresh:
    """Test token refresh functionality."""

    @pytest.fixture
    def token_service(self, app):
        """Create TokenService with mocked MongoDB."""
        with app.app_context():
            mock_db_service = Mock()
            mock_db_service.client = MagicMock()
            mock_db_service.db_name = 'test_db'

            mock_refresh_collection = Mock()
            mock_refresh_collection.create_index = Mock()

            mock_blacklist_collection = Mock()
            mock_blacklist_collection.create_index = Mock()

            def get_collection(db_name):
                db_mock = MagicMock()
                db_mock.__getitem__.side_effect = lambda col: (
                    mock_refresh_collection if col == 'refresh_tokens'
                    else mock_blacklist_collection if col == 'token_blacklist'
                    else Mock()
                )
                return db_mock

            mock_db_service.client.__getitem__.side_effect = get_collection

            service = TokenService(mock_db_service)
            service.refresh_tokens_collection = mock_refresh_collection
            service.blacklist_collection = mock_blacklist_collection
            return service

    def test_refresh_access_token_success(self, app, token_service):
        """Test successful token refresh."""
        with app.app_context():
            # Arrange
            username = 'test_user'
            role = 'user'
            token_id = 'test_token_id'

            # Create a valid refresh token
            refresh_token = jwt.encode(
                {
                    'username': username,
                    'role': role,
                    'token_type': 'refresh',
                    'token_id': token_id,
                    'exp': datetime.utcnow() + timedelta(days=7)
                },
                app.config['JWT_SECRET_KEY'],
                algorithm=app.config['JWT_ALGORITHM']
            )

            # Mock database response
            token_service.refresh_tokens_collection.find_one.return_value = {
                'token_id': token_id,
                'username': username,
                'revoked': False
            }
            token_service.refresh_tokens_collection.update_one.return_value = Mock(modified_count=1)
            token_service.refresh_tokens_collection.insert_one.return_value = Mock()

            # Act
            result, error = token_service.refresh_access_token(refresh_token)

            # Assert
            assert error is None
            assert result is not None
            assert 'access_token' in result
            assert result['username'] == username
            assert result['role'] == role

    def test_refresh_access_token_with_invalid_token(self, app, token_service):
        """Test refresh with invalid token."""
        with app.app_context():
            # Arrange
            invalid_token = 'invalid.token.string'

            # Act
            result, error = token_service.refresh_access_token(invalid_token)

            # Assert
            assert result is None
            assert error is not None
            assert 'Invalid' in error or 'invalid' in error

    def test_refresh_access_token_with_revoked_token(self, app, token_service):
        """Test refresh with revoked token."""
        with app.app_context():
            # Arrange
            username = 'test_user'
            token_id = 'test_token_id'

            refresh_token = jwt.encode(
                {
                    'username': username,
                    'role': 'user',
                    'token_type': 'refresh',
                    'token_id': token_id,
                    'exp': datetime.utcnow() + timedelta(days=7)
                },
                app.config['JWT_SECRET_KEY'],
                algorithm=app.config['JWT_ALGORITHM']
            )

            # Mock revoked token in database
            token_service.refresh_tokens_collection.find_one.return_value = {
                'token_id': token_id,
                'username': username,
                'revoked': True
            }

            # Act
            result, error = token_service.refresh_access_token(refresh_token)

            # Assert
            assert result is None
            assert error is not None
            assert 'revoked' in error.lower()

    def test_refresh_access_token_rotates_token(self, app, token_service):
        """Test that token rotation creates new refresh token."""
        with app.app_context():
            # Arrange
            username = 'test_user'
            token_id = 'old_token_id'

            refresh_token = jwt.encode(
                {
                    'username': username,
                    'role': 'user',
                    'token_type': 'refresh',
                    'token_id': token_id,
                    'exp': datetime.utcnow() + timedelta(days=7)
                },
                app.config['JWT_SECRET_KEY'],
                algorithm=app.config['JWT_ALGORITHM']
            )

            token_service.refresh_tokens_collection.find_one.return_value = {
                'token_id': token_id,
                'username': username,
                'revoked': False
            }
            token_service.refresh_tokens_collection.update_one.return_value = Mock(modified_count=1)
            token_service.refresh_tokens_collection.insert_one.return_value = Mock()

            # Act
            result, error = token_service.refresh_access_token(refresh_token)

            # Assert
            assert error is None
            assert 'refresh_token' in result  # New refresh token should be present
            assert token_service.refresh_tokens_collection.update_one.called  # Old token revoked


class TestTokenBlacklistCheck:
    """Test token blacklist checking functionality."""

    @pytest.fixture
    def token_service(self, app):
        """Create TokenService with mocked MongoDB."""
        with app.app_context():
            mock_db_service = Mock()
            mock_db_service.client = MagicMock()
            mock_db_service.db_name = 'test_db'

            mock_refresh_collection = Mock()
            mock_refresh_collection.create_index = Mock()

            mock_blacklist_collection = Mock()
            mock_blacklist_collection.create_index = Mock()

            def get_collection(db_name):
                db_mock = MagicMock()
                db_mock.__getitem__.side_effect = lambda col: (
                    mock_refresh_collection if col == 'refresh_tokens'
                    else mock_blacklist_collection if col == 'token_blacklist'
                    else Mock()
                )
                return db_mock

            mock_db_service.client.__getitem__.side_effect = get_collection

            service = TokenService(mock_db_service)
            service.refresh_tokens_collection = mock_refresh_collection
            service.blacklist_collection = mock_blacklist_collection
            return service

    def test_is_token_blacklisted_returns_true(self, app, token_service):
        """Test checking if token is blacklisted."""
        with app.app_context():
            # Arrange
            jti = 'test_jti'
            token_service.blacklist_collection.find_one.return_value = {'token_jti': jti}

            # Act
            result = token_service.is_token_blacklisted(jti)

            # Assert
            assert result is True

    def test_is_token_blacklisted_returns_false(self, app, token_service):
        """Test checking non-blacklisted token."""
        with app.app_context():
            # Arrange
            jti = 'test_jti'
            token_service.blacklist_collection.find_one.return_value = None

            # Act
            result = token_service.is_token_blacklisted(jti)

            # Assert
            assert result is False

    def test_is_token_blacklisted_handles_error(self, app, token_service):
        """Test blacklist check handles database errors gracefully."""
        with app.app_context():
            # Arrange
            jti = 'test_jti'
            token_service.blacklist_collection.find_one.side_effect = Exception('DB Error')

            # Act
            result = token_service.is_token_blacklisted(jti)

            # Assert - should return False on error
            assert result is False


class TestTokenRevocation:
    """Test token revocation functionality."""

    @pytest.fixture
    def token_service(self, app):
        """Create TokenService with mocked MongoDB."""
        with app.app_context():
            mock_db_service = Mock()
            mock_db_service.client = MagicMock()
            mock_db_service.db_name = 'test_db'

            mock_refresh_collection = Mock()
            mock_refresh_collection.create_index = Mock()

            mock_blacklist_collection = Mock()
            mock_blacklist_collection.create_index = Mock()

            def get_collection(db_name):
                db_mock = MagicMock()
                db_mock.__getitem__.side_effect = lambda col: (
                    mock_refresh_collection if col == 'refresh_tokens'
                    else mock_blacklist_collection if col == 'token_blacklist'
                    else Mock()
                )
                return db_mock

            mock_db_service.client.__getitem__.side_effect = get_collection

            service = TokenService(mock_db_service)
            service.refresh_tokens_collection = mock_refresh_collection
            service.blacklist_collection = mock_blacklist_collection
            return service

    def test_revoke_refresh_token_success(self, app, token_service):
        """Test successful refresh token revocation."""
        with app.app_context():
            # Arrange
            token_id = 'test_token_id'
            refresh_token = jwt.encode(
                {
                    'token_id': token_id,
                    'username': 'test_user',
                    'exp': datetime.utcnow() + timedelta(days=7)
                },
                app.config['JWT_SECRET_KEY'],
                algorithm=app.config['JWT_ALGORITHM']
            )

            token_service.refresh_tokens_collection.update_one.return_value = Mock(modified_count=1)

            # Act
            success, error = token_service.revoke_refresh_token(refresh_token)

            # Assert
            assert success is True
            assert error is None
            assert token_service.refresh_tokens_collection.update_one.called

    def test_revoke_access_token_adds_to_blacklist(self, app, token_service):
        """Test that revoking access token adds it to blacklist."""
        with app.app_context():
            # Arrange
            jti = 'test_jti'
            access_token = jwt.encode(
                {
                    'jti': jti,
                    'username': 'test_user',
                    'exp': datetime.utcnow() + timedelta(minutes=15)
                },
                app.config['JWT_SECRET_KEY'],
                algorithm=app.config['JWT_ALGORITHM']
            )

            token_service.blacklist_collection.insert_one.return_value = Mock()

            # Act
            success, error = token_service.revoke_access_token(access_token)

            # Assert
            assert success is True
            assert token_service.blacklist_collection.insert_one.called

    def test_revoke_all_user_tokens(self, app, token_service):
        """Test revoking all tokens for a user."""
        with app.app_context():
            # Arrange
            username = 'test_user'
            token_service.refresh_tokens_collection.update_many.return_value = Mock(modified_count=3)

            # Act
            count, error = token_service.revoke_all_user_tokens(username)

            # Assert
            assert count == 3
            assert error is None
            token_service.refresh_tokens_collection.update_many.assert_called_once()


class TestAccessTokenRevocation:
    """Test access token revocation/blacklisting functionality."""

    @pytest.fixture
    def token_service(self, app):
        """Create TokenService with mocked MongoDB."""
        with app.app_context():
            mock_db_service = Mock()
            mock_db_service.client = MagicMock()
            mock_db_service.db_name = 'test_db'

            mock_refresh_collection = Mock()
            mock_refresh_collection.create_index = Mock()

            mock_blacklist_collection = Mock()
            mock_blacklist_collection.create_index = Mock()

            def get_collection(db_name):
                db_mock = MagicMock()
                db_mock.__getitem__.side_effect = lambda col: (
                    mock_refresh_collection if col == 'refresh_tokens'
                    else mock_blacklist_collection if col == 'token_blacklist'
                    else Mock()
                )
                return db_mock

            mock_db_service.client.__getitem__.side_effect = get_collection

            service = TokenService(mock_db_service)
            service.refresh_tokens_collection = mock_refresh_collection
            service.blacklist_collection = mock_blacklist_collection
            return service

    def test_revoke_access_token_success(self, app, token_service):
        """Test successful access token revocation via blacklisting."""
        with app.app_context():
            # Arrange
            jti = 'test_jti'
            access_token = jwt.encode(
                {
                    'jti': jti,
                    'username': 'test_user',
                    'exp': datetime.utcnow() + timedelta(minutes=15)
                },
                app.config['JWT_SECRET_KEY'],
                algorithm=app.config['JWT_ALGORITHM']
            )

            token_service.blacklist_collection.insert_one.return_value = Mock()

            # Act
            success, error = token_service.revoke_access_token(access_token)

            # Assert
            assert success is True
            assert error is None
            assert token_service.blacklist_collection.insert_one.called

    def test_revoke_access_token_duplicate(self, app, token_service):
        """Test revoking access token that's already blacklisted."""
        with app.app_context():
            # Arrange
            jti = 'test_jti'
            access_token = jwt.encode(
                {
                    'jti': jti,
                    'username': 'test_user',
                    'exp': datetime.utcnow() + timedelta(minutes=15)
                },
                app.config['JWT_SECRET_KEY'],
                algorithm=app.config['JWT_ALGORITHM']
            )

            # Mock duplicate key error
            from pymongo.errors import DuplicateKeyError
            token_service.blacklist_collection.insert_one.side_effect = DuplicateKeyError('duplicate')

            # Act
            success, error = token_service.revoke_access_token(access_token)

            # Assert - Should still return success for already-blacklisted tokens
            assert success is True
            assert error is None

    def test_revoke_access_token_invalid_token(self, app, token_service):
        """Test revoking invalid access token."""
        with app.app_context():
            # Arrange
            invalid_token = 'invalid.token.string'

            # Act
            success, error = token_service.revoke_access_token(invalid_token)

            # Assert
            assert success is False
            assert error is not None


class TestTokenCleanup:
    """Test token cleanup functionality."""

    @pytest.fixture
    def token_service(self, app):
        """Create TokenService with mocked MongoDB."""
        with app.app_context():
            mock_db_service = Mock()
            mock_db_service.client = MagicMock()
            mock_db_service.db_name = 'test_db'

            mock_refresh_collection = Mock()
            mock_refresh_collection.create_index = Mock()
            mock_refresh_collection.delete_many.return_value = Mock(deleted_count=5)

            mock_blacklist_collection = Mock()
            mock_blacklist_collection.create_index = Mock()
            mock_blacklist_collection.delete_many.return_value = Mock(deleted_count=3)

            def get_collection(db_name):
                db_mock = MagicMock()
                db_mock.__getitem__.side_effect = lambda col: (
                    mock_refresh_collection if col == 'refresh_tokens'
                    else mock_blacklist_collection if col == 'token_blacklist'
                    else Mock()
                )
                return db_mock

            mock_db_service.client.__getitem__.side_effect = get_collection

            service = TokenService(mock_db_service)
            service.refresh_tokens_collection = mock_refresh_collection
            service.blacklist_collection = mock_blacklist_collection
            return service

    def test_cleanup_expired_tokens(self, app, token_service):
        """Test cleanup of expired tokens."""
        with app.app_context():
            # Act
            result = token_service.cleanup_expired_tokens()

            # Assert
            assert result['refresh_tokens_deleted'] == 5
            assert result['blacklist_entries_deleted'] == 3
            assert token_service.refresh_tokens_collection.delete_many.called
            assert token_service.blacklist_collection.delete_many.called

    def test_get_user_active_tokens(self, app, token_service):
        """Test retrieving user's active tokens."""
        with app.app_context():
            # Arrange
            username = 'test_user'
            mock_tokens = [
                {
                    'token_id': 'token123456789',
                    'created_at': datetime(2025, 1, 1),
                    'expires_at': datetime(2025, 1, 8),
                    'used_at': None
                },
                {
                    'token_id': 'token987654321',
                    'created_at': datetime(2025, 1, 2),
                    'expires_at': datetime(2025, 1, 9),
                    'used_at': datetime(2025, 1, 3)
                }
            ]

            # Create proper mock cursor with both sort and iteration support
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor  # sort returns itself
            mock_cursor.__iter__.return_value = iter(mock_tokens)

            token_service.refresh_tokens_collection.find.return_value = mock_cursor

            # Act
            result = token_service.get_user_active_tokens(username)

            # Assert
            assert len(result) == 2
            assert result[0]['token_id'].endswith('...')  # Truncated for security
            token_service.refresh_tokens_collection.find.assert_called_with(
                {'username': username, 'revoked': False}
            )


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def token_service(self, app):
        """Create TokenService with mocked MongoDB."""
        with app.app_context():
            mock_db_service = Mock()
            mock_db_service.client = MagicMock()
            mock_db_service.db_name = 'test_db'

            mock_refresh_collection = Mock()
            mock_refresh_collection.create_index = Mock()

            mock_blacklist_collection = Mock()
            mock_blacklist_collection.create_index = Mock()

            def get_collection(db_name):
                db_mock = MagicMock()
                db_mock.__getitem__.side_effect = lambda col: (
                    mock_refresh_collection if col == 'refresh_tokens'
                    else mock_blacklist_collection if col == 'token_blacklist'
                    else Mock()
                )
                return db_mock

            mock_db_service.client.__getitem__.side_effect = get_collection

            service = TokenService(mock_db_service)
            service.refresh_tokens_collection = mock_refresh_collection
            service.blacklist_collection = mock_blacklist_collection
            return service

    def test_revoke_refresh_token_with_invalid_token(self, app, token_service):
        """Test revoking invalid refresh token."""
        with app.app_context():
            # Arrange
            invalid_token = 'invalid.token.string'

            # Act
            success, error = token_service.revoke_refresh_token(invalid_token)

            # Assert
            assert success is False
            assert error is not None

    def test_revoke_access_token_with_invalid_token(self, app, token_service):
        """Test revoking invalid access token."""
        with app.app_context():
            # Arrange
            invalid_token = 'invalid.token.string'

            # Act
            success, error = token_service.revoke_access_token(invalid_token)

            # Assert
            assert success is False
            assert error is not None

    def test_generate_token_with_empty_username(self, app, token_service):
        """Test generating token with empty username."""
        with app.app_context():
            # This should still work - validation happens at API layer
            result = token_service.generate_access_token('', 'user')

            # Assert
            assert 'token' in result
            assert result['username'] == ''

    def test_database_error_during_refresh_token_creation(self, app, token_service):
        """Test handling database errors during refresh token creation."""
        with app.app_context():
            # Arrange
            token_service.refresh_tokens_collection.insert_one.side_effect = Exception('DB Error')

            # Act & Assert
            with pytest.raises(Exception):
                token_service.generate_refresh_token('test_user', 'user')

    def test_cleanup_with_database_error(self, app, token_service):
        """Test cleanup with database errors - should return zeros instead of raising."""
        with app.app_context():
            # Arrange
            token_service.refresh_tokens_collection.delete_many.side_effect = Exception('DB Error')

            # Act - cleanup_expired_tokens catches exceptions and returns zeros
            result = token_service.cleanup_expired_tokens()

            # Assert - should return dict with zeros, not raise exception
            assert result['refresh_tokens_deleted'] == 0
            assert result['blacklist_entries_deleted'] == 0
