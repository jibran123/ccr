"""Flask application factory."""
import logging
from flask import Flask
from flask_cors import CORS
from app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    
    # Initialize database service - FIX: Use correct database and collection
    from app.services.database import DatabaseService
    app.db_service = DatabaseService(
        mongo_uri=app.config['MONGO_URI'],
        db_name='ccr',  # Explicitly set database name
        collection_name='apis'  # Explicitly set collection name
    )
    
    # Register blueprints
    from app.routes import api_routes, health_routes, main_routes
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(api_routes.bp)
    app.register_blueprint(health_routes.bp)
    
    logger.info("Application initialized successfully")
    
    return app