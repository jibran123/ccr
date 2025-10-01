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

# Platform Mapping
PLATFORM_MAPPING = {
    'IP2': 'IP2 Platform',
    'IP3': 'IP3 Platform',
    'IP4': 'IP4 Platform',
    'IP5': 'IP5 Platform',
    'IP6': 'IP6 Platform',
    'IP7': 'IP7 Platform',
    'OpenShift': 'OpenShift',
    'Kubernetes': 'Kubernetes',
    'Docker': 'Docker',
    'AWS': 'Amazon Web Services',
    'Azure': 'Microsoft Azure',
    'GCP': 'Google Cloud Platform'
}

# Environment Mapping
ENVIRONMENT_MAPPING = {
    'dev': 'Development',
    'tst': 'Test',
    'acc': "Acceptance",
    'stg': 'Staging',
    'prd': 'Production',
    'prd-uitwijk': 'Production Uitwijk / Fallback',
    'dr': 'Disaster Recovery',
    'uat': 'User Acceptance Testing',
    'qa': 'Quality Assurance'
}

# Status Options
STATUS_OPTIONS = [
    'RUNNING',
    'STARTED',
    'STOPPED',
    'PENDING',
    'FAILED',
    'DEPLOYMENT FAIELD',
    'DEPLOYING',
    'DEPLOYED',
    'UNKNOWN',
    'ERROR',
    'MAINTENANCE',
    'UNDEPLOYING',
    'STARTING',
    'STOPPING',
    'UNKNOWN'
]