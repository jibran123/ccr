"""Update routes for API management."""
from flask import Blueprint, request, jsonify, current_app
import logging
from app.utils.auth import require_auth

# Import configuration
from app.config import (
    is_valid_platform,
    is_valid_environment,
    is_valid_status,
    get_valid_platforms,
    get_valid_environments,
    get_valid_statuses
)

logger = logging.getLogger(__name__)

bp = Blueprint('update', __name__, url_prefix='/api/apis')

@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>', methods=['PUT'])
@require_auth()
def update_deployment_full(api_name, platform_id, env_id):
    """
    Full update (PUT) - Replace entire deployment.
    Replaces all fields including properties.
    
    URL: PUT /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
    
    Body: {
        "version": "2.0.0",
        "status": "RUNNING",
        "updated_by": "john.doe",
        "properties": {
            "api.id": "12345",
            "config": "value"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Validate required fields for full update (including version)
        required_fields = ['version', 'status', 'updated_by', 'properties']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            return jsonify({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        # Validate values
        if not is_valid_platform(platform_id):
            return jsonify({
                'status': 'error',
                'message': f'Invalid platform. Must be one of: {", ".join(get_valid_platforms())}'
            }), 400
        
        if not is_valid_environment(env_id):
            return jsonify({
                'status': 'error',
                'message': f'Invalid environment. Must be one of: {", ".join(get_valid_environments())}'
            }), 400
        
        if not is_valid_status(data['status']):
            return jsonify({
                'status': 'error',
                'message': f'Invalid status. Must be one of: {", ".join(get_valid_statuses())}'
            }), 400
        
        if not isinstance(data['properties'], dict):
            return jsonify({
                'status': 'error',
                'message': 'Properties must be an object'
            }), 400
        
        # Call service
        from app.services.deploy_service import DeploymentService
        service = DeploymentService(current_app.db_service)
        
        result = service.update_deployment_full(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id,
            version=data['version'],  # ← FIXED: Added version parameter
            status=data['status'],
            updated_by=data['updated_by'],
            properties=data['properties']
        )
        
        if result['success']:
            status_code = 200 if result['action'] in ['updated', 'unchanged'] else 201
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': env_id,
                    'action': result['action']
                }
            }), status_code
        else:
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), 404 if result['action'] == 'not_found' else 500
            
    except Exception as e:
        logger.error(f"Full update error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>', methods=['PATCH'])
@require_auth()
def update_deployment_partial(api_name, platform_id, env_id):
    """
    Partial update (PATCH) - Update only specified fields.
    Merges with existing data.
    
    URL: PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
    
    Body: {
        "version": "1.1.0",
        "status": "DEPLOYING",
        "updated_by": "admin",
        "properties": {
            "new_config": "value"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # At least one field to update
        updatable_fields = ['version', 'status', 'properties', 'updated_by']
        has_update = any(field in data for field in updatable_fields)
        
        if not has_update:
            return jsonify({
                'status': 'error',
                'message': 'At least one field to update is required'
            }), 400
        
        # Validate platform/environment
        if not is_valid_platform(platform_id):
            return jsonify({
                'status': 'error',
                'message': f'Invalid platform. Must be one of: {", ".join(get_valid_platforms())}'
            }), 400
        
        if not is_valid_environment(env_id):
            return jsonify({
                'status': 'error',
                'message': f'Invalid environment. Must be one of: {", ".join(get_valid_environments())}'
            }), 400
        
        # Validate status if provided
        if 'status' in data and not is_valid_status(data['status']):
            return jsonify({
                'status': 'error',
                'message': f'Invalid status. Must be one of: {", ".join(get_valid_statuses())}'
            }), 400
        
        # Validate properties if provided
        if 'properties' in data and not isinstance(data['properties'], dict):
            return jsonify({
                'status': 'error',
                'message': 'Properties must be an object'
            }), 400
        
        # Call service
        from app.services.deploy_service import DeploymentService
        service = DeploymentService(current_app.db_service)
        
        result = service.update_deployment_partial(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id,
            updates=data
        )
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': env_id,
                    'action': result['action'],
                    'modified_fields': result.get('modified_fields', [])
                }
            }), 200
        else:
            status_code = 404 if result['action'] == 'not_found' else 500
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), status_code
            
    except Exception as e:
        logger.error(f"Partial update error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>/status', methods=['PATCH'])
@require_auth()
def update_deployment_status(api_name, platform_id, env_id):
    """
    Update only deployment status.
    
    URL: PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}/status
    
    Body: {
        "status": "RUNNING",
        "updated_by": "admin"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Status is required'
            }), 400
        
        if 'updated_by' not in data:
            return jsonify({
                'status': 'error',
                'message': 'updated_by is required'
            }), 400
        
        # Validate status
        if not is_valid_status(data['status']):
            return jsonify({
                'status': 'error',
                'message': f'Invalid status. Must be one of: {", ".join(get_valid_statuses())}'
            }), 400
        
        # Call service
        from app.services.deploy_service import DeploymentService
        service = DeploymentService(current_app.db_service)
        
        result = service.update_status_only(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id,
            status=data['status'],
            updated_by=data['updated_by']
        )
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': env_id,
                    'new_status': data['status']
                }
            }), 200
        else:
            status_code = 404 if result['action'] == 'not_found' else 500
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), status_code
            
    except Exception as e:
        logger.error(f"Status update error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>/properties', methods=['PATCH'])
@require_auth()
def update_deployment_properties(api_name, platform_id, env_id):
    """
    Update only deployment properties.
    Merges with existing properties.
    
    URL: PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}/properties
    
    Body: {
        "updated_by": "admin",
        "properties": {
            "version": "2.1.0",
            "new_config": "value"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'properties' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Properties are required'
            }), 400
        
        if 'updated_by' not in data:
            return jsonify({
                'status': 'error',
                'message': 'updated_by is required'
            }), 400
        
        if not isinstance(data['properties'], dict):
            return jsonify({
                'status': 'error',
                'message': 'Properties must be an object'
            }), 400
        
        # Call service
        from app.services.deploy_service import DeploymentService
        service = DeploymentService(current_app.db_service)
        
        result = service.update_properties_only(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id,
            properties=data['properties'],
            updated_by=data['updated_by']
        )
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': env_id,
                    'updated_properties': list(data['properties'].keys())
                }
            }), 200
        else:
            status_code = 404 if result['action'] == 'not_found' else 500
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), status_code
            
    except Exception as e:
        logger.error(f"Properties update error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>', methods=['DELETE'])
@require_auth()
def delete_deployment(api_name, platform_id, env_id):
    """
    Delete a specific deployment.
    Removes the environment from platform.
    If platform becomes empty, removes platform.
    If API has no more deployments, removes API.
    
    URL: DELETE /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
    """
    try:
        # Call service
        from app.services.deploy_service import DeploymentService
        service = DeploymentService(current_app.db_service)
        
        result = service.delete_deployment(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id
        )
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': env_id,
                    'action': result['action']
                }
            }), 200
        else:
            status_code = 404 if result['action'] == 'not_found' else 500
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), status_code
            
    except Exception as e:
        logger.error(f"Delete error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>', methods=['GET'])
@require_auth()
def get_deployment(api_name, platform_id, env_id):
    """
    Get details of a specific deployment.
    
    URL: GET /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
    """
    try:
        from app.services.deploy_service import DeploymentService
        service = DeploymentService(current_app.db_service)
        
        deployment = service.get_deployment_status(api_name, platform_id, env_id)
        
        if deployment:
            return jsonify({
                'status': 'success',
                'deployment': deployment
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Deployment not found: {api_name} on {platform_id}/{env_id}'
            }), 404
            
    except Exception as e:
        logger.error(f"Get deployment error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500