"""
Admin routes for system management.

Includes backup/restore endpoints and other administrative functions.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

from app.utils.auth import require_auth, AuthError
from app.services.backup_service import BackupService

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def get_backup_service() -> BackupService:
    """Get configured backup service instance."""
    return BackupService(
        mongo_uri=current_app.config.get('MONGO_URI'),
        db_name=current_app.config.get('MONGO_DB'),
        backup_dir=current_app.config.get('BACKUP_DIR')
    )


@bp.route('/backup', methods=['POST'])
@require_auth(roles=['admin'])
def create_backup():
    """
    Create a new database backup.
    
    **Authentication:** Requires admin role
    
    **Request:**
```
    POST /api/admin/backup
    Headers:
        Authorization: Bearer <token>
    Body (optional):
        {
            "compression": true  // Optional, default: true
        }
```
    
    **Response (201):**
```json
    {
        "status": "success",
        "message": "Backup created successfully",
        "data": {
            "backup_id": "20251030_020000",
            "filename": "backup_ccr_20251030_020000.json.gz",
            "size_mb": 2.3,
            "timestamp": "2025-10-30T02:00:00Z",
            "collections": 1,
            "total_documents": 150,
            "compressed": true
        }
    }
```
    
    **Example:**
```bash
    curl -X POST http://localhost:5000/api/admin/backup \
      -H "Authorization: Bearer $TOKEN"
```
    """
    try:
        # Check if backups are enabled
        if not current_app.config.get('BACKUP_ENABLED', True):
            return jsonify({
                'status': 'error',
                'message': 'Backups are disabled in configuration'
            }), 400
        
        # Parse request body (optional) - handle empty body gracefully
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            data = {}
        
        compression = data.get('compression', True)
        
        # Validate compression parameter
        if not isinstance(compression, bool):
            return jsonify({
                'status': 'error',
                'message': 'compression must be a boolean'
            }), 400
        
        # Get backup service
        backup_service = get_backup_service()
        
        logger.info("Starting manual backup via API...")
        
        # Create backup
        result = backup_service.create_backup(compression=compression)
        
        logger.info(f"✅ Backup created: {result['filename']}")
        
        return jsonify({
            'status': 'success',
            'message': 'Backup created successfully',
            'data': {
                'backup_id': result['backup_id'],
                'filename': result['filename'],
                'size_mb': result['size_mb'],
                'timestamp': result['timestamp'],
                'collections': result['collections'],
                'total_documents': result['total_documents'],
                'compressed': result['compressed']
            }
        }), 201
        
    except PermissionError as e:
        # Filesystem permission error
        logger.error(f"Backup permission error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'PermissionError',
                'message': 'Unable to create backup due to filesystem permissions.',
                'error_code': 'BACKUP_PERMISSION_DENIED',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            'help': 'Please contact support. The backup directory may not be writable.'
        }), 500
    except OSError as e:
        # Disk space or other OS errors
        logger.error(f"Backup OS error: {str(e)}")
        error_msg = str(e).lower()
        if 'space' in error_msg or 'disk' in error_msg:
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'DiskSpaceError',
                    'message': 'Insufficient disk space to create backup.',
                    'error_code': 'BACKUP_NO_SPACE',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                },
                'help': 'Please free up disk space or contact support.'
            }), 507
        return jsonify({
            'status': 'error',
            'error': {
                'type': 'OSError',
                'message': 'Filesystem error occurred while creating backup.',
                'error_code': 'BACKUP_FILESYSTEM_ERROR',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500
    except Exception as e:
        logger.error(f"Backup creation failed: {str(e)}", exc_info=True)

        # Check for database connection errors
        error_msg = str(e).lower()
        if 'connection' in error_msg or 'timeout' in error_msg:
            return jsonify({
                'status': 'error',
                'error': {
                    'type': 'DatabaseConnectionError',
                    'message': 'Unable to connect to database for backup. Please try again.',
                    'error_code': 'DB_CONNECTION_FAILED',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }), 503

        return jsonify({
            'status': 'error',
            'error': {
                'type': 'BackupError',
                'message': 'Backup creation failed due to an unexpected error.',
                'error_code': 'BACKUP_FAILED',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            'help': 'Please try again or contact support if the problem persists.'
        }), 500


@bp.route('/backups', methods=['GET'])
@require_auth()
def list_backups():
    """
    List all available backups.
    
    **Authentication:** Requires valid token (any role)
    
    **Request:**
```
    GET /api/admin/backups
    Headers:
        Authorization: Bearer <token>
```
    
    **Response (200):**
```json
    {
        "status": "success",
        "data": [
            {
                "backup_id": "20251030_020000",
                "filename": "backup_ccr_20251030_020000.json.gz",
                "timestamp": "2025-10-30T02:00:00Z",
                "size_mb": 2.3,
                "age_days": 0,
                "compressed": true
            }
        ],
        "count": 1
    }
```
    
    **Example:**
```bash
    curl http://localhost:5000/api/admin/backups \
      -H "Authorization: Bearer $TOKEN"
```
    """
    try:
        # Get backup service
        backup_service = get_backup_service()
        
        # List all backups
        backups = backup_service.list_backups()
        
        return jsonify({
            'status': 'success',
            'data': backups,
            'count': len(backups)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to list backups: {str(e)}'
        }), 500


@bp.route('/backups/<backup_id>', methods=['DELETE'])
@require_auth(roles=['admin'])
def delete_backup(backup_id: str):
    """
    Delete a specific backup.
    
    **Authentication:** Requires admin role
    
    **Request:**
```
    DELETE /api/admin/backups/<backup_id>
    Headers:
        Authorization: Bearer <token>
```
    
    **Response (200):**
```json
    {
        "status": "success",
        "message": "Backup deleted successfully",
        "data": {
            "backup_id": "20251030_020000"
        }
    }
```
    
    **Example:**
```bash
    curl -X DELETE http://localhost:5000/api/admin/backups/20251030_020000 \
      -H "Authorization: Bearer $TOKEN"
```
    """
    try:
        # Get backup service
        backup_service = get_backup_service()
        
        # Delete backup
        backup_service.delete_backup(backup_id)
        
        logger.info(f"✅ Backup deleted: {backup_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Backup deleted successfully',
            'data': {
                'backup_id': backup_id
            }
        }), 200
        
    except FileNotFoundError:
        return jsonify({
            'status': 'error',
            'message': f'Backup not found: {backup_id}',
            'error_code': 'BACKUP_NOT_FOUND'
        }), 404
    except Exception as e:
        logger.error(f"Failed to delete backup: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete backup: {str(e)}'
        }), 500


@bp.route('/restore', methods=['POST'])
@require_auth(roles=['admin'])
def restore_backup():
    """
    Restore database from a backup.
    
    **Authentication:** Requires admin role
    
    **⚠️ WARNING:** This will modify/replace database contents!
    
    **Request:**
```
    POST /api/admin/restore
    Headers:
        Authorization: Bearer <token>
    Body:
        {
            "backup_id": "20251030_020000",
            "drop_existing": false  // Optional: drop existing collections first
        }
```
    
    **Response (200):**
```json
    {
        "status": "success",
        "message": "Database restored successfully",
        "data": {
            "backup_id": "20251030_020000",
            "collections_restored": 1,
            "total_documents": 150,
            "drop_existing": false,
            "restored_at": "2025-10-30T10:30:00Z"
        }
    }
```
    
    **Example:**
```bash
    curl -X POST http://localhost:5000/api/admin/restore \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "backup_id": "20251030_020000",
        "drop_existing": false
      }'
```
    """
    try:
        # Parse request body
        try:
            data = request.get_json(force=True)
        except Exception:
            return jsonify({
                'status': 'error',
                'message': 'Invalid JSON in request body'
            }), 400
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body required'
            }), 400
        
        # Validate backup_id
        backup_id = data.get('backup_id', '').strip()
        if not backup_id:
            return jsonify({
                'status': 'error',
                'message': 'backup_id is required'
            }), 400
        
        # Validate drop_existing
        drop_existing = data.get('drop_existing', False)
        if not isinstance(drop_existing, bool):
            return jsonify({
                'status': 'error',
                'message': 'drop_existing must be a boolean'
            }), 400
        
        # Get backup service
        backup_service = get_backup_service()
        
        logger.warning(f"⚠️  Starting database restore from backup: {backup_id}, drop_existing={drop_existing}")
        
        # Perform restore
        result = backup_service.restore_backup(
            backup_id=backup_id,
            drop_existing=drop_existing
        )
        
        logger.info(f"✅ Database restored: {result['total_documents']} documents")
        
        return jsonify({
            'status': 'success',
            'message': 'Database restored successfully',
            'data': result
        }), 200
        
    except FileNotFoundError:
        return jsonify({
            'status': 'error',
            'message': f'Backup not found: {backup_id}',
            'error_code': 'BACKUP_NOT_FOUND'
        }), 404
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Restore failed: {str(e)}',
            'error_code': 'RESTORE_FAILED'
        }), 500


@bp.route('/backups/cleanup', methods=['POST'])
@require_auth(roles=['admin'])
def cleanup_old_backups():
    """
    Delete backups older than retention period.
    
    **Authentication:** Requires admin role
    
    **Request:**
```
    POST /api/admin/backups/cleanup
    Headers:
        Authorization: Bearer <token>
    Body (optional):
        {
            "retention_days": 14  // Optional, default from config
        }
```
    
    **Response (200):**
```json
    {
        "status": "success",
        "message": "Cleanup completed",
        "data": {
            "deleted_count": 3,
            "deleted_size_mb": 6.9,
            "retention_days": 14
        }
    }
```
    
    **Example:**
```bash
    curl -X POST http://localhost:5000/api/admin/backups/cleanup \
      -H "Authorization: Bearer $TOKEN"
```
    """
    try:
        # Parse request body (optional)
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            data = {}
        
        # Get retention days from request or config
        retention_days = data.get('retention_days')
        if retention_days is None:
            retention_days = current_app.config.get('BACKUP_RETENTION_DAYS', 14)
        
        # Validate retention_days
        if not isinstance(retention_days, int) or retention_days < 1:
            return jsonify({
                'status': 'error',
                'message': 'retention_days must be a positive integer'
            }), 400
        
        # Get backup service
        backup_service = get_backup_service()
        
        logger.info(f"Starting backup cleanup: retention={retention_days} days")
        
        # Cleanup old backups
        result = backup_service.cleanup_old_backups(retention_days=retention_days)
        
        logger.info(f"✅ Cleanup completed: deleted {result['deleted_count']} backups")
        
        return jsonify({
            'status': 'success',
            'message': 'Cleanup completed',
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Cleanup failed: {str(e)}'
        }), 500


@bp.route('/backup/status', methods=['GET'])
@require_auth()
def backup_status():
    """
    Get backup system status and configuration.
    
    **Authentication:** Requires valid token (any role)
    
    **Request:**
```
    GET /api/admin/backup/status
    Headers:
        Authorization: Bearer <token>
```
    
    **Response (200):**
```json
    {
        "status": "success",
        "data": {
            "enabled": true,
            "backup_dir": "/app/backups",
            "retention_days": 14,
            "compression": true,
            "schedule": "Daily at 02:00",
            "total_backups": 5,
            "total_size_mb": 11.5,
            "oldest_backup": "2025-10-25T02:00:00Z",
            "newest_backup": "2025-10-30T02:00:00Z"
        }
    }
```
    """
    try:
        # Get configuration
        backup_enabled = current_app.config.get('BACKUP_ENABLED', True)
        backup_dir = current_app.config.get('BACKUP_DIR')
        retention_days = current_app.config.get('BACKUP_RETENTION_DAYS', 14)
        compression = current_app.config.get('BACKUP_COMPRESSION', True)
        schedule_hour = current_app.config.get('BACKUP_SCHEDULE_HOUR', 2)
        schedule_minute = current_app.config.get('BACKUP_SCHEDULE_MINUTE', 0)
        
        # Get backup service
        backup_service = get_backup_service()
        
        # List backups
        backups = backup_service.list_backups()
        
        # Calculate statistics
        total_size_mb = sum(b['size_mb'] for b in backups)
        oldest_backup = backups[-1]['timestamp'] if backups else None
        newest_backup = backups[0]['timestamp'] if backups else None
        
        return jsonify({
            'status': 'success',
            'data': {
                'enabled': backup_enabled,
                'backup_dir': backup_dir,
                'retention_days': retention_days,
                'compression': compression,
                'schedule': f"Daily at {schedule_hour:02d}:{schedule_minute:02d}",
                'total_backups': len(backups),
                'total_size_mb': round(total_size_mb, 2),
                'oldest_backup': oldest_backup,
                'newest_backup': newest_backup
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get backup status: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get backup status: {str(e)}'
        }), 500

@bp.route('/scheduler/jobs', methods=['GET'])
@require_auth()
def get_scheduled_jobs():
    """
    Get list of scheduled jobs.

    Returns information about scheduled background jobs (like automated backups).
    Requires authentication.
    
    **Response (200):**
```json
    {
        "status": "success",
        "scheduler_running": true,
        "data": [
            {
                "id": "automated_backup",
                "name": "Automated Database Backup",
                "next_run": "2025-11-05T02:00:00+00:00",
                "trigger": "cron[hour='2', minute='0']"
            }
        ],
        "count": 1
    }
```
    """
    try:
        from app import scheduler
        
        jobs = scheduler.get_jobs()
        
        return jsonify({
            'status': 'success',
            'scheduler_running': scheduler.scheduler.running if scheduler.scheduler else False,
            'data': jobs,
            'count': len(jobs)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get scheduled jobs: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get scheduled jobs: {str(e)}'
        }), 500