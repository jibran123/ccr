from typing import Dict, Any, Tuple, Optional
from app.config import PLATFORM_MAPPING, ENVIRONMENT_MAPPING, STATUS_OPTIONS

def validate_api_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate API data for creation/update.
    Returns (is_valid, error_message)
    """
    # Check if data is provided
    if not data:
        return False, "No data provided"
    
    # Define required fields
    required_fields = ['api_name', 'platform_id', 'environment_id']
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate API name
    api_name = data['api_name']
    if not isinstance(api_name, str):
        return False, "API name must be a string"
    if len(api_name) > 255:
        return False, "API name must be 255 characters or less"
    if not api_name.strip():
        return False, "API name cannot be empty or just whitespace"
    
    # Validate platform ID
    platform_id = data['platform_id']
    if platform_id not in PLATFORM_MAPPING:
        valid_platforms = ', '.join(PLATFORM_MAPPING.keys())
        return False, f"Invalid Platform ID '{platform_id}'. Must be one of: {valid_platforms}"
    
    # Validate environment ID
    environment_id = data['environment_id']
    if environment_id not in ENVIRONMENT_MAPPING:
        valid_environments = ', '.join(ENVIRONMENT_MAPPING.keys())
        return False, f"Invalid Environment ID '{environment_id}'. Must be one of: {valid_environments}"
    
    # Validate status if provided
    if 'status' in data and data['status']:
        if data['status'] not in STATUS_OPTIONS:
            valid_statuses = ', '.join(STATUS_OPTIONS)
            return False, f"Invalid status '{data['status']}'. Must be one of: {valid_statuses}"
    
    # Validate properties if provided
    if 'properties' in data:
        if not isinstance(data['properties'], dict):
            return False, "Properties must be a dictionary/object"
        
        # Check property count
        if len(data['properties']) > 100:
            return False, "Maximum 100 properties allowed per deployment"
        
        # Validate each property
        for key, value in data['properties'].items():
            if not isinstance(key, str):
                return False, f"Property key must be a string: {key}"
            if len(key) > 100:
                return False, f"Property key too long (max 100 chars): {key}"
            if not key.strip():
                return False, "Property key cannot be empty"
            
            # Convert value to string if needed
            if value is not None and len(str(value)) > 1000:
                return False, f"Property value too long (max 1000 chars): {key}"
    
    # Validate updated_by if provided
    if 'updated_by' in data and data['updated_by']:
        if not isinstance(data['updated_by'], str):
            return False, "updated_by must be a string"
        if len(data['updated_by']) > 100:
            return False, "updated_by must be 100 characters or less"
    
    return True, None