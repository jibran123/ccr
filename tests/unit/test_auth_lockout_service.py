"""
Unit tests for AuthLockoutService.

Tests the brute force protection service that tracks failed authentication
attempts and implements IP-based lockout mechanism.

Week 13-14: Testing & Quality Assurance - Phase 1 Critical Security Tests

All tests updated to use Flask app context properly.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from flask import Flask
from app.services.auth_lockout_service import AuthLockoutService


@pytest.fixture(scope='function')
def app():
    """Create minimal Flask app for testing with proper app context."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    app.config['AUTH_LOCKOUT_ENABLED'] = True
    app.config['AUTH_LOCKOUT_MAX_ATTEMPTS'] = 5
    app.config['AUTH_LOCKOUT_WINDOW_MINUTES'] = 15
    app.config['AUTH_LOCKOUT_DURATION_MINUTES'] = 30
    return app


@pytest.fixture(scope='function')
def mock_db_service():
    """Create mock database service."""
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_collection = MagicMock()

    mock_db.client = mock_client
    mock_db.db_name = 'test_db'
    mock_client.__getitem__.return_value.__getitem__.return_value = mock_collection

    return mock_db


@pytest.fixture(scope='function')
def auth_lockout_service(mock_db_service):
    """Create AuthLockoutService instance with mocked database."""
    with patch.object(AuthLockoutService, '_ensure_indexes'):
        return AuthLockoutService(mock_db_service)


class TestAuthLockoutServiceInitialization:
    """Test AuthLockoutService initialization with proper Flask app context."""

    def test_init_creates_service_with_collection_name(self, app, mock_db_service):
        """Test that initialization sets collection name."""
        with app.app_context():
            service = AuthLockoutService(mock_db_service)
            assert service.db == mock_db_service
            assert service.collection_name == 'auth_lockouts'

    def test_init_calls_ensure_indexes(self, app, mock_db_service):
        """Test that initialization creates indexes."""
        with app.app_context():
            mock_collection = mock_db_service.client[mock_db_service.db_name]['auth_lockouts']

            service = AuthLockoutService(mock_db_service)

            # Verify index creation was called
            assert mock_collection.create_index.call_count == 2

            # Verify ip_address unique index
            mock_collection.create_index.assert_any_call('ip_address', unique=True)

            # Verify TTL index on locked_until
            mock_collection.create_index.assert_any_call(
                'locked_until',
                expireAfterSeconds=3600,
                partialFilterExpression={'locked_until': {'$exists': True}}
            )


class TestLockoutStatusChecking:
    """Test lockout status checking functionality with proper Flask app context."""

    def test_is_locked_out_returns_false_when_disabled(self, app, auth_lockout_service):
        """Test that lockout check returns False when feature is disabled."""
        with app.app_context():
            app.config['AUTH_LOCKOUT_ENABLED'] = False

            is_locked, message = auth_lockout_service.is_locked_out('192.168.1.1')

        assert is_locked is False
        assert message is None

    def test_is_locked_out_returns_false_when_no_record(self, app, auth_lockout_service):
        """Test that lockout check returns False when no lockout record exists."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = None

        with app.app_context():
            is_locked, message = auth_lockout_service.is_locked_out('192.168.1.1')

        assert is_locked is False
        assert message is None
        mock_collection.find_one.assert_called_once_with({'ip_address': '192.168.1.1'})

    def test_is_locked_out_returns_false_when_lockout_expired(self, app, auth_lockout_service):
        """Test that lockout check returns False when lockout period has expired."""
        past_time = datetime.utcnow() - timedelta(minutes=10)

        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = {
            'ip_address': '192.168.1.1',
            'locked_until': past_time,
            'failed_attempts': 5
        }

        with app.app_context():
            is_locked, message = auth_lockout_service.is_locked_out('192.168.1.1')

        assert is_locked is False
        assert message is None

    def test_is_locked_out_returns_true_when_currently_locked(self, app, auth_lockout_service):
        """Test that lockout check returns True when IP is currently locked out."""
        future_time = datetime.utcnow() + timedelta(minutes=20)

        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = {
            'ip_address': '192.168.1.1',
            'locked_until': future_time,
            'failed_attempts': 5
        }

        with app.app_context():
            is_locked, message = auth_lockout_service.is_locked_out('192.168.1.1')

        assert is_locked is True
        assert message is not None
        assert "Too many failed authentication attempts" in message
        # Allow for small timing variations (19-20 minutes)
        assert "19 minutes" in message or "20 minutes" in message

    def test_is_locked_out_handles_exception_gracefully(self, app, auth_lockout_service):
        """Test that exceptions are handled and fail open."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.side_effect = Exception("Database error")

        with app.app_context():
            is_locked, message = auth_lockout_service.is_locked_out('192.168.1.1')

        # Should fail open - don't block on error
        assert is_locked is False
        assert message is None


class TestFailedAttemptRecording:
    """Test failed attempt recording functionality with proper Flask app context."""

    def test_record_failed_attempt_returns_false_when_disabled(self, app, auth_lockout_service):
        """Test that recording returns False when feature is disabled."""
        with app.app_context():
            app.config['AUTH_LOCKOUT_ENABLED'] = False

            was_locked, message = auth_lockout_service.record_failed_attempt('192.168.1.1', 'test_user')

        assert was_locked is False
        assert message is None

    def test_record_first_failed_attempt_creates_record(self, app, auth_lockout_service):
        """Test that first failed attempt creates a new record."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = None

        with app.app_context():
            was_locked, message = auth_lockout_service.record_failed_attempt('192.168.1.1', 'test_user')

        assert was_locked is False
        assert message is None

        # Verify insert_one was called with correct structure
        mock_collection.insert_one.assert_called_once()
        insert_call = mock_collection.insert_one.call_args[0][0]
        assert insert_call['ip_address'] == '192.168.1.1'
        assert insert_call['failed_attempts'] == 1
        assert insert_call['last_attempted_username'] == 'test_user'
        assert 'first_attempt_time' in insert_call
        assert 'last_attempt_time' in insert_call

    def test_record_failed_attempt_increments_counter_within_window(self, app, auth_lockout_service):
        """Test that failed attempt counter increments within time window."""
        recent_time = datetime.utcnow() - timedelta(minutes=5)

        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = {
            'ip_address': '192.168.1.1',
            'failed_attempts': 2,
            'first_attempt_time': recent_time,
            'last_attempt_time': recent_time
        }

        with app.app_context():
            was_locked, message = auth_lockout_service.record_failed_attempt('192.168.1.1', 'test_user')

        assert was_locked is False
        assert message is None

        # Verify update_one was called to increment counter
        mock_collection.update_one.assert_called_once()
        update_call = mock_collection.update_one.call_args[0][1]
        assert update_call['$set']['failed_attempts'] == 3

    def test_record_failed_attempt_resets_counter_outside_window(self, app, auth_lockout_service):
        """Test that failed attempt counter resets when outside time window."""
        old_time = datetime.utcnow() - timedelta(minutes=20)  # Outside 15-minute window

        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = {
            'ip_address': '192.168.1.1',
            'failed_attempts': 3,
            'first_attempt_time': old_time,
            'last_attempt_time': old_time
        }

        with app.app_context():
            was_locked, message = auth_lockout_service.record_failed_attempt('192.168.1.1', 'test_user')

        assert was_locked is False
        assert message is None

        # Verify counter was reset to 1
        mock_collection.update_one.assert_called_once()
        update_call = mock_collection.update_one.call_args[0][1]
        assert update_call['$set']['failed_attempts'] == 1

    def test_record_failed_attempt_triggers_lockout_at_threshold(self, app, auth_lockout_service):
        """Test that lockout is triggered when threshold is reached."""
        recent_time = datetime.utcnow() - timedelta(minutes=5)

        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = {
            'ip_address': '192.168.1.1',
            'failed_attempts': 4,  # One away from threshold of 5
            'first_attempt_time': recent_time,
            'last_attempt_time': recent_time
        }

        with app.app_context():
            was_locked, message = auth_lockout_service.record_failed_attempt('192.168.1.1', 'test_user')

        assert was_locked is True
        assert message is not None
        assert "Too many failed authentication attempts" in message
        assert "30 minutes" in message

        # Verify lockout was set
        mock_collection.update_one.assert_called_once()
        update_call = mock_collection.update_one.call_args[0][1]
        assert update_call['$set']['failed_attempts'] == 5
        assert 'locked_until' in update_call['$set']

    def test_record_failed_attempt_stores_username(self, app, auth_lockout_service):
        """Test that attempted username is stored in lockout record."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = None

        with app.app_context():
            auth_lockout_service.record_failed_attempt('192.168.1.1', 'attacker_username')

        insert_call = mock_collection.insert_one.call_args[0][0]
        assert insert_call['last_attempted_username'] == 'attacker_username'

    def test_record_failed_attempt_handles_exception_gracefully(self, app, auth_lockout_service):
        """Test that exceptions are handled and don't block authentication."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.side_effect = Exception("Database error")

        with app.app_context():
            was_locked, message = auth_lockout_service.record_failed_attempt('192.168.1.1', 'test_user')

        # Should fail open - don't block on error
        assert was_locked is False
        assert message is None


class TestFailedAttemptReset:
    """Test failed attempt reset functionality with proper Flask app context."""

    def test_reset_failed_attempts_does_nothing_when_disabled(self, app, auth_lockout_service):
        """Test that reset does nothing when feature is disabled."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']

        with app.app_context():
            app.config['AUTH_LOCKOUT_ENABLED'] = False

            auth_lockout_service.reset_failed_attempts('192.168.1.1')

        mock_collection.delete_one.assert_not_called()

    def test_reset_failed_attempts_deletes_record(self, app, auth_lockout_service):
        """Test that reset deletes the lockout record."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        with app.app_context():
            auth_lockout_service.reset_failed_attempts('192.168.1.1')

        mock_collection.delete_one.assert_called_once_with({'ip_address': '192.168.1.1'})

    def test_reset_failed_attempts_handles_no_record(self, app, auth_lockout_service):
        """Test that reset handles case when no record exists."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.delete_one.return_value = MagicMock(deleted_count=0)

        with app.app_context():
            # Should not raise exception
            auth_lockout_service.reset_failed_attempts('192.168.1.1')

        mock_collection.delete_one.assert_called_once()

    def test_reset_failed_attempts_handles_exception_gracefully(self, app, auth_lockout_service):
        """Test that exceptions are handled gracefully."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.delete_one.side_effect = Exception("Database error")

        with app.app_context():
            # Should not raise exception
            auth_lockout_service.reset_failed_attempts('192.168.1.1')


class TestLockoutInfoRetrieval:
    """Test lockout information retrieval functionality with proper Flask app context."""

    def test_get_lockout_info_returns_none_when_no_record(self, app, auth_lockout_service):
        """Test that get_lockout_info returns None when no record exists."""
        with app.app_context():
            mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
            mock_collection.find_one.return_value = None

            result = auth_lockout_service.get_lockout_info('192.168.1.1')

            assert result is None
            mock_collection.find_one.assert_called_once_with({'ip_address': '192.168.1.1'})

    def test_get_lockout_info_returns_formatted_record(self, app, auth_lockout_service):
        """Test that get_lockout_info returns properly formatted record."""
        with app.app_context():
            mock_time = datetime(2025, 1, 1, 12, 0, 0)

            mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
            mock_collection.find_one.return_value = {
                '_id': 'some_mongodb_id',
                'ip_address': '192.168.1.1',
                'failed_attempts': 5,
                'first_attempt_time': mock_time,
                'last_attempt_time': mock_time,
                'locked_until': mock_time + timedelta(minutes=30),
                'last_attempted_username': 'test_user'
            }

            result = auth_lockout_service.get_lockout_info('192.168.1.1')

            assert result is not None
            assert '_id' not in result  # Should be removed
            assert result['ip_address'] == '192.168.1.1'
            assert result['failed_attempts'] == 5
            assert result['first_attempt_time'] == '2025-01-01T12:00:00Z'
            assert result['last_attempt_time'] == '2025-01-01T12:00:00Z'
            assert result['locked_until'] == '2025-01-01T12:30:00Z'
            assert result['last_attempted_username'] == 'test_user'
            assert 'is_currently_locked' in result

    def test_get_lockout_info_handles_exception_gracefully(self, app, auth_lockout_service):
        """Test that exceptions are handled and return None."""
        with app.app_context():
            mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
            mock_collection.find_one.side_effect = Exception("Database error")

            result = auth_lockout_service.get_lockout_info('192.168.1.1')

            assert result is None


class TestAllLockoutsRetrieval:
    """Test all lockouts retrieval functionality with proper Flask app context."""

    def test_get_all_lockouts_returns_empty_list_when_no_records(self, app, auth_lockout_service):
        """Test that get_all_lockouts returns empty list when no records exist."""
        with app.app_context():
            mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value.limit.return_value = []
            mock_collection.find.return_value = mock_cursor

            result = auth_lockout_service.get_all_lockouts()

            assert result == []
            mock_collection.find.assert_called_once()

    def test_get_all_lockouts_returns_formatted_records(self, app, auth_lockout_service):
        """Test that get_all_lockouts returns properly formatted records."""
        with app.app_context():
            mock_time = datetime(2025, 1, 1, 12, 0, 0)

            mock_records = [
                {
                    '_id': 'id1',
                    'ip_address': '192.168.1.1',
                    'failed_attempts': 5,
                    'first_attempt_time': mock_time,
                    'last_attempt_time': mock_time,
                    'locked_until': mock_time + timedelta(minutes=30)
                },
                {
                    '_id': 'id2',
                    'ip_address': '192.168.1.2',
                    'failed_attempts': 3,
                    'first_attempt_time': mock_time,
                    'last_attempt_time': mock_time,
                    'locked_until': None
                }
            ]

            mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value.limit.return_value = mock_records
            mock_collection.find.return_value = mock_cursor

            result = auth_lockout_service.get_all_lockouts()

            assert len(result) == 2
            assert '_id' not in result[0]
            assert result[0]['ip_address'] == '192.168.1.1'
            assert 'is_currently_locked' in result[0]

    def test_get_all_lockouts_respects_limit(self, app, auth_lockout_service):
        """Test that get_all_lockouts respects the limit parameter."""
        with app.app_context():
            mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value.limit.return_value = []
            mock_collection.find.return_value = mock_cursor

            auth_lockout_service.get_all_lockouts(limit=50)

            mock_cursor.sort.return_value.limit.assert_called_with(50)

    def test_get_all_lockouts_handles_exception_gracefully(self, app, auth_lockout_service):
        """Test that exceptions are handled and return empty list."""
        with app.app_context():
            mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
            mock_collection.find.side_effect = Exception("Database error")

            result = auth_lockout_service.get_all_lockouts()

            assert result == []


class TestManualUnlock:
    """Test manual unlock functionality with proper Flask app context."""

    def test_manually_unlock_succeeds_when_record_exists(self, app, auth_lockout_service):
        """Test that manual unlock succeeds when lockout record exists."""
        with app.app_context():
            mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
            mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

            success, message = auth_lockout_service.manually_unlock('192.168.1.1')

            assert success is True
            assert "unlocked" in message.lower()
            mock_collection.delete_one.assert_called_once_with({'ip_address': '192.168.1.1'})

    def test_manually_unlock_fails_when_no_record(self, app, auth_lockout_service):
        """Test that manual unlock fails when no lockout record exists."""
        with app.app_context():
            mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
            mock_collection.delete_one.return_value = MagicMock(deleted_count=0)

            success, message = auth_lockout_service.manually_unlock('192.168.1.1')

            assert success is False
            assert "No lockout record found" in message

    def test_manually_unlock_handles_exception(self, app, auth_lockout_service):
        """Test that manual unlock handles exceptions."""
        with app.app_context():
            mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
            mock_collection.delete_one.side_effect = Exception("Database error")

            success, message = auth_lockout_service.manually_unlock('192.168.1.1')

            assert success is False
            assert "Error unlocking IP" in message


class TestEdgeCases:
    """Test edge cases and error conditions with proper Flask app context."""

    def test_record_failed_attempt_with_no_username(self, app, auth_lockout_service):
        """Test that failed attempt recording works without username."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = None

        with app.app_context():
            was_locked, message = auth_lockout_service.record_failed_attempt('192.168.1.1', None)

        assert was_locked is False
        insert_call = mock_collection.insert_one.call_args[0][0]
        assert insert_call['last_attempted_username'] is None

    def test_lockout_calculates_time_remaining_correctly(self, app, auth_lockout_service):
        """Test that time remaining calculation is accurate."""
        # Set lockout to expire in exactly 25 minutes
        future_time = datetime.utcnow() + timedelta(minutes=25)

        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = {
            'ip_address': '192.168.1.1',
            'locked_until': future_time,
            'failed_attempts': 5
        }

        with app.app_context():
            is_locked, message = auth_lockout_service.is_locked_out('192.168.1.1')

        assert is_locked is True
        # Allow for small timing variations (24-25 minutes)
        assert "24 minutes" in message or "25 minutes" in message

    def test_multiple_ips_tracked_independently(self, app, auth_lockout_service):
        """Test that different IPs are tracked independently."""
        mock_collection = auth_lockout_service.db.client[auth_lockout_service.db.db_name]['auth_lockouts']
        mock_collection.find_one.return_value = None

        with app.app_context():
            # Record attempts for two different IPs
            auth_lockout_service.record_failed_attempt('192.168.1.1', 'user1')
            auth_lockout_service.record_failed_attempt('192.168.1.2', 'user2')

        # Verify both IPs were tracked separately
        assert mock_collection.insert_one.call_count == 2

        call1 = mock_collection.insert_one.call_args_list[0][0][0]
        call2 = mock_collection.insert_one.call_args_list[1][0][0]

        assert call1['ip_address'] == '192.168.1.1'
        assert call2['ip_address'] == '192.168.1.2'
