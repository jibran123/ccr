"""Database service for MongoDB operations with advanced search."""
import logging
from typing import Dict, List, Any, Optional, Tuple
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson import ObjectId
import re
from datetime import datetime

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
            
            # Log a sample document ID to verify
            sample = self.collection.find_one({}, {'_id': 1})
            if sample:
                logger.info(f"Sample document ID: {sample.get('_id')}")
            
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
                # Convert ObjectId to string if it's an ObjectId
                if '_id' in doc:
                    if isinstance(doc['_id'], ObjectId):
                        doc['_id'] = str(doc['_id'])
                    # If _id is already a string, keep it as is
                
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
        
        Args:
            query: Search query supporting multiple syntaxes
            regex: Use regex for text searches
            case_sensitive: Case sensitivity for text searches
            limit: Maximum results
            
        Returns:
            List of matching API documents
        """
        try:
            logger.info(f"=== SEARCH START ===")
            logger.info(f"Query: '{query}'")
            logger.info(f"Regex: {regex}, Case Sensitive: {case_sensitive}")
            
            # If empty query, return all
            if not query or not query.strip():
                return self.get_all_apis(limit)
            
            # Parse and build filter
            search_filter = self._build_search_filter(query, regex, case_sensitive)
            
            logger.info(f"Final MongoDB filter: {search_filter}")
            
            # Execute search
            cursor = self.collection.find(search_filter).limit(limit)
            results = []
            
            for doc in cursor:
                # Convert ObjectId to string if needed
                if '_id' in doc and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
                
                # Convert dates to strings
                doc = self._convert_dates_to_strings(doc)
                
                results.append(doc)
            
            logger.info(f"Search returned {len(results)} results")
            logger.info(f"=== SEARCH END ===")
            return results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            return []
    
    def _build_search_filter(self, query: str, regex: bool, case_sensitive: bool) -> Dict:
        """
        Build MongoDB filter from search query.
        
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
                
                # Use JavaScript $where function to handle properties with dots
                # This works correctly with property names containing dots
                # Escape single quotes in key and value to prevent injection
                key_escaped = key.replace("'", "\\'")
                value_escaped = value.replace("'", "\\'")
                
                where_clause = f"""function() {{
                    if (!this.Platform || !this.Platform.Environment) return false;
                    for (var i = 0; i < this.Platform.Environment.length; i++) {{
                        if (this.Platform.Environment[i].Properties && 
                            this.Platform.Environment[i].Properties['{key_escaped}'] === '{value_escaped}') {{
                            return true;
                        }}
                    }}
                    return false;
                }}"""
                
                return {'$where': where_clause}
        
        # Check for attribute searches
        attribute_patterns = {
            'API NAME': 'API Name',
            'Platform': 'Platform.PlatformID',
            'Environment': 'Platform.Environment.environmentID',
            'Status': 'Platform.Environment.Status',
            'UpdatedBy': 'Platform.Environment.UpdatedBy'
        }
        
        for attr_name, field_path in attribute_patterns.items():
            # Check if condition matches "AttributeName = value"
            pattern = rf'{re.escape(attr_name)}\s*=\s*(.+)'
            match = re.match(pattern, condition, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                logger.info(f"Attribute search: {attr_name} = '{value}'")
                
                # Special handling for Environment array fields
                if 'Platform.Environment.' in field_path:
                    # Use $elemMatch for array fields
                    field_name = field_path.replace('Platform.Environment.', '')
                    return {
                        'Platform.Environment': {
                            '$elemMatch': {
                                field_name: value
                            }
                        }
                    }
                else:
                    return {field_path: value}
        
        # If no special syntax matched, treat as simple text search
        logger.info(f"Text search: '{condition}'")
        
        if regex:
            # Use regex search
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(condition, flags)
            return {
                '$or': [
                    {'API Name': {'$regex': pattern}},
                    {'_id': {'$regex': pattern}},
                    {'Platform.PlatformID': {'$regex': pattern}},
                    {'Platform.Environment': {'$elemMatch': {'environmentID': {'$regex': pattern}}}},
                    {'Platform.Environment': {'$elemMatch': {'Status': {'$regex': pattern}}}},
                    {'Platform.Environment': {'$elemMatch': {'UpdatedBy': {'$regex': pattern}}}}
                ]
            }
        else:
            # Use case-insensitive contains search
            options = '' if case_sensitive else 'i'
            return {
                '$or': [
                    {'API Name': {'$regex': re.escape(condition), '$options': options}},
                    {'_id': {'$regex': re.escape(condition), '$options': options}},
                    {'Platform.PlatformID': {'$regex': re.escape(condition), '$options': options}},
                    {'Platform.Environment': {'$elemMatch': {'environmentID': {'$regex': re.escape(condition), '$options': options}}}},
                    {'Platform.Environment': {'$elemMatch': {'Status': {'$regex': re.escape(condition), '$options': options}}}},
                    {'Platform.Environment': {'$elemMatch': {'UpdatedBy': {'$regex': re.escape(condition), '$options': options}}}}
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
            platforms = self.collection.distinct("Platform.PlatformID")
            
            # Get unique environments
            environments = self.collection.distinct("Platform.Environment.environmentID")
            
            return {
                'total_apis': total_count,
                'database': self.db_name,
                'collection': self.collection_name,
                'unique_platforms': len(platforms) if platforms else 0,
                'unique_environments': len(environments) if environments else 0
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