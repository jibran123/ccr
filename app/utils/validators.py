"""
Input validation utilities for API requests.

Provides validation functions for deployment and update requests with detailed error messages.
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import re


class ValidationError(Exception):
    """Custom exception for validation errors with field-level details."""
    
    def __init__(self, message: str, field: str = None, errors: Dict[str, str] = None):
        self.message = message
        self.field = field
        self.errors = errors or {}
        super().__init__(self.message)


def validate_deployment_request(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate deployment request data.
    
    Args:
        data: Request data dictionary
        
    Returns:
        Tuple of (is_valid, error_details)
        
    Raises:
        ValidationError: If validation fails with detailed error information
    """
    errors = {}
    
    # Required fields
    required_fields = {
        'api_name': 'API Name',
        'platform_id': 'Platform ID',
        'environment_id': 'Environment ID',
        'status': 'Status',
        'updated_by': 'Updated By'
    }
    
    # Check for missing required fields
    for field, display_name in required_fields.items():
        if field not in data or data[field] is None or str(data[field]).strip() == '':
            errors[field] = f"{display_name} is required"
    
    # If basic required fields are missing, return early
    if errors:
        return False, {
            'message': 'Missing required fields',
            'errors': errors,
            'required_fields': list(required_fields.keys()),
            'example': {
                'api_name': 'my-api',
                'platform_id': 'IP4',
                'environment_id': 'tst',
                'status': 'RUNNING',
                'updated_by': 'username',
                'version': '1.0.0',
                'properties': {}
            }
        }
    
    # Validate api_name
    api_name = str(data['api_name']).strip()
    if not validate_api_name(api_name):
        errors['api_name'] = 'API Name must be 3-100 characters, alphanumeric with hyphens/underscores only'
    
    # Validate platform_id
    platform_id = str(data['platform_id']).strip()
    if not validate_platform_id(platform_id):
        errors['platform_id'] = 'Platform ID must be valid (e.g., IP2, IP3, IP4, IP5)'
    
    # Validate environment_id
    environment_id = str(data['environment_id']).strip()
    if not validate_environment_id(environment_id):
        errors['environment_id'] = 'Environment ID must be valid (e.g., prod, tst, dev, acc)'
    
    # Validate status
    status = str(data['status']).strip()
    if not validate_status(status):
        errors['status'] = 'Status must be one of: RUNNING, STOPPED, DEPLOYING, FAILED, MAINTENANCE'
    
    # Validate updated_by
    updated_by = str(data['updated_by']).strip()
    if not validate_updated_by(updated_by):
        errors['updated_by'] = 'Updated By must be 2-50 characters'
    
    # Validate optional version field
    if 'version' in data and data['version']:
        version = str(data['version']).strip()
        if not validate_version(version):
            errors['version'] = 'Version must be valid format (e.g., 1.0.0, v2.1.3)'
    
    # Validate optional properties field
    if 'properties' in data and data['properties'] is not None:
        if not isinstance(data['properties'], dict):
            errors['properties'] = 'Properties must be a valid JSON object'
    
    if errors:
        return False, {
            'message': 'Validation failed',
            'errors': errors
        }
    
    return True, None


def validate_update_request(data: Dict[str, Any], is_patch: bool = False) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate update request data (PUT or PATCH).
    
    Args:
        data: Request data dictionary
        is_patch: True for PATCH (partial update), False for PUT (full update)
        
    Returns:
        Tuple of (is_valid, error_details)
    """
    errors = {}
    
    # For PUT, all fields are required except properties
    if not is_patch:
        required_fields = {
            'version': 'Version',
            'status': 'Status',
            'updated_by': 'Updated By'
        }
        
        for field, display_name in required_fields.items():
            if field not in data or data[field] is None or str(data[field]).strip() == '':
                errors[field] = f"{display_name} is required for full update (PUT)"
    
    # For PATCH, at least one field must be provided
    if is_patch:
        updateable_fields = ['version', 'status', 'updated_by', 'properties']
        provided_fields = [f for f in updateable_fields if f in data and data[f] is not None]
        
        if not provided_fields:
            return False, {
                'message': 'At least one field must be provided for partial update (PATCH)',
                'updateable_fields': updateable_fields,
                'example': {
                    'status': 'STOPPED',
                    'updated_by': 'username'
                }
            }
    
    # Validate version if provided
    if 'version' in data and data['version']:
        version = str(data['version']).strip()
        if not validate_version(version):
            errors['version'] = 'Version must be valid format (e.g., 1.0.0, v2.1.3)'
    
    # Validate status if provided
    if 'status' in data and data['status']:
        status = str(data['status']).strip()
        if not validate_status(status):
            errors['status'] = 'Status must be one of: RUNNING, STOPPED, DEPLOYING, FAILED, MAINTENANCE'
    
    # Validate updated_by if provided
    if 'updated_by' in data and data['updated_by']:
        updated_by = str(data['updated_by']).strip()
        if not validate_updated_by(updated_by):
            errors['updated_by'] = 'Updated By must be 2-50 characters'
    
    # Validate properties if provided
    if 'properties' in data and data['properties'] is not None:
        if not isinstance(data['properties'], dict):
            errors['properties'] = 'Properties must be a valid JSON object'
    
    if errors:
        return False, {
            'message': 'Validation failed',
            'errors': errors
        }
    
    return True, None


# ===========================
# FIELD VALIDATION FUNCTIONS
# ===========================

def validate_api_name(api_name: str) -> bool:
    """
    Validate API name.
    - 3-100 characters
    - Alphanumeric, hyphens, underscores only
    - Cannot start/end with hyphen or underscore
    """
    if not api_name or len(api_name) < 3 or len(api_name) > 100:
        return False
    
    # Must match pattern: alphanumeric, hyphens, underscores, but not start/end with special chars
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$'
    return bool(re.match(pattern, api_name))


def validate_platform_id(platform_id: str) -> bool:
    """
    Validate platform ID.
    Currently accepts: IP2, IP3, IP4, IP5 (case insensitive)
    """
    if not platform_id:
        return False
    
    # For now, allow any reasonable platform ID format
    # Can be made more restrictive based on actual platform list
    valid_platforms = ['IP2', 'IP3', 'IP4', 'IP5']
    return platform_id.upper() in valid_platforms or bool(re.match(r'^[A-Z0-9]{2,10}$', platform_id.upper()))


def validate_environment_id(environment_id: str) -> bool:
    """
    Validate environment ID.
    Common environments: prod, tst, dev, acc, uat, stg
    """
    if not environment_id:
        return False
    
    # Allow common environment IDs (flexible for different naming conventions)
    valid_envs = ['prod', 'production', 'tst', 'test', 'dev', 'development', 
                  'acc', 'acceptance', 'uat', 'stg', 'staging', 'prd', 'prd-uitwijk']
    
    return environment_id.lower() in valid_envs or bool(re.match(r'^[a-z0-9_-]{2,20}$', environment_id.lower()))


def validate_status(status: str) -> bool:
    """
    Validate deployment status.
    Allowed: RUNNING, STOPPED, DEPLOYING, FAILED, MAINTENANCE
    """
    if not status:
        return False
    
    valid_statuses = ['RUNNING', 'STOPPED', 'DEPLOYING', 'FAILED', 'MAINTENANCE', 
                     'ACTIVE', 'INACTIVE', 'PENDING', 'ERROR']
    return status.upper() in valid_statuses


def validate_version(version: str) -> bool:
    """
    Validate version string.
    Accepts: 1.0.0, v1.0.0, 2.1.3-beta, etc.
    """
    if not version:
        return False
    
    # Flexible version pattern
    # Allows: 1.0.0, v1.0.0, 1.0, 1.0.0-beta, 1.0.0-rc.1, etc.
    pattern = r'^v?\d+(\.\d+){0,3}(-[a-zA-Z0-9.-]+)?$'
    return bool(re.match(pattern, version))


def validate_updated_by(updated_by: str) -> bool:
    """
    Validate updated_by field (username or identifier).
    - 2-50 characters
    - Alphanumeric, dots, hyphens, underscores
    """
    if not updated_by or len(updated_by) < 2 or len(updated_by) > 50:
        return False
    
    pattern = r'^[a-zA-Z0-9._-]+$'
    return bool(re.match(pattern, updated_by))


# ===========================
# SEARCH QUERY VALIDATION
# ===========================

def validate_search_query(query: str) -> Tuple[bool, Optional[str]]:
    """
    Validate search query syntax.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not query or query.strip() == '':
        return True, None  # Empty query is valid (returns all)
    
    query = query.strip()
    
    # Check for common syntax errors
    
    # 1. Unmatched quotes
    if query.count('"') % 2 != 0:
        return False, 'Unmatched quotes in search query. Example: APIName="my-api"'
    
    # 2. Invalid operators in attribute search
    if '=' in query or '!=' in query or 'contains' in query.lower():
        # This looks like an attribute search, check syntax
        if not validate_attribute_search_syntax(query):
            return False, 'Invalid attribute search syntax. Example: Platform = IP4 AND Environment = prod'
    
    # 3. Check for Properties search syntax
    if 'properties' in query.lower() and ':' in query:
        if not validate_properties_search_syntax(query):
            return False, 'Invalid properties search syntax. Example: Properties : key = value'
    
    return True, None


def validate_attribute_search_syntax(query: str) -> bool:
    """
    Validate attribute search syntax.
    Expected: FieldName operator value [AND/OR FieldName operator value]
    """
    # Basic check - if it has operators, it should have field names
    operators = ['=', '!=', '>', '<', '>=', '<=', 'contains', 'startswith', 'endswith']
    has_operator = any(op in query for op in operators)
    
    if has_operator:
        # Should have at least one word before operator
        parts = re.split(r'[=!<>]|contains|startswith|endswith', query, flags=re.IGNORECASE)
        if len(parts) < 2:
            return False
        
        # First part should have a field name
        first_part = parts[0].strip().split()[-1]  # Get last word before operator
        if len(first_part) < 2:
            return False
    
    return True


def validate_properties_search_syntax(query: str) -> bool:
    """
    Validate properties search syntax.
    Expected: Properties : key operator value
    """
    # Should have format: Properties : ...
    if 'properties' not in query.lower():
        return True
    
    # Check for colon after Properties
    props_index = query.lower().find('properties')
    after_props = query[props_index + len('properties'):].strip()
    
    if not after_props.startswith(':'):
        return False
    
    return True


# ===========================
# HELPER FUNCTIONS
# ===========================

def get_validation_example(endpoint: str) -> Dict[str, Any]:
    """
    Get example request body for a given endpoint.
    """
    examples = {
        'deploy': {
            'api_name': 'my-api',
            'platform_id': 'IP4',
            'environment_id': 'tst',
            'version': '1.0.0',
            'status': 'RUNNING',
            'updated_by': 'username',
            'properties': {
                'owner': 'team-name',
                'repo': 'https://github.com/org/repo'
            }
        },
        'update_full': {
            'version': '1.0.1',
            'status': 'RUNNING',
            'updated_by': 'username',
            'properties': {
                'owner': 'team-name'
            }
        },
        'update_partial': {
            'status': 'STOPPED',
            'updated_by': 'username'
        }
    }
    
    return examples.get(endpoint, {})


def format_validation_error_response(error_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format validation error into standardized response.
    """
    return {
        'status': 'error',
        'error': {
            'type': 'ValidationError',
            'message': error_details.get('message', 'Validation failed'),
            'details': error_details.get('errors', {}),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        },
        'help': error_details.get('example') or error_details.get('required_fields')
    }