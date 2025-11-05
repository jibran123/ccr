"""
Unit tests for AppScheduler.

Tests scheduler initialization and job registration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.utils.scheduler import AppScheduler


class TestScheduler:
    """Test AppScheduler functionality."""
    
    def test_scheduler_initialization(self):
        """Test scheduler initializes correctly."""
        scheduler = AppScheduler()
        
        assert scheduler.scheduler is None
        assert scheduler.app is None
    
    def test_scheduler_with_app(self):
        """Test scheduler initialization with Flask app."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0,
            'MONGO_URI': 'mongodb://test:27017',
            'MONGO_DB': 'test_db',
            'BACKUP_DIR': '/tmp/backups'
        }.get(key, default)
        
        scheduler = AppScheduler(mock_app)
        
        assert scheduler.app == mock_app
        assert scheduler.scheduler is not None
    
    def test_scheduler_jobs_registered(self):
        """Test that backup job is registered."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)
        
        scheduler = AppScheduler()
        scheduler.init_app(mock_app)
        
        jobs = scheduler.get_jobs()
        
        assert len(jobs) >= 1
        assert any(job['id'] == 'automated_backup' for job in jobs)
    
    def test_scheduler_disabled(self):
        """Test scheduler respects BACKUP_ENABLED=false."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': False
        }.get(key, default)
        
        scheduler = AppScheduler()
        scheduler.init_app(mock_app)
        
        assert scheduler.scheduler is None
    
    def test_scheduler_start_stop(self):
        """Test scheduler start and stop."""
        mock_app = Mock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            'BACKUP_ENABLED': True,
            'BACKUP_SCHEDULE_HOUR': 2,
            'BACKUP_SCHEDULE_MINUTE': 0
        }.get(key, default)
        
        scheduler = AppScheduler()
        scheduler.init_app(mock_app)
        
        # Start scheduler
        scheduler.start()
        assert scheduler.scheduler.running is True
        
        # Stop scheduler
        scheduler.shutdown(wait=False)
        assert scheduler.scheduler.running is False
