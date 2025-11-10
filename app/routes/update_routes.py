"""
Update routes for API management.

PUT /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id} - Full update
PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id} - Partial update
GET /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id} - Get deployment details
DELETE /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id} - Delete deployment
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

from app.utils.auth import require_auth
from app.utils.validators import (
    validate_update_request,
    format_validation_error_response,
    get_validation_example
)

# Import configuration
from app.config import (
    is_valid_platform,
    is_valid_environment,
    get_valid_platforms,
    get_valid_environments
)

logger = logging.getLogger(__name__)

bp = Blueprint('update', __name__, url_prefix='/api/apis')


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>', methods=['PUT'])
@require_auth()
def update_deployment_full(api_name, platform_id, env_id):
    """
    Full update (PUT) - Replace entire deployment.
    
    Replaces all fields including properties. All fields are required.
    
    URL: PUT /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
    
    Request Body:
    {
        "version": "2.0.0",           # Required: Version string
        "status": "RUNNING",          # Required: Valid status
        "updated_by": "username",     # Required: 2-50 chars
        "properties": {}              # Required: JSON object (can be empty)
    }
    
    Returns:
        200 OK: Deployment updated successfully
        400 Bad Request: Validation error
        404 Not Found: Deployment doesn't exist
        500 Internal Server Error: Update failed
    """
    try:
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
                    'example': get_validation_example('update_full')
                }
            }), 400
        
        # Validate platform and environment from URL
        if not is_valid_platform(platform_id):
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': f'Invalid platform: {platform_id}',
                    'details': {
                        'platform_id': f'Must be one of: {", ".join(get_valid_platforms())}'
                    },
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        if not is_valid_environment(env_id):
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': f'Invalid environment: {env_id}',
                    'details': {
                        'environment_id': f'Must be one of: {", ".join(get_valid_environments())}'
                    },
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        # Validate request body (is_patch=False for PUT)
        is_valid, error_details = validate_update_request(data, is_patch=False)
        
        if not is_valid:
            logger.warning(f"Validation failed for PUT {api_name}/{platform_id}/{env_id}: {error_details}")
            return jsonify(format_validation_error_response(error_details)), 400
        
        # Extract validated fields
        version = str(data['version']).strip()
        status = str(data['status']).strip()
        updated_by = str(data['updated_by']).strip()
        properties = data['properties']
        
        logger.info(f"Full update for {api_name} on {platform_id}/{env_id} by {updated_by}")
        
        # Call deployment service
        from app.services.deploy_service import DeploymentService
        deploy_service = DeploymentService(current_app.db_service)
        
        result = deploy_service.update_deployment_full(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id,
            version=version,
            status=status,
            updated_by=updated_by,
            properties=properties
        )
        
        if result['success']:
            logger.info(f"✅ Successfully updated {api_name} on {platform_id}/{env_id}")
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': env_id,
                    'version': version,
                    'action': 'updated',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 200
        else:
            status_code = 404 if 'not found' in result['message'].lower() else 500
            logger.error(f"❌ Failed to update {api_name}: {result['message']}")
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'UpdateError',
                    'message': result['message'],
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), status_code
            
    except Exception as e:
        logger.error(f"❌ Update error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': f'Update failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>', methods=['PATCH'])
@require_auth()
def update_deployment_partial(api_name, platform_id, env_id):
    """
    Partial update (PATCH) - Update only specified fields.
    
    Merges with existing data. At least one field required.
    
    URL: PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
    
    Request Body (all fields optional, but at least one required):
    {
        "version": "2.0.0",           # Optional: New version
        "status": "RUNNING",          # Optional: New status
        "updated_by": "username",     # Optional: Who made the update
        "properties": {}              # Optional: Properties to merge
    }
    
    Returns:
        200 OK: Deployment updated successfully
        400 Bad Request: Validation error
        404 Not Found: Deployment doesn't exist
        500 Internal Server Error: Update failed
    """
    try:
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
                    'example': get_validation_example('update_partial')
                }
            }), 400
        
        # Validate platform and environment from URL
        if not is_valid_platform(platform_id):
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': f'Invalid platform: {platform_id}',
                    'details': {
                        'platform_id': f'Must be one of: {", ".join(get_valid_platforms())}'
                    },
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        if not is_valid_environment(env_id):
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': f'Invalid environment: {env_id}',
                    'details': {
                        'environment_id': f'Must be one of: {", ".join(get_valid_environments())}'
                    },
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        # Validate request body (is_patch=True for PATCH)
        is_valid, error_details = validate_update_request(data, is_patch=True)
        
        if not is_valid:
            logger.warning(f"Validation failed for PATCH {api_name}/{platform_id}/{env_id}: {error_details}")
            return jsonify(format_validation_error_response(error_details)), 400
        
        logger.info(f"Partial update for {api_name} on {platform_id}/{env_id}")
        
        # Call deployment service
        from app.services.deploy_service import DeploymentService
        deploy_service = DeploymentService(current_app.db_service)
        
        result = deploy_service.update_deployment_partial(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id,
            update_data=data
        )
        
        if result['success']:
            logger.info(f"✅ Successfully patched {api_name} on {platform_id}/{env_id}")
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': env_id,
                    'action': 'updated',
                    'fields_updated': list(data.keys()),
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 200
        else:
            status_code = 404 if 'not found' in result['message'].lower() else 500
            logger.error(f"❌ Failed to patch {api_name}: {result['message']}")
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'UpdateError',
                    'message': result['message'],
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), status_code
            
    except Exception as e:
        logger.error(f"❌ Partial update error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': f'Update failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>', methods=['GET'])
def get_deployment_details(api_name, platform_id, env_id):
    """
    Get deployment details.
    
    URL: GET /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
    
    Returns:
        200 OK: Deployment details
        404 Not Found: Deployment doesn't exist
        500 Internal Server Error: Fetch failed
    """
    try:
        # Validate platform and environment
        if not is_valid_platform(platform_id):
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': f'Invalid platform: {platform_id}',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        if not is_valid_environment(env_id):
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': f'Invalid environment: {env_id}',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        # Fetch deployment
        from app.services.deploy_service import DeploymentService
        deploy_service = DeploymentService(current_app.db_service)
        
        result = deploy_service.get_deployment(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id
        )
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'data': result['deployment']
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'NotFoundError',
                    'message': result['message'],
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 404
            
    except Exception as e:
        logger.error(f"❌ Get deployment error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>', methods=['DELETE'])
@require_auth()
def delete_deployment(api_name, platform_id, env_id):
    """
    Delete a deployment.
    
    URL: DELETE /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
    
    Returns:
        200 OK: Deployment deleted successfully
        404 Not Found: Deployment doesn't exist
        500 Internal Server Error: Delete failed
    """
    try:
        # Validate platform and environment
        if not is_valid_platform(platform_id):
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': f'Invalid platform: {platform_id}',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        if not is_valid_environment(env_id):
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': f'Invalid environment: {env_id}',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        logger.info(f"Deleting deployment {api_name} on {platform_id}/{env_id}")
        
        # Call deployment service
        from app.services.deploy_service import DeploymentService
        deploy_service = DeploymentService(current_app.db_service)
        
        result = deploy_service.delete_deployment(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id
        )
        
        if result['success']:
            logger.info(f"✅ Successfully deleted {api_name} on {platform_id}/{env_id}")
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': env_id,
                    'action': 'deleted',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 200
        else:
            status_code = 404 if 'not found' in result['message'].lower() else 500
            logger.error(f"❌ Failed to delete {api_name}: {result['message']}")
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'DeleteError',
                    'message': result['message'],
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), status_code
            
    except Exception as e:
        logger.error(f"❌ Delete error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': f'Delete failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500