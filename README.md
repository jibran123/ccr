# Common Configuration Repository (CCR)

**Internal operations tool for managing API deployments across multiple platforms and environments**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/mongodb-7.0-green.svg)](https://www.mongodb.com/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-ready-326CE5.svg)](https://kubernetes.io/)

---

## Overview

CCR is a centralized configuration management system designed for internal operations teams to track and manage API deployments across multiple platforms (IP2-IP7, OpenShift, AWS, Azure) and environments (dev, tst, acc, prd). It provides a unified interface for viewing deployment configurations, searching deployment history, and tracking changes through comprehensive audit logs.

### Key Features

- **Multi-Platform Support**: Manage APIs across 6+ platforms with environment-specific configurations
- **Advanced Search**: Query deployments using simple text, attribute filters, or logical operators (AND/OR)
- **Audit Logging**: Complete immutable audit trail with 180-day retention policy
- **RESTful API**: Full CRUD operations with JWT authentication
- **Modern UI**: Responsive web interface with real-time search and 3D animated navigation
- **Production Ready**: Kubernetes-native with health checks, metrics, and auto-scaling

---

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Backend** | Python / Flask | 3.11 / 3.0 |
| **Database** | MongoDB (StatefulSet) | 7.0 |
| **Container Runtime** | Podman (rootful) | Latest |
| **Orchestration** | Kubernetes (kind) | 1.31.0 |
| **Package Management** | Helm | 3.x |
| **CI/CD** | GitLab CI | Latest |
| **Registry** | Harbor | 2.x |

---

## Quick Start

### Prerequisites

- Kubernetes cluster (kind, minikube, or production cluster)
- kubectl configured
- Helm 3.x installed
- (Optional) Podman/Docker for local development

### Deploy to Kubernetes

```bash
# Option 1: Automated deployment script
./scripts/deploy-local-k8s.sh

# Option 2: Manual Helm deployment
helm install ccr ./helm/ccr \
  -f helm/ccr/values-dev.yaml \
  --namespace default

# Check deployment status
kubectl get pods
kubectl get svc

# Access application
kubectl port-forward svc/flask-service 31500:5000
# Open http://localhost:31500
```

### Local Development (Podman Compose)

```bash
# Start all services
podman-compose up -d

# View logs
podman logs -f flask-app

# Access application
http://localhost:5000

# Rebuild after code changes
./scripts/rebuild.sh

# Stop services
podman-compose down
```

---

## Architecture

### Data Model

CCR uses a nested document structure to represent API deployments:

```json
{
  "_id": "my-api",
  "API Name": "my-api",
  "Platform": [
    {
      "PlatformID": "IP4",
      "Environment": [
        {
          "environmentID": "tst",
          "version": "1.0.0",
          "status": "RUNNING",
          "lastUpdated": "2024-11-27T10:00:00Z",
          "updatedBy": "Jibran Patel",
          "Properties": {}
        }
      ]
    }
  ]
}
```

### Search Query Syntax

| Query Type | Example | Description |
|-----------|---------|-------------|
| **Simple Text** | `user-api` | Search across API Name, Platform, Environment |
| **Attribute** | `Platform = IP4` | Exact match on specific field |
| **Logical AND** | `Platform = IP4 AND Environment = prd` | Multiple conditions (all must match) |
| **Logical OR** | `Status = RUNNING OR Status = DEPLOYING` | Alternative conditions |
| **Comparison** | `Version >= 2.0` | Numeric/string comparison |
| **Contains** | `APIName contains user` | Substring search |
| **Properties** | `Properties : owner = team-alpha` | Nested property search |

---

## Deployment Strategies

### Kubernetes (Production)

**Architecture:**
- **Flask Deployment**: 2 replicas (HPA enabled: 2-5 pods based on CPU/memory)
- **MongoDB StatefulSet**: 1 replica with persistent storage (10Gi data + 5Gi backups)
- **Services**: ClusterIP for internal, NodePort (31500) for external access
- **Secrets**: JWT keys, admin keys, SECRET_KEY stored in Kubernetes secrets

**Environment-Specific Deployments:**

```bash
# Development
helm install ccr ./helm/ccr -f helm/ccr/values-dev.yaml

# Test
helm install ccr ./helm/ccr -f helm/ccr/values-tst.yaml

# Acceptance
helm install ccr ./helm/ccr -f helm/ccr/values-acc.yaml

# Production
helm install ccr ./helm/ccr -f helm/ccr/values-prd.yaml
```

**Health Checks:**
- Liveness: `/health/live` (checks if application is running)
- Readiness: `/health/ready` (checks MongoDB connection)
- Metrics: `/health/metrics` (Prometheus format)

**Helper Scripts:**
- `./deploy-local-k8s.sh` - Full automated deployment
- `./cleanup-local-k8s.sh` - Teardown cluster
- `./k8s-status.sh` - Quick cluster status
- `./k8s-describe-flask.sh` - Detailed Flask pod diagnostics
- `./fix-and-redeploy.sh` - Fix and redeploy utility

### CI/CD Pipeline

CCR uses GitLab CI for automated build and deployment:

**Build Pipeline** (Source Repository):
1. **Test**: Unit + Integration tests (621 tests, 80% coverage)
2. **Build**: Multi-stage Docker build (non-root, optimized)
3. **Scan**: Trivy (vulnerabilities) + TruffleHog (secrets)
4. **Publish**: Push to Harbor registry
5. **Tag**: Git tag with semantic version

**Deployment Pipeline** (Deployment Repository):
1. **Validate**: Helm chart validation
2. **Deploy**: Environment-specific deployment (dev → tst → acc → prd)
3. **Verify**: Health checks and smoke tests
4. **Rollback**: One-click rollback on failure

See [Build Pipeline](docs/BUILD_PIPELINE.md) and [Deployment Pipeline](docs/DEPLOYMENT_PIPELINE.md) for details.

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MONGO_HOST` | MongoDB hostname | `mongodb-service` | Yes |
| `MONGO_PORT` | MongoDB port | `27017` | Yes |
| `MONGO_DB` | Database name | `ccr` | Yes |
| `MONGO_COLLECTION` | Collection name | `apis` | Yes |
| `SECRET_KEY` | Flask secret key | - | Yes |
| `JWT_SECRET_KEY` | JWT signing key | - | Yes |
| `JWT_ADMIN_KEY` | Admin API key | - | Yes |
| `AUTH_ENABLED` | Enable authentication | `true` | No |
| `RATELIMIT_ENABLED` | Enable rate limiting | `true` | No |
| `BACKUP_ENABLED` | Enable automated backups | `true` | No |
| `BACKUP_RETENTION_DAYS` | Backup retention period | `14` | No |

### Platform & Environment Mappings

**Platforms**: IP2, IP3, IP4, IP5, IP6, IP7, OpenShift, AWS, Azure
**Environments**: dev, tst, acc, prd
**Status Values**: RUNNING, STOPPED, DEPLOYING, FAILED, MAINTENANCE

See `app/config.py` for complete mappings.

---

## API Documentation

Complete OpenAPI 3.0 specification: [API Documentation](docs/openapi.yaml)

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/search` | Search API deployments |
| `POST` | `/api/deploy` | Create new deployment |
| `PUT` | `/api/update/<api_name>/<platform>/<env>` | Update deployment |
| `DELETE` | `/api/delete/<api_name>/<platform>/<env>` | Delete deployment |
| `GET` | `/api/audit/recent` | Get recent audit logs |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/metrics` | Prometheus metrics |

### Authentication

JWT-based authentication (when `AUTH_ENABLED=true`):

```bash
# Get access token
curl -X POST http://localhost:31500/api/auth/token \
  -H "X-Admin-Key: <admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "role": "admin"}'

# Use token in requests
curl http://localhost:31500/api/search?q=my-api \
  -H "Authorization: Bearer <access-token>"
```

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/unit/              # Unit tests
pytest tests/integration/       # Integration tests
pytest -m auth                  # Authentication tests
pytest -m backup                # Backup tests

# Performance tests
pytest tests/performance/
```

**Test Results**: 621 tests passing, 80% code coverage

See [Testing Guide](docs/TESTING_GUIDE.md) for comprehensive testing documentation.

---

## Maintenance

### Backup & Recovery

**Automated Backups:**
- Schedule: Daily at 2:00 AM (configurable via `BACKUP_SCHEDULE`)
- Retention: 14 days (configurable via `BACKUP_RETENTION_DAYS`)
- Location: `/app/backups` (mounted PersistentVolume)

**Manual Backup:**

```bash
curl -X POST http://localhost:31500/api/admin/backup \
  -H "Authorization: Bearer <admin-token>"
```

**Recovery:**

```bash
# List available backups
ls /app/backups

# Restore from backup
mongorestore --archive=/app/backups/ccr_backup_20241127_020000.archive --gzip
```

### Monitoring

**Prometheus Metrics** (http://localhost:31500/health/metrics):
- `ccr_documents_total` - Total API documents
- `ccr_platforms_total` - Total platforms
- `ccr_environments_total` - Total environments
- `ccr_request_duration_seconds` - Request latency

**Logs:**

```bash
# View Flask logs
kubectl logs -f deployment/flask-deployment

# View MongoDB logs
kubectl logs -f mongodb-0

# View all logs
kubectl logs -f -l app=ccr
```

See [Maintenance Guide](docs/MAINTENANCE_GUIDE.md) for operational procedures.

---

## Security

### Security Features

- **JWT Authentication**: Token-based API access with configurable expiration
- **Rate Limiting**: Protect against abuse (configurable per endpoint)
- **Brute Force Protection**: IP-based lockout after failed login attempts
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc. (via Flask-Talisman)
- **Input Validation**: Strict validation against config-based mappings
- **SQL Injection Protection**: Frontend blocks SQL keywords while allowing logical operators
- **Secret Management**: All secrets stored in Kubernetes secrets (not in code)
- **Container Security**: Non-root user, minimal base image, security scanning

### OWASP Top 10 Compliance

CCR has been audited against OWASP Top 10 2021. See [Security Report](archive/security-reports/SECURITY_AUDIT_REPORT.md) for details.

**To Report Security Issues**: Contact security@yourcompany.com

---

## Project Structure

```
ccr/
├── app/                        # Application code
│   ├── models/                # Data models
│   ├── routes/                # API endpoints (8 route modules)
│   ├── services/              # Business logic (6 services)
│   ├── utils/                 # Utilities (validators, auth, timezone)
│   ├── static/                # Frontend assets (CSS, JS, images)
│   └── templates/             # HTML templates
├── tests/                     # Test suite (621 tests)
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   ├── performance/           # Performance tests
│   └── security/              # Security tests
├── helm/                      # Helm chart
│   └── ccr/       # Chart files (20 templates)
├── k8s/                       # Raw Kubernetes manifests
├── docs/                      # Documentation
│   ├── BUILD_PIPELINE.md      # Build pipeline guide
│   ├── DEPLOYMENT_PIPELINE.md # Deployment guide
│   ├── MAINTENANCE_GUIDE.md   # Operations manual
│   ├── TESTING_GUIDE.md       # Testing procedures
│   └── openapi.yaml           # OpenAPI 3.0 specification
├── archive/                   # Historical reports (not for production)
├── Dockerfile                 # Multi-stage production build
├── podman-compose.yml         # Local development setup
├── requirements.txt           # Python dependencies
├── CHANGELOG.md               # Version history
├── SECURITY.md                # Security policy
└── README.md                  # This file
```

---

## Troubleshooting

### Common Issues

**Pods not starting:**

```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

**MongoDB connection failed:**

```bash
# Check MongoDB status
kubectl get statefulset mongodb
kubectl logs mongodb-0

# Verify service
kubectl get svc mongodb-service
```

**Authentication errors:**

```bash
# Check secrets
kubectl get secret flask-secrets -o yaml

# Verify AUTH_ENABLED setting
kubectl get configmap flask-config -o yaml | grep AUTH_ENABLED
```

**Health checks failing:**

```bash
# Test endpoints manually
kubectl exec -it deployment/flask-deployment -- curl http://localhost:5000/health/live
kubectl exec -it deployment/flask-deployment -- curl http://localhost:5000/health/ready
```

---

## Contributing

This is an internal tool. For feature requests or bug reports, contact the development team.

**Development Workflow:**
1. Create feature branch from `main`
2. Implement changes with tests
3. Run full test suite (`pytest`)
4. Create merge request
5. CI pipeline automatically runs tests and security scans
6. Code review required before merge

---

## License

Internal Use Only - Proprietary

Copyright © 2024-2025 Your Company. All rights reserved.

---

## Support

- **Team Lead**: Jibran Patel
- **Email**: jibran@yourcompany.com
- **Documentation**: [docs/](docs/)
- **Issue Tracker**: Internal GitLab Issues

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

**Current Version**: 2.0.0 (November 2025)
