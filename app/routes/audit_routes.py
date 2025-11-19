"""
Audit log API routes.

Provides endpoints for querying and managing audit logs.
Role-based access: Admin sees all, users see their own changes.
"""

import logging
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta
from app.utils.auth import require_auth, get_current_user
from app import limiter

logger = logging.getLogger(__name__)

bp = Blueprint('audit', __name__, url_prefix='/api/audit')


def get_audit_service():
    """Get audit service instance from current app"""
    return current_app.audit_service


def is_admin_user() -> bool:
    """
    Check if current user is admin.
    For now, returns True (implement proper role check when AUTH_ENABLED=true)

    Returns:
        True if user is admin
    """
    # TODO: Implement proper role checking when authentication is enabled
    # For now, all users are considered admin in development
    if current_app.config.get('AUTH_ENABLED', False):
        try:
            user = get_current_user()
            return user.get('role') == 'admin' if user else False
        except:
            return False
    return True


@bp.route('/logs', methods=['GET'])
@require_auth()
@limiter.limit(lambda: current_app.config.get('RATELIMIT_AUDIT_LOGS', '30 per minute'))
def get_logs():
    """
    Get audit logs with optional filters.
    
    Query Parameters:
        - api_name: Filter by API name
        - changed_by: Filter by user (admin only, or current user)
        - action: Filter by action type
        - start_date: Start date (ISO format)
        - end_date: End date (ISO format)
        - limit: Maximum results (default: 100, max: 1000)
        - skip: Skip N results for pagination (default: 0)
    
    Returns:
        200 OK: List of audit logs
        400 Bad Request: Invalid parameters
        403 Forbidden: Access denied
        500 Internal Server Error: Query failed
    
    Example:
        GET /api/audit/logs?api_name=ivp-test-app&limit=50
        GET /api/audit/logs?changed_by=Jibran&action=UPDATE_STATUS
    """
    try:
        audit_service = get_audit_service()
        
        # Get query parameters
        api_name = request.args.get('api_name')
        changed_by = request.args.get('changed_by')
        action = request.args.get('action')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Pagination parameters
        try:
            limit = int(request.args.get('limit', 100))
            skip = int(request.args.get('skip', 0))
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'limit and skip must be integers'
            }), 400
        
        # Enforce max limit
        if limit > 1000:
            limit = 1000
        
        if limit < 1:
            limit = 100
        
        if skip < 0:
            skip = 0
        
        # Role-based access control
        if changed_by and not is_admin_user():
            # Non-admin users can only see their own changes
            # Get current user from token
            try:
                user = get_current_user()
                if user:
                    current_user = user.get('username') or user.get('sub')

                    if changed_by != current_user:
                        return jsonify({
                            'status': 'error',
                            'message': 'Access denied: You can only view your own audit logs'
                        }), 403
            except:
                # If can't get user, only allow querying own changes
                pass
        
        # Parse dates
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid start_date format. Use ISO 8601 format (e.g., 2025-11-12T00:00:00Z)'
                }), 400
        
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid end_date format. Use ISO 8601 format'
                }), 400
        
        # Query audit logs
        logs = audit_service.get_audit_logs(
            api_name=api_name,
            changed_by=changed_by,
            action=action,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            skip=skip
        )
        
        # Get total count for pagination
        total = audit_service.count_logs(
            api_name=api_name,
            changed_by=changed_by,
            action=action
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'logs': logs,
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'skip': skip,
                    'count': len(logs),
                    'has_more': (skip + len(logs)) < total
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to query audit logs: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to query audit logs: {str(e)}'
        }), 500


@bp.route('/logs/<api_name>', methods=['GET'])
@require_auth()
def get_api_history(api_name):
    """
    Get complete change history for a specific API.
    
    Query Parameters:
        - limit: Maximum results (default: 50, max: 500)
    
    Returns:
        200 OK: List of audit logs for the API
        500 Internal Server Error: Query failed
    
    Example:
        GET /api/audit/logs/ivp-test-app
        GET /api/audit/logs/user-service?limit=100
    """
    try:
        audit_service = get_audit_service()
        
        # Get limit
        try:
            limit = int(request.args.get('limit', 50))
        except ValueError:
            limit = 50
        
        if limit > 500:
            limit = 500
        
        # Get history
        logs = audit_service.get_api_history(api_name=api_name, limit=limit)
        
        return jsonify({
            'status': 'success',
            'data': {
                'api_name': api_name,
                'logs': logs,
                'count': len(logs)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get API history: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get API history: {str(e)}'
        }), 500


@bp.route('/users/<username>/activity', methods=['GET'])
@require_auth()
def get_user_activity(username):
    """
    Get activity history for a specific user.
    
    Access Control:
        - Admins can view any user's activity
        - Non-admin users can only view their own activity
    
    Query Parameters:
        - limit: Maximum results (default: 50, max: 500)
    
    Returns:
        200 OK: List of audit logs for the user
        403 Forbidden: Access denied
        500 Internal Server Error: Query failed
    
    Example:
        GET /api/audit/users/Jibran/activity
        GET /api/audit/users/john.doe/activity?limit=100
    """
    try:
        # Access control check
        if not is_admin_user():
            # Non-admin can only view their own activity
            try:
                user = get_current_user()
                if user:
                    current_user = user.get('username') or user.get('sub')

                    if username != current_user:
                        return jsonify({
                            'status': 'error',
                            'message': 'Access denied: You can only view your own activity'
                        }), 403
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Access denied'
                    }), 403
            except:
                return jsonify({
                    'status': 'error',
                    'message': 'Access denied'
                }), 403
        
        audit_service = get_audit_service()
        
        # Get limit
        try:
            limit = int(request.args.get('limit', 50))
        except ValueError:
            limit = 50
        
        if limit > 500:
            limit = 500
        
        # Get user activity
        logs = audit_service.get_user_activity(changed_by=username, limit=limit)
        
        return jsonify({
            'status': 'success',
            'data': {
                'username': username,
                'logs': logs,
                'count': len(logs)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get user activity: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get user activity: {str(e)}'
        }), 500


@bp.route('/recent', methods=['GET'])
@require_auth()
def get_recent_changes():
    """
    Get recent changes within the last N hours.
    
    Query Parameters:
        - hours: Number of hours to look back (default: 24, max: 168/7 days)
        - limit: Maximum results (default: 100, max: 1000)
    
    Returns:
        200 OK: List of recent audit logs
        400 Bad Request: Invalid parameters
        500 Internal Server Error: Query failed
    
    Example:
        GET /api/audit/recent
        GET /api/audit/recent?hours=48&limit=200
    """
    try:
        audit_service = get_audit_service()
        
        # Get parameters
        try:
            hours = int(request.args.get('hours', 24))
            limit = int(request.args.get('limit', 100))
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'hours and limit must be integers'
            }), 400
        
        # Enforce limits
        if hours > 168:  # Max 7 days
            hours = 168
        
        if hours < 1:
            hours = 24
        
        if limit > 1000:
            limit = 1000
        
        # Get recent changes
        logs = audit_service.get_recent_changes(hours=hours, limit=limit)
        
        return jsonify({
            'status': 'success',
            'data': {
                'logs': logs,
                'count': len(logs),
                'hours': hours
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get recent changes: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get recent changes: {str(e)}'
        }), 500


@bp.route('/stats', methods=['GET'])
@require_auth()
@limiter.limit(lambda: current_app.config.get('RATELIMIT_AUDIT_STATS', '20 per minute'))
def get_stats():
    """
    Get audit log statistics.
    
    Returns:
        200 OK: Audit statistics
        500 Internal Server Error: Query failed
    
    Example:
        GET /api/audit/stats
    """
    try:
        audit_service = get_audit_service()
        
        stats = audit_service.get_stats()
        
        return jsonify({
            'status': 'success',
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get audit stats: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get audit stats: {str(e)}'
        }), 500


@bp.route('/cleanup', methods=['POST'])
@require_auth()
def cleanup_old_logs():
    """
    Cleanup old audit logs (admin only).
    
    Request Body (optional):
        {
            "retention_days": 180  // Optional, uses config default if not provided
        }
    
    Returns:
        200 OK: Cleanup completed
        400 Bad Request: Invalid parameters
        403 Forbidden: Admin only
        500 Internal Server Error: Cleanup failed
    
    Example:
        POST /api/audit/cleanup
        POST /api/audit/cleanup -d '{"retention_days": 90}'
    """
    try:
        # Admin only
        if not is_admin_user():
            return jsonify({
                'status': 'error',
                'message': 'Access denied: Admin only'
            }), 403
        
        audit_service = get_audit_service()
        
        # Get retention days from request or use default
        data = request.get_json(silent=True) or {}
        retention_days = data.get('retention_days')
        
        if retention_days is not None:
            if not isinstance(retention_days, int) or retention_days < 1:
                return jsonify({
                    'status': 'error',
                    'message': 'retention_days must be a positive integer'
                }), 400
        
        # Cleanup
        result = audit_service.cleanup_old_logs(retention_days=retention_days)
        
        return jsonify({
            'status': 'success',
            'message': f"Cleanup completed: {result['deleted_count']} logs deleted",
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to cleanup audit logs: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to cleanup audit logs: {str(e)}'
        }), 500


@bp.route('/actions', methods=['GET'])
def get_action_types():
    """
    Get list of available audit action types.
    
    Returns:
        200 OK: List of action types
    
    Example:
        GET /api/audit/actions
    """
    from app.services.audit_service import AuditAction
    
    actions = [
        attr for attr in dir(AuditAction)
        if not attr.startswith('_') and attr.isupper()
    ]
    
    return jsonify({
        'status': 'success',
        'data': {
            'actions': actions,
            'count': len(actions)
        }
    }), 200