"""Deployment service for API management."""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pymongo import ReturnDocument
from bson import ObjectId

logger = logging.getLogger(__name__)

class DeploymentService:
    """Service for handling API deployments with upsert logic."""
    
    def __init__(self, db_service):
        """
        Initialize deployment service.
        
        Args:
            db_service: Database service instance
        """
        self.db_service = db_service
        self.collection = db_service.collection
    
    def deploy_api(self, api_name: str, platform_id: str, environment_id: str,
                  status: str, updated_by: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy or update an API using upsert logic.
        
        Args:
            api_name: Name of the API
            platform_id: Platform identifier
            environment_id: Environment identifier
            status: Deployment status
            updated_by: User making the deployment
            properties: Key-value properties for the deployment
            
        Returns:
            Dictionary with success status and message
        """
        try:
            logger.info(f"Deploying {api_name} to {platform_id}/{environment_id}")
            
            # Current timestamp
            now = datetime.utcnow()
            now_str = now.isoformat() + 'Z'
            
            # Check if API already exists
            existing_api = self.collection.find_one({'API Name': api_name})
            
            if not existing_api:
                # Create new API document
                logger.info(f"Creating new API: {api_name}")
                
                new_doc = {
                    'API Name': api_name,
                    'Platform': [
                        {
                            'PlatformID': platform_id,
                            'Environment': [
                                {
                                    'environmentID': environment_id,
                                    'deploymentDate': now_str,
                                    'lastUpdated': now_str,
                                    'updatedBy': updated_by,
                                    'status': status,
                                    'Properties': properties
                                }
                            ]
                        }
                    ]
                }
                
                result = self.collection.insert_one(new_doc)
                
                if result.inserted_id:
                    return {
                        'success': True,
                        'message': f'API {api_name} created and deployed to {platform_id}/{environment_id}',
                        'action': 'created',
                        'api_id': str(result.inserted_id)
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Failed to create API',
                        'action': 'failed'
                    }
            
            else:
                # API exists, update it
                logger.info(f"Updating existing API: {api_name}")
                
                # Check if platform exists
                platform_exists = False
                platform_index = -1
                
                if 'Platform' in existing_api and isinstance(existing_api['Platform'], list):
                    for idx, platform in enumerate(existing_api['Platform']):
                        if platform.get('PlatformID') == platform_id:
                            platform_exists = True
                            platform_index = idx
                            break
                
                if not platform_exists:
                    # Add new platform to array
                    logger.info(f"Adding new platform {platform_id} to API {api_name}")
                    
                    result = self.collection.update_one(
                        {'API Name': api_name},
                        {
                            '$push': {
                                'Platform': {
                                    'PlatformID': platform_id,
                                    'Environment': [
                                        {
                                            'environmentID': environment_id,
                                            'deploymentDate': now_str,
                                            'lastUpdated': now_str,
                                            'updatedBy': updated_by,
                                            'status': status,
                                            'Properties': properties
                                        }
                                    ]
                                }
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        return {
                            'success': True,
                            'message': f'Added new platform {platform_id} with environment {environment_id} to API {api_name}',
                            'action': 'updated'
                        }
                    else:
                        return {
                            'success': False,
                            'message': 'Failed to add platform',
                            'action': 'failed'
                        }
                
                else:
                    # Platform exists, check if environment exists
                    environment_exists = False
                    environment_index = -1
                    
                    platform = existing_api['Platform'][platform_index]
                    if 'Environment' in platform and isinstance(platform['Environment'], list):
                        for idx, env in enumerate(platform['Environment']):
                            if env.get('environmentID') == environment_id:
                                environment_exists = True
                                environment_index = idx
                                break
                    
                    if not environment_exists:
                        # Add new environment to platform
                        logger.info(f"Adding new environment {environment_id} to platform {platform_id}")
                        
                        result = self.collection.update_one(
                            {
                                'API Name': api_name,
                                'Platform.PlatformID': platform_id
                            },
                            {
                                '$push': {
                                    f'Platform.$.Environment': {
                                        'environmentID': environment_id,
                                        'deploymentDate': now_str,
                                        'lastUpdated': now_str,
                                        'updatedBy': updated_by,
                                        'status': status,
                                        'Properties': properties
                                    }
                                }
                            }
                        )
                        
                        if result.modified_count > 0:
                            return {
                                'success': True,
                                'message': f'Added environment {environment_id} to platform {platform_id} for API {api_name}',
                                'action': 'updated'
                            }
                        else:
                            return {
                                'success': False,
                                'message': 'Failed to add environment',
                                'action': 'failed'
                            }
                    
                    else:
                        # Environment exists, update it (upsert)
                        logger.info(f"Updating environment {environment_id} in platform {platform_id}")
                        
                        # Use aggregation pipeline for complex update
                        result = self.collection.update_one(
                            {'API Name': api_name},
                            [{
                                '$set': {
                                    'Platform': {
                                        '$map': {
                                            'input': '$Platform',
                                            'as': 'platform',
                                            'in': {
                                                '$cond': {
                                                    'if': {'$eq': ['$$platform.PlatformID', platform_id]},
                                                    'then': {
                                                        '$mergeObjects': [
                                                            '$$platform',
                                                            {
                                                                'Environment': {
                                                                    '$map': {
                                                                        'input': '$$platform.Environment',
                                                                        'as': 'env',
                                                                        'in': {
                                                                            '$cond': {
                                                                                'if': {'$eq': ['$$env.environmentID', environment_id]},
                                                                                'then': {
                                                                                    'environmentID': environment_id,
                                                                                    'deploymentDate': '$$env.deploymentDate',  # Keep original
                                                                                    'lastUpdated': now_str,
                                                                                    'updatedBy': updated_by,
                                                                                    'status': status,
                                                                                    'Properties': properties
                                                                                },
                                                                                'else': '$$env'
                                                                            }
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        ]
                                                    },
                                                    'else': '$$platform'
                                                }
                                            }
                                        }
                                    }
                                }
                            }]
                        )
                        
                        if result.modified_count > 0:
                            return {
                                'success': True,
                                'message': f'Updated deployment for {api_name} on {platform_id}/{environment_id}',
                                'action': 'updated'
                            }
                        else:
                            # Even if no modification, it's still a success (idempotent)
                            return {
                                'success': True,
                                'message': f'Deployment for {api_name} on {platform_id}/{environment_id} is already up to date',
                                'action': 'unchanged'
                            }
            
        except Exception as e:
            logger.error(f"Deployment error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Deployment failed: {str(e)}',
                'action': 'error'
            }
    
    def get_deployment_status(self, api_name: str, platform_id: str, 
                            environment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a specific deployment.
        
        Args:
            api_name: API name
            platform_id: Platform ID
            environment_id: Environment ID
            
        Returns:
            Deployment details or None if not found
        """
        try:
            api = self.collection.find_one({'API Name': api_name})
            
            if not api:
                return None
            
            if 'Platform' not in api or not isinstance(api['Platform'], list):
                return None
            
            for platform in api['Platform']:
                if platform.get('PlatformID') != platform_id:
                    continue
                
                if 'Environment' not in platform or not isinstance(platform['Environment'], list):
                    continue
                
                for env in platform['Environment']:
                    if env.get('environmentID') == environment_id:
                        return {
                            'api_name': api_name,
                            'platform': platform_id,
                            'environment': environment_id,
                            'status': env.get('status'),
                            'last_updated': env.get('lastUpdated'),
                            'updated_by': env.get('updatedBy'),
                            'properties': env.get('Properties', {})
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting deployment status: {str(e)}")
            return None