#!/usr/bin/env python
"""
Application entry point.
Starts the Flask application.
"""

from app import create_app, scheduler
import logging

logger = logging.getLogger(__name__)

app = create_app()

if __name__ == '__main__':
    # Start scheduler after app is created
    if hasattr(scheduler, 'scheduler') and scheduler.scheduler:
        scheduler.start()
        logger.info("✅ Scheduler started")
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )