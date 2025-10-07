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
        
        Search Rules:
        1. Simple text (e.g., "blue") - Partial match, case insensitive, all fields EXCEPT Properties
        2. Attribute search (e.g., "Platform = IP4") - Exact match, case sensitive
        3. Properties search (e.g., "Properties : key = value") - Exact match, case sensitive
        4. AND/OR operators for combining conditions
        
        Args:
            query: Search query supporting multiple syntaxes
            regex: Use regex for text searches (from UI checkbox)
            case_sensitive: Case sensitivity for text searches (from UI checkbox)
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
    
    def _build_search_filter(self, query: str, regex: bool, case_sensitive: bool) -> Dict:
        """
        Build MongoDB filter from search query.
        
        Supports:
        1. Simple text search: "blue" (partial, case insensitive, excludes Properties)
        2. Attribute search: "Platform = IP4" (exact, case sensitive)
        3. Properties search: "Properties : key = value" (exact, case sensitive)
        4. Combined with AND/OR
        
        Args:
            query: Search query string
            regex: Enable regex mode (from UI)
            case_sensitive: Enable case sensitivity for simple text search (from UI)
            
        Returns:
            MongoDB filter dictionary
        """
        # Split by AND/OR to get individual conditions
        # Use regex to preserve AND/OR as separate tokens
        parts = re.split(r'\s+(AND|OR)\s+', query, flags=re.IGNORECASE)
        
        conditions = []
        operators = []
        
        for part in parts:
            part_upper = part.strip().upper()
            
            if part_upper in ['AND', 'OR']:
                operators.append(part_upper)
            elif part.strip():
                # Build filter for this part
                condition_filter = self._parse_single_condition(part.strip(), regex, case_sensitive)
                if condition_filter:
                    conditions.append(condition_filter)
                    logger.info(f"Parsed condition '{part.strip()}' -> {condition_filter}")
        
        # Combine conditions
        if not conditions:
            return {}
        
        if len(conditions) == 1:
            return conditions[0]
        
        # Combine based on operators
        # If we have mixed AND/OR, we need to be careful
        # For now, if ANY OR exists, use $or for all (simple approach)
        # Better approach: respect operator precedence, but that's complex
        
        if 'OR' in operators:
            # If there's at least one OR, use $or for all conditions
            return {'$or': conditions}
        else:
            # All AND operators
            return {'$and': conditions}
    
    def _parse_single_condition(self, condition: str, regex: bool, case_sensitive: bool) -> Optional[Dict]:
        """
        Parse a single search condition into a MongoDB filter.
        
        Three types:
        1. Properties search: "Properties : key = value" (exact, case sensitive)
        2. Attribute search: "Field = value" (exact, case sensitive)
        3. Simple text: "searchterm" (partial, case insensitive by default)
        
        Returns:
            MongoDB filter dictionary
        """
        condition = condition.strip()
        
        # TYPE 1: Properties search - "Properties : key = value"
        if re.match(r'Properties\s*:', condition, re.IGNORECASE):
            return self._parse_properties_condition(condition)
        
        # TYPE 2: Attribute search - "Field = value"
        if '=' in condition:
            return self._parse_attribute_condition(condition)
        
        # TYPE 3: Simple text search - "searchterm"
        return self._parse_simple_text_condition(condition, regex, case_sensitive)
    
    def _parse_properties_condition(self, condition: str) -> Optional[Dict]:
        """
        Parse Properties condition: "Properties : key = value"
        
        Rules:
        - Exact match only (no partial text)
        - Case sensitive
        - Searches within Properties object only
        
        Example: "Properties : debug.logging = true"
        """
        # Extract: Properties : key = value
        match = re.match(r'Properties\s*:\s*([^=]+?)\s*=\s*(.+)', condition, re.IGNORECASE)
        
        if not match:
            logger.warning(f"Invalid Properties syntax: {condition}")
            return None
        
        key = match.group(1).strip()
        value = match.group(2).strip()
        
        # Remove quotes if present
        value = value.strip('"').strip("'")
        
        logger.info(f"Properties search - Key: '{key}', Value: '{value}' (exact, case sensitive)")
        
        # Search in nested Properties within Platform array
        return {
            'Platform.Environment.Properties.' + key: value
        }
    
    def _parse_attribute_condition(self, condition: str) -> Optional[Dict]:
        """
        Parse attribute condition: "Field = value"
        
        Rules:
        - Exact match only (no partial text)
        - Case sensitive
        - Searches specific attribute
        
        Examples: 
        - "Platform = IP4"
        - "Environment = prd"
        - "API Name = ivp-test-app"
        """
        # Extract: Field = value
        parts = condition.split('=', 1)
        if len(parts) != 2:
            return None
        
        field = parts[0].strip()
        value = parts[1].strip()
        
        # Remove quotes if present
        value = value.strip('"').strip("'")
        
        logger.info(f"Attribute search - Field: '{field}', Value: '{value}' (exact, case sensitive)")
        
        # Map attribute names to MongoDB fields
        field_mapping = {
            'API NAME': ['_id', 'API Name'],
            'PLATFORM': 'Platform.PlatformID',
            'ENVIRONMENT': 'Platform.Environment.environmentID',
            'STATUS': 'Platform.Environment.status',
            'UPDATEDBY': 'Platform.Environment.updatedBy',
            'VERSION': 'Platform.Environment.version'
        }
        
        field_upper = field.upper().replace(' ', '')
        
        if field_upper in field_mapping:
            field_paths = field_mapping[field_upper]
            
            # Make field_paths always a list
            if isinstance(field_paths, str):
                field_paths = [field_paths]
            
            # Build exact match query
            if len(field_paths) == 1:
                return {field_paths[0]: value}
            else:
                # Multiple possible fields (e.g., _id or API Name)
                return {'$or': [{fp: value} for fp in field_paths]}
        
        # Unknown field - return None
        logger.warning(f"Unknown attribute field: {field}")
        return None
    
    def _parse_simple_text_condition(self, condition: str, regex: bool, case_sensitive: bool) -> Optional[Dict]:
        """
        Parse simple text search: "searchterm"
        
        Rules:
        - Partial match (contains)
        - Case insensitive by default (unless case_sensitive checkbox is enabled)
        - Searches ALL fields EXCEPT Properties
        
        Example: "blue" searches for "blue" in API Name, Platform, Environment, Status, etc.
        """
        search_text = condition.strip()
        
        logger.info(f"Simple text search: '{search_text}' (partial, case_sensitive={case_sensitive})")
        
        # Fields to search (EXCLUDE Properties)
        search_fields = [
            '_id',
            'API Name',
            'Platform.PlatformID',
            'Platform.Environment.environmentID',
            'Platform.Environment.status',
            'Platform.Environment.updatedBy',
            'Platform.Environment.version'
        ]
        
        if regex:
            # Use as regex pattern
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
                
                return {
                    '$or': [
                        {field: {'$regex': pattern}} for field in search_fields
                    ]
                }
            except re.error:
                # Invalid regex, fall back to literal search
                logger.warning(f"Invalid regex pattern: {search_text}")
        
        # Regular search - case insensitive contains
        options = '' if case_sensitive else 'i'
        
        return {
            '$or': [
                {field: {'$regex': re.escape(search_text), '$options': options}}
                for field in search_fields
            ]
        }
    
    def _flatten_api_document(self, api: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Flatten API document with Platform array into table rows.
        Each platform-environment combination becomes a row.
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
                        
                        # Extract version from environment level
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
        """
        if not date_value:
            return 'N/A'
        
        return format_datetime(date_value, include_timezone=True)
    
    def _convert_dates_to_strings(self, obj):
        """
        Recursively convert datetime objects to ISO format strings.
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
        """Get database statistics."""
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
        """Check database health."""
        try:
            self.client.admin.command('ping')
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