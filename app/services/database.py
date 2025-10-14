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
    
    def search_apis(self, query: str, regex: bool = False, 
                   case_sensitive: bool = False, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Search APIs with ROW-LEVEL filtering using MongoDB Aggregation Pipeline.
        
        Search Types:
        1. Simple text: "blue" - Word boundary, case insensitive, excludes Properties
        2. Attribute: "Platform = IP4" - Exact match, case sensitive
        3. Properties: "Properties : key = value" - Exact match, case sensitive, handles dots in keys
        4. Combined: "blue AND Platform = IP4" - Row-level filtering
        
        Args:
            query: Search query
            regex: Unused (kept for compatibility)
            case_sensitive: Unused (kept for compatibility)
            limit: Maximum results
            
        Returns:
            List of matching deployment rows (already flattened)
        """
        try:
            logger.info("=" * 70)
            logger.info(f"SEARCH QUERY: '{query}'")
            logger.info("=" * 70)
            
            # Build aggregation pipeline
            pipeline = self._build_aggregation_pipeline(query, limit)
            
            logger.info("Aggregation Pipeline:")
            for i, stage in enumerate(pipeline):
                logger.info(f"Stage {i+1}: {stage}")
            
            # Execute aggregation
            results = list(self.collection.aggregate(pipeline))
            
            logger.info(f"Found {len(results)} matching rows")
            
            # Format results for frontend
            formatted_results = []
            for row in results:
                # Handle _id (could be ObjectId or string)
                if '_id' in row and isinstance(row['_id'], ObjectId):
                    row['_id'] = str(row['_id'])
                
                # Format dates
                row['DeploymentDate'] = self._format_date(row.get('DeploymentDate'))
                row['LastUpdated'] = self._format_date(row.get('LastUpdated'))
                
                # Ensure all expected fields exist
                formatted_row = {
                    '_id': row.get('_id', 'N/A'),
                    'API Name': row.get('API Name', 'N/A'),
                    'Version': row.get('Version', 'N/A'),
                    'PlatformID': row.get('PlatformID', 'N/A'),
                    'Environment': row.get('Environment', 'N/A'),
                    'DeploymentDate': row.get('DeploymentDate', 'N/A'),
                    'LastUpdated': row.get('LastUpdated', 'N/A'),
                    'UpdatedBy': row.get('UpdatedBy', 'N/A'),
                    'Status': row.get('Status', 'UNKNOWN'),
                    'Properties': row.get('Properties', {})
                }
                
                formatted_results.append(formatted_row)
            
            logger.info("=" * 70)
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            return []
    
    def _build_aggregation_pipeline(self, query: str, limit: int) -> List[Dict]:
        """
        Build MongoDB aggregation pipeline for row-level filtering.
        
        Pipeline:
        1. Unwind Platform array
        2. Unwind Environment array
        3. Match conditions (row-level)
        4. Project flat structure
        5. Limit results
        """
        pipeline = []
        
        # Stage 1: Unwind Platform array
        pipeline.append({
            '$unwind': {
                'path': '$Platform',
                'preserveNullAndEmptyArrays': False
            }
        })
        
        # Stage 2: Unwind Environment array
        pipeline.append({
            '$unwind': {
                'path': '$Platform.Environment',
                'preserveNullAndEmptyArrays': False
            }
        })
        
        # Stage 3: Match conditions (row-level filtering)
        if query and query.strip():
            match_filter = self._build_row_level_filter(query)
            if match_filter:
                pipeline.append({'$match': match_filter})
        
        # Stage 4: Project flat structure for table display
        pipeline.append({
            '$project': {
                '_id': 1,
                'API Name': {
                    '$ifNull': ['$API Name', '$_id']
                },
                'Version': {
                    '$ifNull': ['$Platform.Environment.version', 'N/A']
                },
                'PlatformID': '$Platform.PlatformID',
                'Environment': '$Platform.Environment.environmentID',
                'DeploymentDate': {
                    '$ifNull': ['$Platform.Environment.deploymentDate', None]
                },
                'LastUpdated': {
                    '$ifNull': ['$Platform.Environment.lastUpdated', None]
                },
                'UpdatedBy': {
                    '$ifNull': ['$Platform.Environment.updatedBy', 'N/A']
                },
                'Status': {
                    '$ifNull': ['$Platform.Environment.status', 'UNKNOWN']
                },
                'Properties': {
                    '$ifNull': ['$Platform.Environment.Properties', {}]
                }
            }
        })
        
        # Stage 5: Limit results
        pipeline.append({'$limit': limit})
        
        return pipeline
    
    def _build_row_level_filter(self, query: str) -> Dict:
        """
        Build MongoDB filter for row-level matching.
        
        After unwinding, document structure is:
        {
            "_id": "api-name",
            "API Name": "api-name",
            "Platform": {
                "PlatformID": "IP4",
                "Environment": {
                    "environmentID": "tst",
                    "version": "1.0.0",
                    "status": "RUNNING",
                    "Properties": {...}
                }
            }
        }
        """
        # Split by AND/OR
        parts = re.split(r'\s+(AND|OR)\s+', query, flags=re.IGNORECASE)
        
        conditions = []
        operators = []
        
        for part in parts:
            part_upper = part.strip().upper()
            
            if part_upper in ['AND', 'OR']:
                operators.append(part_upper)
            elif part.strip():
                condition = self._parse_single_condition(part.strip())
                if condition:
                    conditions.append(condition)
                    logger.info(f"Parsed: '{part.strip()}' -> {condition}")
        
        # No valid conditions
        if not conditions:
            return {}
        
        # Single condition
        if len(conditions) == 1:
            return conditions[0]
        
        # Multiple conditions with operators
        if 'OR' in operators:
            # Any OR present -> use $or for all
            return {'$or': conditions}
        else:
            # All AND -> use $and
            return {'$and': conditions}
    
    def _parse_single_condition(self, condition: str) -> Optional[Dict]:
        """
        Parse single condition into MongoDB filter.
        
        Three types:
        1. Properties: "Properties : key = value"
        2. Attribute: "Field = value"
        3. Simple text: "searchterm"
        """
        condition = condition.strip()
        
        # Type 1: Properties search
        if re.match(r'Properties\s*:', condition, re.IGNORECASE):
            return self._parse_properties_condition(condition)
        
        # Type 2: Attribute search
        if '=' in condition:
            return self._parse_attribute_condition(condition)
        
        # Type 3: Simple text search
        return self._parse_simple_text_condition(condition)
    
    def _parse_properties_condition(self, condition: str) -> Optional[Dict]:
        """
        Parse: "Properties : key = value"
        
        After unwinding, Properties are at: Platform.Environment.Properties
        
        Rules:
        - Exact match, case sensitive
        - Values stored as strings ('true', 'false', not boolean)
        - Handles property keys with DOTS (e.g., 'debug.logging', 'api.id')
        
        CRITICAL FIX: Uses $getField to properly handle keys with dots
        """
        match = re.match(r'Properties\s*:\s*([^=]+?)\s*=\s*(.+)', condition, re.IGNORECASE)
        
        if not match:
            logger.warning(f"Invalid Properties syntax: {condition}")
            return None
        
        key = match.group(1).strip()
        value = match.group(2).strip().strip('"').strip("'")
        
        logger.info(f"Properties search: key='{key}', value='{value}' (exact string match)")
        
        # CRITICAL FIX: Use $expr with $getField to handle dots in property keys
        # This treats 'debug.logging' as a SINGLE key, not nested fields
        return {
            '$expr': {
                '$eq': [
                    {
                        '$getField': {
                            'field': key,
                            'input': '$Platform.Environment.Properties'
                        }
                    },
                    value
                ]
            }
        }
    
    def _parse_attribute_condition(self, condition: str) -> Optional[Dict]:
        """
        Parse: "Field = value"
        
        After unwinding, fields are at:
        - API Name: _id or "API Name"
        - Platform: Platform.PlatformID
        - Environment: Platform.Environment.environmentID
        - Status: Platform.Environment.status
        - Version: Platform.Environment.version
        - UpdatedBy: Platform.Environment.updatedBy
        
        Rules:
        - Exact match, case sensitive
        """
        parts = condition.split('=', 1)
        if len(parts) != 2:
            return None
        
        field = parts[0].strip()
        value = parts[1].strip().strip('"').strip("'")
        
        # Map field names to MongoDB paths (after unwinding)
        field_mapping = {
            'API NAME': ['_id', 'API Name'],
            'PLATFORM': 'Platform.PlatformID',
            'ENVIRONMENT': 'Platform.Environment.environmentID',
            'STATUS': 'Platform.Environment.status',
            'VERSION': 'Platform.Environment.version',
            'UPDATEDBY': 'Platform.Environment.updatedBy'
        }
        
        field_upper = field.upper().replace(' ', '')
        
        if field_upper in field_mapping:
            field_paths = field_mapping[field_upper]
            
            # Make it a list
            if isinstance(field_paths, str):
                field_paths = [field_paths]
            
            logger.info(f"Attribute search: {field} = '{value}' (exact match)")
            
            # Exact match
            if len(field_paths) == 1:
                return {field_paths[0]: value}
            else:
                # Multiple possible fields (e.g., _id or "API Name")
                return {'$or': [{fp: value} for fp in field_paths]}
        
        logger.warning(f"Unknown attribute field: {field}")
        return None
    
    def _parse_simple_text_condition(self, condition: str) -> Optional[Dict]:
        """
        Parse: "searchterm"
        
        After unwinding, searchable fields:
        - _id
        - API Name
        - Platform.PlatformID
        - Platform.Environment.environmentID
        - Platform.Environment.status
        - Platform.Environment.updatedBy
        - Platform.Environment.version
        
        Rules:
        - Word boundary matching (\bterm\b)
        - Case insensitive
        - Excludes Properties
        - Treats - and _ as word boundaries
        """
        search_text = condition.strip()
        
        # Word boundary regex pattern
        # \b naturally treats - and _ as non-word chars (boundaries)
        pattern = f'\\b{re.escape(search_text)}\\b'
        
        logger.info(f"Simple text search: '{search_text}' (word boundary, case insensitive)")
        logger.info(f"Regex pattern: {pattern}")
        
        # Fields to search (after unwinding)
        search_fields = [
            '_id',
            'API Name',
            'Platform.PlatformID',
            'Platform.Environment.environmentID',
            'Platform.Environment.status',
            'Platform.Environment.updatedBy',
            'Platform.Environment.version'
        ]
        
        # Build $or with regex for each field
        return {
            '$or': [
                {field: {'$regex': pattern, '$options': 'i'}}
                for field in search_fields
            ]
        }
    
    def _format_date(self, date_value):
        """Format date for display in local timezone (CET/CEST)."""
        if not date_value:
            return 'N/A'
        
        return format_datetime(date_value, include_timezone=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            total_count = self.collection.count_documents({})
            
            # Get unique platforms
            pipeline = [
                {'$unwind': '$Platform'},
                {'$group': {
                    '_id': None,
                    'unique_platforms': {'$addToSet': '$Platform.PlatformID'}
                }}
            ]
            
            platform_result = list(self.collection.aggregate(pipeline))
            platforms = platform_result[0]['unique_platforms'] if platform_result else []
            
            # Get unique environments
            env_pipeline = [
                {'$unwind': '$Platform'},
                {'$unwind': '$Platform.Environment'},
                {'$group': {
                    '_id': None,
                    'unique_environments': {'$addToSet': '$Platform.Environment.environmentID'}
                }}
            ]
            
            env_result = list(self.collection.aggregate(env_pipeline))
            environments = env_result[0]['unique_environments'] if env_result else []
            
            # Count total deployments
            deploy_pipeline = [
                {'$unwind': '$Platform'},
                {'$unwind': '$Platform.Environment'},
                {'$count': 'total'}
            ]
            
            deploy_result = list(self.collection.aggregate(deploy_pipeline))
            total_deployments = deploy_result[0]['total'] if deploy_result else 0
            
            return {
                'total_apis': total_count,
                'total_deployments': total_deployments,
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