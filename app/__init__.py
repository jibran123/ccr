"""Flask application factory."""
import logging
from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.services.database import DatabaseService
from app.utils.exceptions import register_error_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    
    # Initialize database service
    app.db_service = DatabaseService(
        mongo_uri=app.config['MONGO_URI'],
        db_name=app.config['MONGO_DB'],
        collection_name=app.config['MONGO_COLLECTION']
    )
    
    # Register blueprints - imports MUST be inside function to avoid circular imports
    from app.routes import api_routes, health_routes, main_routes, deploy_routes
    
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(api_routes.bp)
    app.register_blueprint(health_routes.bp)
    app.register_blueprint(deploy_routes.bp)  # Register deploy routes
    
    # Register error handlers
    register_error_handlers(app)
    
    logger.info("Application initialized successfully")
    logger.info(f"Database: {app.config['MONGO_DB']}, Collection: {app.config['MONGO_COLLECTION']}")
    logger.info("Deploy API endpoint available at: POST /api/deploy")
    
    return app