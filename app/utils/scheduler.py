"""
Background task scheduler for automated operations.

Uses APScheduler to run periodic tasks like automated backups.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)


class AppScheduler:
    """Application scheduler for background jobs."""
    
    def __init__(self, app=None):
        """
        Initialize scheduler.
        
        Args:
            app: Flask application instance (optional)
        """
        self.scheduler = None
        self.app = app
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        Initialize scheduler with Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Check if backups are enabled or scheduler is explicitly disabled
        if not app.config.get('BACKUP_ENABLED', True) or not app.config.get('ENABLE_SCHEDULER', True):
            logger.info("Scheduler is disabled (BACKUP_ENABLED=%s, ENABLE_SCHEDULER=%s)",
                       app.config.get('BACKUP_ENABLED', True),
                       app.config.get('ENABLE_SCHEDULER', True))
            return
        
        # Create scheduler
        self.scheduler = BackgroundScheduler(
            daemon=True,
            timezone='UTC'
        )
        
        # Add event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )
        
        # Schedule backup job
        self._schedule_backup_job(app)
        
        logger.info("Scheduler initialized successfully")
    
    def _schedule_backup_job(self, app):
        """
        Schedule automated backup job.
        
        Args:
            app: Flask application instance
        """
        hour = app.config.get('BACKUP_SCHEDULE_HOUR', 2)
        minute = app.config.get('BACKUP_SCHEDULE_MINUTE', 0)
        
        # Create cron trigger (runs daily at specified time)
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone='UTC'
        )
        
        # Add job
        self.scheduler.add_job(
            func=self._run_backup_job,
            trigger=trigger,
            id='automated_backup',
            name='Automated Database Backup',
            replace_existing=True,
            args=[app]
        )
        
        logger.info(f"Scheduled automated backup job: Daily at {hour:02d}:{minute:02d} UTC")
    
    def _run_backup_job(self, app):
        """
        Execute automated backup job.
        
        Args:
            app: Flask application instance
        """
        try:
            logger.info("🔄 Starting automated backup job...")
            
            # Import here to avoid circular dependency
            from app.services.backup_service import BackupService
            
            # Create backup service with app config
            backup_service = BackupService(
                mongo_uri=app.config.get('MONGO_URI'),
                db_name=app.config.get('MONGO_DB'),
                backup_dir=app.config.get('BACKUP_DIR')
            )
            
            # Create backup
            result = backup_service.create_backup(compression=True)
            
            logger.info(f"✅ Automated backup completed: {result['backup_id']}")
            
            # Cleanup old backups
            retention_days = app.config.get('BACKUP_RETENTION_DAYS', 14)
            cleanup_result = backup_service.cleanup_old_backups(retention_days)
            
            logger.info(f"🧹 Cleanup completed: Deleted {cleanup_result['deleted_count']} old backups")
            
        except Exception as e:
            logger.error(f"❌ Automated backup job failed: {str(e)}", exc_info=True)
            raise
    
    def _job_executed_listener(self, event):
        """
        Listener for successful job execution.
        
        Args:
            event: Job execution event
        """
        logger.info(f"Job '{event.job_id}' executed successfully")
    
    def _job_error_listener(self, event):
        """
        Listener for job execution errors.
        
        Args:
            event: Job error event
        """
        logger.error(f"Job '{event.job_id}' failed with error: {event.exception}")
    
    def start(self):
        """Start the scheduler."""
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
    
    def shutdown(self, wait=True):
        """
        Shutdown the scheduler gracefully.
        
        Args:
            wait: Wait for running jobs to complete
        """
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scheduler stopped")
    
    def get_jobs(self):
        """
        Get list of scheduled jobs.
        
        Returns:
            List of job information
        """
        if not self.scheduler:
            return []
        
        jobs = []
        for job in self.scheduler.get_jobs():
            # ✅ FIX: Handle different APScheduler versions
            # Try to get next_run_time, handle if attribute doesn't exist
            try:
                # APScheduler 3.x style
                next_run = job.next_run_time.isoformat() if job.next_run_time else None
            except AttributeError:
                # APScheduler 4.x or attribute doesn't exist
                # Try alternative methods
                try:
                    if hasattr(job, 'trigger') and hasattr(job.trigger, 'get_next_fire_time'):
                        next_fire = job.trigger.get_next_fire_time(None, datetime.now(job.trigger.timezone))
                        next_run = next_fire.isoformat() if next_fire else None
                    else:
                        next_run = None
                except Exception:
                    next_run = None
            
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': next_run,
                'trigger': str(job.trigger)
            })
        
        return jobs