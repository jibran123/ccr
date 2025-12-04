"""
Token Service for managing access and refresh tokens.

This module provides:
- Access token generation (short-lived, 15 minutes)
- Refresh token generation (long-lived, 7 days)
- Token refresh with rotation
- Token blacklist/revocation
- Token storage in MongoDB
"""

import jwt
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from flask import current_app

logger = logging.getLogger(__name__)


class TokenService:
    """Service for managing JWT access and refresh tokens."""

    def __init__(self, db_service):
        """
        Initialize TokenService.

        Args:
            db_service: DatabaseService instance for MongoDB operations
        """
        self.db = db_service
        self.db_client = db_service.client
        self.db_name = db_service.db_name

        # Collections
        self.refresh_tokens_collection = self.db_client[self.db_name]['refresh_tokens']
        self.blacklist_collection = self.db_client[self.db_name]['token_blacklist']

        # Ensure indexes
        self._ensure_indexes()

        logger.info("TokenService initialized")

    def _ensure_indexes(self):
        """Create indexes for token collections."""
        try:
            # Refresh tokens indexes
            self.refresh_tokens_collection.create_index('token_id', unique=True)
            self.refresh_tokens_collection.create_index('username')
            self.refresh_tokens_collection.create_index('expires_at')

            # TTL index: auto-delete expired refresh tokens after 1 day grace period
            self.refresh_tokens_collection.create_index(
                'expires_at',
                expireAfterSeconds=86400  # 24 hours
            )

            # Blacklist indexes
            self.blacklist_collection.create_index('token_jti', unique=True)
            self.blacklist_collection.create_index('expires_at')

            # TTL index: auto-delete expired blacklisted tokens
            self.blacklist_collection.create_index(
                'expires_at',
                expireAfterSeconds=0
            )

            logger.info("Token collection indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating token indexes: {e}")

    def generate_access_token(self, username: str, role: str = 'user') -> Dict[str, Any]:
        """
        Generate a short-lived access token (15 minutes).

        Args:
            username: Username/identifier
            role: User role (e.g., 'admin', 'user', 'readonly')

        Returns:
            Dictionary containing token, expires_at, username, role
        """
        try:
            secret_key = current_app.config.get('JWT_SECRET_KEY')
            algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')
            expires_in_minutes = current_app.config.get('JWT_ACCESS_TOKEN_EXPIRATION_MINUTES', 15)

            # Calculate expiration time
            expiration = datetime.utcnow() + timedelta(minutes=expires_in_minutes)

            # Generate unique JTI (JWT ID) for blacklist tracking
            jti = secrets.token_urlsafe(32)

            # Build JWT payload
            payload = {
                'username': username,
                'role': role,
                'token_type': 'access',
                'jti': jti,
                'iat': datetime.utcnow(),
                'exp': expiration,
                'iss': 'ccr'
            }

            # Generate token
            token = jwt.encode(payload, secret_key, algorithm=algorithm)

            logger.info(
                f"Generated access token for user '{username}' with role '{role}', "
                f"expires at {expiration.isoformat()} (JTI: {jti[:10]}...)"
            )

            return {
                'token': token,
                'token_type': 'access',
                'expires_at': expiration.isoformat() + 'Z',
                'expires_in': expires_in_minutes * 60,  # seconds
                'username': username,
                'role': role
            }

        except Exception as e:
            logger.error(f"Error generating access token: {str(e)}")
            raise

    def generate_refresh_token(self, username: str, role: str = 'user') -> Dict[str, Any]:
        """
        Generate a long-lived refresh token (7 days) and store in MongoDB.

        Args:
            username: Username/identifier
            role: User role

        Returns:
            Dictionary containing token, token_id, expires_at, username, role
        """
        try:
            secret_key = current_app.config.get('JWT_SECRET_KEY')
            algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')
            expires_in_days = current_app.config.get('JWT_REFRESH_TOKEN_EXPIRATION_DAYS', 7)

            # Calculate expiration time
            expiration = datetime.utcnow() + timedelta(days=expires_in_days)

            # Generate unique token ID
            token_id = secrets.token_urlsafe(32)

            # Build JWT payload
            payload = {
                'username': username,
                'role': role,
                'token_type': 'refresh',
                'token_id': token_id,
                'iat': datetime.utcnow(),
                'exp': expiration,
                'iss': 'ccr'
            }

            # Generate token
            token = jwt.encode(payload, secret_key, algorithm=algorithm)

            # Store refresh token in MongoDB
            token_doc = {
                'token_id': token_id,
                'username': username,
                'role': role,
                'created_at': datetime.utcnow(),
                'expires_at': expiration,
                'revoked': False,
                'used_at': None
            }

            self.refresh_tokens_collection.insert_one(token_doc)

            logger.info(
                f"Generated refresh token for user '{username}', "
                f"expires at {expiration.isoformat()} (Token ID: {token_id[:10]}...)"
            )

            return {
                'token': token,
                'token_type': 'refresh',
                'token_id': token_id,
                'expires_at': expiration.isoformat() + 'Z',
                'expires_in': expires_in_days * 24 * 60 * 60,  # seconds
                'username': username,
                'role': role
            }

        except Exception as e:
            logger.error(f"Error generating refresh token: {str(e)}")
            raise

    def generate_token_pair(self, username: str, role: str = 'user') -> Dict[str, Any]:
        """
        Generate both access and refresh tokens.

        Args:
            username: Username/identifier
            role: User role

        Returns:
            Dictionary containing access_token, refresh_token, and metadata
        """
        access_token_data = self.generate_access_token(username, role)
        refresh_token_data = self.generate_refresh_token(username, role)

        return {
            'access_token': access_token_data['token'],
            'refresh_token': refresh_token_data['token'],
            'token_type': 'Bearer',
            'access_token_expires_in': access_token_data['expires_in'],
            'refresh_token_expires_in': refresh_token_data['expires_in'],
            'username': username,
            'role': role
        }

    def refresh_access_token(self, refresh_token: str) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Use refresh token to get new access token and optionally new refresh token.

        Implements token rotation: old refresh token is revoked, new one issued.

        Args:
            refresh_token: JWT refresh token string

        Returns:
            Tuple of (new_tokens_dict, error_message)
            - new_tokens_dict: Contains new access_token and optionally refresh_token
            - error_message: Error message if validation fails, None otherwise
        """
        try:
            # Decode and validate refresh token
            secret_key = current_app.config.get('JWT_SECRET_KEY')
            algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')

            payload = jwt.decode(
                refresh_token,
                secret_key,
                algorithms=[algorithm],
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'require': ['username', 'role', 'token_id', 'token_type']
                }
            )

            # Verify token type
            if payload.get('token_type') != 'refresh':
                logger.warning(f"Invalid token type: {payload.get('token_type')}")
                return None, "Invalid token type"

            token_id = payload.get('token_id')
            username = payload.get('username')
            role = payload.get('role')

            # Check if token exists in database and is not revoked
            token_doc = self.refresh_tokens_collection.find_one({'token_id': token_id})

            if not token_doc:
                logger.warning(f"Refresh token not found: {token_id[:10]}...")
                return None, "Invalid refresh token"

            if token_doc.get('revoked'):
                logger.warning(f"Refresh token has been revoked: {token_id[:10]}...")
                return None, "Refresh token has been revoked"

            # Generate new access token
            new_access_token = self.generate_access_token(username, role)

            result = {
                'access_token': new_access_token['token'],
                'token_type': 'Bearer',
                'access_token_expires_in': new_access_token['expires_in'],
                'username': username,
                'role': role
            }

            # Token rotation: generate new refresh token if enabled
            rotation_enabled = current_app.config.get('REFRESH_TOKEN_ROTATION_ENABLED', True)

            if rotation_enabled:
                # Revoke old refresh token
                self.refresh_tokens_collection.update_one(
                    {'token_id': token_id},
                    {
                        '$set': {
                            'revoked': True,
                            'used_at': datetime.utcnow()
                        }
                    }
                )

                # Generate new refresh token
                new_refresh_token = self.generate_refresh_token(username, role)
                result['refresh_token'] = new_refresh_token['token']
                result['refresh_token_expires_in'] = new_refresh_token['expires_in']

                logger.info(
                    f"Token rotation: Revoked old refresh token {token_id[:10]}..., "
                    f"issued new refresh token {new_refresh_token['token_id'][:10]}..."
                )
            else:
                # Just mark as used
                self.refresh_tokens_collection.update_one(
                    {'token_id': token_id},
                    {'$set': {'used_at': datetime.utcnow()}}
                )

            logger.info(f"Refreshed access token for user '{username}'")

            return result, None

        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token has expired")
            return None, "Refresh token has expired"
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {str(e)}")
            return None, "Invalid refresh token"
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return None, "Token refresh failed"

    def revoke_refresh_token(self, refresh_token: str) -> Tuple[bool, Optional[str]]:
        """
        Revoke a refresh token.

        Args:
            refresh_token: JWT refresh token string

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Decode token to get token_id
            secret_key = current_app.config.get('JWT_SECRET_KEY')
            algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')

            payload = jwt.decode(
                refresh_token,
                secret_key,
                algorithms=[algorithm],
                options={'verify_signature': True}
            )

            token_id = payload.get('token_id')

            if not token_id:
                return False, "Invalid token format"

            # Mark as revoked
            result = self.refresh_tokens_collection.update_one(
                {'token_id': token_id},
                {
                    '$set': {
                        'revoked': True,
                        'revoked_at': datetime.utcnow()
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"Revoked refresh token: {token_id[:10]}...")
                return True, None
            else:
                logger.warning(f"Refresh token not found or already revoked: {token_id[:10]}...")
                return False, "Token not found or already revoked"

        except Exception as e:
            logger.error(f"Error revoking refresh token: {str(e)}")
            return False, f"Failed to revoke token: {str(e)}"

    def revoke_access_token(self, access_token: str) -> Tuple[bool, Optional[str]]:
        """
        Revoke an access token by adding it to blacklist.

        Args:
            access_token: JWT access token string

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Decode token to get JTI and expiration
            secret_key = current_app.config.get('JWT_SECRET_KEY')
            algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')

            payload = jwt.decode(
                access_token,
                secret_key,
                algorithms=[algorithm],
                options={'verify_signature': True}
            )

            jti = payload.get('jti')
            exp = payload.get('exp')

            if not jti:
                return False, "Invalid token format"

            # Add to blacklist (expires when token would expire)
            expiration = datetime.utcfromtimestamp(exp)

            blacklist_doc = {
                'token_jti': jti,
                'blacklisted_at': datetime.utcnow(),
                'expires_at': expiration,
                'username': payload.get('username')
            }

            try:
                self.blacklist_collection.insert_one(blacklist_doc)
                logger.info(f"Blacklisted access token: JTI {jti[:10]}...")
                return True, None
            except Exception as e:
                # Token might already be blacklisted
                logger.warning(f"Token already blacklisted or error: {str(e)}")
                return True, None  # Consider already blacklisted as success

        except Exception as e:
            logger.error(f"Error blacklisting access token: {str(e)}")
            return False, f"Failed to blacklist token: {str(e)}"

    def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if an access token is blacklisted.

        Args:
            jti: JWT ID from token payload

        Returns:
            True if blacklisted, False otherwise
        """
        try:
            doc = self.blacklist_collection.find_one({'token_jti': jti})
            return doc is not None
        except Exception as e:
            logger.error(f"Error checking token blacklist: {str(e)}")
            return False

    def revoke_all_user_tokens(self, username: str) -> Tuple[int, Optional[str]]:
        """
        Revoke all refresh tokens for a user (e.g., on password change, logout all devices).

        Args:
            username: Username

        Returns:
            Tuple of (count_revoked, error_message)
        """
        try:
            result = self.refresh_tokens_collection.update_many(
                {'username': username, 'revoked': False},
                {
                    '$set': {
                        'revoked': True,
                        'revoked_at': datetime.utcnow()
                    }
                }
            )

            count = result.modified_count
            logger.info(f"Revoked {count} refresh token(s) for user '{username}'")

            return count, None

        except Exception as e:
            logger.error(f"Error revoking user tokens: {str(e)}")
            return 0, f"Failed to revoke tokens: {str(e)}"

    def cleanup_expired_tokens(self) -> Dict[str, int]:
        """
        Manual cleanup of expired tokens (TTL indexes should handle this automatically).

        Returns:
            Dictionary with count of deleted refresh_tokens and blacklisted tokens
        """
        try:
            now = datetime.utcnow()

            # Delete expired refresh tokens
            refresh_result = self.refresh_tokens_collection.delete_many(
                {'expires_at': {'$lt': now}}
            )

            # Delete expired blacklisted tokens
            blacklist_result = self.blacklist_collection.delete_many(
                {'expires_at': {'$lt': now}}
            )

            logger.info(
                f"Cleanup: Deleted {refresh_result.deleted_count} expired refresh tokens, "
                f"{blacklist_result.deleted_count} expired blacklist entries"
            )

            return {
                'refresh_tokens_deleted': refresh_result.deleted_count,
                'blacklist_entries_deleted': blacklist_result.deleted_count
            }

        except Exception as e:
            logger.error(f"Error during token cleanup: {str(e)}")
            return {'refresh_tokens_deleted': 0, 'blacklist_entries_deleted': 0}

    def get_user_active_tokens(self, username: str) -> list:
        """
        Get all active (non-revoked) refresh tokens for a user.

        Args:
            username: Username

        Returns:
            List of token documents (without token value, just metadata)
        """
        try:
            tokens = self.refresh_tokens_collection.find(
                {'username': username, 'revoked': False}
            ).sort('created_at', -1)

            result = []
            for token in tokens:
                result.append({
                    'token_id': token['token_id'][:10] + '...',  # Truncated for security
                    'created_at': token['created_at'].isoformat() + 'Z',
                    'expires_at': token['expires_at'].isoformat() + 'Z',
                    'used_at': token['used_at'].isoformat() + 'Z' if token.get('used_at') else None
                })

            return result

        except Exception as e:
            logger.error(f"Error fetching user tokens: {str(e)}")
            return []
