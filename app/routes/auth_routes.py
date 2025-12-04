"""Authentication routes for token generation and management."""

from flask import Blueprint, request, jsonify, current_app
import logging

from app.utils.auth import (
    generate_token,
    validate_token,
    validate_admin_key,
    get_token_from_request,
    AuthError
)
from app import limiter

logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def get_token_service():
    """Get TokenService instance from app context."""
    if not hasattr(current_app, 'token_service'):
        from app.services.token_service import TokenService
        current_app.token_service = TokenService(current_app.db_service)
    return current_app.token_service


def get_lockout_service():
    """Get AuthLockoutService instance from app context."""
    if not hasattr(current_app, 'lockout_service'):
        from app.services.auth_lockout_service import AuthLockoutService
        current_app.lockout_service = AuthLockoutService(current_app.db_service)
    return current_app.lockout_service


def get_client_ip():
    """Get the client's IP address, considering proxy headers."""
    # Check for X-Forwarded-For header (if behind proxy)
    if request.headers.get('X-Forwarded-For'):
        # Get first IP in the chain
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    # Check for X-Real-IP header
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    # Fall back to remote_addr
    else:
        return request.remote_addr


@bp.route('/token', methods=['POST'])
@limiter.limit(lambda: current_app.config.get('RATELIMIT_AUTH_TOKEN', '5 per minute'))
def create_token():
    """
    Generate a new JWT token.
    
    **Security:** Requires admin key in X-Admin-Key header.
    
    **Request:**
```
    POST /api/auth/token
    Headers:
        X-Admin-Key: <your-admin-key>
        Content-Type: application/json
    Body:
        {
            "username": "api_user",           # Required
            "role": "admin",                  # Optional, default: "user"
            "expires_in_hours": 24            # Optional, default from config
        }
```
    
    **Response (200):**
```json
    {
        "status": "success",
        "message": "Token generated successfully",
        "data": {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "expires_at": "2025-10-16T10:30:00Z",
            "username": "api_user",
            "role": "admin"
        }
    }
```
    
    **Example:**
```bash
    curl -X POST http://localhost:5000/api/auth/token \
      -H "Content-Type: application/json" \
      -H "X-Admin-Key: your-admin-key" \
      -d '{
        "username": "john.doe",
        "role": "admin",
        "expires_in_hours": 24
      }'
```
    """
    try:
        # Check if auth is enabled
        if not current_app.config.get('AUTH_ENABLED', False):
            return jsonify({
                'status': 'error',
                'message': 'Authentication is not enabled in this environment. Set AUTH_ENABLED=true in .env'
            }), 400

        # Get client IP for lockout tracking
        client_ip = get_client_ip()
        lockout_service = get_lockout_service()

        # Check if IP is currently locked out
        is_locked, lockout_message = lockout_service.is_locked_out(client_ip)
        if is_locked:
            logger.warning(f"Token generation attempt from locked out IP: {client_ip}")
            return jsonify({
                'status': 'error',
                'message': lockout_message,
                'error_code': 'ACCOUNT_LOCKED'
            }), 429

        # Validate admin key from header
        admin_key = request.headers.get('X-Admin-Key', '')

        if not admin_key:
            logger.warning("Token generation attempted without admin key")
            return jsonify({
                'status': 'error',
                'message': 'Admin key required. Provide X-Admin-Key header.',
                'error_code': 'ADMIN_KEY_REQUIRED'
            }), 401

        if not validate_admin_key(admin_key):
            logger.warning(f"Token generation attempted with invalid admin key from IP {client_ip}")

            # Record failed attempt
            data = request.get_json() or {}
            username = data.get('username', 'unknown')
            was_locked, lockout_msg = lockout_service.record_failed_attempt(client_ip, username)

            if was_locked:
                return jsonify({
                    'status': 'error',
                    'message': lockout_msg,
                    'error_code': 'ACCOUNT_LOCKED'
                }), 429
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid admin key',
                    'error_code': 'INVALID_ADMIN_KEY'
                }), 403
        
        # Parse request body
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body required'
            }), 400
        
        # Extract parameters
        username = data.get('username', '').strip()
        role = data.get('role', 'user').strip()
        expires_in_hours = data.get('expires_in_hours')
        
        # Validate username
        if not username:
            return jsonify({
                'status': 'error',
                'message': 'username is required'
            }), 400
        
        if len(username) < 3 or len(username) > 100:
            return jsonify({
                'status': 'error',
                'message': 'username must be between 3 and 100 characters'
            }), 400
        
        # Validate role
        valid_roles = ['admin', 'user', 'readonly']
        if role not in valid_roles:
            return jsonify({
                'status': 'error',
                'message': f'Invalid role. Must be one of: {", ".join(valid_roles)}'
            }), 400
        
        # Validate expiration
        if expires_in_hours is not None:
            try:
                expires_in_hours = int(expires_in_hours)
                if expires_in_hours < 1 or expires_in_hours > 8760:  # Max 1 year
                    return jsonify({
                        'status': 'error',
                        'message': 'expires_in_hours must be between 1 and 8760 (1 year)'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'status': 'error',
                    'message': 'expires_in_hours must be a valid integer'
                }), 400
        
        # Generate token pair (access + refresh tokens)
        token_service = get_token_service()
        token_data = token_service.generate_token_pair(username, role)

        # Reset failed attempts on successful authentication
        lockout_service.reset_failed_attempts(client_ip)

        logger.info(f"Token pair generated for user '{username}' with role '{role}' from IP {client_ip}")

        return jsonify({
            'status': 'success',
            'message': 'Token pair generated successfully',
            'data': token_data
        }), 200
        
    except AuthError as e:
        return jsonify({
            'status': 'error',
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate token'
        }), 500


@bp.route('/verify', methods=['POST'])
@limiter.limit(lambda: current_app.config.get('RATELIMIT_AUTH_TOKEN', '5 per minute'))
def verify_token_endpoint():
    """
    Verify a JWT token (for testing/debugging).
    
    **Request:**
```
    POST /api/auth/verify
    Content-Type: application/json
    Body:
        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }
```
    
    **Response (200):**
```json
    {
        "status": "success",
        "message": "Token is valid",
        "data": {
            "username": "john.doe",
            "role": "admin",
            "issued_at": "2025-10-14T10:30:00Z",
            "expires_at": "2025-10-15T10:30:00Z"
        }
    }
```
    
    **Example:**
```bash
    curl -X POST http://localhost:5000/api/auth/verify \
      -H "Content-Type: application/json" \
      -d '{"token": "eyJ0eXAiOiJKV1Qi..."}'
```
    """
    try:
        data = request.get_json()
        
        if not data or 'token' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Token required in request body'
            }), 400
        
        token = data['token']
        
        # Validate token
        payload = validate_token(token)
        
        from datetime import datetime
        
        return jsonify({
            'status': 'success',
            'message': 'Token is valid',
            'data': {
                'username': payload.get('username'),
                'role': payload.get('role'),
                'issued_at': datetime.fromtimestamp(payload.get('iat')).isoformat() + 'Z',
                'expires_at': datetime.fromtimestamp(payload.get('exp')).isoformat() + 'Z'
            }
        }), 200
        
    except AuthError as e:
        return jsonify({
            'status': 'error',
            'message': e.message,
            'error_code': 'INVALID_TOKEN'
        }), e.status_code
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Token verification failed'
        }), 500


@bp.route('/status', methods=['GET'])
def auth_status():
    """
    Get authentication status and configuration.

    **Response:**
```json
    {
        "status": "success",
        "data": {
            "auth_enabled": true,
            "access_token_expiration_minutes": 15,
            "refresh_token_expiration_days": 7,
            "refresh_token_rotation_enabled": true,
            "valid_roles": ["admin", "user", "readonly"]
        }
    }
```

    **Example:**
```bash
    curl http://localhost:5000/api/auth/status
```
    """
    try:
        return jsonify({
            'status': 'success',
            'data': {
                'auth_enabled': current_app.config.get('AUTH_ENABLED', False),
                'access_token_expiration_minutes': current_app.config.get('JWT_ACCESS_TOKEN_EXPIRATION_MINUTES', 15),
                'refresh_token_expiration_days': current_app.config.get('JWT_REFRESH_TOKEN_EXPIRATION_DAYS', 7),
                'refresh_token_rotation_enabled': current_app.config.get('REFRESH_TOKEN_ROTATION_ENABLED', True),
                'token_expiration_hours': current_app.config.get('JWT_EXPIRATION_HOURS', 24),  # Legacy
                'valid_roles': ['admin', 'user', 'readonly']
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting auth status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/refresh', methods=['POST'])
@limiter.limit(lambda: current_app.config.get('RATELIMIT_AUTH_REFRESH', '10 per minute'))
def refresh_token():
    """
    Refresh access token using refresh token.

    **Request:**
```
    POST /api/auth/refresh
    Content-Type: application/json
    Body:
        {
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }
```

    **Response (200):**
```json
    {
        "status": "success",
        "message": "Token refreshed successfully",
        "data": {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",  // New refresh token (if rotation enabled)
            "token_type": "Bearer",
            "access_token_expires_in": 900,
            "refresh_token_expires_in": 604800,
            "username": "john.doe",
            "role": "admin"
        }
    }
```

    **Example:**
```bash
    curl -X POST http://localhost:5000/api/auth/refresh \
      -H "Content-Type: application/json" \
      -d '{"refresh_token": "eyJ0eXAiOiJKV1Qi..."}'
```
    """
    try:
        data = request.get_json()

        if not data or 'refresh_token' not in data:
            return jsonify({
                'status': 'error',
                'message': 'refresh_token required in request body'
            }), 400

        refresh_token_str = data['refresh_token']

        # Use TokenService to refresh the token
        token_service = get_token_service()
        new_tokens, error = token_service.refresh_access_token(refresh_token_str)

        if error:
            logger.warning(f"Token refresh failed: {error}")
            return jsonify({
                'status': 'error',
                'message': error,
                'error_code': 'REFRESH_FAILED'
            }), 401

        logger.info(f"Token refreshed for user '{new_tokens['username']}'")

        return jsonify({
            'status': 'success',
            'message': 'Token refreshed successfully',
            'data': new_tokens
        }), 200

    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Token refresh failed'
        }), 500


@bp.route('/revoke', methods=['POST'])
@limiter.limit(lambda: current_app.config.get('RATELIMIT_AUTH_TOKEN', '5 per minute'))
def revoke_token():
    """
    Revoke a token (access or refresh).

    **Request:**
```
    POST /api/auth/revoke
    Content-Type: application/json
    Body:
        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "token_type": "refresh"  // or "access"
        }
```

    **Response (200):**
```json
    {
        "status": "success",
        "message": "Token revoked successfully"
    }
```

    **Example:**
```bash
    curl -X POST http://localhost:5000/api/auth/revoke \
      -H "Content-Type: application/json" \
      -d '{
        "token": "eyJ0eXAiOiJKV1Qi...",
        "token_type": "refresh"
      }'
```
    """
    try:
        data = request.get_json()

        if not data or 'token' not in data:
            return jsonify({
                'status': 'error',
                'message': 'token required in request body'
            }), 400

        token = data['token']
        token_type = data.get('token_type', 'refresh')

        if token_type not in ['access', 'refresh']:
            return jsonify({
                'status': 'error',
                'message': 'token_type must be "access" or "refresh"'
            }), 400

        # Revoke the token
        token_service = get_token_service()

        if token_type == 'refresh':
            success, error = token_service.revoke_refresh_token(token)
        else:
            success, error = token_service.revoke_access_token(token)

        if not success:
            logger.warning(f"Token revocation failed: {error}")
            return jsonify({
                'status': 'error',
                'message': error or 'Token revocation failed',
                'error_code': 'REVOKE_FAILED'
            }), 400

        logger.info(f"{token_type.capitalize()} token revoked successfully")

        return jsonify({
            'status': 'success',
            'message': f'{token_type.capitalize()} token revoked successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error revoking token: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Token revocation failed'
        }), 500


@bp.route('/logout', methods=['POST'])
@limiter.limit(lambda: current_app.config.get('RATELIMIT_AUTH_TOKEN', '5 per minute'))
def logout():
    """
    Logout user by revoking all their tokens.

    **Request:**
```
    POST /api/auth/logout
    Headers:
        Authorization: Bearer <access_token>
    Content-Type: application/json
    Body:
        {
            "revoke_all": true  // Optional: revoke all refresh tokens for user
        }
```

    **Response (200):**
```json
    {
        "status": "success",
        "message": "Logged out successfully",
        "data": {
            "tokens_revoked": 3
        }
    }
```

    **Example:**
```bash
    curl -X POST http://localhost:5000/api/auth/logout \
      -H "Authorization: Bearer eyJ0eXAiOiJKV1Qi..." \
      -H "Content-Type: application/json" \
      -d '{"revoke_all": true}'
```
    """
    try:
        # Get access token from Authorization header
        access_token = get_token_from_request()

        if not access_token:
            return jsonify({
                'status': 'error',
                'message': 'Access token required in Authorization header'
            }), 401

        # Validate and extract username from access token
        try:
            payload = validate_token(access_token)
            username = payload.get('username')
        except AuthError as e:
            return jsonify({
                'status': 'error',
                'message': e.message
            }), 401

        data = request.get_json() or {}
        revoke_all = data.get('revoke_all', True)

        token_service = get_token_service()

        # Revoke current access token
        token_service.revoke_access_token(access_token)

        tokens_revoked = 1

        # Revoke all refresh tokens for user if requested
        if revoke_all:
            count, error = token_service.revoke_all_user_tokens(username)
            if error:
                logger.warning(f"Error revoking user tokens: {error}")
            else:
                tokens_revoked += count

        logger.info(f"User '{username}' logged out, {tokens_revoked} token(s) revoked")

        return jsonify({
            'status': 'success',
            'message': 'Logged out successfully',
            'data': {
                'tokens_revoked': tokens_revoked
            }
        }), 200

    except Exception as e:
        logger.error(f"Error during logout: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Logout failed'
        }), 500