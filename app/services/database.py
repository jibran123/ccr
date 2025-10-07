"""Database service for MongoDB operations with advanced search."""
import logging
from typing import Dict, List, Any, Optional, Tuple
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
    
    def __init__(self, mongo_uri: str, db_name: str = 'ccr', collection_name: str = 'apis'):
        """
        Initialize database connection.
        
        Args:
            mongo_uri: MongoDB connection URI
            db_name: Database name
            collection_name: Collection name
        """
        self.mongo_uri = mongo_uri
        self.db_name = db_name
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
    
    def get_all_apis(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all APIs from database.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of API documents
        """
        try:
            logger.info(f"Fetching all APIs from '{self.db_name}.{self.collection_name}' with limit {limit}")
            
            # Fetch documents
            cursor = self.collection.find({}).limit(limit)
            results = []
            
            for doc in cursor:
                # _id is now a string (API name), so no conversion needed
                # But handle legacy documents with ObjectId just in case
                if '_id' in doc and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
                
                # Convert any datetime objects to ISO format strings
                doc = self._convert_dates_to_strings(doc)
                
                results.append(doc)
            
            logger.info(f"Retrieved {len(results)} APIs from collection")
            
            return results
            
        except Exception as e:
            logger.error(f"Error fetching all APIs: {str(e)}", exc_info=True)
            return []
    
    def search_apis(self, query: str, regex: bool = False, 
                   case_sensitive: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search APIs based on advanced query syntax.
        Now handles Platform array structure and returns flattened results.
        Optimized to search _id field (which is the API name).
        
        Args:
            query: Search query supporting multiple syntaxes
            regex: Use regex for text searches
            case_sensitive: Case sensitivity for text searches
            limit: Maximum results
            
        Returns:
            List of matching API documents (flattened for table display)
        """
        try:
            logger.info(f"=== SEARCH START ===")
            logger.info(f"Query: '{query}'")
            logger.info(f"Regex: {regex}, Case Sensitive: {case_sensitive}")
            
            # If empty query, return all flattened
            if not query or not query.strip():
                apis = self.get_all_apis(limit)
                flattened_results = []
                for api in apis:
                    rows = self._flatten_api_document(api)
                    flattened_results.extend(rows)
                return flattened_results
            
            # Parse and build filter
            search_filter = self._build_search_filter(query, regex, case_sensitive)
            
            logger.info(f"Final MongoDB filter: {search_filter}")
            
            # Execute search
            cursor = self.collection.find(search_filter).limit(limit)
            results = []
            
            for doc in cursor:
                # Handle legacy ObjectId documents
                if '_id' in doc and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
                
                # Convert dates to strings
                doc = self._convert_dates_to_strings(doc)
                
                # Flatten the document for table display
                rows = self._flatten_api_document(doc)
                results.extend(rows)
            
            logger.info(f"Search returned {len(results)} flattened results")
            logger.info(f"=== SEARCH END ===")
            return results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            return []
    
    def _flatten_api_document(self, api: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Flatten API document with Platform array into table rows.
        Each platform-environment combination becomes a row.
        _id is now the API name (string).
        Dates are formatted in local timezone (CET/CEST).
        Version is extracted from Environment level (not Properties).
        """
        rows = []
        
        # _id is now the API name
        api_name = api.get('_id', api.get('API Name', 'N/A'))
        
        # Also support legacy "API Name" field
        if api_name == 'N/A' and 'API Name' in api:
            api_name = api['API Name']
        
        # Check if Platform is an array (new structure)
        if 'Platform' in api and isinstance(api['Platform'], list) and len(api['Platform']) > 0:
            for platform in api['Platform']:
                # Handle various field name formats for PlatformID
                platform_id = (platform.get('PlatformID') or 
                             platform.get('platformID') or 
                             platform.get('platform_id') or 
                             platform.get('platformId') or 'N/A')
                
                if 'Environment' in platform and isinstance(platform['Environment'], list) and len(platform['Environment']) > 0:
                    for env in platform['Environment']:
                        # Handle various field name formats
                        environment_id = (env.get('environmentID') or 
                                        env.get('environment_id') or 
                                        env.get('environmentId') or 
                                        env.get('environment') or 'N/A')
                        
                        # Extract version from environment level (not from Properties!)
                        version = (env.get('version') or 
                                  env.get('Version') or 
                                  env.get('api_version') or 
                                  env.get('apiVersion') or 
                                  env.get('app_version') or 
                                  env.get('appVersion') or 'N/A')
                        
                        # Try different field name formats for dates
                        deployment_date = (env.get('deploymentDate') or 
                                         env.get('deployment_date') or 
                                         env.get('DeploymentDate') or 
                                         env.get('created_at') or 
                                         env.get('createdAt'))
                        
                        last_updated = (env.get('lastUpdated') or 
                                      env.get('last_updated') or 
                                      env.get('LastUpdated') or 
                                      env.get('updated_at') or 
                                      env.get('updatedAt'))
                        
                        updated_by = (env.get('updatedBy') or 
                                    env.get('updated_by') or 
                                    env.get('UpdatedBy') or 
                                    env.get('modified_by') or 
                                    env.get('modifiedBy') or 'N/A')
                        
                        status = (env.get('status') or 
                                env.get('Status') or 
                                env.get('state') or 
                                env.get('State') or 'UNKNOWN')
                        
                        properties = (env.get('Properties') or 
                                    env.get('properties') or 
                                    env.get('props') or 
                                    env.get('attributes') or {})
                        
                        row = {
                            '_id': api_name,
                            'API Name': api_name,
                            'Version': version,
                            'PlatformID': platform_id,
                            'Environment': environment_id,
                            'DeploymentDate': self._format_date(deployment_date),
                            'LastUpdated': self._format_date(last_updated),
                            'UpdatedBy': updated_by,
                            'Status': status,
                            'Properties': properties
                        }
                        rows.append(row)
                else:
                    # Platform without environments
                    version = platform.get('version', platform.get('Version', 'N/A'))
                    
                    row = {
                        '_id': api_name,
                        'API Name': api_name,
                        'Version': version,
                        'PlatformID': platform_id,
                        'Environment': 'N/A',
                        'DeploymentDate': self._format_date(platform.get('deploymentDate')),
                        'LastUpdated': self._format_date(platform.get('lastUpdated')),
                        'UpdatedBy': platform.get('updatedBy', 'N/A'),
                        'Status': platform.get('status', 'UNKNOWN'),
                        'Properties': platform.get('Properties', {})
                    }
                    rows.append(row)
        
        # Handle old structure (Platform as string) - for backward compatibility
        elif 'Platform' in api and isinstance(api['Platform'], str):
            version = api.get('version', api.get('Version', 'N/A'))
            
            row = {
                '_id': api_name,
                'API Name': api_name,
                'Version': version,
                'PlatformID': api.get('Platform', 'N/A'),
                'Environment': api.get('Environment', 'N/A'),
                'DeploymentDate': self._format_date(api.get('DeploymentDate')),
                'LastUpdated': self._format_date(api.get('LastUpdated')),
                'UpdatedBy': api.get('UpdatedBy', 'N/A'),
                'Status': api.get('Status', 'UNKNOWN'),
                'Properties': api.get('Properties', {})
            }
            rows.append(row)
        else:
            # No platform data - return single row with available data
            version = api.get('version', api.get('Version', 'N/A'))
            
            row = {
                '_id': api_name,
                'API Name': api_name,
                'Version': version,
                'PlatformID': api.get('platform', api.get('Platform', 'N/A')),
                'Environment': api.get('environment', api.get('Environment', 'N/A')),
                'DeploymentDate': self._format_date(api.get('deploymentDate', api.get('created_at'))),
                'LastUpdated': self._format_date(api.get('lastUpdated', api.get('updated_at'))),
                'UpdatedBy': api.get('updatedBy', api.get('updated_by', 'N/A')),
                'Status': api.get('status', api.get('Status', 'UNKNOWN')),
                'Properties': api.get('properties', api.get('Properties', {}))
            }
            rows.append(row)
        
        return rows
    
    def _format_date(self, date_value):
        """
        Format date for display in local timezone (CET/CEST).
        Automatically handles daylight saving time transitions.
        
        Args:
            date_value: Date value (datetime object, ISO string, or None)
            
        Returns:
            Formatted date string in CET/CEST with timezone abbreviation
        """
        if not date_value:
            return 'N/A'
        
        # Use timezone utility to format
        # This automatically converts UTC to CET/CEST
        return format_datetime(date_value, include_timezone=True)
    
    def _build_search_filter(self, query: str, regex: bool, case_sensitive: bool) -> Dict:
        """
        Build MongoDB filter from search query.
        Updated to handle Platform array structure.
        Now searches _id field (which is the API name).
        
        Supports:
        1. Simple text search: "blue"
        2. Attribute search: "Platform = IP4"
        3. Properties search: "Properties : key = value"
        4. Combined with AND/OR
        """
        # Split by AND/OR to get individual conditions
        parts = re.split(r'\s+(AND|OR)\s+', query)
        
        conditions = []
        operators = []
        
        for part in parts:
            part = part.strip()
            
            if part in ['AND', 'OR']:
                operators.append(part)
            elif part:
                # Build filter for this part
                condition_filter = self._parse_single_condition(part, regex, case_sensitive)
                if condition_filter:
                    conditions.append(condition_filter)
                    logger.info(f"Condition '{part}' -> {condition_filter}")
        
        # Combine conditions
        if not conditions:
            return {}
        
        if len(conditions) == 1:
            return conditions[0]
        
        # If any OR operator exists, use $or for all
        # Otherwise use $and
        if 'OR' in operators:
            return {'$or': conditions}
        else:
            return {'$and': conditions}
    
    def _parse_single_condition(self, condition: str, regex: bool, case_sensitive: bool) -> Optional[Dict]:
        """
        Parse a single search condition.
        Updated to handle Platform array structure.
        _id field is now searchable (contains API name).
        
        Returns MongoDB filter for this condition.
        """
        condition = condition.strip()
        
        # Check for Properties search
        if re.search(r'Properties\s*:', condition, re.IGNORECASE):
            # Extract key and value
            match = re.match(r'Properties\s*:\s*([^=]+?)\s*=\s*(.+)', condition, re.IGNORECASE)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                
                logger.info(f"Property search: key='{key}', value='{value}'")
                
                # For Platform array structure, search in nested Properties
                return {
                    '$or': [
                        # New structure - Platform array
                        {'Platform.Environment.Properties.' + key: value},
                        # Old structure - top-level Properties
                        {'Properties.' + key: value}
                    ]
                }
        
        # Check for attribute searches
        attribute_patterns = {
            'API NAME': ['_id', 'API Name'],
            'Platform': 'Platform.PlatformID',
            'Environment': 'Platform.Environment.environmentID',
            'Status': 'Platform.Environment.status',
            'UpdatedBy': 'Platform.Environment.updatedBy'
        }
        
        for attr_name, field_paths in attribute_patterns.items():
            # Make field_paths always a list for uniform handling
            if isinstance(field_paths, str):
                field_paths = [field_paths]
            
            # Check if condition matches "AttributeName = value"
            pattern = rf'{re.escape(attr_name)}\s*=\s*(.+)'
            match = re.match(pattern, condition, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                logger.info(f"Attribute search: {attr_name} = '{value}'")
                
                # Build $or query for all field paths
                or_conditions = []
                for field_path in field_paths:
                    or_conditions.append({field_path: value})
                
                return {'$or': or_conditions} if len(or_conditions) > 1 else or_conditions[0]
        
        # If no special syntax matched, treat as simple text search
        logger.info(f"Text search: '{condition}'")
        
        if regex:
            # Use regex search
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(condition, flags)
            return {
                '$or': [
                    {'_id': {'$regex': pattern}},
                    {'API Name': {'$regex': pattern}},
                    {'Platform.PlatformID': {'$regex': pattern}},
                    {'Platform.Environment.environmentID': {'$regex': pattern}},
                    {'Platform.Environment.status': {'$regex': pattern}},
                    {'Platform.Environment.updatedBy': {'$regex': pattern}},
                    # Also search old structure
                    {'Platform': {'$regex': pattern}},
                    {'Environment': {'$regex': pattern}},
                    {'Status': {'$regex': pattern}}
                ]
            }
        else:
            # Use case-insensitive contains search
            options = '' if case_sensitive else 'i'
            return {
                '$or': [
                    {'_id': {'$regex': re.escape(condition), '$options': options}},
                    {'API Name': {'$regex': re.escape(condition), '$options': options}},
                    {'Platform.PlatformID': {'$regex': re.escape(condition), '$options': options}},
                    {'Platform.Environment.environmentID': {'$regex': re.escape(condition), '$options': options}},
                    {'Platform.Environment.status': {'$regex': re.escape(condition), '$options': options}},
                    {'Platform.Environment.updatedBy': {'$regex': re.escape(condition), '$options': options}},
                    # Also search old structure
                    {'Platform': {'$regex': re.escape(condition), '$options': options}},
                    {'Environment': {'$regex': re.escape(condition), '$options': options}},
                    {'Status': {'$regex': re.escape(condition), '$options': options}}
                ]
            }
    
    def _convert_dates_to_strings(self, obj):
        """
        Recursively convert datetime objects to ISO format strings.
        
        Args:
            obj: Object to convert
            
        Returns:
            Object with dates converted to strings
        """
        if isinstance(obj, dict):
            return {k: self._convert_dates_to_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_dates_to_strings(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat() + 'Z'
        else:
            return obj
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            total_count = self.collection.count_documents({})
            
            # Get unique platforms
            pipeline = [
                {'$project': {
                    'platforms': {
                        '$cond': {
                            'if': {'$isArray': '$Platform'},
                            'then': '$Platform.PlatformID',
                            'else': ['$Platform']
                        }
                    }
                }},
                {'$unwind': '$platforms'},
                {'$group': {
                    '_id': None,
                    'unique_platforms': {'$addToSet': '$platforms'}
                }}
            ]
            
            platform_result = list(self.collection.aggregate(pipeline))
            platforms = platform_result[0]['unique_platforms'] if platform_result else []
            
            # Get unique environments
            env_pipeline = [
                {'$project': {
                    'environments': {
                        '$cond': {
                            'if': {'$isArray': '$Platform'},
                            'then': '$Platform.Environment.environmentID',
                            'else': ['$Environment']
                        }
                    }
                }},
                {'$unwind': '$environments'},
                {'$unwind': {'path': '$environments', 'preserveNullAndEmptyArrays': True}},
                {'$group': {
                    '_id': None,
                    'unique_environments': {'$addToSet': '$environments'}
                }}
            ]
            
            env_result = list(self.collection.aggregate(env_pipeline))
            environments = env_result[0]['unique_environments'] if env_result else []
            
            return {
                'total_apis': total_count,
                'database': self.db_name,
                'collection': self.collection_name,
                'unique_platforms': len([p for p in platforms if p]),
                'unique_environments': len([e for e in environments if e])
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {
                'total_apis': 0,
                'database': self.db_name,
                'collection': self.collection_name,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check database health.
        
        Returns:
            Health status dictionary
        """
        try:
            # Ping database
            self.client.admin.command('ping')
            
            # Get collection stats
            count = self.collection.count_documents({})
            
            return {
                'status': 'healthy',
                'database': self.db_name,
                'collection': self.collection_name,
                'document_count': count
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")