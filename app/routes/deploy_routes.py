"""Deployment routes for API management."""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

# Import configuration
from app.config import (
    get_valid_platforms,
    get_valid_environments,
    get_valid_statuses,
    is_valid_platform,
    is_valid_environment,
    is_valid_status,
    PLATFORM_MAPPING,
    ENVIRONMENT_MAPPING
)

logger = logging.getLogger(__name__)

bp = Blueprint('deploy', __name__, url_prefix='/api')

@bp.route('/deploy', methods=['POST'])
def deploy_api():
    """
    Deploy or update an API deployment.
    Uses upsert logic for Platform array structure.
    Now supports version field.
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Extract fields
        api_name = data.get('api_name', '').strip()
        platform_id = data.get('platform_id', '').strip()
        environment_id = data.get('environment_id', '').strip()
        version = data.get('version', '1.0.0').strip()  # Default to 1.0.0 if not provided
        status = data.get('status', 'DEPLOYING').strip()
        updated_by = data.get('updated_by', 'system').strip()
        properties = data.get('properties', {})
        
        # Validate required fields
        if not api_name:
            return jsonify({
                'status': 'error',
                'message': 'API name is required'
            }), 400
        
        if not platform_id:
            return jsonify({
                'status': 'error',
                'message': 'Platform ID is required'
            }), 400
        
        if not environment_id:
            return jsonify({
                'status': 'error',
                'message': 'Environment ID is required'
            }), 400
        
        # Validate platform using config
        if not is_valid_platform(platform_id):
            valid_platforms = get_valid_platforms()
            return jsonify({
                'status': 'error',
                'message': f'Invalid platform. Must be one of: {", ".join(valid_platforms)}'
            }), 400
        
        # Validate environment using config
        if not is_valid_environment(environment_id):
            valid_environments = get_valid_environments()
            return jsonify({
                'status': 'error',
                'message': f'Invalid environment. Must be one of: {", ".join(valid_environments)}'
            }), 400
        
        # Validate status using config
        if not is_valid_status(status):
            valid_statuses = get_valid_statuses()
            return jsonify({
                'status': 'error',
                'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        # Validate properties
        if not isinstance(properties, dict):
            return jsonify({
                'status': 'error',
                'message': 'Properties must be an object/dictionary'
            }), 400
        
        # Validate version format (optional - can be made stricter)
        if version and len(version) > 50:
            return jsonify({
                'status': 'error',
                'message': 'Version must be 50 characters or less'
            }), 400
        
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
            logger.info(f"Successfully deployed {api_name} v{version} to {platform_id}/{environment_id}")
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': environment_id,
                    'version': version,
                    'action': result['action']  # 'created' or 'updated'
                }
            }), 201 if result['action'] == 'created' else 200
        else:
            logger.error(f"Failed to deploy {api_name}: {result['message']}")
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Deployment failed: {str(e)}'
        }), 500

@bp.route('/deploy/validate', methods=['POST'])
def validate_deployment():
    """
    Validate deployment data without actually deploying.
    Useful for form validation.
    """
    try:
        data = request.get_json()
        
        # Perform validation
        errors = []
        
        # Check required fields
        if not data.get('api_name'):
            errors.append('API name is required')
        elif len(data['api_name']) > 255:
            errors.append('API name must be 255 characters or less')
        
        if not data.get('platform_id'):
            errors.append('Platform is required')
        elif not is_valid_platform(data['platform_id']):
            valid_platforms = get_valid_platforms()
            errors.append(f"Invalid platform. Must be one of: {', '.join(valid_platforms)}")
        
        if not data.get('environment_id'):
            errors.append('Environment is required')
        elif not is_valid_environment(data['environment_id']):
            valid_environments = get_valid_environments()
            errors.append(f"Invalid environment. Must be one of: {', '.join(valid_environments)}")
        
        # Check status if provided
        if 'status' in data and data['status']:
            if not is_valid_status(data['status']):
                valid_statuses = get_valid_statuses()
                errors.append(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        # Check version if provided
        if 'version' in data and data['version']:
            if len(str(data['version'])) > 50:
                errors.append('Version must be 50 characters or less')
        
        # Check properties
        if 'properties' in data:
            if not isinstance(data['properties'], dict):
                errors.append('Properties must be an object')
            elif len(data['properties']) > 100:
                errors.append('Maximum 100 properties allowed')
            else:
                for key, value in data['properties'].items():
                    if len(str(key)) > 100:
                        errors.append(f'Property key "{key}" is too long (max 100 chars)')
                    if len(str(value)) > 1000:
                        errors.append(f'Property value for "{key}" is too long (max 1000 chars)')
        
        if errors:
            return jsonify({
                'status': 'error',
                'valid': False,
                'errors': errors
            }), 400
        
        return jsonify({
            'status': 'success',
            'valid': True,
            'message': 'Validation successful'
        })
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/platforms', methods=['GET'])
def get_platforms():
    """Get list of available platforms from config."""
    try:
        platforms = [
            {
                'id': platform_id,
                'name': display_name
            }
            for platform_id, display_name in PLATFORM_MAPPING.items()
        ]
        
        return jsonify({
            'status': 'success',
            'data': platforms,
            'count': len(platforms)
        })
    except Exception as e:
        logger.error(f"Error getting platforms: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/environments', methods=['GET'])
def get_environments():
    """Get list of available environments from config."""
    try:
        environments = [
            {
                'id': env_id,
                'name': display_name
            }
            for env_id, display_name in ENVIRONMENT_MAPPING.items()
        ]
        
        return jsonify({
            'status': 'success',
            'data': environments,
            'count': len(environments)
        })
    except Exception as e:
        logger.error(f"Error getting environments: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/statuses', methods=['GET'])
def get_statuses():
    """Get list of available statuses from config."""
    try:
        statuses = get_valid_statuses()
        
        return jsonify({
            'status': 'success',
            'data': statuses,
            'count': len(statuses)
        })
    except Exception as e:
        logger.error(f"Error getting statuses: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/config', methods=['GET'])
def get_deployment_config():
    """
    Get complete deployment configuration.
    Useful for frontend forms and validation.
    """
    try:
        config = {
            'platforms': [
                {'id': pid, 'name': name} 
                for pid, name in PLATFORM_MAPPING.items()
            ],
            'environments': [
                {'id': eid, 'name': name} 
                for eid, name in ENVIRONMENT_MAPPING.items()
            ],
            'statuses': get_valid_statuses()
        }
        
        return jsonify({
            'status': 'success',
            'data': config
        })
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500