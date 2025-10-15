"""
Flask application factory.
Creates and configures the Flask application with all routes and services.
"""

from flask import Flask
from flask_cors import CORS
import logging

from app.config import Config
from app.services.database import DatabaseService  # ← CORRECT: DatabaseService, not Database

logger = logging.getLogger(__name__)


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
    
    # ⚠️ CRITICAL: Load configuration from Config class into Flask app.config
    # This ensures current_app.config.get() works in decorators and routes
    app.config.from_object(config_class)
    
    logger.info(f"Starting {app.config.get('APP_NAME')} v{app.config.get('APP_VERSION')}")
    logger.info(f"Authentication enabled: {app.config.get('AUTH_ENABLED')}")
    
    # Configure CORS with Authorization header support
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', '*'),
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Admin-Key"],  # Include auth headers
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": False
        }
    })
    
    # Initialize database connection
    try:
        # Create DatabaseService instance with correct parameters
        db = DatabaseService(
            mongo_uri=app.config.get('MONGO_URI'),
            db_name=app.config.get('MONGO_DB'),
            collection_name=app.config.get('MONGO_COLLECTION')
        )
        
        # Attach database to app for access in routes
        app.db_service = db
        
        logger.info("Application initialized successfully")
        logger.info(f"Database: {app.config.get('MONGO_DB')}, Collection: {app.config.get('MONGO_COLLECTION')}")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Register blueprints - imports MUST be inside function to avoid circular imports
    from app.routes import (
        api_routes,
        health_routes,
        main_routes,
        deploy_routes,
        update_routes,
        auth_routes  # Authentication endpoints
    )
    
    # Register all blueprints
    app.register_blueprint(main_routes.bp)        # Web interface routes
    app.register_blueprint(api_routes.bp)         # API routes (search, stats, etc.)
    app.register_blueprint(health_routes.bp)      # Health check endpoints
    app.register_blueprint(deploy_routes.bp)      # Deployment routes
    app.register_blueprint(update_routes.bp)      # Update/Delete routes
    app.register_blueprint(auth_routes.bp)        # Authentication routes (NEW)
    
    logger.info("Deploy API endpoint available at: POST /api/deploy")
    logger.info("Update API endpoints available at: PUT/PATCH/DELETE /api/apis/...")
    logger.info("Auth API endpoints available at: POST /api/auth/token, /api/auth/verify")
    
    # Log authentication status
    if app.config.get('AUTH_ENABLED'):
        logger.warning("🔒 Authentication is ENABLED - API endpoints require valid JWT tokens")
    else:
        logger.warning("⚠️  Authentication is DISABLED - API endpoints are publicly accessible")
    
    return app