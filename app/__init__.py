"""
Flask application factory.
Creates and configures the Flask application with all routes and services.
"""

from flask import Flask
from flask_cors import CORS
from flask_compress import Compress
import logging
import atexit

from app.config import Config
from app.services.database import DatabaseService
from app.services.audit_service import AuditService
from app.utils.scheduler import AppScheduler

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AppScheduler()


def create_app(config_class=Config):
    """
    Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use (defaults to Config)
        
    Returns:
        Configured Flask application instance
    """
    
    # Create Flask app
    app = Flask(__name__)

    # Load configuration from Config class into Flask app.config
    app.config.from_object(config_class)

    logger.info(f"Starting {app.config.get('APP_NAME')} v{app.config.get('APP_VERSION')}")
    logger.info(f"Authentication enabled: {app.config.get('AUTH_ENABLED')}")
    logger.info(f"Backup enabled: {app.config.get('BACKUP_ENABLED')}")

    # Enable gzip compression for all responses
    # Compresses responses > 500 bytes (default)
    # Automatically adds Content-Encoding: gzip header
    Compress(app)
    logger.info("✅ Response compression (gzip) enabled")
    
    # Configure CORS with Authorization header support
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', '*'),
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Admin-Key"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": False
        }
    })
    
    # Initialize database connection
    try:
        db = DatabaseService(
            mongo_uri=app.config.get('MONGO_URI'),
            db_name=app.config.get('MONGO_DB'),
            collection_name=app.config.get('MONGO_COLLECTION')
        )

        app.db_service = db

        # Initialize audit service
        audit_retention_days = app.config.get('AUDIT_RETENTION_DAYS', 180)
        audit_service = AuditService(db, retention_days=audit_retention_days)
        app.audit_service = audit_service

        logger.info("Application initialized successfully")
        logger.info(f"Database: {app.config.get('MONGO_DB')}, Collection: {app.config.get('MONGO_COLLECTION')}")
        logger.info(f"Audit logging enabled with {audit_retention_days} day retention")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Register blueprints
    from app.routes import (
        api_routes,
        health_routes,
        main_routes,
        deploy_routes,
        update_routes,
        auth_routes,
        admin_routes,
        audit_routes
    )

    app.register_blueprint(main_routes.bp)
    app.register_blueprint(api_routes.bp)
    app.register_blueprint(health_routes.bp)
    app.register_blueprint(deploy_routes.bp)
    app.register_blueprint(update_routes.bp)
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(admin_routes.bp)
    app.register_blueprint(audit_routes.bp)

    logger.info("Deploy API endpoint available at: POST /api/deploy")
    logger.info("Update API endpoints available at: PUT/PATCH/DELETE /api/apis/...")
    logger.info("Auth API endpoints available at: POST /api/auth/token, /api/auth/verify")
    logger.info("Admin API endpoints available at: /api/admin/*")
    logger.info("Audit API endpoints available at: /api/audit/*")
    
    # Log authentication status
    if app.config.get('AUTH_ENABLED'):
        logger.warning("🔒 Authentication is ENABLED - API endpoints require valid JWT tokens")
    else:
        logger.warning("⚠️  Authentication is DISABLED - API endpoints are publicly accessible")
    
    # Initialize and start scheduler
    if app.config.get('BACKUP_ENABLED', True):
        scheduler.init_app(app)
        logger.info("✅ Scheduler initialized - will start after app context")
    else:
        logger.info("⚠️  Scheduler disabled - automated backups will not run")
    
    # Register cleanup on shutdown
    atexit.register(lambda: scheduler.shutdown(wait=False))
    
    return app