#!/usr/bin/env python3
"""Test configuration loading."""

import sys
sys.path.insert(0, '/app')  # For container

from app.config import Config

print("=" * 60)
print("CCR API Manager - Configuration Test")
print("=" * 60)

print("\n✅ BASIC CONFIG:")
print(f"  App Name: {Config.APP_NAME}")
print(f"  App Version: {Config.APP_VERSION}")
print(f"  MongoDB: {Config.MONGO_HOST}:{Config.MONGO_PORT}/{Config.MONGO_DB}")

print("\n🔐 AUTHENTICATION CONFIG:")
print(f"  Auth Enabled: {Config.AUTH_ENABLED}")
print(f"  JWT Secret Key: {Config.JWT_SECRET_KEY[:20]}... (hidden)")
print(f"  JWT Admin Key: {Config.JWT_ADMIN_KEY[:20]}... (hidden)")
print(f"  Token Expiration: {Config.JWT_EXPIRATION_HOURS} hours")
print(f"  JWT Algorithm: {Config.JWT_ALGORITHM}")

print("\n📋 PUBLIC ENDPOINTS:")
for endpoint in Config.PUBLIC_ENDPOINTS:
    print(f"  - {endpoint}")

print("\n🧪 TESTING is_public_endpoint():")
test_paths = [
    '/health',
    '/api/search',
    '/api/deploy',
    '/static/css/main.css',
    '/api/auth/token'
]

for path in test_paths:
    is_public = Config.is_public_endpoint(path)
    status = "🟢 PUBLIC" if is_public else "🔴 PROTECTED"
    print(f"  {path:<30} → {status}")

print("\n" + "=" * 60)
print("✅ Configuration loaded successfully!")
print("=" * 60)
