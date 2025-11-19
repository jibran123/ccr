import os
from datetime import timedelta

class Config:
    """Application configuration."""
    
    # Application Configuration
    APP_NAME = "CCR API Manager"
    APP_VERSION = "2.0.0"
    
    # Flask Configuration
    # Environment detection
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')

    # SECRET_KEY - REQUIRED in production, defaults for development only
    if FLASK_ENV == 'production':
        SECRET_KEY = os.getenv('SECRET_KEY')
        if not SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
    else:
        SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-ONLY-FOR-DEVELOPMENT')

    # DEBUG mode - only allow in development
    DEBUG = FLASK_ENV == 'development' and os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    if FLASK_ENV == 'production' and DEBUG:
        raise RuntimeError("DEBUG mode cannot be enabled in production environment!")

    # MongoDB Configuration
    MONGO_HOST = os.getenv('MONGO_HOST', 'mongo')
    MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
    MONGO_DB = os.getenv('MONGO_DB', 'ccr')
    MONGO_COLLECTION = os.getenv('MONGO_COLLECTION', 'apis')

    # MongoDB authentication - optional for development, recommended for production
    MONGO_USER = os.getenv('MONGO_USER', '')
    MONGO_PASS = os.getenv('MONGO_PASS', '')

    if MONGO_USER and MONGO_PASS:
        # Use authentication
        MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
    else:
        # No authentication (development only)
        MONGO_URI = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
        if FLASK_ENV == 'production':
            import logging
            logging.warning("⚠️  MongoDB authentication not configured. Set MONGO_USER and MONGO_PASS for production.")
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 500
    
    # CORS Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # ==================== AUTHENTICATION CONFIGURATION ====================
    # JWT Authentication Settings

    # Feature flag - Enable/disable authentication
    # SECURITY: Authentication is ENABLED by default. Explicitly disable for development only.
    AUTH_ENABLED = os.getenv('AUTH_ENABLED', 'true').lower() == 'true'

    # JWT Secret Key - REQUIRED in production
    if FLASK_ENV == 'production':
        JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
        if not JWT_SECRET_KEY:
            raise RuntimeError(
                "JWT_SECRET_KEY environment variable must be set in production. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
    else:
        JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-ONLY-FOR-DEVELOPMENT')
    
    # JWT Token expiration
    # Access tokens: short-lived for API operations
    JWT_ACCESS_TOKEN_EXPIRATION_MINUTES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRATION_MINUTES') or 15)

    # Refresh tokens: long-lived for obtaining new access tokens
    JWT_REFRESH_TOKEN_EXPIRATION_DAYS = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRATION_DAYS') or 7)

    # Legacy support (deprecated - use JWT_ACCESS_TOKEN_EXPIRATION_MINUTES instead)
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS') or 24)

    # JWT Algorithm
    JWT_ALGORITHM = 'HS256'

    # Admin key for initial token generation - REQUIRED in production
    if FLASK_ENV == 'production':
        JWT_ADMIN_KEY = os.getenv('JWT_ADMIN_KEY')
        if not JWT_ADMIN_KEY:
            raise RuntimeError(
                "JWT_ADMIN_KEY environment variable must be set in production. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
    else:
        JWT_ADMIN_KEY = os.getenv('JWT_ADMIN_KEY', 'dev-admin-key-ONLY-FOR-DEVELOPMENT')

    # Token prefix for Authorization header
    AUTH_HEADER_PREFIX = 'Bearer'

    # Token refresh settings
    REFRESH_TOKEN_ROTATION_ENABLED = os.getenv('REFRESH_TOKEN_ROTATION_ENABLED', 'true').lower() == 'true'

    # Brute force protection settings
    AUTH_LOCKOUT_ENABLED = os.getenv('AUTH_LOCKOUT_ENABLED', 'true').lower() == 'true'
    AUTH_LOCKOUT_MAX_ATTEMPTS = int(os.getenv('AUTH_LOCKOUT_MAX_ATTEMPTS') or 5)
    AUTH_LOCKOUT_WINDOW_MINUTES = int(os.getenv('AUTH_LOCKOUT_WINDOW_MINUTES') or 15)
    AUTH_LOCKOUT_DURATION_MINUTES = int(os.getenv('AUTH_LOCKOUT_DURATION_MINUTES') or 30)

    # Endpoints that are always public (no authentication required)
    PUBLIC_ENDPOINTS = [
        '/health',
        '/health/ready',
        '/health/live',
        '/health/metrics',
        '/',
        '/search',
        '/static/',
        '/api/auth/token',
        '/api/auth/verify',
        '/api/auth/status',
        '/api/auth/refresh',
        '/api/auth/revoke',
        '/api/auth/logout',
    ]
    
    @staticmethod
    def is_public_endpoint(path: str) -> bool:
        """
        Check if an endpoint is public (no authentication required).
        
        Args:
            path: Request path (e.g., '/api/search', '/health')
            
        Returns:
            True if endpoint is public, False if authentication required
        """
        # Special case: exact match for root path
        if path == '/' or path == '/search':
            return True
        
        # Check other public endpoints
        for public_path in Config.PUBLIC_ENDPOINTS:
            if public_path in ['/', '/search']:
                continue
            
            if path.startswith(public_path):
                return True
        
        return False
    
    # ==================== RATE LIMITING CONFIGURATION ====================
    # Rate Limiting Settings
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'true').lower() == 'true'

    # Storage backend for rate limiting
    # Options: 'memory://' (development) or 'redis://localhost:6379' (production)
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')

    # Default rate limits (applies to all endpoints unless overridden)
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '100 per hour, 20 per minute')

    # Per-endpoint rate limits
    RATELIMIT_AUTH_TOKEN = os.getenv('RATELIMIT_AUTH_TOKEN', '5 per minute')
    RATELIMIT_AUTH_REFRESH = os.getenv('RATELIMIT_AUTH_REFRESH', '10 per minute')
    RATELIMIT_SEARCH = os.getenv('RATELIMIT_SEARCH', '60 per minute')
    RATELIMIT_AUDIT_LOGS = os.getenv('RATELIMIT_AUDIT_LOGS', '30 per minute')
    RATELIMIT_AUDIT_STATS = os.getenv('RATELIMIT_AUDIT_STATS', '20 per minute')
    RATELIMIT_WRITE_OPS = os.getenv('RATELIMIT_WRITE_OPS', '20 per minute')
    RATELIMIT_HEALTH = os.getenv('RATELIMIT_HEALTH', '60 per minute')

    # Rate limit headers
    RATELIMIT_HEADERS_ENABLED = os.getenv('RATELIMIT_HEADERS_ENABLED', 'true').lower() == 'true'

    # ==================== SECURITY HEADERS CONFIGURATION ====================
    # Security Headers Settings
    SECURITY_HEADERS_ENABLED = os.getenv('SECURITY_HEADERS_ENABLED', 'true').lower() == 'true'

    # Force HTTPS (disable in development, enable in production)
    FORCE_HTTPS = os.getenv('FORCE_HTTPS', 'false').lower() == 'true'

    # HTTP Strict Transport Security (HSTS)
    HSTS_ENABLED = os.getenv('HSTS_ENABLED', 'true').lower() == 'true'
    HSTS_MAX_AGE = int(os.getenv('HSTS_MAX_AGE', 31536000))  # 1 year
    HSTS_INCLUDE_SUBDOMAINS = os.getenv('HSTS_INCLUDE_SUBDOMAINS', 'true').lower() == 'true'
    HSTS_PRELOAD = os.getenv('HSTS_PRELOAD', 'false').lower() == 'true'

    # Content Security Policy (CSP)
    CSP_ENABLED = os.getenv('CSP_ENABLED', 'true').lower() == 'true'

    # ==================== BACKUP CONFIGURATION ====================
    # Backup settings
    BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'true').lower() == 'true'
    BACKUP_DIR = os.getenv('BACKUP_DIR') or '/app/backups'
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS') or 14)
    BACKUP_COMPRESSION = os.getenv('BACKUP_COMPRESSION', 'true').lower() == 'true'

    # Backup schedule
    BACKUP_SCHEDULE_HOUR = int(os.getenv('BACKUP_SCHEDULE_HOUR') or 2)
    BACKUP_SCHEDULE_MINUTE = int(os.getenv('BACKUP_SCHEDULE_MINUTE') or 0)
    
    # ==================== DEPLOYMENT CONFIGURATION ====================
    # Platform Mapping
    PLATFORM_MAPPING = {
        'IP2': 'IP2 Platform',
        'IP3': 'IP3 Platform',
        'IP4': 'IP4 Platform',
        'IP5': 'IP5 Platform',
        'IP6': 'IP6 Platform',
        'IP7': 'IP7 Platform',
        'OpenShift': 'OpenShift Container Platform',
        'Kubernetes': 'Kubernetes',
        'Docker': 'Docker',
        'AWS': 'Amazon Web Services',
        'Azure': 'Microsoft Azure',
        'GCP': 'Google Cloud Platform',
        'Alibaba': 'Alibaba Cloud'
    }
    
    # Environment Mapping
    ENVIRONMENT_MAPPING = {
        'dev': 'Development',
        'tst': 'Test',
        'acc': 'Acceptance',
        'stg': 'Staging',
        'prd': 'Production',
        'prd-uitwijk': 'Production Uitwijk / Fallback',
        'dr': 'Disaster Recovery',
        'uat': 'User Acceptance Testing',
        'qa': 'Quality Assurance',
        'sandbox': 'Sandbox'
    }
    
    # Status Options
    STATUS_OPTIONS = [
        'RUNNING',
        'STARTED',
        'STOPPED',
        'PENDING',
        'FAILED',
        'DEPLOYMENT FAILED',
        'DEPLOYING',
        'DEPLOYED',
        'UNKNOWN',
        'ERROR',
        'MAINTENANCE',
        'UNDEPLOYING',
        'STARTING',
        'STOPPING',
        'DEGRADED',
        'SCALING'
    ]


# ==================== MODULE-LEVEL EXPORTS ====================
MONGO_HOST = Config.MONGO_HOST
MONGO_PORT = Config.MONGO_PORT
MONGO_DB = Config.MONGO_DB
MONGO_COLLECTION = Config.MONGO_COLLECTION
MONGO_URI = Config.MONGO_URI

AUTH_ENABLED = Config.AUTH_ENABLED
JWT_SECRET_KEY = Config.JWT_SECRET_KEY
JWT_ACCESS_TOKEN_EXPIRATION_MINUTES = Config.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES
JWT_REFRESH_TOKEN_EXPIRATION_DAYS = Config.JWT_REFRESH_TOKEN_EXPIRATION_DAYS
JWT_EXPIRATION_HOURS = Config.JWT_EXPIRATION_HOURS
JWT_ALGORITHM = Config.JWT_ALGORITHM
JWT_ADMIN_KEY = Config.JWT_ADMIN_KEY
REFRESH_TOKEN_ROTATION_ENABLED = Config.REFRESH_TOKEN_ROTATION_ENABLED
PUBLIC_ENDPOINTS = Config.PUBLIC_ENDPOINTS

PLATFORM_MAPPING = Config.PLATFORM_MAPPING
ENVIRONMENT_MAPPING = Config.ENVIRONMENT_MAPPING
STATUS_OPTIONS = Config.STATUS_OPTIONS


# ==================== HELPER FUNCTIONS ====================
def get_valid_platforms():
    return list(Config.PLATFORM_MAPPING.keys())

def get_valid_environments():
    return list(Config.ENVIRONMENT_MAPPING.keys())

def get_valid_statuses():
    return Config.STATUS_OPTIONS

def is_valid_platform(platform_id: str) -> bool:
    return platform_id in Config.PLATFORM_MAPPING

def is_valid_environment(environment_id: str) -> bool:
    return environment_id in Config.ENVIRONMENT_MAPPING

def is_valid_status(status: str) -> bool:
    return status in Config.STATUS_OPTIONS

def get_platform_display_name(platform_id: str) -> str:
    return Config.PLATFORM_MAPPING.get(platform_id, platform_id)

def get_environment_display_name(environment_id: str) -> str:
    return Config.ENVIRONMENT_MAPPING.get(environment_id, environment_id)

def is_public_endpoint(path: str) -> bool:
    return Config.is_public_endpoint(path)