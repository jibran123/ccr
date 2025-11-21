"""
Input validation utilities for API requests.

Provides validation functions for deployment and update requests with detailed error messages.

VALIDATION RULES:
- api_name: 3-100 chars, alphanumeric + hyphen/underscore, cannot start/end with special chars
- platform_id: STRICT - Only values from config.py allowed
- environment_id: STRICT - Only values from config.py allowed  
- status: STRICT - Only values from config.py allowed
- version: Numbers separated by dots (e.g., 1.0.0, 2.3.86)
- updated_by: 2-100 chars, supports full names with spaces, unicode, special chars
- properties: MANDATORY - Must be valid JSON object (can be empty {})
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
                'updated_by': 'Jibran Patel',
                'version': '1.0.0',
                'properties': {}
            }
        }
    
    # Validate api_name
    api_name = str(data['api_name']).strip()
    if not validate_api_name(api_name):
        errors['api_name'] = 'API Name must be 3-100 characters, alphanumeric with hyphens/underscores only, cannot start or end with special characters'
    
    # Validate platform_id - STRICT: Only config values allowed
    platform_id = str(data['platform_id']).strip()
    if not validate_platform_id_strict(platform_id):
        errors['platform_id'] = 'Platform ID must be a valid configured platform. Check /api/platforms for valid values.'
    
    # Validate environment_id - STRICT: Only config values allowed
    environment_id = str(data['environment_id']).strip()
    if not validate_environment_id_strict(environment_id):
        errors['environment_id'] = 'Environment ID must be a valid configured environment. Check /api/environments for valid values.'
    
    # Validate status - STRICT: Only config values allowed
    status = str(data['status']).strip()
    if not validate_status_strict(status):
        errors['status'] = 'Status must be a valid configured status. Check /api/statuses for valid values.'
    
    # Validate updated_by - RELAXED: Allow full names with spaces, parentheses, unicode
    updated_by = str(data['updated_by']).strip()
    if not validate_updated_by(updated_by):
        errors['updated_by'] = 'Updated By must be 2-100 characters (supports full names, spaces, and special characters)'
    
    # Validate optional version field
    if 'version' in data and data['version']:
        version = str(data['version']).strip()
        if not validate_version(version):
            errors['version'] = 'Version must be valid format (e.g., 1.0.0, 2.1.3, v1.2.3)'
    
    # Validate properties field - MANDATORY JSON object
    if 'properties' not in data or data['properties'] is None:
        errors['properties'] = 'Properties field is mandatory (can be empty object {})'
    elif not isinstance(data['properties'], dict):
        errors['properties'] = 'Properties must be a valid JSON object (dictionary)'
    
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
    
    # For PUT, all fields are required
    if not is_patch:
        required_fields = {
            'version': 'Version',
            'status': 'Status',
            'updated_by': 'Updated By',
            'properties': 'Properties'
        }

        for field, display_name in required_fields.items():
            if field not in data or data[field] is None:
                if field == 'properties':
                    errors[field] = f"{display_name} is mandatory (can be empty object {{}})"
                else:
                    errors[field] = f"{display_name} is required for full update (PUT)"
            elif field == 'version' and (data[field] == '' or str(data[field]).strip() == ''):
                # Check for empty version string only if field exists
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
                    'updated_by': 'Jibran Patel'
                }
            }
    
    # Validate version if provided
    if 'version' in data and data['version']:
        version = str(data['version']).strip()
        if not validate_version(version):
            errors['version'] = 'Version must be valid format (e.g., 1.0.0, 2.1.3, v1.2.3)'
    
    # Validate status if provided - STRICT
    if 'status' in data and data['status']:
        status = str(data['status']).strip()
        if not validate_status_strict(status):
            errors['status'] = 'Status must be a valid configured status. Check /api/statuses for valid values.'
    
    # Validate updated_by if provided
    if 'updated_by' in data and data['updated_by']:
        updated_by = str(data['updated_by']).strip()
        if not validate_updated_by(updated_by):
            errors['updated_by'] = 'Updated By must be 2-100 characters (supports full names, spaces, and special characters)'
    
    # Validate properties if provided - Must be JSON object
    if 'properties' in data and data['properties'] is not None:
        if not isinstance(data['properties'], dict):
            errors['properties'] = 'Properties must be a valid JSON object (dictionary)'
    
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
    # Single char: just alphanumeric
    # Multi char: start and end with alphanumeric, middle can have hyphens/underscores
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$'
    return bool(re.match(pattern, api_name))


def validate_platform_id_strict(platform_id: str) -> bool:
    """
    Validate platform ID - STRICT MODE.
    Only allows values configured in config.py.
    
    This function dynamically checks against the config at runtime.
    """
    if not platform_id:
        return False
    
    # Import here to avoid circular imports
    try:
        from app.config import is_valid_platform
        return is_valid_platform(platform_id)
    except ImportError:
        # Fallback for testing without app context
        # In production, config must be available
        return False


def validate_environment_id_strict(environment_id: str) -> bool:
    """
    Validate environment ID - STRICT MODE.
    Only allows values configured in config.py.
    
    This function dynamically checks against the config at runtime.
    """
    if not environment_id:
        return False
    
    # Import here to avoid circular imports
    try:
        from app.config import is_valid_environment
        return is_valid_environment(environment_id)
    except ImportError:
        # Fallback for testing without app context
        return False


def validate_status_strict(status: str) -> bool:
    """
    Validate deployment status - STRICT MODE.
    Only allows values configured in config.py.
    
    This function dynamically checks against the config at runtime.
    """
    if not status:
        return False
    
    # Import here to avoid circular imports
    try:
        from app.config import is_valid_status
        return is_valid_status(status)
    except ImportError:
        # Fallback for testing without app context
        return False


def validate_version(version: str) -> bool:
    """
    Validate version string.
    Accepts: 1.0.0, 2.3.86, v1.0.0, etc.
    Numbers separated by dots.
    """
    if not version:
        return False
    
    # Flexible version pattern: digits separated by dots
    # Allows: 1.0.0, 2.3.86, v2.1.3, 1.0, etc.
    # Optional 'v' prefix, then digits with dots
    pattern = r'^v?\d+(\.\d+){0,3}$'
    return bool(re.match(pattern, version))


def validate_updated_by(updated_by: str) -> bool:
    """
    Validate updated_by field (username or full name from Azure AD).
    - 2-100 characters
    - Supports full names with spaces (e.g., "Jibran Patel")
    - Supports department info in parentheses (e.g., "Jibran Patel (DevOps Team)")
    - Supports email addresses (e.g., "jibran.patel@company.com")
    - Supports unicode characters for international names (e.g., "José García")
    - Does NOT allow: newlines, tabs, control characters
    """
    if not updated_by or len(updated_by) < 2 or len(updated_by) > 100:
        return False
    
    # Allow almost anything except control characters (newlines, tabs, etc.)
    # This supports:
    # - Full names: "Jibran Patel"
    # - With dept: "Jibran Patel (DevOps Team)"
    # - Emails: "jibran.patel@company.com"
    # - Unicode: "José García", "李明"
    # - Special chars: dots, hyphens, underscores, parentheses, @, etc.
    
    # Check for forbidden characters (control characters)
    if any(ord(char) < 32 or ord(char) == 127 for char in updated_by):
        return False
    
    return True


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
            return False, 'Invalid attribute search syntax. Example: Platform = IP4 AND Environment = tst'
    
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
        first_part_words = parts[0].strip().split()
        if not first_part_words:  # No field name before operator (e.g., "= value")
            return False

        first_part = first_part_words[-1]  # Get last word before operator
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
            'updated_by': 'Jibran Patel',
            'properties': {
                'owner': 'DevOps Team',
                'repo': 'https://github.com/org/repo'
            }
        },
        'update_full': {
            'version': '1.0.1',
            'status': 'RUNNING',
            'updated_by': 'Jibran Patel',
            'properties': {
                'owner': 'DevOps Team'
            }
        },
        'update_partial': {
            'status': 'STOPPED',
            'updated_by': 'Jibran Patel'
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