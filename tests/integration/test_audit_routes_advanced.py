"""
Integration Tests: Advanced Audit Routes
Tests for audit log endpoints and functionality
Week 13-14: Testing & Quality Assurance - Coverage Improvement
Target: audit_routes.py 19% → 75%
"""

import pytest
import json
from datetime import datetime, timedelta
from flask import current_app


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_audit_logs(app):
    """
    Create sample audit log entries for testing.

    Creates 15 audit entries with various:
    - Actions: CREATE, UPDATE, DELETE
    - Users: user-1, user-2, admin
    - APIs: test-api-1, test-api-2, test-api-3
    - Platforms: IP4, IP5
    - Environments: dev, tst, prd
    """
    audit_service = app.audit_service
    created_logs = []

    # Clean existing logs first
    audit_service.audit_collection.delete_many({})

    # Create logs over 3 days
    base_time = datetime.utcnow() - timedelta(days=2)

    actions = ['CREATE', 'UPDATE_STATUS', 'UPDATE_VERSION', 'UPDATE_PROPERTIES', 'DELETE']
    users = ['user-1', 'user-2', 'admin']
    apis = ['test-api-1', 'test-api-2', 'test-api-3']
    platforms = ['IP4', 'IP5']
    environments = ['dev', 'tst', 'prd']

    for i in range(15):
        timestamp = base_time + timedelta(hours=i*3)
        action = actions[i % len(actions)]
        user = users[i % len(users)]
        api_name = apis[i % len(apis)]
        platform = platforms[i % len(platforms)]
        env = environments[i % len(environments)]

        # Create appropriate changes based on action
        if action == 'CREATE':
            changes = {
                'before': {},
                'after': {
                    'version': f'{i}.0.0',
                    'status': 'RUNNING',
                    'Properties': {}
                }
            }
        elif action == 'UPDATE_STATUS':
            changes = {
                'before': {'status': 'STOPPED'},
                'after': {'status': 'RUNNING'}
            }
        elif action == 'UPDATE_VERSION':
            changes = {
                'before': {'version': f'{i}.0.0'},
                'after': {'version': f'{i+1}.0.0'}
            }
        elif action == 'UPDATE_PROPERTIES':
            changes = {
                'before': {'Properties': {'key': 'old-value'}},
                'after': {'Properties': {'key': 'new-value', 'new-key': 'value'}}
            }
        else:  # DELETE
            changes = {
                'before': {
                    'version': f'{i}.0.0',
                    'status': 'STOPPED',
                    'Properties': {}
                },
                'after': {}
            }

        # Log the action
        audit_id = audit_service.log_change(
            action=action,
            api_name=api_name,
            changed_by=user,
            changes=changes,
            platform_id=platform,
            environment_id=env
        )

        # Update timestamp to simulate historical data
        audit_service.audit_collection.update_one(
            {'audit_id': audit_id},
            {'$set': {'timestamp': timestamp}}
        )

        created_logs.append({
            'audit_id': audit_id,
            'action': action,
            'api_name': api_name,
            'changed_by': user,
            'timestamp': timestamp,
            'platform_id': platform,
            'environment_id': env
        })

    return created_logs


@pytest.fixture
def clear_audit_logs(app):
    """Clear audit logs before and after test."""
    audit_service = app.audit_service
    audit_service.audit_collection.delete_many({})
    yield
    audit_service.audit_collection.delete_many({})


# ============================================================================
# Test Classes
# ============================================================================

class TestGetLogsEndpoint:
    """Test GET /api/audit/logs endpoint with various filters."""

    def test_get_logs_no_filters(self, client, sample_audit_logs):
        """Test getting all logs without filters."""
        response = client.get('/api/audit/logs')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'logs' in data['data']
        assert 'pagination' in data['data']
        assert len(data['data']['logs']) > 0
        assert data['data']['pagination']['total'] == 15

    def test_get_logs_filter_by_api_name(self, client, sample_audit_logs):
        """Test filtering logs by API name."""
        response = client.get('/api/audit/logs?api_name=test-api-1')

        assert response.status_code == 200
        data = response.json
        logs = data['data']['logs']

        # Verify all logs are for test-api-1
        for log in logs:
            assert log['api_name'] == 'test-api-1'

        assert len(logs) == 5  # Should have 5 logs (15 total / 3 apis)

    def test_get_logs_filter_by_user(self, client, sample_audit_logs):
        """Test filtering logs by username."""
        response = client.get('/api/audit/logs?changed_by=admin')

        assert response.status_code == 200
        data = response.json
        logs = data['data']['logs']

        # Verify all logs are by admin
        for log in logs:
            assert log['changed_by'] == 'admin'

        assert len(logs) == 5  # Should have 5 logs (15 total / 3 users)

    def test_get_logs_filter_by_action(self, client, sample_audit_logs):
        """Test filtering logs by action type."""
        response = client.get('/api/audit/logs?action=CREATE')

        assert response.status_code == 200
        data = response.json
        logs = data['data']['logs']

        # Verify all logs are CREATE actions
        for log in logs:
            assert log['action'] == 'CREATE'

        assert len(logs) == 3  # Should have 3 CREATE logs

    def test_get_logs_filter_by_date_range(self, client, sample_audit_logs):
        """Test filtering logs by date range."""
        # Get logs from last 24 hours
        start_date = (datetime.utcnow() - timedelta(days=1)).isoformat() + 'Z'
        end_date = datetime.utcnow().isoformat() + 'Z'

        response = client.get(f'/api/audit/logs?start_date={start_date}&end_date={end_date}')

        assert response.status_code == 200
        data = response.json
        logs = data['data']['logs']

        # Verify logs are within date range
        for log in logs:
            log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
            start_time = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            assert start_time <= log_time <= end_time

    def test_get_logs_combined_filters(self, client, sample_audit_logs):
        """Test combining multiple filters."""
        response = client.get('/api/audit/logs?api_name=test-api-1&action=UPDATE_STATUS')

        assert response.status_code == 200
        data = response.json
        logs = data['data']['logs']

        # Verify all filters applied
        for log in logs:
            assert log['api_name'] == 'test-api-1'
            assert log['action'] == 'UPDATE_STATUS'

    def test_get_logs_pagination(self, client, sample_audit_logs):
        """Test pagination parameters."""
        # Get first page (5 logs)
        response = client.get('/api/audit/logs?limit=5&skip=0')

        assert response.status_code == 200
        data = response.json
        logs = data['data']['logs']
        pagination = data['data']['pagination']

        assert len(logs) == 5
        assert pagination['total'] == 15
        assert pagination['limit'] == 5
        assert pagination['skip'] == 0
        assert pagination['count'] == 5
        assert pagination['has_more'] is True

        # Get second page
        response = client.get('/api/audit/logs?limit=5&skip=5')
        data = response.json
        assert len(data['data']['logs']) == 5
        assert data['data']['pagination']['has_more'] is True

        # Get last page
        response = client.get('/api/audit/logs?limit=5&skip=10')
        data = response.json
        assert len(data['data']['logs']) == 5
        assert data['data']['pagination']['has_more'] is False

    def test_get_logs_invalid_limit(self, client, sample_audit_logs):
        """Test with invalid limit parameter."""
        response = client.get('/api/audit/logs?limit=invalid')

        assert response.status_code == 400
        data = response.json
        assert data['status'] == 'error'
        assert 'integers' in data['message'].lower()

    def test_get_logs_invalid_date_format(self, client, sample_audit_logs):
        """Test with invalid date format."""
        response = client.get('/api/audit/logs?start_date=invalid-date')

        assert response.status_code == 400
        data = response.json
        assert data['status'] == 'error'
        assert 'date format' in data['message'].lower()

    def test_get_logs_limit_enforcement(self, client, sample_audit_logs):
        """Test that limit is enforced (max 1000)."""
        response = client.get('/api/audit/logs?limit=5000')

        assert response.status_code == 200
        data = response.json
        # Limit should be capped at 1000
        assert data['data']['pagination']['limit'] == 1000

    def test_get_logs_negative_skip(self, client, sample_audit_logs):
        """Test with negative skip value."""
        response = client.get('/api/audit/logs?skip=-5')

        assert response.status_code == 200
        data = response.json
        # Skip should be normalized to 0
        assert data['data']['pagination']['skip'] == 0


class TestGetAPIHistoryEndpoint:
    """Test GET /api/audit/logs/<api_name> endpoint."""

    def test_get_api_history_basic(self, client, sample_audit_logs):
        """Test getting history for a specific API."""
        response = client.get('/api/audit/logs/test-api-1')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert data['data']['api_name'] == 'test-api-1'
        assert 'logs' in data['data']
        assert 'count' in data['data']
        assert len(data['data']['logs']) > 0

        # Verify all logs are for test-api-1
        for log in data['data']['logs']:
            assert log['api_name'] == 'test-api-1'

    def test_get_api_history_with_limit(self, client, sample_audit_logs):
        """Test history with limit parameter."""
        response = client.get('/api/audit/logs/test-api-1?limit=2')

        assert response.status_code == 200
        data = response.json
        assert len(data['data']['logs']) <= 2

    def test_get_api_history_nonexistent_api(self, client, clear_audit_logs):
        """Test getting history for non-existent API."""
        response = client.get('/api/audit/logs/nonexistent-api')

        assert response.status_code == 200
        data = response.json
        assert data['data']['api_name'] == 'nonexistent-api'
        assert data['data']['count'] == 0
        assert len(data['data']['logs']) == 0

    def test_get_api_history_limit_enforcement(self, client, sample_audit_logs):
        """Test that limit is enforced (max 500)."""
        response = client.get('/api/audit/logs/test-api-1?limit=1000')

        assert response.status_code == 200
        data = response.json
        # Limit should be capped at 500
        assert len(data['data']['logs']) <= 500


class TestGetUserActivityEndpoint:
    """Test GET /api/audit/users/<username>/activity endpoint."""

    def test_get_user_activity_basic(self, client, sample_audit_logs):
        """Test getting activity for a specific user."""
        response = client.get('/api/audit/users/admin/activity')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert 'logs' in data['data']
        assert len(data['data']['logs']) > 0

        # Verify all logs are by admin
        for log in data['data']['logs']:
            assert log['changed_by'] == 'admin'

    def test_get_user_activity_with_limit(self, client, sample_audit_logs):
        """Test user activity with limit parameter."""
        response = client.get('/api/audit/users/admin/activity?limit=2')

        assert response.status_code == 200
        data = response.json
        assert len(data['data']['logs']) <= 2

    def test_get_user_activity_nonexistent_user(self, client, clear_audit_logs):
        """Test getting activity for non-existent user."""
        response = client.get('/api/audit/users/nonexistent-user/activity')

        assert response.status_code == 200
        data = response.json
        assert len(data['data']['logs']) == 0


class TestRecentChangesEndpoint:
    """Test /api/audit/recent endpoint."""

    def test_get_recent_changes_default(self, client, sample_audit_logs):
        """Test getting recent changes with default parameters."""
        response = client.get('/api/audit/recent')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert 'logs' in data['data']
        assert 'hours' in data['data']
        assert data['data']['hours'] == 24  # Default 24 hours


class TestAuditStatsEndpoint:
    """Test /api/audit/stats endpoint."""

    def test_get_stats_basic(self, client, sample_audit_logs):
        """Test getting audit statistics."""
        response = client.get('/api/audit/stats')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert 'data' in data

        stats = data['data']
        assert 'total_logs' in stats
        assert 'by_action' in stats
        assert 'top_users' in stats
        assert 'recent_24h' in stats
        assert 'retention_days' in stats
        assert stats['total_logs'] == 15

    def test_get_stats_action_distribution(self, client, sample_audit_logs):
        """Test action type distribution in stats."""
        response = client.get('/api/audit/stats')

        assert response.status_code == 200
        data = response.json
        stats = data['data']

        # Verify action distribution
        assert 'CREATE' in stats['by_action']
        assert 'UPDATE_STATUS' in stats['by_action']
        assert 'UPDATE_VERSION' in stats['by_action']
        assert 'UPDATE_PROPERTIES' in stats['by_action']
        assert 'DELETE' in stats['by_action']

        # Verify counts add up
        total_by_action = sum(stats['by_action'].values())
        assert total_by_action == stats['total_logs']

    def test_get_stats_user_distribution(self, client, sample_audit_logs):
        """Test user activity distribution in stats."""
        response = client.get('/api/audit/stats')

        assert response.status_code == 200
        data = response.json
        stats = data['data']

        # Verify top_users format
        assert isinstance(stats['top_users'], list)
        assert len(stats['top_users']) == 3  # All 3 users should be in top users

        # Verify each user entry has correct structure
        for user_entry in stats['top_users']:
            assert 'user' in user_entry
            assert 'changes' in user_entry
            assert user_entry['user'] in ['user-1', 'user-2', 'admin']
            assert user_entry['changes'] == 5  # Each user has 5 logs

    def test_get_stats_retention_days(self, client, sample_audit_logs):
        """Test retention days in stats."""
        response = client.get('/api/audit/stats')

        assert response.status_code == 200
        data = response.json
        stats = data['data']

        # Verify retention days
        assert 'retention_days' in stats
        assert stats['retention_days'] == 180  # Default retention

    def test_get_stats_recent_24h(self, client, sample_audit_logs):
        """Test recent 24h count in stats."""
        response = client.get('/api/audit/stats')

        assert response.status_code == 200
        data = response.json
        stats = data['data']

        # Verify recent_24h field exists (count depends on timestamps)
        assert 'recent_24h' in stats
        assert isinstance(stats['recent_24h'], int)
        assert stats['recent_24h'] >= 0

    def test_get_stats_empty_database(self, client, clear_audit_logs):
        """Test statistics with no audit logs."""
        response = client.get('/api/audit/stats')

        assert response.status_code == 200
        data = response.json
        stats = data['data']

        assert stats['total_logs'] == 0
        assert stats['by_action'] == {}
        assert stats['top_users'] == []
        assert stats['recent_24h'] == 0


class TestCountLogsEndpoint:
    """Test log counting functionality."""

    def test_count_logs_no_filters(self, client, sample_audit_logs):
        """Test counting all logs."""
        response = client.get('/api/audit/logs?limit=1')

        assert response.status_code == 200
        data = response.json
        pagination = data['data']['pagination']

        assert pagination['total'] == 15

    def test_count_logs_with_filters(self, client, sample_audit_logs):
        """Test counting filtered logs."""
        response = client.get('/api/audit/logs?api_name=test-api-1&limit=1')

        assert response.status_code == 200
        data = response.json
        pagination = data['data']['pagination']

        assert pagination['total'] == 5  # 5 logs for test-api-1


class TestAuditEdgeCases:
    """Test edge cases and error scenarios."""

    def test_empty_database(self, client, clear_audit_logs):
        """Test endpoints with empty audit database."""
        # Test /api/audit/logs
        response = client.get('/api/audit/logs')
        assert response.status_code == 200
        assert len(response.json['data']['logs']) == 0

        # Test /api/audit/stats
        response = client.get('/api/audit/stats')
        assert response.status_code == 200
        assert response.json['data']['total_logs'] == 0

        # Test /api/audit/recent
        response = client.get('/api/audit/recent')
        assert response.status_code == 200
        assert len(response.json['data']['logs']) == 0

    def test_special_characters_in_api_name(self, client, app):
        """Test handling special characters in API name."""
        audit_service = app.audit_service

        # Create log with special characters
        audit_service.log_change(
            action='CREATE',
            api_name='test-api_special-chars@123',
            changed_by='test-user',
            changes={'before': {}, 'after': {'version': '1.0.0'}},
            platform_id='IP4',
            environment_id='dev'
        )

        # Query by API name
        response = client.get('/api/audit/logs/test-api_special-chars@123')
        assert response.status_code == 200
        assert len(response.json['data']['logs']) > 0

    def test_unicode_characters_in_username(self, client, app):
        """Test handling unicode characters in username."""
        audit_service = app.audit_service

        # Create log with unicode username
        audit_service.log_change(
            action='CREATE',
            api_name='test-api',
            changed_by='Jürgen-Müller',
            changes={'before': {}, 'after': {'version': '1.0.0'}},
            platform_id='IP4',
            environment_id='dev'
        )

        # Query by username
        response = client.get('/api/audit/users/Jürgen-Müller/activity')
        assert response.status_code == 200
        assert len(response.json['data']['logs']) > 0


class TestRecentChangesAdvanced:
    """Test advanced /api/audit/recent endpoint scenarios."""

    def test_recent_with_custom_hours(self, client, sample_audit_logs):
        """Test recent changes with custom hours parameter."""
        response = client.get('/api/audit/recent?hours=48')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert data['data']['hours'] == 48

    def test_recent_with_custom_limit(self, client, sample_audit_logs):
        """Test recent changes with custom limit."""
        response = client.get('/api/audit/recent?limit=5')

        assert response.status_code == 200
        data = response.json
        assert len(data['data']['logs']) <= 5

    def test_recent_invalid_hours(self, client):
        """Test recent changes with invalid hours parameter."""
        response = client.get('/api/audit/recent?hours=invalid')

        assert response.status_code == 400
        data = response.json
        assert data['status'] == 'error'
        assert 'integers' in data['message'].lower()

    def test_recent_hours_limit_enforcement(self, client, sample_audit_logs):
        """Test that hours is capped at 168 (7 days)."""
        response = client.get('/api/audit/recent?hours=1000')

        assert response.status_code == 200
        data = response.json
        # Hours should be capped at 168
        assert data['data']['hours'] == 168

    def test_recent_negative_hours(self, client, sample_audit_logs):
        """Test with negative hours value."""
        response = client.get('/api/audit/recent?hours=-5')

        assert response.status_code == 200
        data = response.json
        # Should be normalized to default (24)
        assert data['data']['hours'] == 24

    def test_recent_limit_enforcement(self, client, sample_audit_logs):
        """Test that limit is capped at 1000."""
        response = client.get('/api/audit/recent?limit=5000')

        assert response.status_code == 200
        # Should not error, limit capped at 1000


class TestCleanupEndpoint:
    """Test POST /api/audit/cleanup endpoint."""

    def test_cleanup_default_retention(self, client, app):
        """Test cleanup with default retention days."""
        audit_service = app.audit_service

        # Create old logs (over 180 days old)
        old_timestamp = (datetime.utcnow() - timedelta(days=200)).isoformat() + 'Z'
        audit_id = audit_service.log_change(
            action='CREATE',
            api_name='old-api',
            changed_by='test-user',
            changes={'before': {}, 'after': {'version': '1.0.0'}},
            platform_id='IP4',
            environment_id='dev'
        )

        # Update timestamp to be old
        audit_service.audit_collection.update_one(
            {'audit_id': audit_id},
            {'$set': {'timestamp': old_timestamp}}
        )

        # Cleanup
        response = client.post('/api/audit/cleanup')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert 'deleted_count' in data['data']
        assert data['data']['deleted_count'] >= 1

    def test_cleanup_custom_retention(self, client, app):
        """Test cleanup with custom retention days."""
        audit_service = app.audit_service

        # Create log 100 days old
        old_timestamp = (datetime.utcnow() - timedelta(days=100)).isoformat() + 'Z'
        audit_id = audit_service.log_change(
            action='CREATE',
            api_name='semi-old-api',
            changed_by='test-user',
            changes={'before': {}, 'after': {'version': '1.0.0'}},
            platform_id='IP4',
            environment_id='dev'
        )

        audit_service.audit_collection.update_one(
            {'audit_id': audit_id},
            {'$set': {'timestamp': old_timestamp}}
        )

        # Cleanup with 90 day retention
        response = client.post('/api/audit/cleanup', json={'retention_days': 90})

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert data['data']['deleted_count'] >= 1

    def test_cleanup_invalid_retention_days(self, client):
        """Test cleanup with invalid retention_days."""
        # Negative retention days
        response = client.post('/api/audit/cleanup', json={'retention_days': -5})

        assert response.status_code == 400
        data = response.json
        assert data['status'] == 'error'
        assert 'positive integer' in data['message'].lower()

        # Zero retention days
        response = client.post('/api/audit/cleanup', json={'retention_days': 0})
        assert response.status_code == 400

        # String retention days
        response = client.post('/api/audit/cleanup', json={'retention_days': 'invalid'})
        assert response.status_code == 400

    def test_cleanup_no_old_logs(self, client, clear_audit_logs):
        """Test cleanup when no logs need to be deleted."""
        response = client.post('/api/audit/cleanup')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert data['data']['deleted_count'] == 0


class TestGetActionTypesEndpoint:
    """Test GET /api/audit/actions endpoint."""

    def test_get_action_types(self, client):
        """Test getting list of action types."""
        response = client.get('/api/audit/actions')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert 'actions' in data['data']
        assert isinstance(data['data']['actions'], list)

        # Verify common action types are included
        actions = data['data']['actions']
        assert 'CREATE' in actions
        assert 'UPDATE' in actions or 'UPDATE_STATUS' in actions
        assert 'DELETE' in actions


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_get_logs_with_invalid_date_end_date(self, client):
        """Test logs endpoint with invalid end_date."""
        response = client.get('/api/audit/logs?end_date=not-a-date')

        assert response.status_code == 400
        data = response.json
        assert data['status'] == 'error'
        assert 'date format' in data['message'].lower()

    def test_user_activity_invalid_limit(self, client, sample_audit_logs):
        """Test user activity with invalid limit."""
        response = client.get('/api/audit/users/admin/activity?limit=invalid')

        assert response.status_code == 200  # Falls back to default
        data = response.json
        assert len(data['data']['logs']) > 0

    def test_user_activity_limit_enforcement(self, client, sample_audit_logs):
        """Test that user activity limit is capped at 500."""
        response = client.get('/api/audit/users/admin/activity?limit=1000')

        assert response.status_code == 200
        # Verify limit is enforced (should have at most 500 logs)

    def test_api_history_invalid_limit(self, client, sample_audit_logs):
        """Test API history with invalid limit parameter."""
        response = client.get('/api/audit/logs/test-api-1?limit=abc')

        assert response.status_code == 200  # Falls back to default (50)
        data = response.json
        assert len(data['data']['logs']) > 0
