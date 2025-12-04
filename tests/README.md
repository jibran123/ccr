# Common Configuration Repository (CCR) - Test Suite Documentation

**Last Updated:** November 19, 2025
**Project:** Common Configuration Repository (CCR)
**Purpose:** Comprehensive testing framework for quality assurance and CI/CD integration

---

## Overview

This directory contains the complete test suite for the Common Configuration Repository (CCR). Tests are organized by type and functionality, following pytest best practices and designed for integration with CI/CD pipelines.

---

## Directory Structure

```
tests/
├── README.md                     # This file
├── conftest.py                   # Shared pytest fixtures and configuration
├── __init__.py
│
├── unit/                         # Unit tests (fast, isolated)
│   ├── test_backup_service.py
│   ├── test_scheduler.py
│   └── __init__.py
│
├── integration/                  # Integration tests (require app + DB)
│   ├── test_admin_routes.py
│   ├── test_api_core.py
│   ├── test_api_deploy.py
│   ├── test_api_update.py
│   └── __init__.py
│
├── security/                     # Security tests (Week 11-12)
│   ├── test_rate_limiting.py           # Rate limiting functionality
│   ├── test_security_headers.py        # HTTP security headers
│   ├── test_token_refresh.py           # Token refresh & revocation
│   ├── test_brute_force_protection.py  # Brute force protection
│   └── __init__.py
│
├── performance/                  # Performance tests (Week 9-10)
│   ├── test_caching.py           # Cache effectiveness
│   ├── test_compression.py       # Response compression
│   └── __init__.py
│
└── load/                         # Load/stress tests
    ├── locustfile.py             # Locust load testing configuration
    └── __init__.py
```

---

## Test Categories

### Unit Tests (`tests/unit/`)

**Purpose:** Test individual components in isolation
**Requirements:** None (mocked dependencies)
**Speed:** Very fast (<100ms per test)
**Markers:** `@pytest.mark.unit`

**Files:**
- `test_backup_service.py` - Backup/restore service logic
- `test_scheduler.py` - Background scheduler functionality

**Run unit tests only:**
```bash
pytest tests/unit/ -m unit
```

---

### Integration Tests (`tests/integration/`)

**Purpose:** Test components working together with real database
**Requirements:**
- Running Flask application (localhost:5000)
- MongoDB (localhost:27017)
**Speed:** Moderate (1-5 seconds per test)
**Markers:** `@pytest.mark.integration`

**Files:**
- `test_admin_routes.py` - Admin endpoints (audit logs, scheduler, backups)
- `test_api_core.py` - Core API operations (CRUD)
- `test_api_deploy.py` - Deployment operations
- `test_api_update.py` - Update operations

**Run integration tests:**
```bash
# Ensure application is running first
pytest tests/integration/ -m integration
```

---

### Security Tests (`tests/security/`)

**Purpose:** Test security features and vulnerabilities
**Requirements:**
- Running Flask application with security features enabled
- MongoDB for token/lockout storage
**Speed:** Moderate to slow (2-10 seconds per test)
**Markers:** `@pytest.mark.security`

**Files:**

1. **test_rate_limiting.py**
   - Tests Flask-Limiter rate limiting
   - Verifies per-endpoint limits
   - Checks rate limit headers
   - Tests 429 responses

2. **test_security_headers.py**
   - Tests Flask-Talisman headers
   - Verifies CSP, HSTS, X-Frame-Options
   - Checks CORS configuration
   - Tests information disclosure prevention

3. **test_token_refresh.py**
   - Tests JWT token generation
   - Verifies token refresh mechanism
   - Tests token revocation
   - Checks token blacklist
   - Tests logout functionality

4. **test_brute_force_protection.py**
   - Tests IP-based lockout
   - Verifies failed attempt tracking
   - Tests lockout trigger and duration
   - Checks MongoDB persistence

**Run security tests:**
```bash
pytest tests/security/ -m security
```

---

### Performance Tests (`tests/performance/`)

**Purpose:** Test performance optimizations
**Requirements:**
- Running Flask application
- MongoDB with data
**Speed:** Moderate (1-5 seconds per test)
**Markers:** `@pytest.mark.performance`

**Files:**

1. **test_caching.py**
   - Tests TTL-based caching (cachetools)
   - Verifies cache hit/miss performance
   - Tests cache consistency
   - Checks cache expiration

2. **test_compression.py**
   - Tests gzip compression effectiveness
   - Verifies compression headers
   - Tests bandwidth savings
   - Checks compression on various endpoints

**Run performance tests:**
```bash
pytest tests/performance/ -m performance
```

---

### Load Tests (`tests/load/`)

**Purpose:** Stress testing and load validation
**Requirements:**
- Running Flask application
- Locust installed (`pip install locust`)
**Speed:** Very slow (minutes to hours)
**Markers:** `@pytest.mark.load`

**Files:**
- `locustfile.py` - Locust configuration for load testing

**Run load tests:**
```bash
# Using Locust web interface
locust -f tests/load/locustfile.py --host=http://localhost:5000

# Headless mode
locust -f tests/load/locustfile.py --host=http://localhost:5000 \
       --users=100 --spawn-rate=10 --run-time=60s --headless
```

---

## Running Tests

### Prerequisites

1. **Install Dependencies:**
```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-timeout pytest-xdist
```

2. **Start Application:**
```bash
# Using podman-compose
./rebuild.sh

# Or manually
podman-compose up -d
```

3. **Verify Application:**
```bash
curl http://localhost:5000/health
```

---

### Basic Test Execution

**Run all tests:**
```bash
pytest
```

**Run specific test file:**
```bash
pytest tests/security/test_rate_limiting.py
```

**Run specific test function:**
```bash
pytest tests/security/test_rate_limiting.py::TestRateLimiting::test_health_endpoint_rate_limit
```

**Run tests with verbose output:**
```bash
pytest -v
```

**Run tests with detailed output:**
```bash
pytest -vv --showlocals
```

---

### Running Tests by Marker

**Run only unit tests:**
```bash
pytest -m unit
```

**Run only security tests:**
```bash
pytest -m security
```

**Run multiple marker types:**
```bash
pytest -m "unit or integration"
```

**Exclude slow tests:**
```bash
pytest -m "not slow"
```

**Run security tests excluding slow ones:**
```bash
pytest -m "security and not slow"
```

---

### Advanced Test Execution

**Run tests in parallel:**
```bash
# Requires pytest-xdist
pytest -n auto  # Use all CPU cores
pytest -n 4     # Use 4 workers
```

**Run with coverage report:**
```bash
# Requires pytest-cov
pytest --cov=app --cov-report=html --cov-report=term-missing
```

**Run with timeout:**
```bash
# Requires pytest-timeout
pytest --timeout=300  # 5 minute timeout per test
```

**Run tests with custom base URL:**
```bash
pytest --base-url=http://production-server:5000
```

**Stop on first failure:**
```bash
pytest -x
```

**Show test durations:**
```bash
pytest --durations=10  # Show 10 slowest tests
```

---

## Test Markers Reference

| Marker | Description | Usage |
|--------|-------------|-------|
| `unit` | Unit tests (fast, isolated) | `pytest -m unit` |
| `integration` | Integration tests (app + DB) | `pytest -m integration` |
| `security` | Security-related tests | `pytest -m security` |
| `performance` | Performance tests | `pytest -m performance` |
| `load` | Load/stress tests | `pytest -m load` |
| `slow` | Slow tests (>5 seconds) | `pytest -m "not slow"` |
| `skip_ci` | Skip in CI/CD | `pytest -m "not skip_ci"` |
| `requires_auth` | Needs authentication | Manual categorization |
| `requires_db` | Needs database | Manual categorization |

---

## Fixtures Reference

### Application Fixtures

- **`app`** - Flask application instance
- **`client`** - Flask test client
- **`base_url`** - Base URL for API testing (default: http://localhost:5000)

### Data Fixtures

- **`sample_api_data`** - Sample API deployment data
- **`sample_backup_data`** - Sample backup data
- **`temp_backup_dir`** - Temporary directory for backup tests

### Security Fixtures

- **`admin_headers`** - Headers with admin key
- **`security_headers`** - Common security headers
- **`valid_admin_key`** - Valid admin key
- **`invalid_admin_key`** - Invalid admin key (negative testing)
- **`test_user_credentials`** - User credentials dict
- **`test_admin_credentials`** - Admin credentials dict
- **`auth_token`** - Valid JWT token

### Mock Fixtures

- **`mock_mongodb`** - Mocked MongoDB collection

---

## Writing New Tests

### Test File Naming

- **Unit tests:** `test_<module_name>.py`
- **Integration tests:** `test_<feature>_routes.py` or `test_<feature>_integration.py`
- **Security tests:** `test_<security_feature>.py`
- **Performance tests:** `test_<optimization>.py`

### Test Class Naming

```python
class TestFeatureName:
    """Test suite for feature description."""

    def test_specific_behavior(self):
        """Test that specific behavior works correctly."""
        # Arrange
        # Act
        # Assert
        pass
```

### Using Markers

```python
import pytest

@pytest.mark.unit
def test_unit_example():
    """Example unit test."""
    pass

@pytest.mark.integration
@pytest.mark.requires_db
def test_integration_example(client):
    """Example integration test."""
    pass

@pytest.mark.security
@pytest.mark.slow
def test_security_example(base_url, admin_headers):
    """Example security test."""
    pass
```

### Using Fixtures

```python
def test_with_fixtures(client, sample_api_data, admin_headers):
    """Test using multiple fixtures."""
    response = client.post('/api/apis',
                          json=sample_api_data,
                          headers=admin_headers)
    assert response.status_code == 201
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mongodb:
        image: mongo:latest
        ports:
          - 27017:27017

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-timeout

      - name: Start application
        run: |
          export FLASK_ENV=development
          export AUTH_ENABLED=false
          python -m flask run &
          sleep 5

      - name: Run tests
        run: |
          # Run fast tests only (skip slow and load tests)
          pytest -m "not slow and not load" \
                 --cov=app \
                 --cov-report=xml \
                 --cov-report=term-missing

      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

---

## Test Maintenance

### Regular Tasks

1. **Review test failures** - Investigate and fix flaky tests
2. **Update fixtures** - Keep fixtures in sync with code changes
3. **Add tests for new features** - Maintain test coverage
4. **Archive obsolete tests** - Remove tests for deprecated features
5. **Performance review** - Ensure tests run efficiently

### Test Quality Checklist

- [ ] Tests are isolated (no dependencies between tests)
- [ ] Tests are deterministic (same input = same output)
- [ ] Tests are fast (unit tests <100ms, integration <5s)
- [ ] Tests have clear names describing behavior
- [ ] Tests use AAA pattern (Arrange-Act-Assert)
- [ ] Tests clean up resources (use fixtures with yield)
- [ ] Tests are well-documented with docstrings
- [ ] Tests use appropriate markers

---

## Troubleshooting

### Application Not Running

```bash
# Check if application is running
curl http://localhost:5000/health

# Check podman containers
podman ps

# Restart application
./rebuild.sh
```

### MongoDB Connection Issues

```bash
# Check MongoDB status
podman ps | grep mongo

# Check MongoDB logs
podman logs mongo

# Restart MongoDB
podman restart mongo
```

### Test Failures

**Rate limiting tests failing:**
- Ensure application has Flask-Limiter enabled
- Adjust test timing to account for rate limit windows
- Check for rate limit carryover between tests

**Authentication tests failing:**
- Verify `AUTH_ENABLED=true` in environment
- Check that admin key matches in tests and config
- Ensure MongoDB is storing tokens correctly

**Performance tests inconsistent:**
- Run tests multiple times to account for variance
- Check system load during testing
- Verify caching is enabled

---

## Archive Directory

The `scripts/archive/` directory contains old ad-hoc test scripts that have been converted to pytest. These are kept for reference but should not be used for regular testing.

**Archived files:**
- `test_rate_limiting.py` → Converted to `tests/security/test_rate_limiting.py`
- `test_security_headers.py` → Converted to `tests/security/test_security_headers.py`
- `test_token_refresh.py` → Converted to `tests/security/test_token_refresh.py`
- `test_brute_force.py` → Converted to `tests/security/test_brute_force_protection.py`
- `test_cache_performance.py` → Converted to `tests/performance/test_caching.py`
- `test_compression.py` → Converted to `tests/performance/test_compression.py`
- `performance_baseline.py` → Reference for performance benchmarks
- `manual_brute_force_test.sh` → Manual testing script

---

## Next Steps (Week 13-14)

1. **Increase coverage to 80%+**
   - Add unit tests for services
   - Add integration tests for all routes
   - Add edge case testing

2. **CI/CD Integration**
   - Set up automated testing pipeline
   - Configure coverage reporting
   - Add pre-commit hooks

3. **Test Enhancement**
   - Add parameterized tests
   - Add property-based testing
   - Add contract testing for APIs

---

**For questions or issues, refer to:**
- `CLAUDE.md` - Project overview and roadmap
- `WEEK_11-12_COMPLETION_REPORT.md` - Security enhancements
- `WEEK_9-10_COMPLETION_REPORT.md` - Performance optimizations
