from typing import Dict, Any, Tuple, Optional

# Import from config instead of hardcoding
from app.config import (
    is_valid_platform,
    is_valid_environment,
    is_valid_status,
    get_valid_platforms,
    get_valid_environments,
    get_valid_statuses
)

def validate_api_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate API data for creation/update.
    Uses centralized configuration from app/config.py
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['api_name', 'platform_id', 'environment_id']
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate platform ID using config
    if not is_valid_platform(data['platform_id']):
        valid_platforms = get_valid_platforms()
        return False, f"Invalid Platform ID. Must be one of: {', '.join(valid_platforms)}"
    
    # Validate environment ID using config
    if not is_valid_environment(data['environment_id']):
        valid_environments = get_valid_environments()
        return False, f"Invalid Environment ID. Must be one of: {', '.join(valid_environments)}"
    
    # Validate status if provided using config
    if 'status' in data and data['status']:
        if not is_valid_status(data['status']):
            valid_statuses = get_valid_statuses()
            return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
    
    return True, None