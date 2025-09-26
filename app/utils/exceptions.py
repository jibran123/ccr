"""Custom exceptions and error handlers."""
import logging
from flask import jsonify

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass

class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

def register_error_handlers(app):
    """
    Register error handlers for the application.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """Handle validation errors."""
        logger.warning(f"Validation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    
    @app.errorhandler(DatabaseError)
    def handle_database_error(e):
        """Handle database errors."""
        logger.error(f"Database error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database operation failed'
        }), 500
    
    @app.errorhandler(AuthenticationError)
    def handle_authentication_error(e):
        """Handle authentication errors."""
        logger.warning(f"Authentication error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Authentication failed'
        }), 401
    
    @app.errorhandler(404)
    def handle_not_found(e):
        """Handle 404 errors."""
        return jsonify({
            'status': 'error',
            'message': 'Resource not found'
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(e):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500