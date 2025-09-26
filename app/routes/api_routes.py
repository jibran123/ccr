from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from datetime import datetime
import logging
import os

# Import configuration
from app.config import MONGO_HOST, MONGO_PORT, MONGO_DB, MONGO_COLLECTION

# Import services and utilities
from app.services.search_service import SearchService
from app.utils.validators import validate_api_data
from app.utils.parsers import (
    format_api_response, 
    build_platform_environment_update,
    flatten_api_for_table
)

logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Initialize services
search_service = SearchService()

def get_db():
    """Get MongoDB database connection"""
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    return client[MONGO_DB]

@api_bp.route('/apis', methods=['GET'])
def get_apis():
    """Get all APIs with optional filtering - handles Platform array structure"""
    try:
        # Parse query parameters
        search_query = request.args.get('q', '')
        case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
        regex_mode = request.args.get('regex', 'false').lower() == 'true'
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
        
        # Check for property search
        prop_key = request.args.get('prop_key')
        prop_value = request.args.get('prop_value')
        
        if prop_key and prop_value:
            # Use property search
            formatted_apis = search_service.search_by_properties(prop_key, prop_value)
            return jsonify({
                'apis': formatted_apis,
                'total': len(formatted_apis),
                'page': 1,
                'per_page': len(formatted_apis),
                'total_pages': 1
            })
        else:
            # Regular search
            result = search_service.search_apis(
                query=search_query,
                case_sensitive=case_sensitive,
                regex_mode=regex_mode,
                page=page,
                per_page=per_page
            )
            return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in get_apis: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/apis/<api_id>', methods=['GET'])
def get_api(api_id):
    """Get single API by ID with full Platform array structure"""
    try:
        api = search_service.get_api_by_id(api_id)
        
        if not api:
            return jsonify({'error': 'API not found'}), 404
        
        # Format response with nested structure
        formatted = format_api_response(api)
        
        return jsonify(formatted)
        
    except Exception as e:
        logger.error(f"Error in get_api: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/apis/deploy', methods=['POST'])
def deploy_api():
    """Deploy/update API with Platform array structure using upsert logic"""
    try:
        data = request.json
        
        # Validate input
        is_valid, error_msg = validate_api_data(data)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        api_name = data['api_name']
        platform_id = data['platform_id']
        environment_id = data['environment_id']
        
        # Build environment document
        env_doc = build_platform_environment_update(data)
        
        # Get database
        db = get_db()
        apis_collection = db[MONGO_COLLECTION]
        
        # Find existing API
        existing_api = apis_collection.find_one({'API Name': api_name})
        
        if not existing_api:
            # Create new API with Platform array
            new_api = {
                'API Name': api_name,
                'Platform': [{
                    'PlatformID': platform_id,
                    'Environment': [env_doc]
                }]
            }
            result = apis_collection.insert_one(new_api)
            logger.info(f"Created new API: {api_name} with platform {platform_id}/{environment_id}")
            return jsonify({
                'message': f'API {api_name} created successfully',
                'api_id': str(result.inserted_id),
                'action': 'created'
            }), 201
        
        # API exists - ensure Platform field is an array
        if 'Platform' not in existing_api or not isinstance(existing_api['Platform'], list):
            # Convert to array structure
            apis_collection.update_one(
                {'API Name': api_name},
                {'$set': {'Platform': []}}
            )
            existing_api['Platform'] = []
        
        # Check if platform exists
        platform_exists = False
        platform_index = -1
        
        for idx, platform in enumerate(existing_api['Platform']):
            if platform.get('PlatformID') == platform_id:
                platform_exists = True
                platform_index = idx
                break
        
        if not platform_exists:
            # Add new platform to array
            apis_collection.update_one(
                {'API Name': api_name},
                {'$push': {
                    'Platform': {
                        'PlatformID': platform_id,
                        'Environment': [env_doc]
                    }
                }}
            )
            logger.info(f"Added platform {platform_id} to API {api_name}")
            return jsonify({
                'message': f'Platform {platform_id} added to API {api_name}',
                'action': 'platform_added'
            }), 200
        
        # Platform exists - check for environment
        platform_data = existing_api['Platform'][platform_index]
        if 'Environment' not in platform_data:
            platform_data['Environment'] = []
        
        env_exists = False
        env_index = -1
        
        for idx, env in enumerate(platform_data['Environment']):
            if env.get('environmentID') == environment_id:
                env_exists = True
                env_index = idx
                break
        
        if env_exists:
            # Update existing environment (redeployment)
            update_path = f'Platform.{platform_index}.Environment.{env_index}'
            apis_collection.update_one(
                {'API Name': api_name},
                {'$set': {update_path: env_doc}}
            )
            logger.info(f"Updated environment {environment_id} for {api_name}/{platform_id}")
            return jsonify({
                'message': f'Environment {environment_id} updated for {api_name}',
                'action': 'environment_updated'
            }), 200
        else:
            # Add new environment to platform
            apis_collection.update_one(
                {
                    'API Name': api_name,
                    'Platform.PlatformID': platform_id
                },
                {'$push': {
                    'Platform.$.Environment': env_doc
                }}
            )
            logger.info(f"Added environment {environment_id} to {api_name}/{platform_id}")
            return jsonify({
                'message': f'Environment {environment_id} added to platform {platform_id}',
                'action': 'environment_added'
            }), 200
            
    except Exception as e:
        logger.error(f"Error in deploy_api: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/apis/<api_id>', methods=['DELETE'])
def delete_api(api_id):
    """Delete an API by ID"""
    try:
        db = get_db()
        apis_collection = db[MONGO_COLLECTION]
        
        result = apis_collection.delete_one({'_id': ObjectId(api_id)})
        
        if result.deleted_count == 0:
            return jsonify({'error': 'API not found'}), 404
        
        logger.info(f"Deleted API with ID: {api_id}")
        return jsonify({'message': 'API deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error in delete_api: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/apis/search/properties', methods=['GET'])
def search_by_properties():
    """Search APIs by property key-value pair"""
    try:
        prop_key = request.args.get('key')
        prop_value = request.args.get('value')
        
        if not prop_key or not prop_value:
            return jsonify({'error': 'Both key and value parameters are required'}), 400
        
        # Use the search service for property search
        formatted_apis = search_service.search_by_properties(prop_key, prop_value)
        
        return jsonify({
            'apis': formatted_apis,
            'total': len(formatted_apis),
            'page': 1,
            'per_page': len(formatted_apis),
            'total_pages': 1
        })
        
    except Exception as e:
        logger.error(f"Error in search_by_properties: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/apis/stats', methods=['GET'])
def get_stats():
    """Get statistics about APIs"""
    try:
        db = get_db()
        apis_collection = db[MONGO_COLLECTION]
        
        # Get total count
        total_apis = apis_collection.count_documents({})
        
        # Aggregate platform and environment counts
        pipeline = [
            {'$unwind': '$Platform'},
            {'$unwind': '$Platform.Environment'},
            {'$group': {
                '_id': None,
                'platforms': {'$addToSet': '$Platform.PlatformID'},
                'environments': {'$addToSet': '$Platform.Environment.environmentID'},
                'total_deployments': {'$sum': 1}
            }}
        ]
        
        result = list(apis_collection.aggregate(pipeline))
        
        if result:
            stats = result[0]
            return jsonify({
                'total_apis': total_apis,
                'total_deployments': stats.get('total_deployments', 0),
                'unique_platforms': len(stats.get('platforms', [])),
                'unique_environments': len(stats.get('environments', [])),
                'platforms': stats.get('platforms', []),
                'environments': stats.get('environments', [])
            })
        else:
            return jsonify({
                'total_apis': total_apis,
                'total_deployments': 0,
                'unique_platforms': 0,
                'unique_environments': 0,
                'platforms': [],
                'environments': []
            })
        
    except Exception as e:
        logger.error(f"Error in get_stats: {e}")
        return jsonify({'error': str(e)}), 500