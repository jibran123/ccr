import os
from datetime import timedelta

class Config:
    """Application configuration."""
    
    # Application Configuration
    APP_NAME = "CCR API Manager"
    APP_VERSION = "2.0.0"
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # MongoDB Configuration
    MONGO_HOST = os.getenv('MONGO_HOST', 'mongo')
    MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
    MONGO_DB = os.getenv('MONGO_DB', 'ccr')
    MONGO_COLLECTION = os.getenv('MONGO_COLLECTION', 'apis')
    MONGO_URI = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 500
    
    # CORS Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # ==================== AUTHENTICATION CONFIGURATION ====================
    # JWT Authentication Settings
    
    # Feature flag - Enable/disable authentication
    # Set to 'true' in production after testing
    AUTH_ENABLED = os.getenv('AUTH_ENABLED', 'false').lower() == 'true'
    
    # JWT Secret Key - Used to sign tokens
    # CRITICAL: Generate a strong random key for production!
    # Example: python -c "import secrets; print(secrets.token_urlsafe(32))"
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-CHANGE-IN-PRODUCTION')
    
    # JWT Token expiration (in hours)
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))
    
    # JWT Algorithm (don't change unless you know what you're doing)
    JWT_ALGORITHM = 'HS256'
    
    # Admin key for initial token generation
    # CRITICAL: Change this to a strong password/key in production!
    JWT_ADMIN_KEY = os.getenv('JWT_ADMIN_KEY', 'dev-admin-key-CHANGE-IN-PRODUCTION')
    
    # Token prefix for Authorization header
    AUTH_HEADER_PREFIX = 'Bearer'
    
    # Endpoints that are always public (no authentication required)
    PUBLIC_ENDPOINTS = [
        '/health',           # Health check
        '/health/ready',     # Readiness probe
        '/health/live',      # Liveness probe
        '/health/metrics',   # Prometheus metrics
        '/',                 # Main page
        '/search',           # Web interface
        '/static/',          # Static files (CSS, JS, images)
        '/api/auth/token',   # Token generation endpoint
        '/api/auth/verify',  # Token verification endpoint
        '/api/auth/status',  # Authentication status
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
        
        # Check other public endpoints (skip root to avoid matching everything)
        for public_path in Config.PUBLIC_ENDPOINTS:
            # Skip root path (already handled above)
            if public_path in ['/', '/search']:
                continue
            
            # Check if path starts with this public endpoint
            if path.startswith(public_path):
                return True
        
        return False
    
    # ==================== DEPLOYMENT CONFIGURATION ====================
    # Platform Mapping - Add/remove platforms here
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
    
    # Environment Mapping - Add/remove environments here
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
    
    # Status Options - Add/remove statuses here
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
# Export variables for backward compatibility with existing code

# MongoDB Configuration
MONGO_HOST = Config.MONGO_HOST
MONGO_PORT = Config.MONGO_PORT
MONGO_DB = Config.MONGO_DB
MONGO_COLLECTION = Config.MONGO_COLLECTION
MONGO_URI = Config.MONGO_URI

# Authentication Configuration
AUTH_ENABLED = Config.AUTH_ENABLED
JWT_SECRET_KEY = Config.JWT_SECRET_KEY
JWT_EXPIRATION_HOURS = Config.JWT_EXPIRATION_HOURS
JWT_ALGORITHM = Config.JWT_ALGORITHM
JWT_ADMIN_KEY = Config.JWT_ADMIN_KEY
PUBLIC_ENDPOINTS = Config.PUBLIC_ENDPOINTS

# Deployment Configuration
PLATFORM_MAPPING = Config.PLATFORM_MAPPING
ENVIRONMENT_MAPPING = Config.ENVIRONMENT_MAPPING
STATUS_OPTIONS = Config.STATUS_OPTIONS


# ==================== HELPER FUNCTIONS ====================

def get_valid_platforms():
    """Get list of valid platform IDs."""
    return list(Config.PLATFORM_MAPPING.keys())

def get_valid_environments():
    """Get list of valid environment IDs."""
    return list(Config.ENVIRONMENT_MAPPING.keys())

def get_valid_statuses():
    """Get list of valid status values."""
    return Config.STATUS_OPTIONS

def is_valid_platform(platform_id: str) -> bool:
    """Check if platform ID is valid."""
    return platform_id in Config.PLATFORM_MAPPING

def is_valid_environment(environment_id: str) -> bool:
    """Check if environment ID is valid."""
    return environment_id in Config.ENVIRONMENT_MAPPING

def is_valid_status(status: str) -> bool:
    """Check if status is valid."""
    return status in Config.STATUS_OPTIONS

def get_platform_display_name(platform_id: str) -> str:
    """Get display name for platform."""
    return Config.PLATFORM_MAPPING.get(platform_id, platform_id)

def get_environment_display_name(environment_id: str) -> str:
    """Get display name for environment."""
    return Config.ENVIRONMENT_MAPPING.get(environment_id, environment_id)

def is_public_endpoint(path: str) -> bool:
    """Check if endpoint is public (no authentication required)."""
    return Config.is_public_endpoint(path)