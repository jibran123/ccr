# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Common Configuration Repository (CCR)** is an internal operations tool for managing API deployments across multiple platforms (IP2-IP7, OpenShift, AWS, Azure, etc.) and environments (dev, tst, acc, prd, etc.). This is a Flask + MongoDB web application serving 20 internal users managing 100-300 APIs.

**Key Characteristics:**
- Internal tool (not customer-facing)
- Read-heavy workload (UI primarily for search/view)
- All deployments handled through CI/CD pipelines
- Team: 2-3 person maintenance (~10 hours/week capacity)
- Current Version: 2.0.0

---

## Quick Start Commands

### Kubernetes Deployment (Primary Method - Production Ready)

**IMPORTANT:** This project uses Helm charts on kind cluster for all development and testing. Podman Compose is deprecated.

```bash
# Automated deployment (Recommended)
./scripts/deploy-local-k8s.sh

# Manual Helm deployment
helm install ccr ./helm/ccr -f helm/ccr/values-dev.yaml --namespace default

# Check deployment status
kubectl get pods
kubectl get svc
kubectl logs -f deployment/flask-deployment

# Access application
# Method 1: NodePort (automatic)
http://localhost:31500

# Method 2: Port forwarding
kubectl port-forward svc/flask-service 31500:5000
http://localhost:31500

# Update deployment after code changes
./scripts/deploy-local-k8s.sh

# Cleanup
./scripts/cleanup-local-k8s.sh
```

### Legacy Development Methods (Deprecated)

**⚠️ WARNING: Podman Compose is deprecated. Use Helm charts for all testing.**

```bash
# Podman Compose (DEPRECATED - Do not use)
podman-compose up -d           # NOT RECOMMENDED
podman-compose down            # NOT RECOMMENDED

# Direct Python (DEPRECATED - Use only for quick local debugging)
python run.py
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific categories
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests
pytest -m auth                  # Authentication tests
pytest -m backup                # Backup tests

# Single test
pytest tests/unit/test_backup_service.py::test_backup_creation

# Test Results: 621 tests passing, 80% coverage
```

### Health Checks

```bash
curl http://localhost:5000/health          # Basic health
curl http://localhost:5000/health/ready    # Readiness probe
curl http://localhost:5000/health/live     # Liveness probe
curl http://localhost:5000/health/metrics  # Prometheus metrics
```

---

## Architecture

### Data Model (Critical Understanding)

CCR uses a **nested document structure** with Platform arrays. Understanding this is essential:

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

**Row-Level Filtering Pattern:**
- UI displays flattened rows (one row per Platform+Environment combination)
- `DatabaseService.search_apis()` uses MongoDB aggregation pipelines with `$unwind`
- This pattern expands nested arrays into individual rows

**Standard Aggregation Pipeline:**
```python
pipeline = [
    {'$unwind': {'path': '$Platform', 'preserveNullAndEmptyArrays': False}},
    {'$unwind': {'path': '$Platform.Environment', 'preserveNullAndEmptyArrays': False}},
    {'$match': {...}},  # Filter condition
    {
        '$project': {
            'API Name': 1,
            'PlatformID': '$Platform.PlatformID',
            'Environment': '$Platform.Environment.environmentID',
            'Version': '$Platform.Environment.version',
            'Status': '$Platform.Environment.status',
            'LastUpdated': '$Platform.Environment.lastUpdated',
            'UpdatedBy': '$Platform.Environment.updatedBy',
            'Properties': '$Platform.Environment.Properties'
        }
    },
    {'$limit': limit}
]
```

This pattern is used throughout the codebase for all search and filtering operations.

### Layer Architecture

**Routes** (`app/routes/`)
- `main_routes.py` - Page routes (index, audit)
- `api_routes.py` - Search and suggestions endpoints
- `deploy_routes.py` - POST /api/deploy (create deployments)
- `update_routes.py` - PUT/PATCH/DELETE for environment updates
- `admin_routes.py` - Administrative endpoints (backup triggers, scheduler)
- `audit_routes.py` - Audit log queries and statistics
- `auth_routes.py` - JWT token generation and verification
- `health_routes.py` - Health checks and Prometheus metrics

**Services** (`app/services/`)
- `database.py` - Core MongoDB operations with aggregation pipeline logic
- `deploy_service.py` - Deployment orchestration and array manipulation
- `backup_service.py` - Automated MongoDB backups with APScheduler
- `audit_service.py` - Immutable audit log with 180-day retention
- `token_service.py` - JWT token management (access + refresh tokens)
- `auth_lockout_service.py` - Brute force protection

**Utils** (`app/utils/`)
- `validators.py` - Input validation with **STRICT** config-based checks
- `auth.py` - `@require_auth` decorator (AUTH_ENABLED=false in dev)
- `scheduler.py` - APScheduler wrapper for automated tasks
- `timezone_utils.py` - Timezone handling utilities
- `cache.py` - TTL-based caching (87.4% DB query reduction)

**Models** (`app/models/`)
- `api_model.py` - Data models and schemas

### Search Query Syntax

The search system supports multiple query types (implemented in `database.py:search_apis()`):

1. **Simple Text:** `user` - Word boundary search across API Name, Platform, Environment
2. **Attribute:** `Platform = IP4` - Exact match on specific field
3. **Logical AND:** `Platform = IP4 AND Environment = prd` - Multiple conditions
4. **Logical OR:** `Status = RUNNING OR Status = DEPLOYING` - Alternative conditions
5. **Comparison:** `Version >= 2.0` - Numeric/string comparison
6. **Contains:** `APIName contains user` - Substring search
7. **Properties:** `Properties : owner = team-alpha` - Nested property search

**SQL Injection Protection:** Frontend (`app/static/js/validation.js`) blocks SQL keywords while allowing legitimate AND/OR operators.

---

## Configuration & Validation

### Strict Validation Rules (`app/utils/validators.py`)

When validating deployment requests:
- **API Name:** 3-100 chars, alphanumeric + hyphen/underscore
- **Platform ID:** **STRICT** - Only values from `config.PLATFORM_MAPPING`
- **Environment ID:** **STRICT** - Only values from `config.ENVIRONMENT_MAPPING`
- **Status:** **STRICT** - Only values from `config.STATUS_OPTIONS`
- **Updated By:** 2-100 chars, supports full names with spaces, unicode, special chars
- **Properties:** **MANDATORY** - Must be valid JSON object (can be empty `{}`)

See `app/config.py` for complete mappings:
- Platforms: IP2-IP7, OpenShift, AWS, Azure, GCP, Alibaba, Kubernetes, Docker
- Environments: dev, tst, acc, stg, prd, prd-uitwijk, dr, uat, qa, sandbox
- Status: RUNNING, STOPPED, DEPLOYING, FAILED, MAINTENANCE, etc.

### Authentication Configuration (`app/config.py`)

- `AUTH_ENABLED=false` in development (controlled by environment variable)
- All endpoints decorated with `@require_auth` for production readiness
- JWT dual-token system (access + refresh tokens)
- Token blacklist and revocation mechanism
- Brute force protection with IP-based lockout

**Public Endpoints** (no authentication required):
- `/health`, `/health/ready`, `/health/live`, `/health/metrics`
- `/`, `/search`, `/static/`
- `/api/auth/*` (token endpoints)

### Backup System (`app/services/backup_service.py`)

- APScheduler runs daily backups (default: 2:00 AM)
- Retention: 14 days (configurable via `BACKUP_RETENTION_DAYS`)
- Storage: `/app/backups` (mounted volume in containers)
- Compression: gzip enabled by default

---

## Important Implementation Patterns

### Logical Operator Support (AND/OR)

The `DatabaseService._parse_logical_query()` method splits queries by AND/OR and builds MongoDB `$and`/`$or` conditions. Frontend validation **must allow** legitimate AND/OR in attribute queries while blocking SQL injection attempts.

### Excel-Like Column Filters (UI)

The UI implements Excel-like inline filters with dynamic table expansion:
- Filter dropdowns appear inline below column headers
- Table expands (`max-height: none`, `overflow: visible`) when filter opens
- Table restores (`max-height: 600px`, `overflow: auto`) when filter closes
- NO MODAL approach - better UX by keeping everything in context

**Implementation:** See `app/static/js/search.js:toggleFilterDropdown()` and `app/static/css/main.css`

### MongoDB Aggregation Pipeline Debugging

When debugging search or filtering issues:
1. Check `app/services/database.py:search_apis()`
2. Look for aggregation pipeline construction
3. Verify `$unwind`, `$match`, and `$project` stages
4. Test pipeline directly in MongoDB shell if needed

---

## CI/CD Pipeline Architecture

### Build Pipeline (Source Repository)

**Flow:** Code Push → Test → Build → Scan → Publish → Tag

**File:** `.gitlab-ci.yml` (296 lines)
**Stages:**
1. Test (3 jobs) - Unit tests, integration tests, lint
2. Build (1 job) - Multi-stage Docker build
3. Scan (2 jobs) - Trivy vulnerability scan + TruffleHog secret scan
4. Publish (1 job) - Push to Harbor registry (manual)
5. Tag (1 job) - Create git release tags (manual)

**Execution Time:** ~20-25 minutes

### Deployment Pipeline (Deployment Repository)

**Flow:** Set IMAGE_TAG → Validate → Deploy Env → Verify → Rollback

**File:** `deployment-gitlab-ci.yml` (510 lines)
**Stages:**
1. Validate (3 jobs) - Helm chart validation
2. Deploy DEV/TST/ACC/PRD (manual approval gates)
3. Verify (3 jobs) - Health checks and smoke tests
4. Rollback (3 jobs) - Emergency rollback (manual)

**Execution Time:** ~10-15 minutes per environment

### Version Strategy

**Main Branch:**
- Format: `MAJOR.MINOR.PATCH` (e.g., `2.0.0`)
- Source: `VERSION` file in repository
- Tags: Git tag `v2.0.0` + Docker tags `2.0.0` + `latest`

**Feature Branches:**
- Format: `{branch-name}-{short-sha}` (e.g., `feature-auth-abc123d`)
- Tags: Docker tag only (no git tag)

---

## Development Workflow

### Checkpoint-Based Development

This project follows a **strict checkpoint-based approach**:

1. **One feature at a time** - Complete implementation before starting next
2. **Test thoroughly** - Both unit and integration tests for each feature
3. **Commit before moving on** - Create checkpoint with clear commit message
4. **Complete files only** - Never provide code snippets, always full file contents

### Testing Standards

- Target: 70-80% coverage on critical paths
- Both unit tests (`tests/unit/`) and integration tests (`tests/integration/`)
- Test each feature thoroughly before moving to next milestone
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.backup`, `@pytest.mark.auth`

### File Management Rules

- Files in project are **source of truth**
- Before suggesting changes, **review ALL relevant files**
- Suggested changes **must match current codebase** situation

---

## Performance & Security

### Performance Optimizations

- **Database Indexing:** 29% query improvement
- **TTL-Based Caching:** 87.4% reduction in DB queries (cachetools)
- **gzip Compression:** 62.2% bandwidth savings
- **Performance Target:** P95 < 200ms @ 100 concurrent users
- **Achieved:** P95 160ms @ 100 concurrent users, 0% failures

### Security Features

- JWT Authentication with dual-token system
- Rate limiting (Flask-Limiter)
- Security headers (HSTS, CSP, X-Frame-Options via Talisman)
- Brute force protection with IP-based lockout
- Input validation against config-based mappings
- SQL injection protection
- Container security (non-root user, minimal base image)
- OWASP Top 10 compliant

---

## Documentation References

**Core Documentation:**
- `README.md` - General project overview and quick start
- `CHANGELOG.md` - Version history (semantic versioning)
- `SECURITY.md` - Security policy

**Operational Guides** (`docs/`):
- `BUILD_PIPELINE.md` - Complete build pipeline guide (809 lines)
- `DEPLOYMENT_PIPELINE.md` - Deployment guide (743 lines)
- `MAINTENANCE_GUIDE.md` - Operational procedures
- `TESTING_GUIDE.md` - Testing instructions
- `UPDATE_API_GUIDE.md` - API update procedures
- `openapi.yaml` - OpenAPI 3.0 specification (730+ lines)

**Historical Context** (`archive/`):
- `week-reports/` - Weekly completion reports
- `security-reports/` - Security audit reports
- `planning/` - Planning documents
- `session-notes/` - Session notes

---

## Troubleshooting

### Common Issues

**MongoDB Connection Failed:**
```bash
# Check MongoDB status
kubectl get statefulset mongodb
kubectl logs mongodb-0

# Verify connection string in config
echo $MONGO_URI
```

**Tests Failing:**
```bash
# Ensure MongoDB is running on localhost:27017
podman ps | grep mongo

# Check test configuration
cat tests/conftest.py
```

**Authentication Errors:**
```bash
# Check AUTH_ENABLED setting
echo $AUTH_ENABLED

# For development, set AUTH_ENABLED=false
export AUTH_ENABLED=false
```

**Rate Limiting Issues:**
```bash
# For testing, disable rate limiting
export RATELIMIT_ENABLED=false
```

---

## Project Context

- **Status:** Production-ready v2.0.0
- **Test Coverage:** 80% (621 tests passing)
- **Performance:** P95 160ms @ 100 concurrent users
- **Security:** OWASP Top 10 compliant
- **Deployment Method:** Kubernetes with Helm charts (kind cluster for local development)
- **CI/CD:** GitLab CI pipelines defined (build + deployment)

**Deployment Strategy:**
- **Primary:** Helm charts on kind cluster (production-ready testing)
- **Legacy:** Podman Compose (DEPRECATED - no longer used)
- **All changes must be tested on Kubernetes before considering them complete**

**Next Steps:** Infrastructure setup (GitLab Runner, Harbor registry) or additional UI improvements
