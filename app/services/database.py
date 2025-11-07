"""Database service for MongoDB operations with advanced search."""
import logging
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson import ObjectId
import re
from datetime import datetime

# Import timezone utilities
from app.utils.timezone_utils import format_datetime

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for database operations."""
    
    def __init__(self, mongo_uri: str, db_name: str = None, collection_name: str = None):
        """
        Initialize database connection.
        
        Args:
            mongo_uri: MongoDB connection URI
            db_name: Database name (defaults to 'ccr' if None)
            collection_name: Collection name (defaults to 'apis' if None)
        """
        self.mongo_uri = mongo_uri
        
        # Defensive checks for None values with clear error messages
        if db_name is None or not isinstance(db_name, str) or db_name.strip() == '':
            logger.warning(f"Invalid db_name provided: {db_name!r}, using default 'ccr'")
            self.db_name = 'ccr'
        else:
            self.db_name = db_name
            
        if collection_name is None or not isinstance(collection_name, str) or collection_name.strip() == '':
            logger.warning(f"Invalid collection_name provided: {collection_name!r}, using default 'apis'")
            self.collection_name = 'apis'
        else:
            self.collection_name = collection_name
        
        self.client = None
        self.db = None
        self.collection = None
        
        self._connect()
    
    def _connect(self):
        """Establish connection to MongoDB."""
        try:
            logger.info(f"Connecting to MongoDB at {self.mongo_uri}")
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("MongoDB ping successful")
            
            # Set database and collection
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            # Log connection details
            logger.info(f"Connected to database: '{self.db_name}', collection: '{self.collection_name}'")
            
            # Log document count to verify we're in the right place
            count = self.collection.count_documents({})
            logger.info(f"Collection '{self.collection_name}' contains {count} documents")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    def search_apis(self, query: str, regex: bool = False, 
                   case_sensitive: bool = False, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Search APIs with ROW-LEVEL filtering using MongoDB Aggregation Pipeline.
        
        Search Types:
        1. Simple text: "blue" - Word boundary, case insensitive, excludes Properties
        2. Attribute: "Platform = IP4" - Exact match, case sensitive
        3. Properties: "Properties : key = value" - Exact match, case sensitive, handles dots in keys
        4. Complex combinations: Multiple conditions with AND/OR logic
        
        Args:
            query: Search query string
            regex: Enable regex patterns (default: False)
            case_sensitive: Enable case-sensitive search (default: False)
            limit: Maximum results to return (default: 1000)
            
        Returns:
            List of matching API documents (expanded/flattened with one row per Platform+Environment)
        """
        if not query or query.strip() == '':
            logger.info("Empty query - returning all APIs (flattened)")
            return self._get_all_apis_flattened(limit)
        
        query = query.strip()
        logger.info(f"Search query: '{query}' (regex={regex}, case_sensitive={case_sensitive})")
        
        # Detect search type and build aggregation pipeline
        if self._is_properties_search(query):
            pipeline = self._build_properties_pipeline(query, case_sensitive, limit)
        elif self._is_attribute_search(query):
            pipeline = self._build_attribute_pipeline(query, case_sensitive, limit)
        else:
            pipeline = self._build_simple_text_pipeline(query, regex, case_sensitive, limit)
        
        # Execute aggregation pipeline
        try:
            results = list(self.collection.aggregate(pipeline))
            logger.info(f"Search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _get_all_apis_flattened(self, limit: int) -> List[Dict[str, Any]]:
        """Get all APIs with flattened Platform/Environment structure."""
        pipeline = [
            {'$unwind': {'path': '$Platform', 'preserveNullAndEmptyArrays': False}},
            {'$unwind': {'path': '$Platform.Environment', 'preserveNullAndEmptyArrays': False}},
            {
                '$project': {
                    'API Name': 1,
                    'PlatformID': '$Platform.PlatformID',
                    'Environment': '$Platform.Environment.environmentID',
                    'Version': '$Platform.Environment.version',
                    'Status': '$Platform.Environment.status',
                    'LastUpdated': '$Platform.Environment.lastUpdated',
                    'DeploymentDate': '$Platform.Environment.deploymentDate',
                    'UpdatedBy': '$Platform.Environment.updatedBy',
                    'Properties': '$Platform.Environment.Properties'
                }
            },
            {'$limit': limit}
        ]
        
        return list(self.collection.aggregate(pipeline))
    
    def _is_properties_search(self, query: str) -> bool:
        """Check if query is a Properties search (contains 'Properties :' or 'Properties:')."""
        return 'Properties :' in query or 'Properties:' in query
    
    def _is_attribute_search(self, query: str) -> bool:
        """Check if query is an attribute search (contains = or !=)."""
        return '=' in query and not self._is_properties_search(query)
    
    def _build_properties_pipeline(self, query: str, case_sensitive: bool, limit: int) -> List[Dict]:
        """Build pipeline for Properties search with dot notation handling."""
        # Parse: "Properties : key.subkey = value" or "Properties: key = value"
        parts = re.split(r'Properties\s*:', query, maxsplit=1)
        if len(parts) < 2:
            return self._build_simple_text_pipeline(query, False, case_sensitive, limit)
        
        prop_query = parts[1].strip()
        
        # Parse key = value
        if '=' not in prop_query:
            return self._build_simple_text_pipeline(query, False, case_sensitive, limit)
        
        key, value = prop_query.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        
        # Build match condition for nested property
        # Handle dot notation: "api.id" becomes "Properties.api.id"
        property_path = f"Platform.Environment.Properties.{key}"
        
        match_condition = {property_path: value if case_sensitive else {'$regex': f"^{re.escape(value)}$", '$options': 'i'}}
        
        pipeline = [
            {'$unwind': {'path': '$Platform', 'preserveNullAndEmptyArrays': False}},
            {'$unwind': {'path': '$Platform.Environment', 'preserveNullAndEmptyArrays': False}},
            {'$match': match_condition},
            {
                '$project': {
                    'API Name': 1,
                    'PlatformID': '$Platform.PlatformID',
                    'Environment': '$Platform.Environment.environmentID',
                    'Version': '$Platform.Environment.version',
                    'Status': '$Platform.Environment.status',
                    'LastUpdated': '$Platform.Environment.lastUpdated',
                    'DeploymentDate': '$Platform.Environment.deploymentDate',
                    'UpdatedBy': '$Platform.Environment.updatedBy',
                    'Properties': '$Platform.Environment.Properties'
                }
            },
            {'$limit': limit}
        ]
        
        logger.info(f"Properties search pipeline: {pipeline[2]}")  # Log the match stage
        return pipeline
    
    def _build_attribute_pipeline(self, query: str, case_sensitive: bool, limit: int) -> List[Dict]:
        """Build pipeline for attribute search (e.g., 'Platform = IP4')."""
        # Parse: "Attribute = Value" or "Attribute != Value"
        if '!=' in query:
            attr, value = query.split('!=', 1)
            operator = '$ne'
        else:
            attr, value = query.split('=', 1)
            operator = '$eq'
        
        attr = attr.strip()
        value = value.strip().strip('"').strip("'")
        
        # Map attribute names to document paths
        attr_mapping = {
            'API Name': 'API Name',
            'PlatformID': 'Platform.PlatformID',
            'Platform': 'Platform.PlatformID',
            'Environment': 'Platform.Environment.environmentID',
            'Status': 'Platform.Environment.status',
            'Version': 'Platform.Environment.version'
        }
        
        field_path = attr_mapping.get(attr, attr)
        
        # Build match condition
        if case_sensitive:
            match_condition = {field_path: {operator: value}}
        else:
            if operator == '$eq':
                match_condition = {field_path: {'$regex': f"^{re.escape(value)}$", '$options': 'i'}}
            else:  # $ne
                match_condition = {field_path: {'$not': {'$regex': f"^{re.escape(value)}$", '$options': 'i'}}}
        
        pipeline = [
            {'$unwind': {'path': '$Platform', 'preserveNullAndEmptyArrays': False}},
            {'$unwind': {'path': '$Platform.Environment', 'preserveNullAndEmptyArrays': False}},
            {'$match': match_condition},
            {
                '$project': {
                    'API Name': 1,
                    'PlatformID': '$Platform.PlatformID',
                    'Environment': '$Platform.Environment.environmentID',
                    'Version': '$Platform.Environment.version',
                    'Status': '$Platform.Environment.status',
                    'LastUpdated': '$Platform.Environment.lastUpdated',
                    'DeploymentDate': '$Platform.Environment.deploymentDate',
                    'UpdatedBy': '$Platform.Environment.updatedBy',
                    'Properties': '$Platform.Environment.Properties'
                }
            },
            {'$limit': limit}
        ]
        
        logger.info(f"Attribute search pipeline: {pipeline[2]}")
        return pipeline
    
    def _build_simple_text_pipeline(self, query: str, regex: bool, case_sensitive: bool, limit: int) -> List[Dict]:
        """Build pipeline for simple text search (searches only API Name, Platform, Environment - excludes Properties)."""
        # Build regex pattern
        if regex:
            pattern = query
        else:
            # Word boundary search
            escaped = re.escape(query)
            pattern = f"\\b{escaped}\\b"
        
        options = '' if case_sensitive else 'i'
        
        # Search in API Name, Platform.PlatformID, Platform.Environment.environmentID
        # Explicitly exclude Properties from search
        match_condition = {
            '$or': [
                {'API Name': {'$regex': pattern, '$options': options}},
                {'Platform.PlatformID': {'$regex': pattern, '$options': options}},
                {'Platform.Environment.environmentID': {'$regex': pattern, '$options': options}}
            ]
        }
        
        pipeline = [
            {'$unwind': {'path': '$Platform', 'preserveNullAndEmptyArrays': False}},
            {'$unwind': {'path': '$Platform.Environment', 'preserveNullAndEmptyArrays': False}},
            {'$match': match_condition},
            {
                '$project': {
                    'API Name': 1,
                    'PlatformID': '$Platform.PlatformID',
                    'Environment': '$Platform.Environment.environmentID',
                    'Version': '$Platform.Environment.version',
                    'Status': '$Platform.Environment.status',
                    'LastUpdated': '$Platform.Environment.lastUpdated',
                    'DeploymentDate': '$Platform.Environment.deploymentDate',
                    'UpdatedBy': '$Platform.Environment.updatedBy',
                    'Properties': '$Platform.Environment.Properties'
                }
            },
            {'$limit': limit}
        ]
        
        logger.info(f"Simple text search pipeline: {pipeline[2]}")
        return pipeline
    
    def get_api_by_name(self, api_name: str) -> Optional[Dict[str, Any]]:
        """
        Get API by name (returns full document with Platform array).
        
        Args:
            api_name: API name to search for
            
        Returns:
            API document or None if not found
        """
        return self.collection.find_one({'_id': api_name})
    
    def create_api(self, api_data: Dict[str, Any]) -> str:
        """
        Create a new API.
        
        Args:
            api_data: API data to insert
            
        Returns:
            Inserted document ID
        """
        result = self.collection.insert_one(api_data)
        return str(result.inserted_id)
    
    def update_api(self, api_name: str, update_data: Dict[str, Any]) -> bool:
        """
        Update an existing API.
        
        Args:
            api_name: API name to update
            update_data: Update data
            
        Returns:
            True if updated, False otherwise
        """
        result = self.collection.update_one(
            {'_id': api_name},
            {'$set': update_data}
        )
        return result.modified_count > 0
    
    def delete_api(self, api_name: str) -> bool:
        """
        Delete an API.
        
        Args:
            api_name: API name to delete
            
        Returns:
            True if deleted, False otherwise
        """
        result = self.collection.delete_one({'_id': api_name})
        return result.deleted_count > 0
    
    def get_all_apis(self) -> List[Dict[str, Any]]:
        """
        Get all APIs (full documents with Platform arrays).
        
        Returns:
            List of all API documents
        """
        return list(self.collection.find({}))
    
    def count_apis(self) -> int:
        """
        Count total number of APIs.
        
        Returns:
            Total count of APIs
        """
        return self.collection.count_documents({})