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
        Uses API name as the document _id for better performance and readability.
        
        Args:
            api_name: Name of the API (used as _id)
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
            
            # Check if API already exists (using api_name as _id)
            existing_api = self.collection.find_one({'_id': api_name})
            
            if not existing_api:
                # Create new API document with api_name as _id
                logger.info(f"Creating new API: {api_name}")
                
                new_doc = {
                    '_id': api_name,  # Use API name as _id
                    'API Name': api_name,  # Keep for backward compatibility and readability
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
                        {'_id': api_name},
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
                                '_id': api_name,
                                'Platform.PlatformID': platform_id
                            },
                            {
                                '$push': {
                                    'Platform.$.Environment': {
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
                        
                        # Get the original deployment date from existing environment
                        original_deployment_date = platform['Environment'][environment_index].get('deploymentDate', now_str)
                        
                        # Use positional operator with arrayFilters
                        result = self.collection.update_one(
                            {
                                '_id': api_name
                            },
                            {
                                '$set': {
                                    'Platform.$[p].Environment.$[e].lastUpdated': now_str,
                                    'Platform.$[p].Environment.$[e].updatedBy': updated_by,
                                    'Platform.$[p].Environment.$[e].status': status,
                                    'Platform.$[p].Environment.$[e].Properties': properties,
                                    'Platform.$[p].Environment.$[e].deploymentDate': original_deployment_date
                                }
                            },
                            array_filters=[
                                {'p.PlatformID': platform_id},
                                {'e.environmentID': environment_id}
                            ]
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
    
    def update_deployment_full(self, api_name: str, platform_id: str, 
                              environment_id: str, status: str, updated_by: str,
                              properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full update (PUT) - Replaces the entire deployment.
        Same as deploy_api but with clear semantics for updates.
        
        Args:
            api_name: API name
            platform_id: Platform ID
            environment_id: Environment ID
            status: New status
            updated_by: User making the update
            properties: Complete new properties (replaces old)
            
        Returns:
            Result dictionary
        """
        return self.deploy_api(api_name, platform_id, environment_id, 
                              status, updated_by, properties)
    
    def update_deployment_partial(self, api_name: str, platform_id: str, 
                                 environment_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Partial update (PATCH) - Updates only specified fields.
        Merges updates with existing data.
        
        Args:
            api_name: API name
            platform_id: Platform ID
            environment_id: Environment ID
            updates: Dictionary with fields to update (status, updatedBy, properties)
            
        Returns:
            Result dictionary
        """
        try:
            logger.info(f"Partial update for {api_name} on {platform_id}/{environment_id}")
            
            # Check if deployment exists
            existing = self.get_deployment_status(api_name, platform_id, environment_id)
            if not existing:
                return {
                    'success': False,
                    'message': f'Deployment not found: {api_name} on {platform_id}/{environment_id}',
                    'action': 'not_found'
                }
            
            # Build update document
            now_str = datetime.utcnow().isoformat() + 'Z'
            set_updates = {
                'Platform.$[p].Environment.$[e].lastUpdated': now_str
            }
            
            # Add status if provided
            if 'status' in updates:
                set_updates['Platform.$[p].Environment.$[e].status'] = updates['status']
            
            # Add updatedBy if provided
            if 'updated_by' in updates or 'updatedBy' in updates:
                set_updates['Platform.$[p].Environment.$[e].updatedBy'] = updates.get('updated_by', updates.get('updatedBy'))
            
            # Handle properties - merge with existing
            if 'properties' in updates:
                # Get existing properties
                existing_props = existing.get('properties', {})
                
                # Merge with new properties
                merged_props = {**existing_props, **updates['properties']}
                set_updates['Platform.$[p].Environment.$[e].Properties'] = merged_props
            
            # Perform update
            result = self.collection.update_one(
                {'_id': api_name},
                {'$set': set_updates},
                array_filters=[
                    {'p.PlatformID': platform_id},
                    {'e.environmentID': environment_id}
                ]
            )
            
            if result.modified_count > 0:
                return {
                    'success': True,
                    'message': f'Partially updated deployment for {api_name} on {platform_id}/{environment_id}',
                    'action': 'updated',
                    'modified_fields': list(updates.keys())
                }
            else:
                return {
                    'success': True,
                    'message': f'No changes needed for {api_name} on {platform_id}/{environment_id}',
                    'action': 'unchanged'
                }
                
        except Exception as e:
            logger.error(f"Partial update error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Partial update failed: {str(e)}',
                'action': 'error'
            }
    
    def update_status_only(self, api_name: str, platform_id: str, 
                          environment_id: str, status: str, updated_by: str) -> Dict[str, Any]:
        """
        Update only the status of a deployment.
        Useful for status changes without touching properties.
        
        Args:
            api_name: API name
            platform_id: Platform ID
            environment_id: Environment ID
            status: New status
            updated_by: User making the update
            
        Returns:
            Result dictionary
        """
        return self.update_deployment_partial(
            api_name, platform_id, environment_id,
            {'status': status, 'updated_by': updated_by}
        )
    
    def update_properties_only(self, api_name: str, platform_id: str, 
                              environment_id: str, properties: Dict[str, Any],
                              updated_by: str) -> Dict[str, Any]:
        """
        Update only the properties of a deployment.
        Merges with existing properties.
        
        Args:
            api_name: API name
            platform_id: Platform ID
            environment_id: Environment ID
            properties: Properties to add/update
            updated_by: User making the update
            
        Returns:
            Result dictionary
        """
        return self.update_deployment_partial(
            api_name, platform_id, environment_id,
            {'properties': properties, 'updated_by': updated_by}
        )
    
    def delete_deployment(self, api_name: str, platform_id: str, 
                         environment_id: str) -> Dict[str, Any]:
        """
        Delete a specific deployment (remove environment from platform).
        
        Args:
            api_name: API name
            platform_id: Platform ID
            environment_id: Environment ID
            
        Returns:
            Result dictionary
        """
        try:
            logger.info(f"Deleting deployment: {api_name} on {platform_id}/{environment_id}")
            
            # Check if deployment exists
            existing = self.get_deployment_status(api_name, platform_id, environment_id)
            if not existing:
                return {
                    'success': False,
                    'message': f'Deployment not found: {api_name} on {platform_id}/{environment_id}',
                    'action': 'not_found'
                }
            
            # Remove the environment from the platform
            result = self.collection.update_one(
                {
                    '_id': api_name,
                    'Platform.PlatformID': platform_id
                },
                {
                    '$pull': {
                        'Platform.$.Environment': {'environmentID': environment_id}
                    }
                }
            )
            
            if result.modified_count > 0:
                # Check if platform now has no environments
                api_doc = self.collection.find_one({'_id': api_name})
                
                if api_doc and 'Platform' in api_doc:
                    for platform in api_doc['Platform']:
                        if platform.get('PlatformID') == platform_id:
                            if not platform.get('Environment') or len(platform.get('Environment', [])) == 0:
                                # Remove empty platform
                                self.collection.update_one(
                                    {'_id': api_name},
                                    {'$pull': {'Platform': {'PlatformID': platform_id}}}
                                )
                                logger.info(f"Removed empty platform {platform_id}")
                            break
                
                # Check if API now has no platforms
                api_doc = self.collection.find_one({'_id': api_name})
                if api_doc and (not api_doc.get('Platform') or len(api_doc.get('Platform', [])) == 0):
                    # Delete the entire API document
                    self.collection.delete_one({'_id': api_name})
                    logger.info(f"Deleted API {api_name} - no deployments remaining")
                    
                    return {
                        'success': True,
                        'message': f'Deleted last deployment for {api_name} - API removed',
                        'action': 'deleted_api'
                    }
                
                return {
                    'success': True,
                    'message': f'Deleted deployment {api_name} on {platform_id}/{environment_id}',
                    'action': 'deleted'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to delete deployment',
                    'action': 'failed'
                }
                
        except Exception as e:
            logger.error(f"Delete error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Delete failed: {str(e)}',
                'action': 'error'
            }
    
    def get_deployment_status(self, api_name: str, platform_id: str, 
                            environment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a specific deployment.
        
        Args:
            api_name: API name (used as _id)
            platform_id: Platform ID
            environment_id: Environment ID
            
        Returns:
            Deployment details or None if not found
        """
        try:
            # Direct lookup by _id (much faster!)
            api = self.collection.find_one({'_id': api_name})
            
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
                            'deployment_date': env.get('deploymentDate'),
                            'last_updated': env.get('lastUpdated'),
                            'updated_by': env.get('updatedBy'),
                            'properties': env.get('Properties', {})
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting deployment status: {str(e)}")
            return None