"""
Deployment routes for API management.

POST /api/deploy - Deploy or update an API
POST /api/deploy/validate - Validate deployment data without deploying
GET /api/platforms - Get available platforms
GET /api/environments - Get available environments
GET /api/statuses - Get available statuses
GET /api/config - Get full configuration
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

from app.utils.auth import require_auth
from app.utils.validators import (
    validate_deployment_request,
    format_validation_error_response,
    get_validation_example
)
from app import limiter

# Import configuration
from app.config import (
    get_valid_platforms,
    get_valid_environments,
    get_valid_statuses,
    PLATFORM_MAPPING,
    ENVIRONMENT_MAPPING
)

logger = logging.getLogger(__name__)

bp = Blueprint('deploy', __name__, url_prefix='/api')


@bp.route('/deploy', methods=['POST'])
@require_auth()
@limiter.limit(lambda: current_app.config.get('RATELIMIT_WRITE_OPS', '20 per minute'))
def deploy_api():
    """
    Deploy or update an API deployment.
    
    Uses upsert logic for Platform array structure.
    Includes comprehensive validation with detailed error messages.
    
    Request Body:
    {
        "api_name": "my-api",           # Required: 3-100 chars, alphanumeric + hyphen/underscore
        "platform_id": "IP4",           # Required: Valid platform (IP2, IP3, IP4, IP5)
        "environment_id": "tst",        # Required: Valid environment (prod, tst, dev, etc.)
        "version": "1.0.0",             # Optional: Version string (default: 1.0.0)
        "status": "RUNNING",            # Required: Valid status
        "updated_by": "username",       # Required: 2-50 chars
        "properties": {}                # Optional: JSON object
    }
    
    Returns:
        201 Created: New deployment created
        200 OK: Existing deployment updated
        400 Bad Request: Validation error with details
        500 Internal Server Error: Deployment failed
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': 'Request body is required',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                },
                'help': {
                    'content_type': 'application/json',
                    'example': get_validation_example('deploy')
                }
            }), 400
        
        # Validate request data
        is_valid, error_details = validate_deployment_request(data)
        
        if not is_valid:
            logger.warning(f"Validation failed for deployment: {error_details}")
            return jsonify(format_validation_error_response(error_details)), 400
        
        # Extract validated fields
        api_name = str(data['api_name']).strip()
        platform_id = str(data['platform_id']).strip()
        environment_id = str(data['environment_id']).strip()
        version = str(data.get('version', '1.0.0')).strip()
        status = str(data['status']).strip()
        updated_by = str(data['updated_by']).strip()
        properties = data.get('properties', {})
        
        logger.info(f"Deploying {api_name} v{version} to {platform_id}/{environment_id} by {updated_by}")
        
        # Call deployment service
        from app.services.deploy_service import DeploymentService
        deploy_service = DeploymentService(current_app.db_service)
        
        result = deploy_service.deploy_api(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=environment_id,
            version=version,
            status=status,
            updated_by=updated_by,
            properties=properties
        )
        
        if result['success']:
            status_code = 201 if result['action'] == 'created' else 200
            logger.info(f"✅ Successfully deployed {api_name} v{version} to {platform_id}/{environment_id} ({result['action']})")

            # Log to audit trail
            try:
                audit_service = current_app.audit_service
                is_new = result['action'] == 'created'
                audit_service.log_deployment(
                    api_name=api_name,
                    platform_id=platform_id,
                    environment_id=environment_id,
                    version=version,
                    status=status,
                    changed_by=updated_by,
                    properties=properties,
                    is_new=is_new
                )
            except Exception as audit_error:
                # Don't fail the deployment if audit logging fails
                logger.error(f"Failed to create audit log: {audit_error}")

            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': environment_id,
                    'version': version,
                    'action': result['action'],
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), status_code
        else:
            logger.error(f"❌ Failed to deploy {api_name}: {result['message']}")
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'DeploymentError',
                    'message': result['message'],
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Deployment error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': f'Deployment failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            'help': 'Please check your request and try again. If the problem persists, contact support.'
        }), 500


@bp.route('/deploy/validate', methods=['POST'])
def validate_deployment():
    """
    Validate deployment data without actually deploying.
    
    Useful for form validation, pre-flight checks, or CI/CD pipeline validation.
    
    Request Body: Same as /api/deploy
    
    Returns:
        200 OK: Validation successful
        400 Bad Request: Validation failed with detailed errors
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'valid': False,
                'error': {
                    'type': 'ValidationError',
                    'message': 'Request body is required',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                },
                'help': {
                    'example': get_validation_example('deploy')
                }
            }), 400
        
        # Validate request data
        is_valid, error_details = validate_deployment_request(data)
        
        if not is_valid:
            response = format_validation_error_response(error_details)
            response['valid'] = False
            return jsonify(response), 400
        
        return jsonify({
            'status': 'success',
            'valid': True,
            'message': 'Validation successful - deployment request is valid',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
        
    except Exception as e:
        logger.error(f"Validation endpoint error: {str(e)}")
        return jsonify({
            'status': 'error',
            'valid': False,
            'error': {
                'type': 'InternalError',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500


@bp.route('/platforms', methods=['GET'])
def get_platforms():
    """
    Get list of available platforms from configuration.
    
    Returns:
        200 OK: List of platforms with IDs and display names
    """
    try:
        platforms = [
            {
                'id': platform_id,
                'name': platform_name,
                'display_name': platform_name
            }
            for platform_id, platform_name in PLATFORM_MAPPING.items()
        ]
        
        return jsonify({
            'status': 'success',
            'data': platforms,
            'count': len(platforms)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching platforms: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500


@bp.route('/environments', methods=['GET'])
def get_environments():
    """
    Get list of available environments from configuration.
    
    Returns:
        200 OK: List of environments with IDs and display names
    """
    try:
        environments = [
            {
                'id': env_id,
                'name': env_name,
                'display_name': env_name
            }
            for env_id, env_name in ENVIRONMENT_MAPPING.items()
        ]
        
        return jsonify({
            'status': 'success',
            'data': environments,
            'count': len(environments)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching environments: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500


@bp.route('/statuses', methods=['GET'])
def get_statuses():
    """
    Get list of available deployment statuses.
    
    Returns:
        200 OK: List of statuses
    """
    try:
        statuses = get_valid_statuses()
        
        # Format as list of objects for consistency with platforms/environments
        statuses_list = [
            {
                'id': status,
                'name': status,
                'display_name': status
            }
            for status in statuses
        ]
        
        return jsonify({
            'status': 'success',
            'data': statuses_list,
            'count': len(statuses_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching statuses: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500


@bp.route('/config', methods=['GET'])
def get_config():
    """
    Get complete configuration (platforms, environments, statuses).
    
    Useful for building UIs or initializing clients.
    
    Returns:
        200 OK: Complete configuration object
    """
    try:
        config = {
            'platforms': [
                {'id': pid, 'name': pname}
                for pid, pname in PLATFORM_MAPPING.items()
            ],
            'environments': [
                {'id': eid, 'name': ename}
                for eid, ename in ENVIRONMENT_MAPPING.items()
            ],
            'statuses': [
                {'id': status, 'name': status}
                for status in get_valid_statuses()
            ],
            'version': current_app.config.get('APP_VERSION', '2.0.0'),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        return jsonify({
            'status': 'success',
            'data': config
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching config: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500