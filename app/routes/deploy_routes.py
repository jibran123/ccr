"""Deployment routes for API management."""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('deploy', __name__, url_prefix='/api')

@bp.route('/deploy', methods=['POST'])
def deploy_api():
    """
    Deploy or update an API deployment.
    Uses upsert logic for Platform array structure.
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
        
        # Validate platform and environment values
        valid_platforms = ['IP4', 'IP5', 'OpenShift', 'Kubernetes', 'Docker', 'AWS', 'Azure', 'GCP']
        valid_environments = ['dev', 'tst', 'stg', 'prd', 'dr', 'uat', 'qa']
        valid_statuses = ['RUNNING', 'STOPPED', 'PENDING', 'FAILED', 'DEPLOYING', 
                         'DEPLOYED', 'UNKNOWN', 'ERROR', 'MAINTENANCE']
        
        if platform_id not in valid_platforms:
            return jsonify({
                'status': 'error',
                'message': f'Invalid platform. Must be one of: {", ".join(valid_platforms)}'
            }), 400
        
        if environment_id not in valid_environments:
            return jsonify({
                'status': 'error',
                'message': f'Invalid environment. Must be one of: {", ".join(valid_environments)}'
            }), 400
        
        if status not in valid_statuses:
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
        
        # Call deployment service
        from app.services.deploy_service import DeploymentService
        deploy_service = DeploymentService(current_app.db_service)
        
        result = deploy_service.deploy_api(
            api_name=api_name,
            platform_id=platform_id,
            environment_id=environment_id,
            status=status,
            updated_by=updated_by,
            properties=properties
        )
        
        if result['success']:
            logger.info(f"Successfully deployed {api_name} to {platform_id}/{environment_id}")
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'data': {
                    'api_name': api_name,
                    'platform': platform_id,
                    'environment': environment_id,
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
        
        if not data.get('environment_id'):
            errors.append('Environment is required')
        
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
    """Get list of available platforms."""
    platforms = [
        {'id': 'IP4', 'name': 'IP4 Platform'},
        {'id': 'IP5', 'name': 'IP5 Platform'},
        {'id': 'OpenShift', 'name': 'OpenShift'},
        {'id': 'Kubernetes', 'name': 'Kubernetes'},
        {'id': 'Docker', 'name': 'Docker'},
        {'id': 'AWS', 'name': 'Amazon Web Services'},
        {'id': 'Azure', 'name': 'Microsoft Azure'},
        {'id': 'GCP', 'name': 'Google Cloud Platform'}
    ]
    return jsonify({'status': 'success', 'data': platforms})

@bp.route('/environments', methods=['GET'])
def get_environments():
    """Get list of available environments."""
    environments = [
        {'id': 'dev', 'name': 'Development'},
        {'id': 'tst', 'name': 'Test'},
        {'id': 'stg', 'name': 'Staging'},
        {'id': 'prd', 'name': 'Production'},
        {'id': 'dr', 'name': 'Disaster Recovery'},
        {'id': 'uat', 'name': 'User Acceptance Testing'},
        {'id': 'qa', 'name': 'Quality Assurance'}
    ]
    return jsonify({'status': 'success', 'data': environments})

@bp.route('/statuses', methods=['GET'])
def get_statuses():
    """Get list of available statuses."""
    statuses = [
        'RUNNING', 'STOPPED', 'PENDING', 'FAILED',
        'DEPLOYING', 'DEPLOYED', 'UNKNOWN', 'ERROR', 'MAINTENANCE'
    ]
    return jsonify({'status': 'success', 'data': statuses})