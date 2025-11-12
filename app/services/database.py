"""
Database service for CCR API Manager with MongoDB operations.

Enhanced with AND/OR logical operator support for attribute queries.
Supports queries like:
- "Platform = IP4 AND Environment = prd"
- "Status = RUNNING OR Status = DEPLOYING"
- Complex: "(Platform = IP4 OR Platform = IP3) AND Environment = prd"
"""

from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging
import re

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service class for database operations with Platform array support"""
    
    def __init__(self, mongo_uri: str, db_name: str = 'ccr_db', collection_name: str = 'apis'):
        """
        Initialize database service
        
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
        """Establish MongoDB connection"""
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
        3. Attribute with AND/OR: "Platform = IP4 AND Environment = prd"
        4. Properties: "Properties : key = value" - Exact match, case sensitive, handles dots in keys
        
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
    
    # ========================================
    # NEW: LOGICAL OPERATOR SUPPORT (AND/OR)
    # ========================================
    
    def _parse_logical_query(self, query: str) -> Dict[str, Any]:
        """
        Parse query with AND/OR logical operators into conditions.
        
        Examples:
        - "Platform = IP4 AND Environment = prd" 
        - "Status = RUNNING OR Status = DEPLOYING"
        - "Platform = IP4 AND (Status = RUNNING OR Status = DEPLOYING)"
        
        Returns:
            Dictionary with 'operator' (AND/OR/NONE) and 'conditions' list
        """
        query = query.strip()
        
        # Check if query contains logical operators
        has_and = ' AND ' in query
        has_or = ' OR ' in query
        
        if not has_and and not has_or:
            # Single condition - return as-is
            return {
                'operator': 'NONE',
                'conditions': [query]
            }
        
        # Determine primary operator (AND takes precedence over OR for now)
        # For complex queries like "A OR B AND C", we parse as "(A OR B) AND C"
        if has_and:
            operator = 'AND'
            parts = query.split(' AND ')
        else:
            operator = 'OR'
            parts = query.split(' OR ')
        
        # Clean up conditions
        conditions = [part.strip() for part in parts if part.strip()]
        
        logger.info(f"Parsed query into {operator} with {len(conditions)} conditions: {conditions}")
        
        return {
            'operator': operator,
            'conditions': conditions
        }
    
    def _parse_single_condition(self, condition: str, case_sensitive: bool) -> Dict[str, Any]:
        """
        Parse a single attribute condition like "Platform = IP4" into MongoDB match condition.
        
        Returns:
            MongoDB match condition dictionary
        """
        condition = condition.strip()
        
        # Parse operator
        if '!=' in condition:
            attr, value = condition.split('!=', 1)
            operator = '$ne'
        elif '>=' in condition:
            attr, value = condition.split('>=', 1)
            operator = '$gte'
        elif '<=' in condition:
            attr, value = condition.split('<=', 1)
            operator = '$lte'
        elif '>' in condition:
            attr, value = condition.split('>', 1)
            operator = '$gt'
        elif '<' in condition:
            attr, value = condition.split('<', 1)
            operator = '$lt'
        elif ' contains ' in condition.lower():
            parts = re.split(r'\s+contains\s+', condition, flags=re.IGNORECASE)
            attr, value = parts[0], parts[1]
            operator = '$regex'
        elif ' startswith ' in condition.lower():
            parts = re.split(r'\s+startswith\s+', condition, flags=re.IGNORECASE)
            attr, value = parts[0], parts[1]
            operator = '$regex_start'
        elif ' endswith ' in condition.lower():
            parts = re.split(r'\s+endswith\s+', condition, flags=re.IGNORECASE)
            attr, value = parts[0], parts[1]
            operator = '$regex_end'
        elif '=' in condition:
            attr, value = condition.split('=', 1)
            operator = '$eq'
        else:
            logger.warning(f"Could not parse condition: {condition}")
            return {}
        
        attr = attr.strip()
        value = value.strip().strip('"').strip("'")
        
        # Map attribute names to document paths (after unwind)
        attr_mapping = {
            'API Name': 'API Name',
            'PlatformID': 'Platform.PlatformID',
            'Platform': 'Platform.PlatformID',
            'Environment': 'Platform.Environment.environmentID',
            'Status': 'Platform.Environment.status',
            'Version': 'Platform.Environment.version',
            'UpdatedBy': 'Platform.Environment.updatedBy',
        }
        
        field_path = attr_mapping.get(attr, attr)
        
        # Build match condition based on operator
        if operator == '$regex':
            # Contains
            return {field_path: {'$regex': re.escape(value), '$options': 'i' if not case_sensitive else ''}}
        elif operator == '$regex_start':
            # Starts with
            return {field_path: {'$regex': f'^{re.escape(value)}', '$options': 'i' if not case_sensitive else ''}}
        elif operator == '$regex_end':
            # Ends with
            return {field_path: {'$regex': f'{re.escape(value)}$', '$options': 'i' if not case_sensitive else ''}}
        elif operator in ['$gte', '$lte', '$gt', '$lt']:
            # Comparison operators - try to convert to number
            try:
                numeric_value = float(value)
                return {field_path: {operator: numeric_value}}
            except ValueError:
                # If not numeric, use as string
                return {field_path: {operator: value}}
        else:
            # $eq or $ne
            if case_sensitive:
                return {field_path: {operator: value}}
            else:
                # Case-insensitive match
                if operator == '$eq':
                    return {field_path: {'$regex': f'^{re.escape(value)}$', '$options': 'i'}}
                else:  # $ne
                    return {field_path: {'$not': {'$regex': f'^{re.escape(value)}$', '$options': 'i'}}}
    
    def _build_attribute_pipeline(self, query: str, case_sensitive: bool, limit: int) -> List[Dict]:
        """
        Build pipeline for attribute search with AND/OR support.
        
        Handles:
        - Single condition: "Platform = IP4"
        - AND conditions: "Platform = IP4 AND Environment = prd"
        - OR conditions: "Status = RUNNING OR Status = DEPLOYING"
        """
        # Parse query into logical structure
        parsed = self._parse_logical_query(query)
        operator = parsed['operator']
        conditions = parsed['conditions']
        
        # Build match conditions for each part
        match_conditions = []
        for condition in conditions:
            match_cond = self._parse_single_condition(condition, case_sensitive)
            if match_cond:
                match_conditions.append(match_cond)
        
        if not match_conditions:
            logger.warning(f"No valid conditions found in query: {query}")
            return self._get_all_apis_flattened(limit)
        
        # Build final match stage
        if operator == 'AND':
            final_match = {'$and': match_conditions}
        elif operator == 'OR':
            final_match = {'$or': match_conditions}
        else:
            # Single condition
            final_match = match_conditions[0]
        
        pipeline = [
            {'$unwind': {'path': '$Platform', 'preserveNullAndEmptyArrays': False}},
            {'$unwind': {'path': '$Platform.Environment', 'preserveNullAndEmptyArrays': False}},
            {'$match': final_match},
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
        
        logger.info(f"Attribute search pipeline match stage: {final_match}")
        return pipeline
    
    # ========================================
    # END OF LOGICAL OPERATOR SUPPORT
    # ========================================
    
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
        
        match_condition = {property_path: value if case_sensitive else {'$regex': f'^{re.escape(value)}$', '$options': 'i'}}
        
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
            api_name: API name
            update_data: Data to update
            
        Returns:
            True if successful
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
            True if successful
        """
        result = self.collection.delete_one({'_id': api_name})
        return result.deleted_count > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with stats
        """
        total_apis = self.collection.count_documents({})
        
        # Count total deployments (flattened rows)
        pipeline = [
            {'$unwind': '$Platform'},
            {'$unwind': '$Platform.Environment'},
            {'$count': 'total'}
        ]
        
        result = list(self.collection.aggregate(pipeline))
        total_deployments = result[0]['total'] if result else 0
        
        return {
            'total_apis': total_apis,
            'total_deployments': total_deployments
        }
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")