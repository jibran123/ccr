"""
JWT Authentication utilities for Common Configuration Repository (CCR).

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
            'iss': 'ccr'    # Issuer
        }
        
        # Generate token
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        
        # Reduced logging for security - don't log username/expiration
        logger.info(f"Generated token for user with role '{role}'")
        
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
        AuthError: If token is invalid, expired, malformed, or blacklisted
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

        # Check if access token is blacklisted (only for access tokens with JTI)
        jti = payload.get('jti')
        if jti:
            # Access token - check blacklist
            try:
                from app.services.token_service import TokenService
                if hasattr(current_app, 'db_service'):
                    token_service = TokenService(current_app.db_service)
                    if token_service.is_token_blacklisted(jti):
                        logger.warning(f"Token validation failed: Token has been revoked (JTI: {jti[:10]}...)")
                        raise AuthError("Token has been revoked", 401)
            except AuthError:
                # Re-raise AuthError (token is blacklisted)
                raise
            except Exception as e:
                # If blacklist check fails (DB error, etc.), log but don't block (fail open for availability)
                logger.error(f"Error checking token blacklist: {str(e)}")

        # Reduced logging for security
        logger.debug("Token validated successfully")

        return payload

    except AuthError:
        # Re-raise AuthError as-is
        raise
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
            username = request.user['username']
            role = request.user['role']
            ...
    
    Returns:
        - 401 Unauthorized: No token or invalid token
        - 403 Forbidden: Insufficient permissions (wrong role)
        - Calls wrapped function: If authentication successful
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # ==================== ENHANCED DEBUG LOGGING ====================
            logger.warning("=" * 70)
            logger.warning(f"🔍 DECORATOR CALLED for {request.method} {request.path}")
            
            # Check if auth is enabled
            auth_enabled = current_app.config.get('AUTH_ENABLED', False)
            logger.warning(f"🔍 AUTH_ENABLED from current_app.config: {auth_enabled} (type: {type(auth_enabled)})")
            
            if not auth_enabled:
                # Auth disabled - allow request
                logger.warning(f"🔓 Auth DISABLED - ALLOWING request to {request.path}")
                logger.warning("=" * 70)
                return f(*args, **kwargs)
            
            # Check if endpoint is public
            from app.config import is_public_endpoint
            is_public = is_public_endpoint(request.path)
            logger.warning(f"🔍 is_public_endpoint('{request.path}'): {is_public}")
            
            if is_public:
                logger.warning(f"🔓 Public endpoint - ALLOWING request to {request.path}")
                logger.warning("=" * 70)
                return f(*args, **kwargs)
            
            logger.warning(f"🔒 Protected endpoint - REQUIRING TOKEN for {request.path}")
            
            # Auth required - extract token
            token = get_token_from_request()
            
            if not token:
                logger.warning(f"❌ NO TOKEN provided for protected endpoint: {request.path}")
                logger.warning("=" * 70)
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication required. Please provide a valid token in the Authorization header.',
                    'error_code': 'AUTH_REQUIRED'
                }), 401
            
            # Validate token (removed token prefix logging for security)
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
                        logger.warning("=" * 70)
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
                
                # Reduced logging for security
                logger.debug(f"Authenticated request to {request.path}")
                
                # Call the protected function
                return f(*args, **kwargs)
                
            except AuthError as e:
                logger.warning(f"❌ Auth error: {e.message}")
                logger.warning("=" * 70)
                return jsonify({
                    'status': 'error',
                    'message': e.message,
                    'error_code': 'AUTH_FAILED'
                }), e.status_code
            except Exception as e:
                logger.error(f"Unexpected error in auth decorator: {str(e)}", exc_info=True)
                logger.warning("=" * 70)
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
    """
    return getattr(request, 'user', None)