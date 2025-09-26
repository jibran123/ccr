"""Health check routes."""
from flask import Blueprint, jsonify, current_app
from datetime import datetime

bp = Blueprint('health', __name__)

@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        db_status = "healthy"
        db_message = "Connected"
        
        try:
            # Try to ping the database
            current_app.db_service.client.admin.command('ping')
        except Exception as e:
            db_status = "unhealthy"
            db_message = str(e)
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'CCR API Manager',
            'database': {
                'status': db_status,
                'message': db_message
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503

@bp.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check if database is accessible
        current_app.db_service.client.admin.command('ping')
        
        return jsonify({
            'status': 'ready',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'not ready',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503