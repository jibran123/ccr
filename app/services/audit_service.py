"""
Audit logging service for CCR API Manager.

Provides immutable audit trail for all API deployment changes.
Tracks who made changes, what changed, and when for compliance and debugging.

Features:
- Log all deployment changes (create, update, delete)
- Track before/after state
- Configurable retention period (default: 180 days)
- Role-based access (admin sees all, users see their own)
- Automatic cleanup of old logs
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pymongo import DESCENDING, ASCENDING
from pymongo.errors import PyMongoError
import uuid

logger = logging.getLogger(__name__)


class AuditAction:
    """Enum-like class for audit action types"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    UPDATE_STATUS = "UPDATE_STATUS"
    UPDATE_VERSION = "UPDATE_VERSION"
    UPDATE_PROPERTIES = "UPDATE_PROPERTIES"
    UPDATE_FULL = "UPDATE_FULL"
    UPDATE_PARTIAL = "UPDATE_PARTIAL"
    DELETE = "DELETE"
    DELETE_ENVIRONMENT = "DELETE_ENVIRONMENT"
    DELETE_PLATFORM = "DELETE_PLATFORM"
    DELETE_API = "DELETE_API"


class AuditService:
    """Service for audit logging operations"""
    
    def __init__(self, db_service, retention_days: int = 180):
        """
        Initialize audit service.
        
        Args:
            db_service: Database service instance
            retention_days: Number of days to retain audit logs (default: 180)
        """
        self.db = db_service.db
        self.audit_collection = self.db['audit_logs']
        self.retention_days = retention_days
        
        # Create indexes for efficient querying
        self._ensure_indexes()
        
        logger.info(f"AuditService initialized with {retention_days} day retention")
    
    def _ensure_indexes(self):
        """Create indexes on audit_logs collection for performance"""
        try:
            # Index on timestamp for cleanup and time-based queries
            self.audit_collection.create_index([('timestamp', DESCENDING)])
            
            # Index on api_name for filtering by API
            self.audit_collection.create_index('api_name')
            
            # Index on changed_by for user-specific queries
            self.audit_collection.create_index('changed_by')
            
            # Index on action for filtering by action type
            self.audit_collection.create_index('action')
            
            # Compound index for common query patterns
            self.audit_collection.create_index([
                ('api_name', ASCENDING),
                ('timestamp', DESCENDING)
            ])
            
            logger.info("✅ Audit log indexes created")
        except Exception as e:
            logger.warning(f"Could not create audit indexes: {e}")
    
    def log_change(self, action: str, api_name: str, changed_by: str,
                   platform_id: Optional[str] = None, 
                   environment_id: Optional[str] = None,
                   changes: Optional[Dict[str, Any]] = None,
                   old_state: Optional[Dict[str, Any]] = None,
                   new_state: Optional[Dict[str, Any]] = None) -> str:
        """
        Log an API change to the audit trail.
        
        Args:
            action: Type of action (from AuditAction)
            api_name: Name of the API
            changed_by: User who made the change
            platform_id: Platform ID (optional)
            environment_id: Environment ID (optional)
            changes: Dictionary of field changes with old/new values
            old_state: Complete state before change (optional)
            new_state: Complete state after change (optional)
            
        Returns:
            Audit log ID
        """
        try:
            audit_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            audit_entry = {
                'audit_id': audit_id,
                'timestamp': timestamp.isoformat() + 'Z',
                'action': action,
                'api_name': api_name,
                'changed_by': changed_by
            }
            
            # Add optional fields if provided
            if platform_id:
                audit_entry['platform_id'] = platform_id
            
            if environment_id:
                audit_entry['environment_id'] = environment_id
            
            if changes:
                audit_entry['changes'] = changes
            
            if old_state:
                audit_entry['old_state'] = old_state
            
            if new_state:
                audit_entry['new_state'] = new_state
            
            # Insert audit log
            self.audit_collection.insert_one(audit_entry)
            
            logger.info(f"📝 Audit log created: {action} for {api_name} by {changed_by}")
            return audit_id
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}", exc_info=True)
            # Don't fail the operation if audit logging fails
            return None
    
    def log_deployment(self, api_name: str, platform_id: str, environment_id: str,
                      version: str, status: str, changed_by: str,
                      properties: Dict[str, Any], is_new: bool = False) -> str:
        """
        Log a deployment action (create or update).
        
        Args:
            api_name: API name
            platform_id: Platform ID
            environment_id: Environment ID
            version: API version
            status: Deployment status
            changed_by: User making the change
            properties: Deployment properties
            is_new: True if this is a new deployment, False if update
            
        Returns:
            Audit log ID
        """
        action = AuditAction.CREATE if is_new else AuditAction.UPDATE
        
        new_state = {
            'version': version,
            'status': status,
            'properties': properties
        }
        
        return self.log_change(
            action=action,
            api_name=api_name,
            platform_id=platform_id,
            environment_id=environment_id,
            changed_by=changed_by,
            new_state=new_state
        )
    
    def log_status_change(self, api_name: str, platform_id: str, environment_id: str,
                         old_status: str, new_status: str, changed_by: str) -> str:
        """
        Log a status change.
        
        Args:
            api_name: API name
            platform_id: Platform ID
            environment_id: Environment ID
            old_status: Previous status
            new_status: New status
            changed_by: User making the change
            
        Returns:
            Audit log ID
        """
        changes = {
            'status': {
                'old': old_status,
                'new': new_status
            }
        }
        
        return self.log_change(
            action=AuditAction.UPDATE_STATUS,
            api_name=api_name,
            platform_id=platform_id,
            environment_id=environment_id,
            changed_by=changed_by,
            changes=changes
        )
    
    def log_version_change(self, api_name: str, platform_id: str, environment_id: str,
                          old_version: str, new_version: str, changed_by: str) -> str:
        """
        Log a version change.
        
        Args:
            api_name: API name
            platform_id: Platform ID
            environment_id: Environment ID
            old_version: Previous version
            new_version: New version
            changed_by: User making the change
            
        Returns:
            Audit log ID
        """
        changes = {
            'version': {
                'old': old_version,
                'new': new_version
            }
        }
        
        return self.log_change(
            action=AuditAction.UPDATE_VERSION,
            api_name=api_name,
            platform_id=platform_id,
            environment_id=environment_id,
            changed_by=changed_by,
            changes=changes
        )
    
    def log_properties_change(self, api_name: str, platform_id: str, environment_id: str,
                             old_properties: Dict[str, Any], new_properties: Dict[str, Any],
                             changed_by: str) -> str:
        """
        Log a properties change.
        
        Args:
            api_name: API name
            platform_id: Platform ID
            environment_id: Environment ID
            old_properties: Previous properties
            new_properties: New properties
            changed_by: User making the change
            
        Returns:
            Audit log ID
        """
        # Calculate what actually changed
        changes = {}
        
        # Find added/changed properties
        for key, value in new_properties.items():
            if key not in old_properties:
                changes[key] = {'old': None, 'new': value}
            elif old_properties[key] != value:
                changes[key] = {'old': old_properties[key], 'new': value}
        
        # Find removed properties
        for key in old_properties:
            if key not in new_properties:
                changes[key] = {'old': old_properties[key], 'new': None}
        
        return self.log_change(
            action=AuditAction.UPDATE_PROPERTIES,
            api_name=api_name,
            platform_id=platform_id,
            environment_id=environment_id,
            changed_by=changed_by,
            changes={'properties': changes}
        )
    
    def log_deletion(self, api_name: str, platform_id: Optional[str], 
                    environment_id: Optional[str], changed_by: str,
                    old_state: Optional[Dict[str, Any]] = None) -> str:
        """
        Log a deletion action.
        
        Args:
            api_name: API name
            platform_id: Platform ID (None if entire API deleted)
            environment_id: Environment ID (None if platform deleted)
            changed_by: User making the change
            old_state: State before deletion
            
        Returns:
            Audit log ID
        """
        # Determine deletion type
        if environment_id:
            action = AuditAction.DELETE_ENVIRONMENT
        elif platform_id:
            action = AuditAction.DELETE_PLATFORM
        else:
            action = AuditAction.DELETE_API
        
        return self.log_change(
            action=action,
            api_name=api_name,
            platform_id=platform_id,
            environment_id=environment_id,
            changed_by=changed_by,
            old_state=old_state
        )
    
    def get_audit_logs(self, api_name: Optional[str] = None,
                      changed_by: Optional[str] = None,
                      action: Optional[str] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      limit: int = 100,
                      skip: int = 0) -> List[Dict[str, Any]]:
        """
        Query audit logs with optional filters.
        
        Args:
            api_name: Filter by API name
            changed_by: Filter by user
            action: Filter by action type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            skip: Number of results to skip (for pagination)
            
        Returns:
            List of audit log entries
        """
        try:
            query = {}
            
            if api_name:
                query['api_name'] = api_name
            
            if changed_by:
                query['changed_by'] = changed_by
            
            if action:
                query['action'] = action
            
            # Date range filter
            if start_date or end_date:
                query['timestamp'] = {}
                if start_date:
                    query['timestamp']['$gte'] = start_date.isoformat() + 'Z'
                if end_date:
                    query['timestamp']['$lte'] = end_date.isoformat() + 'Z'
            
            # Query with pagination
            cursor = self.audit_collection.find(query).sort('timestamp', DESCENDING).skip(skip).limit(limit)
            
            logs = list(cursor)
            
            # Remove MongoDB _id field
            for log in logs:
                if '_id' in log:
                    del log['_id']
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}", exc_info=True)
            return []
    
    def get_api_history(self, api_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get complete change history for a specific API.
        
        Args:
            api_name: API name
            limit: Maximum number of entries
            
        Returns:
            List of audit log entries for the API
        """
        return self.get_audit_logs(api_name=api_name, limit=limit)
    
    def get_user_activity(self, changed_by: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get activity history for a specific user.
        
        Args:
            changed_by: User name
            limit: Maximum number of entries
            
        Returns:
            List of audit log entries for the user
        """
        return self.get_audit_logs(changed_by=changed_by, limit=limit)
    
    def get_recent_changes(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent changes within the last N hours.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of entries
            
        Returns:
            List of recent audit log entries
        """
        start_date = datetime.utcnow() - timedelta(hours=hours)
        return self.get_audit_logs(start_date=start_date, limit=limit)
    
    def count_logs(self, api_name: Optional[str] = None,
                   changed_by: Optional[str] = None,
                   action: Optional[str] = None) -> int:
        """
        Count audit logs matching criteria.
        
        Args:
            api_name: Filter by API name
            changed_by: Filter by user
            action: Filter by action type
            
        Returns:
            Count of matching logs
        """
        try:
            query = {}
            
            if api_name:
                query['api_name'] = api_name
            
            if changed_by:
                query['changed_by'] = changed_by
            
            if action:
                query['action'] = action
            
            return self.audit_collection.count_documents(query)
            
        except Exception as e:
            logger.error(f"Failed to count audit logs: {e}")
            return 0
    
    def cleanup_old_logs(self, retention_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Delete audit logs older than retention period.
        
        Args:
            retention_days: Number of days to retain (uses default if not provided)
            
        Returns:
            Dictionary with deletion results
        """
        try:
            days = retention_days if retention_days is not None else self.retention_days
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat() + 'Z'
            
            logger.info(f"Cleaning up audit logs older than {cutoff_str} ({days} days)")
            
            # Count logs to be deleted
            count_query = {'timestamp': {'$lt': cutoff_str}}
            count = self.audit_collection.count_documents(count_query)
            
            if count == 0:
                logger.info("No old audit logs to clean up")
                return {
                    'deleted_count': 0,
                    'retention_days': days,
                    'cutoff_date': cutoff_str
                }
            
            # Delete old logs
            result = self.audit_collection.delete_many(count_query)
            
            logger.info(f"✅ Deleted {result.deleted_count} old audit logs")
            
            return {
                'deleted_count': result.deleted_count,
                'retention_days': days,
                'cutoff_date': cutoff_str
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup audit logs: {e}", exc_info=True)
            return {
                'deleted_count': 0,
                'error': str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            total_logs = self.audit_collection.count_documents({})
            
            # Count by action type
            action_pipeline = [
                {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]
            action_counts = list(self.audit_collection.aggregate(action_pipeline))
            
            # Count by user
            user_pipeline = [
                {'$group': {'_id': '$changed_by', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': 10}
            ]
            top_users = list(self.audit_collection.aggregate(user_pipeline))
            
            # Recent activity (last 24 hours)
            recent_cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat() + 'Z'
            recent_count = self.audit_collection.count_documents({
                'timestamp': {'$gte': recent_cutoff}
            })
            
            return {
                'total_logs': total_logs,
                'recent_24h': recent_count,
                'by_action': {item['_id']: item['count'] for item in action_counts},
                'top_users': [
                    {'user': item['_id'], 'changes': item['count']} 
                    for item in top_users
                ],
                'retention_days': self.retention_days
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit stats: {e}")
            return {'error': str(e)}