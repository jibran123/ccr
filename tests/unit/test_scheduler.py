"""
Unit tests for AppScheduler.

Tests scheduler initialization, job registration, and job execution.

Week 13-14: Testing & Quality Assurance - Phase 1 Quick Wins (Pure Functions)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from app.utils.scheduler import AppScheduler


class TestSchedulerInitialization:
    """Test scheduler initialization."""

    def test_scheduler_initialization_without_app(self):
        """Test scheduler initializes correctly without app."""
        scheduler = AppScheduler()

        assert scheduler.scheduler is None
        assert scheduler.app is None

    def test_scheduler_initialization_with_app(self):
        """Test scheduler initialization with Flask app."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0,
            'MONGO_URI': 'mongodb://test:27017',
            'MONGO_DB': 'test_db',
            'BACKUP_DIR': '/tmp/backups'
        }.get(key, default)

        scheduler = AppScheduler(mock_app)

        assert scheduler.app == mock_app
        assert scheduler.scheduler is not None

    def test_scheduler_init_app_method(self):
        """Test init_app method."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 3,
            'BACKUP_SCHEDULE_MINUTE': 30
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        assert scheduler.app == mock_app
        assert scheduler.scheduler is not None


class TestSchedulerConfiguration:
    """Test scheduler configuration options."""

    def test_scheduler_disabled_backup_false(self):
        """Test scheduler respects BACKUP_ENABLED=false."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': False,
            'ENABLE_SCHEDULER': True
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        assert scheduler.scheduler is None

    def test_scheduler_disabled_enable_scheduler_false(self):
        """Test scheduler respects ENABLE_SCHEDULER=false."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': False
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        assert scheduler.scheduler is None

    def test_scheduler_custom_backup_schedule(self):
        """Test scheduler with custom backup schedule."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 14,  # 2 PM
            'BACKUP_SCHEDULE_MINUTE': 45
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        jobs = scheduler.get_jobs()
        assert len(jobs) >= 1
        assert any(job['id'] == 'automated_backup' for job in jobs)


class TestSchedulerJobManagement:
    """Test job registration and management."""

    def test_scheduler_jobs_registered(self):
        """Test that backup job is registered."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        jobs = scheduler.get_jobs()

        assert len(jobs) >= 1
        assert any(job['id'] == 'automated_backup' for job in jobs)

    def test_get_jobs_when_no_scheduler(self):
        """Test get_jobs returns empty list when scheduler is None."""
        scheduler = AppScheduler()

        jobs = scheduler.get_jobs()

        assert jobs == []

    def test_get_jobs_structure(self):
        """Test get_jobs returns correct structure."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        jobs = scheduler.get_jobs()

        assert len(jobs) > 0
        for job in jobs:
            assert 'id' in job
            assert 'name' in job
            assert 'next_run' in job
            assert 'trigger' in job


class TestSchedulerLifecycle:
    """Test scheduler start, stop, and lifecycle."""

    def test_scheduler_start(self):
        """Test scheduler start."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        scheduler.start()
        assert scheduler.scheduler.running is True

    def test_scheduler_shutdown(self):
        """Test scheduler shutdown."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        scheduler.start()
        scheduler.shutdown(wait=False)
        assert scheduler.scheduler.running is False

    def test_scheduler_start_when_already_running(self):
        """Test starting scheduler when already running."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        scheduler.start()
        # Try to start again - should not error
        scheduler.start()
        assert scheduler.scheduler.running is True

    def test_scheduler_shutdown_when_not_running(self):
        """Test shutting down scheduler when not running."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        # Don't start, just shutdown - should not error
        scheduler.shutdown(wait=False)
        assert scheduler.scheduler.running is False

    def test_scheduler_shutdown_with_wait(self):
        """Test scheduler shutdown with wait=True."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        scheduler.start()
        scheduler.shutdown(wait=True)
        assert scheduler.scheduler.running is False


class TestBackupJobExecution:
    """Test backup job execution."""

    @patch('app.services.backup_service.BackupService')
    def test_run_backup_job_success(self, mock_backup_service_class):
        """Test successful backup job execution."""
        # Setup mock app
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0,
            'MONGO_URI': 'mongodb://test:27017',
            'MONGO_DB': 'test_db',
            'BACKUP_DIR': '/tmp/backups',
            'BACKUP_RETENTION_DAYS': 14
        }.get(key, default)

        # Setup mock backup service
        mock_backup_service = Mock()
        mock_backup_service.create_backup.return_value = {
            'backup_id': 'backup_123',
            'status': 'success'
        }
        mock_backup_service.cleanup_old_backups.return_value = {
            'deleted_count': 2
        }
        mock_backup_service_class.return_value = mock_backup_service

        # Create scheduler and run job
        scheduler = AppScheduler()
        scheduler.init_app(mock_app)
        scheduler._run_backup_job(mock_app)

        # Verify backup service was called correctly
        mock_backup_service_class.assert_called_once_with(
            mongo_uri='mongodb://test:27017',
            db_name='test_db',
            backup_dir='/tmp/backups'
        )
        mock_backup_service.create_backup.assert_called_once_with(compression=True)
        mock_backup_service.cleanup_old_backups.assert_called_once_with(14)

    @patch('app.services.backup_service.BackupService')
    def test_run_backup_job_failure(self, mock_backup_service_class):
        """Test backup job handles failures."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0,
            'MONGO_URI': 'mongodb://test:27017',
            'MONGO_DB': 'test_db',
            'BACKUP_DIR': '/tmp/backups'
        }.get(key, default)

        # Setup mock to raise exception
        mock_backup_service = Mock()
        mock_backup_service.create_backup.side_effect = Exception("Backup failed")
        mock_backup_service_class.return_value = mock_backup_service

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        # Should raise the exception
        with pytest.raises(Exception, match="Backup failed"):
            scheduler._run_backup_job(mock_app)


class TestEventListeners:
    """Test scheduler event listeners."""

    @patch('app.utils.scheduler.logger')
    def test_job_executed_listener(self, mock_logger):
        """Test job executed listener logs success."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        # Create mock event
        mock_event = Mock()
        mock_event.job_id = 'test_job'

        # Call listener
        scheduler._job_executed_listener(mock_event)

        # Verify logging
        mock_logger.info.assert_called()
        assert 'test_job' in str(mock_logger.info.call_args)

    @patch('app.utils.scheduler.logger')
    def test_job_error_listener(self, mock_logger):
        """Test job error listener logs errors."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'ENABLE_SCHEDULER': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)

        scheduler = AppScheduler()
        scheduler.init_app(mock_app)

        # Create mock event
        mock_event = Mock()
        mock_event.job_id = 'test_job'
        mock_event.exception = Exception("Test error")

        # Call listener
        scheduler._job_error_listener(mock_event)

        # Verify error logging
        mock_logger.error.assert_called()
        assert 'test_job' in str(mock_logger.error.call_args)
        assert 'error' in str(mock_logger.error.call_args).lower()
