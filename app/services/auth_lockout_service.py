"""
Authentication Lockout Service for CCR API Manager.

Provides brute force protection by tracking failed authentication attempts
and temporarily locking out IPs that exceed the failure threshold.

Week 11-12: Security Enhancements - Brute Force Protection
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from flask import current_app

logger = logging.getLogger(__name__)


class AuthLockoutService:
    """Service for managing authentication lockouts and failed attempt tracking."""

    def __init__(self, db_service):
        """
        Initialize the Auth Lockout Service.

        Args:
            db_service: DatabaseService instance for MongoDB operations
        """
        self.db = db_service
        self.collection_name = 'auth_lockouts'
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create necessary indexes for the auth_lockouts collection."""
        try:
            collection = self.db.client[self.db.db_name][self.collection_name]

            # Index on ip_address for fast lookups
            collection.create_index('ip_address', unique=True)

            # TTL index to auto-delete old lockout records after they expire
            # Documents expire 1 hour after locked_until time
            collection.create_index(
                'locked_until',
                expireAfterSeconds=3600,  # 1 hour after lockout expires
                partialFilterExpression={'locked_until': {'$exists': True}}
            )

            logger.info(f"✅ Indexes created for {self.collection_name} collection")

        except Exception as e:
            logger.warning(f"Could not create indexes for {self.collection_name}: {str(e)}")

    def is_locked_out(self, ip_address: str) -> Tuple[bool, Optional[str]]:
        """
        Check if an IP address is currently locked out.

        Args:
            ip_address: IP address to check

        Returns:
            Tuple of (is_locked, reason_message)
        """
        if not current_app.config.get('AUTH_LOCKOUT_ENABLED', True):
            return False, None

        try:
            collection = self.db.client[self.db.db_name][self.collection_name]

            lockout_record = collection.find_one({'ip_address': ip_address})

            if not lockout_record:
                return False, None

            # Check if currently locked out
            locked_until = lockout_record.get('locked_until')
            if locked_until and locked_until > datetime.utcnow():
                time_remaining = int((locked_until - datetime.utcnow()).total_seconds() / 60)
                message = f"Too many failed authentication attempts. Please try again in {time_remaining} minutes."
                logger.warning(f"IP {ip_address} is locked out until {locked_until.isoformat()}")
                return True, message

            return False, None

        except Exception as e:
            logger.error(f"Error checking lockout status for {ip_address}: {str(e)}")
            # Fail open - don't block on error
            return False, None

    def record_failed_attempt(self, ip_address: str, username: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Record a failed authentication attempt.

        If the number of failed attempts exceeds the threshold within the time window,
        the IP will be locked out.

        Args:
            ip_address: IP address of the failed attempt
            username: Optional username that was attempted

        Returns:
            Tuple of (was_locked_out, lockout_message)
        """
        if not current_app.config.get('AUTH_LOCKOUT_ENABLED', True):
            return False, None

        try:
            collection = self.db.client[self.db.db_name][self.collection_name]

            max_attempts = current_app.config.get('AUTH_LOCKOUT_MAX_ATTEMPTS', 5)
            window_minutes = current_app.config.get('AUTH_LOCKOUT_WINDOW_MINUTES', 15)
            lockout_duration = current_app.config.get('AUTH_LOCKOUT_DURATION_MINUTES', 30)

            now = datetime.utcnow()
            window_start = now - timedelta(minutes=window_minutes)

            # Get existing record
            lockout_record = collection.find_one({'ip_address': ip_address})

            if lockout_record:
                first_attempt = lockout_record.get('first_attempt_time', now)
                failed_attempts = lockout_record.get('failed_attempts', 0)

                # Check if we're within the time window
                if first_attempt < window_start:
                    # Outside window - reset counter
                    failed_attempts = 1
                    first_attempt = now
                else:
                    # Within window - increment counter
                    failed_attempts += 1

                # Check if we should lock out
                if failed_attempts >= max_attempts:
                    locked_until = now + timedelta(minutes=lockout_duration)

                    collection.update_one(
                        {'ip_address': ip_address},
                        {
                            '$set': {
                                'failed_attempts': failed_attempts,
                                'first_attempt_time': first_attempt,
                                'last_attempt_time': now,
                                'locked_until': locked_until,
                                'last_attempted_username': username
                            }
                        }
                    )

                    logger.warning(
                        f"IP {ip_address} locked out after {failed_attempts} failed attempts. "
                        f"Locked until {locked_until.isoformat()}"
                    )

                    time_remaining = lockout_duration
                    message = f"Too many failed authentication attempts. Account locked for {time_remaining} minutes."
                    return True, message
                else:
                    # Update failed attempt count
                    collection.update_one(
                        {'ip_address': ip_address},
                        {
                            '$set': {
                                'failed_attempts': failed_attempts,
                                'first_attempt_time': first_attempt,
                                'last_attempt_time': now,
                                'last_attempted_username': username
                            }
                        }
                    )

                    logger.info(f"Failed attempt {failed_attempts}/{max_attempts} recorded for IP {ip_address}")
                    return False, None
            else:
                # First failed attempt
                collection.insert_one({
                    'ip_address': ip_address,
                    'failed_attempts': 1,
                    'first_attempt_time': now,
                    'last_attempt_time': now,
                    'last_attempted_username': username
                })

                logger.info(f"First failed attempt recorded for IP {ip_address}")
                return False, None

        except Exception as e:
            logger.error(f"Error recording failed attempt for {ip_address}: {str(e)}")
            return False, None

    def reset_failed_attempts(self, ip_address: str):
        """
        Reset failed attempt counter for an IP (called on successful authentication).

        Args:
            ip_address: IP address to reset
        """
        if not current_app.config.get('AUTH_LOCKOUT_ENABLED', True):
            return

        try:
            collection = self.db.client[self.db.db_name][self.collection_name]

            result = collection.delete_one({'ip_address': ip_address})

            if result.deleted_count > 0:
                logger.info(f"Failed attempt counter reset for IP {ip_address} after successful auth")

        except Exception as e:
            logger.error(f"Error resetting failed attempts for {ip_address}: {str(e)}")

    def get_lockout_info(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """
        Get lockout information for an IP address (for admin monitoring).

        Args:
            ip_address: IP address to check

        Returns:
            Dictionary with lockout info or None if no record exists
        """
        try:
            collection = self.db.client[self.db.db_name][self.collection_name]

            lockout_record = collection.find_one({'ip_address': ip_address})

            if not lockout_record:
                return None

            # Remove MongoDB _id field
            lockout_record.pop('_id', None)

            # Convert datetime objects to ISO strings
            for field in ['first_attempt_time', 'last_attempt_time', 'locked_until']:
                if field in lockout_record and lockout_record[field]:
                    lockout_record[field] = lockout_record[field].isoformat() + 'Z'

            # Add status
            locked_until = lockout_record.get('locked_until')
            if locked_until:
                lockout_record['is_currently_locked'] = locked_until > datetime.utcnow().isoformat() + 'Z'
            else:
                lockout_record['is_currently_locked'] = False

            return lockout_record

        except Exception as e:
            logger.error(f"Error getting lockout info for {ip_address}: {str(e)}")
            return None

    def get_all_lockouts(self, limit: int = 100) -> list:
        """
        Get all current lockout records (for admin monitoring).

        Args:
            limit: Maximum number of records to return

        Returns:
            List of lockout records
        """
        try:
            collection = self.db.client[self.db.db_name][self.collection_name]

            records = list(collection.find().sort('last_attempt_time', -1).limit(limit))

            # Process records
            for record in records:
                record.pop('_id', None)

                # Convert datetime objects to ISO strings
                for field in ['first_attempt_time', 'last_attempt_time', 'locked_until']:
                    if field in record and record[field]:
                        record[field] = record[field].isoformat() + 'Z'

                # Add status
                locked_until_str = record.get('locked_until')
                if locked_until_str:
                    record['is_currently_locked'] = locked_until_str > datetime.utcnow().isoformat() + 'Z'
                else:
                    record['is_currently_locked'] = False

            return records

        except Exception as e:
            logger.error(f"Error getting all lockouts: {str(e)}")
            return []

    def manually_unlock(self, ip_address: str) -> Tuple[bool, str]:
        """
        Manually unlock an IP address (admin function).

        Args:
            ip_address: IP address to unlock

        Returns:
            Tuple of (success, message)
        """
        try:
            collection = self.db.client[self.db.db_name][self.collection_name]

            result = collection.delete_one({'ip_address': ip_address})

            if result.deleted_count > 0:
                logger.info(f"IP {ip_address} manually unlocked by admin")
                return True, f"IP {ip_address} has been unlocked"
            else:
                return False, f"No lockout record found for IP {ip_address}"

        except Exception as e:
            logger.error(f"Error manually unlocking {ip_address}: {str(e)}")
            return False, f"Error unlocking IP: {str(e)}"
