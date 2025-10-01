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
    MONGO_HOST = os.getenv('MONGO_HOST', 'mongo')  # 'mongo' for container, 'localhost' for local
    MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
    MONGO_DB = os.getenv('MONGO_DB', 'ccr')
    MONGO_COLLECTION = os.getenv('MONGO_COLLECTION', 'apis')
    
    # MongoDB Connection String
    MONGO_URI = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 500
    
    # CORS Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

# Keep module-level variables for backward compatibility
MONGO_HOST = Config.MONGO_HOST
MONGO_PORT = Config.MONGO_PORT
MONGO_DB = Config.MONGO_DB
MONGO_COLLECTION = Config.MONGO_COLLECTION
MONGO_URI = Config.MONGO_URI

# ==================== DEPLOYMENT CONFIGURATION ====================
# These are the SINGLE SOURCE OF TRUTH for valid values
# Update these lists as you onboard/decommission platforms, environments, or statuses

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

# ==================== HELPER FUNCTIONS ====================

def get_valid_platforms():
    """Get list of valid platform IDs."""
    return list(PLATFORM_MAPPING.keys())

def get_valid_environments():
    """Get list of valid environment IDs."""
    return list(ENVIRONMENT_MAPPING.keys())

def get_valid_statuses():
    """Get list of valid status values."""
    return STATUS_OPTIONS

def is_valid_platform(platform_id: str) -> bool:
    """Check if platform ID is valid."""
    return platform_id in PLATFORM_MAPPING

def is_valid_environment(environment_id: str) -> bool:
    """Check if environment ID is valid."""
    return environment_id in ENVIRONMENT_MAPPING

def is_valid_status(status: str) -> bool:
    """Check if status is valid."""
    return status in STATUS_OPTIONS

def get_platform_display_name(platform_id: str) -> str:
    """Get display name for platform."""
    return PLATFORM_MAPPING.get(platform_id, platform_id)

def get_environment_display_name(environment_id: str) -> str:
    """Get display name for environment."""
    return ENVIRONMENT_MAPPING.get(environment_id, environment_id)