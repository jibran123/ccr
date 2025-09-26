from typing import Dict, Any, Tuple, Optional
from app.config import PLATFORM_MAPPING, ENVIRONMENT_MAPPING, STATUS_OPTIONS

def validate_api_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate API data for creation/update"""
    required_fields = ['api_name', 'platform_id', 'environment_id']
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate platform ID
    if data['platform_id'] not in PLATFORM_MAPPING:
        return False, f"Invalid Platform ID. Must be one of: {', '.join(PLATFORM_MAPPING.keys())}"
    
    # Validate environment ID  
    if data['environment_id'] not in ENVIRONMENT_MAPPING:
        return False, f"Invalid Environment ID. Must be one of: {', '.join(ENVIRONMENT_MAPPING.keys())}"
    
    # Validate status if provided
    if 'status' in data and data['status']:
        if data['status'] not in STATUS_OPTIONS:
            return False, f"Invalid status. Must be one of: {', '.join(STATUS_OPTIONS)}"
    
    return True, None