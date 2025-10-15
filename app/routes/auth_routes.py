"""Authentication routes for token generation and management."""

from flask import Blueprint, request, jsonify, current_app
import logging

from app.utils.auth import (
    generate_token,
    validate_token,
    validate_admin_key,
    AuthError
)

logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.route('/token', methods=['POST'])
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
            logger.warning("Token generation attempted with invalid admin key")
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
        
        # Generate token
        token_data = generate_token(username, role, expires_in_hours)
        
        logger.info(f"Token generated for user '{username}' with role '{role}'")
        
        return jsonify({
            'status': 'success',
            'message': 'Token generated successfully',
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
            "token_expiration_hours": 24,
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
                'token_expiration_hours': current_app.config.get('JWT_EXPIRATION_HOURS', 24),
                'valid_roles': ['admin', 'user', 'readonly']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting auth status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500