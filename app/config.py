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
    AUTH_ENABLED = os.getenv('AUTH_ENABLED', 'false').lower() == 'true'
    
    # JWT Secret Key - Used to sign tokens
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-CHANGE-IN-PRODUCTION')
    
    # JWT Token expiration (in hours)
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS') or 24)
    
    # JWT Algorithm
    JWT_ALGORITHM = 'HS256'
    
    # Admin key for initial token generation
    JWT_ADMIN_KEY = os.getenv('JWT_ADMIN_KEY', 'dev-admin-key-CHANGE-IN-PRODUCTION')
    
    # Token prefix for Authorization header
    AUTH_HEADER_PREFIX = 'Bearer'
    
    # Endpoints that are always public (no authentication required)
    PUBLIC_ENDPOINTS = [
        '/health',
        '/health/ready',
        '/health/live',
        '/health/metrics',
        '/',
        '/api/admin/scheduler/jobs',
        '/search',
        '/static/',
        '/api/auth/token',
        '/api/auth/verify',
        '/api/auth/status',
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
JWT_EXPIRATION_HOURS = Config.JWT_EXPIRATION_HOURS
JWT_ALGORITHM = Config.JWT_ALGORITHM
JWT_ADMIN_KEY = Config.JWT_ADMIN_KEY
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