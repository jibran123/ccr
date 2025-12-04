"""
Flask application factory.
Creates and configures the Flask application with all routes and services.
"""

from flask import Flask, request
from flask_cors import CORS
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import logging
import atexit

from app.config import Config
from app.services.database import DatabaseService
from app.services.audit_service import AuditService
from app.utils.scheduler import AppScheduler

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AppScheduler()

# Global rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
    headers_enabled=True
)


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

    # Configure session management
    from datetime import timedelta
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)  # 8-hour sessions
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('FORCE_HTTPS', False)  # Secure cookies if HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
    logger.info("✅ Session management configured (8-hour lifetime)")

    logger.info(f"Starting {app.config.get('APP_NAME')} v{app.config.get('APP_VERSION')}")
    logger.info(f"Authentication enabled: {app.config.get('AUTH_ENABLED')}")
    logger.info(f"Backup enabled: {app.config.get('BACKUP_ENABLED')}")

    # Enable gzip compression for all responses
    # Compresses responses > 500 bytes (default)
    # Automatically adds Content-Encoding: gzip header
    Compress(app)
    logger.info("✅ Response compression (gzip) enabled")

    # Configure rate limiting
    if app.config.get('RATELIMIT_ENABLED', True):
        limiter.init_app(app)
        limiter._storage_uri = app.config.get('RATELIMIT_STORAGE_URI', 'memory://')
        limiter._default_limits = app.config.get('RATELIMIT_DEFAULT', '100 per hour, 20 per minute')
        limiter._headers_enabled = app.config.get('RATELIMIT_HEADERS_ENABLED', True)
        logger.info("✅ Rate limiting enabled")
        logger.info(f"   Storage: {app.config.get('RATELIMIT_STORAGE_URI', 'memory://')}")
        logger.info(f"   Default limits: {app.config.get('RATELIMIT_DEFAULT')}")
    else:
        logger.warning("⚠️  Rate limiting is DISABLED")

    # Configure security headers
    if app.config.get('SECURITY_HEADERS_ENABLED', True):
        # Content Security Policy
        csp = {
            'default-src': "'self'",
            'script-src': ["'self'", "'unsafe-inline'"],  # Allow inline scripts for current implementation
            'style-src': ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com"],   # Allow inline styles and FontAwesome CDN
            'img-src': ["'self'", "data:", "https:"],
            'font-src': ["'self'", "data:", "https://cdnjs.cloudflare.com"],  # Allow FontAwesome fonts
            'connect-src': ["'self'"],
            'frame-ancestors': "'none'",
            'base-uri': "'self'",
            'form-action': "'self'"
        }

        Talisman(
            app,
            force_https=app.config.get('FORCE_HTTPS', False),
            strict_transport_security=app.config.get('HSTS_ENABLED', True),
            strict_transport_security_max_age=app.config.get('HSTS_MAX_AGE', 31536000),
            strict_transport_security_include_subdomains=app.config.get('HSTS_INCLUDE_SUBDOMAINS', True),
            strict_transport_security_preload=app.config.get('HSTS_PRELOAD', False),
            content_security_policy=csp if app.config.get('CSP_ENABLED', True) else None,
            # Disable nonce generation - we're using 'unsafe-inline' for compatibility with current templates
            # content_security_policy_nonce_in=None,
            referrer_policy='strict-origin-when-cross-origin',
            feature_policy={
                'geolocation': "'none'",
                'microphone': "'none'",
                'camera': "'none'",
                'payment': "'none'",
                'usb': "'none'"
            }
        )
        logger.info("✅ Security headers enabled")
        logger.info(f"   Force HTTPS: {app.config.get('FORCE_HTTPS', False)}")
        logger.info(f"   HSTS: {app.config.get('HSTS_ENABLED', True)}")
        logger.info(f"   CSP: {app.config.get('CSP_ENABLED', True)}")
    else:
        logger.warning("⚠️  Security headers are DISABLED")

    # Configure CORS with Authorization header support
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', '*'),
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Admin-Key"],
            "expose_headers": ["Content-Type", "Authorization", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
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