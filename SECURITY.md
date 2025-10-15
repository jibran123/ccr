cat > SECURITY.md << 'EOF'
# 🔒 CCR API Manager - Security & Authentication Guide

## Overview

The CCR API Manager uses **JWT (JSON Web Token) Bearer authentication** to secure API endpoints. This guide covers everything you need to know about authentication, token management, and security best practices.

---

## 🚀 Quick Start

### 1. Enable Authentication

Edit your `.env` file:
```bash
# Enable authentication
AUTH_ENABLED=true

# Set secure keys (CRITICAL: Change these!)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
JWT_ADMIN_KEY=your-admin-key-for-token-generation

# Optional: Configure expiration (default: 24 hours)
JWT_EXPIRATION_HOURS=24
```

### 2. Generate Secure Keys
```bash
# Generate JWT secret key
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate admin key
python3 -c "import secrets; print('JWT_ADMIN_KEY=' + secrets.token_urlsafe(32))"
```

### 3. Generate Your First Token
```bash
curl -X POST http://localhost:5000/api/auth/token \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "username": "your_name",
    "role": "admin",
    "expires_in_hours": 24
  }'
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2025-10-16T10:30:00Z",
    "username": "your_name",
    "role": "admin"
  }
}
```

### 4. Use the Token
```bash
# Save token
export TOKEN="your-token-here"

# Use in API calls
curl -X POST http://localhost:5000/api/deploy \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "api_name": "my-api",
    "platform_id": "IP4",
    "environment_id": "tst",
    "status": "RUNNING",
    "updated_by": "your_name",
    "properties": {}
  }'
```

---

## 📋 API Endpoints

### Authentication Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/auth/token` | POST | Generate JWT token | Admin Key |
| `/api/auth/verify` | POST | Verify token validity | No |
| `/api/auth/status` | GET | Get auth configuration | No |

### Protected Endpoints (Require Token)

| Endpoint | Method | Description | Required Role |
|----------|--------|-------------|---------------|
| `/api/deploy` | POST | Create/Update deployment | Any |
| `/api/apis/.../` | PUT | Full deployment update | Any |
| `/api/apis/.../` | PATCH | Partial deployment update | Any |
| `/api/apis/.../` | DELETE | Delete deployment | Any |
| `/api/export` | POST | Export data | Any |

### Public Endpoints (No Token Required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | GET | Search deployments |
| `/api/stats` | GET | Database statistics |
| `/api/platforms` | GET | List platforms |
| `/api/environments` | GET | List environments |
| `/api/statuses` | GET | List statuses |
| `/api/config` | GET | Get configuration |
| `/health/*` | GET | Health checks |
| `/` | GET | Web interface |

---

## 🔑 Token Management

### Token Structure

JWT tokens contain:
```json
{
  "username": "john.doe",
  "role": "admin",
  "iat": 1728901800,    // Issued at (Unix timestamp)
  "exp": 1728988200,    // Expires at (Unix timestamp)
  "iss": "ccr-api-manager"
}
```

### Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| `admin` | Full access to all operations | System administrators |
| `user` | Standard access (CRUD operations) | Regular API users |
| `readonly` | Read-only access (future) | Monitoring, reporting |

### Token Expiration

- **Default:** 24 hours
- **Maximum:** 8760 hours (1 year)
- **Configurable:** Set per-token or via `JWT_EXPIRATION_HOURS`

### Token Security Best Practices

✅ **DO:**
- Store tokens securely (environment variables, secrets manager)
- Use HTTPS in production
- Rotate tokens regularly
- Use short expiration times for sensitive operations
- Generate unique tokens per user/application
- Revoke tokens when no longer needed

❌ **DON'T:**
- Commit tokens to Git repositories
- Share tokens between users
- Store tokens in client-side JavaScript
- Use the same token across multiple applications
- Log tokens in application logs

---

## 🧪 Testing & Examples

### Test Authentication Flow
```bash
#!/bin/bash

# 1. Generate token
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:5000/api/auth/token \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{"username": "test_user", "role": "admin"}')

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.data.token')
echo "Token: $TOKEN"

# 2. Test protected endpoint WITH token (should work)
curl -X POST http://localhost:5000/api/deploy \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"api_name": "test", "platform_id": "IP4", "environment_id": "tst", "status": "RUNNING", "updated_by": "test_user", "properties": {}}'

# 3. Test protected endpoint WITHOUT token (should fail)
curl -X POST http://localhost:5000/api/deploy \
  -H "Content-Type: application/json" \
  -d '{"api_name": "test", "platform_id": "IP4", "environment_id": "tst", "status": "RUNNING", "updated_by": "test", "properties": {}}'
```

### Python Example
```python
import requests
import os

# Configuration
API_URL = "http://localhost:5000"
ADMIN_KEY = os.getenv('JWT_ADMIN_KEY')

# 1. Generate token
token_response = requests.post(
    f'{API_URL}/api/auth/token',
    headers={
        'X-Admin-Key': ADMIN_KEY,
        'Content-Type': 'application/json'
    },
    json={
        'username': 'python_client',
        'role': 'admin',
        'expires_in_hours': 24
    }
)

token = token_response.json()['data']['token']
print(f"Token: {token[:50]}...")

# 2. Use token for API calls
headers = {'Authorization': f'Bearer {token}'}

# Deploy API
deploy_response = requests.post(
    f'{API_URL}/api/deploy',
    headers=headers,
    json={
        'api_name': 'my-api',
        'platform_id': 'IP4',
        'environment_id': 'tst',
        'version': '1.0.0',
        'status': 'RUNNING',
        'updated_by': 'python_client',
        'properties': {'env': 'test'}
    }
)

print(f"Deploy status: {deploy_response.json()['status']}")
```

### JavaScript/Node.js Example
```javascript
const axios = require('axios');

const API_URL = 'http://localhost:5000';
const ADMIN_KEY = process.env.JWT_ADMIN_KEY;

async function main() {
  // 1. Generate token
  const tokenResponse = await axios.post(
    `${API_URL}/api/auth/token`,
    {
      username: 'nodejs_client',
      role: 'admin',
      expires_in_hours: 24
    },
    {
      headers: {
        'X-Admin-Key': ADMIN_KEY
      }
    }
  );

  const token = tokenResponse.data.data.token;
  console.log(`Token: ${token.substring(0, 50)}...`);

  // 2. Use token
  const deployResponse = await axios.post(
    `${API_URL}/api/deploy`,
    {
      api_name: 'my-api',
      platform_id: 'IP4',
      environment_id: 'tst',
      status: 'RUNNING',
      updated_by: 'nodejs_client',
      properties: {}
    },
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );

  console.log(`Deploy status: ${deployResponse.data.status}`);
}

main().catch(console.error);
```

---

## 🛡️ Production Deployment

### 1. Generate Production Keys
```bash
# Generate strong keys
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_ADMIN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Store securely (e.g., AWS Secrets Manager, HashiCorp Vault)
echo "JWT_SECRET_KEY=$JWT_SECRET" >> .env.production
echo "JWT_ADMIN_KEY=$JWT_ADMIN" >> .env.production
```

### 2. Configure Environment
```bash
# Production .env
AUTH_ENABLED=true
JWT_SECRET_KEY=<your-production-secret>
JWT_ADMIN_KEY=<your-production-admin-key>
JWT_EXPIRATION_HOURS=8  # Shorter for production
```

### 3. Enable HTTPS

**Never use HTTP in production!**
```nginx
# Nginx configuration
server {
    listen 443 ssl http2;
    server_name api.yourcompany.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Monitor & Audit
```bash
# Check authentication logs
podman logs flask-app | grep -i "auth\|token"

# Monitor failed authentication attempts
podman logs flask-app | grep "❌"

# Track token generation
podman logs flask-app | grep "Token generated"
```

---

## 🔄 Migration Guide

### Phase 1: Preparation (Week 1)
1. Deploy code with `AUTH_ENABLED=false`
2. Verify all functionality works
3. Generate production tokens
4. Test token generation endpoint

### Phase 2: Testing (Week 2)
1. Enable auth in dev environment
2. Update client applications with tokens
3. Test all endpoints
4. Monitor for errors

### Phase 3: Staging (Week 3)
1. Deploy to staging with `AUTH_ENABLED=true`
2. Full integration testing
3. Performance testing
4. Security audit

### Phase 4: Production (Week 4)
1. Deploy with `AUTH_ENABLED=false` initially
2. Update all client applications
3. Enable authentication: `AUTH_ENABLED=true`
4. Monitor metrics and errors
5. Gradual rollout if needed

---

## 🐛 Troubleshooting

### Error: "Authentication required"

**Cause:** No token provided or `AUTH_ENABLED=true`

**Solution:**
1. Generate token: `POST /api/auth/token`
2. Include in request: `Authorization: Bearer <token>`

### Error: "Token has expired"

**Cause:** Token older than expiration time

**Solution:**
1. Generate new token
2. Use longer `expires_in_hours` (up to 8760)

### Error: "Invalid token"

**Cause:** Token malformed, wrong secret, or tampered

**Solution:**
1. Verify token: `POST /api/auth/verify`
2. Check `JWT_SECRET_KEY` matches
3. Regenerate token

### Error: "Invalid admin key"

**Cause:** Wrong `X-Admin-Key` header

**Solution:**
1. Check `JWT_ADMIN_KEY` in `.env`
2. Verify header format: `X-Admin-Key: <key>`

---

## 📞 Support

For security issues or questions:
1. Check logs: `podman logs -f flask-app`
2. Verify config: `GET /api/auth/status`
3. Test token: `POST /api/auth/verify`

---

## 📊 Security Checklist

- [ ] Strong `JWT_SECRET_KEY` generated and stored securely
- [ ] Strong `JWT_ADMIN_KEY` generated and stored securely
- [ ] `AUTH_ENABLED=true` in production
- [ ] HTTPS enabled (SSL/TLS certificates configured)
- [ ] Token expiration set appropriately (8-24 hours)
- [ ] Tokens stored securely (not in code or logs)
- [ ] Authentication monitored and audited
- [ ] Client applications updated with token support
- [ ] Backup admin key stored securely
- [ ] Documentation provided to users

---

## 🔐 Security Disclosure

If you discover a security vulnerability, please contact the security team immediately. Do not post security issues publicly.

**This system is production-ready and follows industry best practices for API authentication.**
EOF

echo "✅ SECURITY.md created"