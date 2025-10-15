"""
JWT Authentication utilities for CCR API Manager.

This module provides:
- JWT token generation
- Token validation
- Protected route decorator (@require_auth)
- Error handling for authentication failures
"""

import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Custom exception for authentication errors."""
    
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def generate_token(username: str, role: str = 'user', 
                   expires_in_hours: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate a JWT token for a user.
    
    Args:
        username: Username/identifier for the token
        role: User role (e.g., 'admin', 'user', 'readonly')
        expires_in_hours: Token expiration time in hours (overrides config)
        
    Returns:
        Dictionary containing:
        - token: JWT token string
        - expires_at: Expiration timestamp (ISO format)
        - username: Username
        - role: User role
        
    Example:
        >>> with app.app_context():
        ...     token_data = generate_token('john.doe', 'admin', 48)
        ...     print(token_data['token'][:50])
        eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
    """
    try:
        # Get configuration from Flask app
        secret_key = current_app.config.get('JWT_SECRET_KEY')
        algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')
        
        if not expires_in_hours:
            expires_in_hours = current_app.config.get('JWT_EXPIRATION_HOURS', 24)
        
        # Calculate expiration time
        expiration = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        # Build JWT payload
        payload = {
            'username': username,
            'role': role,
            'iat': datetime.utcnow(),  # Issued at
            'exp': expiration,          # Expiration
            'iss': 'ccr-api-manager'    # Issuer
        }
        
        # Generate token
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        
        logger.info(
            f"Generated token for user '{username}' with role '{role}', "
            f"expires at {expiration.isoformat()}"
        )
        
        return {
            'token': token,
            'expires_at': expiration.isoformat() + 'Z',
            'username': username,
            'role': role
        }
        
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        raise AuthError(f"Failed to generate token: {str(e)}")


def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate a JWT token and extract payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary with token payload (username, role, etc.)
        
    Raises:
        AuthError: If token is invalid, expired, or malformed
        
    Example:
        >>> with app.app_context():
        ...     payload = validate_token(token_string)
        ...     print(payload['username'], payload['role'])
        john.doe admin
    """
    try:
        secret_key = current_app.config.get('JWT_SECRET_KEY')
        algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')
        
        # Decode and validate token
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            options={
                'verify_signature': True,
                'verify_exp': True,
                'require': ['username', 'role', 'exp']
            }
        )
        
        logger.info(
            f"Token validated for user '{payload.get('username')}' "
            f"with role '{payload.get('role')}'"
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token validation failed: Token has expired")
        raise AuthError("Token has expired", 401)
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise AuthError("Invalid token", 401)
    except Exception as e:
        logger.error(f"Unexpected error validating token: {str(e)}")
        raise AuthError("Token validation failed", 401)


def get_token_from_request() -> Optional[str]:
    """
    Extract JWT token from request Authorization header.
    
    Expected format: "Authorization: Bearer <token>"
    
    Returns:
        Token string or None if not found
        
    Example:
        >>> # With header: Authorization: Bearer eyJ0eXAi...
        >>> token = get_token_from_request()
        >>> print(token[:20])
        eyJ0eXAiOiJKV1QiLCJh...
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return None
    
    # Split "Bearer <token>"
    parts = auth_header.split()
    
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        logger.warning(f"Invalid Authorization header format: {auth_header[:50]}...")
        return None
    
    return parts[1]


def validate_admin_key(admin_key: str) -> bool:
    """
    Validate admin key for token generation.
    
    Args:
        admin_key: Admin key from request
        
    Returns:
        True if valid, False otherwise
    """
    expected_key = current_app.config.get('JWT_ADMIN_KEY')
    
    if not expected_key:
        logger.error("JWT_ADMIN_KEY not configured")
        return False
    
    is_valid = admin_key == expected_key
    
    if not is_valid:
        logger.warning("Invalid admin key provided")
    
    return is_valid


def require_auth(roles: Optional[list] = None):
    """
    Decorator to protect routes with JWT authentication.
    
    Args:
        roles: Optional list of allowed roles. If None, any authenticated user allowed.
        
    Usage:
        @bp.route('/api/deploy', methods=['POST'])
        @require_auth()  # Any authenticated user
        def deploy_api():
            # Access user info via request.user
            username = request.user['username']
            role = request.user['role']
            ...
        
        @bp.route('/api/admin/users', methods=['GET'])
        @require_auth(roles=['admin'])  # Only admin role
        def list_users():
            ...
    
    The decorator:
    1. Checks if authentication is enabled (AUTH_ENABLED)
    2. Checks if endpoint is public (PUBLIC_ENDPOINTS)
    3. Extracts token from Authorization header
    4. Validates token
    5. Checks user role (if roles specified)
    6. Injects user info into request context (request.user)
    
    Returns:
        - 401 Unauthorized: No token or invalid token
        - 403 Forbidden: Insufficient permissions (wrong role)
        - Calls wrapped function: If authentication successful
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if auth is enabled
            auth_enabled = current_app.config.get('AUTH_ENABLED', False)
    
            logger.info(f"🔍 Request to {request.path} - AUTH_ENABLED={auth_enabled}")
    
            if not auth_enabled:
                # Auth disabled - allow request
                logger.info(f"🔓 Auth disabled - allowing request to {request.path}")
                return f(*args, **kwargs)
    
            # Check if endpoint is public
            from app.config import is_public_endpoint
            is_public = is_public_endpoint(request.path)
    
            logger.info(f"🔍 Endpoint {request.path} public check: {is_public}")
    
            if is_public:
                logger.info(f"🔓 Public endpoint - allowing request to {request.path}")
                return f(*args, **kwargs)
    
            logger.info(f"🔒 Protected endpoint {request.path} - checking for token...")
    
            # Auth required - extract token
            token = get_token_from_request()
            
            if not token:
                logger.warning(f"❌ No token provided for protected endpoint: {request.path}")
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication required. Please provide a valid token in the Authorization header.',
                    'error_code': 'AUTH_REQUIRED'
                }), 401
            
            # Validate token
            try:
                payload = validate_token(token)
                
                # Check role if specified
                if roles:
                    user_role = payload.get('role')
                    if user_role not in roles:
                        logger.warning(
                            f"User '{payload.get('username')}' with role '{user_role}' "
                            f"attempted to access endpoint requiring roles: {roles}"
                        )
                        return jsonify({
                            'status': 'error',
                            'message': f'Insufficient permissions. Required roles: {", ".join(roles)}',
                            'error_code': 'INSUFFICIENT_PERMISSIONS'
                        }), 403
                
                # Inject user info into request context
                request.user = {
                    'username': payload.get('username'),
                    'role': payload.get('role')
                }
                
                logger.info(
                    f"Authenticated request to {request.path} by user '{payload.get('username')}' "
                    f"with role '{payload.get('role')}'"
                )
                
                # Call the protected function
                return f(*args, **kwargs)
                
            except AuthError as e:
                return jsonify({
                    'status': 'error',
                    'message': e.message,
                    'error_code': 'AUTH_FAILED'
                }), e.status_code
            except Exception as e:
                logger.error(f"Unexpected error in auth decorator: {str(e)}", exc_info=True)
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication failed',
                    'error_code': 'AUTH_ERROR'
                }), 500
        
        return decorated_function
    return decorator


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from request context.
    
    Returns:
        Dictionary with user info or None if not authenticated
        
    Usage:
        @bp.route('/api/myinfo')
        @require_auth()
        def my_info():
            user = get_current_user()
            if user:
                return jsonify({
                    'username': user['username'],
                    'role': user['role']
                })
    """
    return getattr(request, 'user', None)