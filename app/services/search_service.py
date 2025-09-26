from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from datetime import datetime
import logging

# Import from config
from app.config import MONGO_HOST, MONGO_PORT, MONGO_DB, MONGO_COLLECTION

logger = logging.getLogger(__name__)

class SearchService:
    """Service class for API search operations with Platform array support"""
    
    def __init__(self):
        """Initialize search service with MongoDB connection"""
        try:
            self.client = MongoClient(MONGO_HOST, MONGO_PORT, serverSelectionTimeoutMS=5000)
            self.db = self.client[MONGO_DB]
            self.collection = self.db[MONGO_COLLECTION]
            logger.info(f"SearchService initialized - Connected to {MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}")
        except Exception as e:
            logger.error(f"Failed to initialize SearchService: {e}")
            raise
    
    def search_apis(self, query: str = '', case_sensitive: bool = False, 
                   regex_mode: bool = False, page: int = 1, 
                   per_page: int = 100) -> Dict[str, Any]:
        """Search APIs with optional filtering - handles Platform array structure"""
        try:
            from app.utils.parsers import parse_search_query, flatten_api_for_table
            
            # Build query filter
            query_filter = parse_search_query(query, case_sensitive, regex_mode)
            
            # Get total count
            total = self.collection.count_documents(query_filter)
            
            # Get paginated results
            skip = (page - 1) * per_page
            cursor = self.collection.find(query_filter).skip(skip).limit(per_page)
            apis = list(cursor)
            
            # Flatten for table display
            formatted_apis = []
            for api in apis:
                rows = flatten_api_for_table(api)
                formatted_apis.extend(rows)
            
            return {
                'apis': formatted_apis,
                'total': len(formatted_apis),  # Return count of flattened rows
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page if per_page > 0 else 1
            }
            
        except PyMongoError as e:
            logger.error(f"Database error in search_apis: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in search_apis: {e}")
            raise
    
    def search_by_properties(self, property_key: str, property_value: str) -> List[Dict[str, Any]]:
        """
        Search APIs by property key-value pair using aggregation pipeline.
        Works with the Platform array structure.
        """
        try:
            from app.utils.parsers import flatten_api_for_table
            
            pipeline = [
                # Unwind the Platform array
                {'$unwind': {'path': '$Platform', 'preserveNullAndEmptyArrays': True}},
                
                # Unwind the Environment array within each platform
                {'$unwind': {'path': '$Platform.Environment', 'preserveNullAndEmptyArrays': True}},
                
                # Match documents where the property exists with the specified value
                {'$match': {
                    f'Platform.Environment.Properties.{property_key}': property_value
                }},
                
                # Group back by API to reconstruct the document structure
                {'$group': {
                    '_id': '$_id',
                    'API Name': {'$first': '$API Name'},
                    'Platform': {'$push': {
                        'PlatformID': '$Platform.PlatformID',
                        'Environment': '$Platform.Environment'
                    }}
                }},
                
                # Restructure Platform array to group environments by platform
                {'$project': {
                    '_id': 1,
                    'API Name': 1,
                    'Platform': {
                        '$reduce': {
                            'input': '$Platform',
                            'initialValue': [],
                            'in': {
                                '$let': {
                                    'vars': {
                                        'existing': {
                                            '$filter': {
                                                'input': '$$value',
                                                'cond': {'$eq': ['$$this.PlatformID', '$$this.PlatformID']}
                                            }
                                        }
                                    },
                                    'in': {
                                        '$cond': {
                                            'if': {'$gt': [{'$size': '$$existing'}, 0]},
                                            'then': '$$value',
                                            'else': {'$concatArrays': ['$$value', [{
                                                'PlatformID': '$$this.PlatformID',
                                                'Environment': ['$$this.Environment']
                                            }]]}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }}
            ]
            
            apis = list(self.collection.aggregate(pipeline))
            
            # Flatten for table display
            formatted_apis = []
            for api in apis:
                rows = flatten_api_for_table(api)
                formatted_apis.extend(rows)
            
            return formatted_apis
            
        except PyMongoError as e:
            logger.error(f"Database error in search_by_properties: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in search_by_properties: {e}")
            raise
    
    def get_api_by_id(self, api_id: str) -> Optional[Dict[str, Any]]:
        """Get single API by ID"""
        try:
            return self.collection.find_one({'_id': ObjectId(api_id)})
        except Exception as e:
            logger.error(f"Error getting API by ID: {e}")
            return None
    
    def get_api_by_name(self, api_name: str) -> Optional[Dict[str, Any]]:
        """Get single API by name"""
        try:
            return self.collection.find_one({'API Name': api_name})
        except Exception as e:
            logger.error(f"Error getting API by name: {e}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        try:
            self.client.close()
            logger.info("SearchService connection closed")
        except Exception as e:
            logger.error(f"Error closing SearchService connection: {e}")