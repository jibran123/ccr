import os
from datetime import timedelta

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

# Session Configuration
SESSION_COOKIE_NAME = 'ccr_session'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

# Platform Mapping
PLATFORM_MAPPING = {
    'IP4': 'IP4 Platform',
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
    'stg': 'Staging',
    'prd': 'Production',
    'dr': 'Disaster Recovery',
    'uat': 'User Acceptance Testing',
    'qa': 'Quality Assurance'
}

# Status Options
STATUS_OPTIONS = [
    'RUNNING',
    'STOPPED',
    'PENDING',
    'FAILED',
    'DEPLOYING',
    'DEPLOYED',
    'UNKNOWN',
    'ERROR',
    'MAINTENANCE'
]

# API Limits
MAX_API_NAME_LENGTH = 255
MAX_PROPERTY_KEY_LENGTH = 100
MAX_PROPERTY_VALUE_LENGTH = 1000
MAX_PROPERTIES_PER_API = 100

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

# CORS Settings
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

# Cache Configuration
CACHE_TYPE = "simple"
CACHE_DEFAULT_TIMEOUT = 300

# Feature Flags
ENABLE_API_KEY_AUTH = os.getenv('ENABLE_API_KEY_AUTH', 'False').lower() == 'true'
ENABLE_RATE_LIMITING = os.getenv('ENABLE_RATE_LIMITING', 'False').lower() == 'true'
ENABLE_AUDIT_LOG = os.getenv('ENABLE_AUDIT_LOG', 'False').lower() == 'true'

# Rate Limiting (if enabled)
RATE_LIMIT = "100 per hour"

# File Upload Settings
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# API Documentation
API_TITLE = "CCR API Manager"
API_VERSION = "2.0"
OPENAPI_VERSION = "3.0.2"
OPENAPI_URL_PREFIX = "/"
OPENAPI_SWAGGER_UI_PATH = "/swagger"
OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"