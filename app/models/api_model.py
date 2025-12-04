"""API data models."""
from datetime import datetime
from typing import Optional, Dict, Any

class APIModel:
    """Model for API data."""
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize API model with data."""
        self.data = data
        self._id = data.get('_id')
        self.api_name = data.get('API Name', '')
        self.platform_id = data.get('PlatformID', '')
        self.environment = data.get('Environment', '')
        self.status = data.get('Status', 'Unknown')
        self.last_updated = data.get('LastUpdated')
        self.properties = data.get('Properties', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.data
    
    @classmethod
    def from_db(cls, doc: Dict[str, Any]) -> 'APIModel':
        """Create model from database document."""
        if '_id' in doc and hasattr(doc['_id'], '__str__'):
            doc['_id'] = str(doc['_id'])
        return cls(doc)