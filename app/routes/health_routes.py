"""Health check routes."""
from flask import Blueprint, jsonify, current_app
from datetime import datetime

bp = Blueprint('health', __name__)

@bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    try:
        db_status = "healthy"
        db_message = "Connected"
        
        try:
            current_app.db_service.client.admin.command('ping')
        except Exception as e:
            db_status = "unhealthy"
            db_message = str(e)
        
        return jsonify({
            'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'CCR API Manager',
            'database': {
                'status': db_status,
                'message': db_message
            }
        }), 200 if db_status == 'healthy' else 503
        
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503


@bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint for Kubernetes."""
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


@bp.route('/health/live', methods=['GET'])
def liveness_check():
    """Liveness check endpoint for Kubernetes."""
    # Simple liveness - if Flask responds, we're alive
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@bp.route('/health/metrics', methods=['GET'])
def metrics():
    """Prometheus-style metrics endpoint."""
    try:
        stats = current_app.db_service.get_stats()
        
        metrics_text = f"""# HELP api_manager_documents_total Total number of API documents
# TYPE api_manager_documents_total gauge
api_manager_documents_total {stats.get('total_apis', 0)}

# HELP api_manager_platforms_total Total number of unique platforms
# TYPE api_manager_platforms_total gauge
api_manager_platforms_total {stats.get('unique_platforms', 0)}

# HELP api_manager_environments_total Total number of unique environments
# TYPE api_manager_environments_total gauge
api_manager_environments_total {stats.get('unique_environments', 0)}

# HELP api_manager_deployments_total Total number of deployments
# TYPE api_manager_deployments_total gauge
api_manager_deployments_total {stats.get('total_deployments', 0)}
"""
        
        return metrics_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except Exception as e:
        current_app.logger.error(f"Metrics error: {str(e)}")
        return f"# Error generating metrics: {str(e)}", 500, {'Content-Type': 'text/plain'}