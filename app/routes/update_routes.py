"""
Update routes for API management.

PUT /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id} - Full update
PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id} - Partial update
PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}/status - Status only
PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}/properties - Properties only
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
        "updated_by": "username",     # Required: 2-100 chars
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
        
        # Call deployment service with correct parameter name: 'updates'
        from app.services.deploy_service import DeploymentService
        deploy_service = DeploymentService(current_app.db_service)
        
        result = deploy_service.update_deployment_partial(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id,
            updates=data  # ✅ FIXED: Changed from update_data to updates
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


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>/status', methods=['PATCH'])
@require_auth()
def update_deployment_status(api_name, platform_id, env_id):
    """
    Update only deployment status.
    
    Specialized endpoint for status changes without touching other fields.
    
    URL: PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}/status
    
    Request Body:
    {
        "status": "STOPPED",          # Required: Valid status
        "updated_by": "username"      # Required: Who made the update
    }
    
    Returns:
        200 OK: Status updated successfully
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
                }
            }), 400
        
        # Validate required fields
        if 'status' not in data or not data['status']:
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': 'Status is required',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        if 'updated_by' not in data or not data['updated_by']:
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': 'Updated By is required',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
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
        
        status = str(data['status']).strip()
        updated_by = str(data['updated_by']).strip()
        
        logger.info(f"Status update for {api_name} on {platform_id}/{env_id} to {status} by {updated_by}")

        # Get old status for audit logging
        old_status = None
        try:
            api_doc = current_app.db_service.collection.find_one({'_id': api_name})
            if api_doc:
                for platform in api_doc.get('Platform', []):
                    if platform.get('PlatformID') == platform_id:
                        for env in platform.get('Environment', []):
                            if env.get('environmentID') == env_id:
                                old_status = env.get('status')
                                break
        except Exception as e:
            logger.warning(f"Could not retrieve old status for audit log: {e}")

        # Call deployment service
        from app.services.deploy_service import DeploymentService
        deploy_service = DeploymentService(current_app.db_service)

        result = deploy_service.update_status_only(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id,
            status=status,
            updated_by=updated_by
        )

        if result['success']:
            logger.info(f"✅ Successfully updated status for {api_name} on {platform_id}/{env_id}")

            # Log to audit trail
            try:
                audit_service = current_app.audit_service
                audit_service.log_status_change(
                    api_name=api_name,
                    platform_id=platform_id,
                    environment_id=env_id,
                    old_status=old_status or 'UNKNOWN',
                    new_status=status,
                    changed_by=updated_by
                )
            except Exception as audit_error:
                logger.error(f"Failed to create audit log: {audit_error}")

            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': env_id,
                    'new_status': status,
                    'action': 'updated',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 200
        else:
            status_code = 404 if 'not found' in result['message'].lower() else 500
            logger.error(f"❌ Failed to update status: {result['message']}")
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'UpdateError',
                    'message': result['message'],
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), status_code
            
    except Exception as e:
        logger.error(f"❌ Status update error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': f'Status update failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500


@bp.route('/<api_name>/platforms/<platform_id>/environments/<env_id>/properties', methods=['PATCH'])
@require_auth()
def update_deployment_properties(api_name, platform_id, env_id):
    """
    Update only deployment properties.
    
    Merges new properties with existing properties.
    
    URL: PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}/properties
    
    Request Body:
    {
        "updated_by": "username",     # Required: Who made the update
        "properties": {               # Required: Properties to merge
            "new_key": "new_value"
        }
    }
    
    Returns:
        200 OK: Properties updated successfully
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
                }
            }), 400
        
        # Validate required fields
        if 'updated_by' not in data or not data['updated_by']:
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': 'Updated By is required',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        if 'properties' not in data or data['properties'] is None:
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': 'Properties is required',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
        if not isinstance(data['properties'], dict):
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'ValidationError',
                    'message': 'Properties must be a valid JSON object',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 400
        
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
        
        updated_by = str(data['updated_by']).strip()
        properties = data['properties']
        
        logger.info(f"Properties update for {api_name} on {platform_id}/{env_id} by {updated_by}")
        
        # Call deployment service
        from app.services.deploy_service import DeploymentService
        deploy_service = DeploymentService(current_app.db_service)
        
        result = deploy_service.update_properties_only(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id,
            properties=properties,
            updated_by=updated_by
        )
        
        if result['success']:
            logger.info(f"✅ Successfully updated properties for {api_name} on {platform_id}/{env_id}")
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': env_id,
                    'action': 'updated',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 200
        else:
            status_code = 404 if 'not found' in result['message'].lower() else 500
            logger.error(f"❌ Failed to update properties: {result['message']}")
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'UpdateError',
                    'message': result['message'],
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), status_code
            
    except Exception as e:
        logger.error(f"❌ Properties update error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'InternalError',
                'message': f'Properties update failed: {str(e)}',
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
        
        # Fetch deployment using correct method name
        from app.services.deploy_service import DeploymentService
        deploy_service = DeploymentService(current_app.db_service)
        
        deployment = deploy_service.get_deployment_status(  # ✅ FIXED: Changed from get_deployment
            api_name=api_name,
            platform_id=platform_id,
            environment_id=env_id
        )
        
        if deployment:
            return jsonify({
                'status': 'success',
                'data': deployment
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'NotFoundError',
                    'message': f'Deployment not found: {api_name} on {platform_id}/{env_id}',
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

        # Get old state for audit logging before deletion
        old_state = None
        try:
            api_doc = current_app.db_service.collection.find_one({'_id': api_name})
            if api_doc:
                for platform in api_doc.get('Platform', []):
                    if platform.get('PlatformID') == platform_id:
                        for env in platform.get('Environment', []):
                            if env.get('environmentID') == env_id:
                                old_state = {
                                    'version': env.get('version'),
                                    'status': env.get('status'),
                                    'properties': env.get('Properties', {})
                                }
                                break
        except Exception as e:
            logger.warning(f"Could not retrieve old state for audit log: {e}")

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

            # Log to audit trail
            try:
                from app.utils.auth import get_current_user
                # Get current user for audit log
                changed_by = "Unknown"
                try:
                    user = get_current_user()
                    if user:
                        changed_by = user.get('username') or user.get('sub', 'Unknown')
                    else:
                        changed_by = "System"
                except:
                    changed_by = "System"

                audit_service = current_app.audit_service
                audit_service.log_deletion(
                    api_name=api_name,
                    platform_id=platform_id,
                    environment_id=env_id,
                    changed_by=changed_by,
                    old_state=old_state
                )
            except Exception as audit_error:
                logger.error(f"Failed to create audit log: {audit_error}")

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