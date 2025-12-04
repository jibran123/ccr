# Common Configuration Repository (CCR) - Build Pipeline Documentation

## Overview

This document describes the CI/CD build pipeline for the Common Configuration Repository (CCR) source code repository. The pipeline automates testing, building, security scanning, and publishing Docker images to Harbor registry.

## Pipeline Architecture

### Repository Structure

```
Source Code Repository (this repo)
├── .gitlab-ci.yml          # Build pipeline definition
├── Dockerfile              # Multi-stage production Dockerfile
├── VERSION                 # Semantic version number
├── requirements.txt        # Python dependencies
├── app/                    # Application source code
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
└── BUILD_PIPELINE.md      # This document
```

### Pipeline Stages

The build pipeline consists of 5 stages:

1. **Test** - Run unit tests, integration tests, and code quality checks
2. **Build** - Build Docker image with proper versioning
3. **Scan** - Security scanning for vulnerabilities and secrets
4. **Publish** - Push image to Harbor registry
5. **Tag** - Create git tags for releases

```
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: TEST                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │ Unit Tests │  │Integration │  │ Lint/Code  │           │
│  │  (pytest)  │  │   Tests    │  │  Quality   │           │
│  └────────────┘  └────────────┘  └────────────┘           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: BUILD                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Docker Build (Multi-Stage)                          │  │
│  │  - Determine version (VERSION file or branch-SHA)    │  │
│  │  - Build image with tag                              │  │
│  │  - Save image as artifact                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 3: SCAN                                              │
│  ┌────────────┐  ┌────────────┐                            │
│  │   Trivy    │  │ TruffleHog │                            │
│  │Vulnerability│  │   Secret   │                            │
│  │  Scanning  │  │  Detection │                            │
│  └────────────┘  └────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 4: PUBLISH (Manual - main/master only)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Push to Harbor Registry                             │  │
│  │  harbor.yourcompany.com/ccr/ccr:VERSION │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 5: TAG (Manual - main/master only)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Create Git Tag (v{VERSION})                         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Versioning Strategy

### Main/Master Branch
- Uses semantic versioning from `VERSION` file
- Format: `MAJOR.MINOR.PATCH` (e.g., `2.0.0`)
- Image tag: `harbor.yourcompany.com/ccr/ccr:2.0.0`
- Also tagged as: `latest`

### Feature Branches
- Uses branch name + commit SHA
- Format: `{branch-name}-{short-sha}` (e.g., `feature-auth-abc123d`)
- Image tag: `harbor.yourcompany.com/ccr/ccr:feature-auth-abc123d`
- Not tagged as `latest`

### How to Update Version

1. Edit the `VERSION` file:
   ```bash
   echo "2.1.0" > VERSION
   ```

2. Commit the change:
   ```bash
   git add VERSION
   git commit -m "Bump version to 2.1.0"
   git push origin main
   ```

3. Pipeline will automatically use new version

4. After successful publish, manually trigger `tag:release` job to create git tag

## Pipeline Jobs

### Stage 1: Test

#### `test:unit`
- **Purpose**: Run unit tests with coverage reporting
- **Image**: `python:3.11-slim`
- **Commands**:
  ```bash
  pytest tests/unit/ -v --cov=app --cov-report=term --cov-report=xml
  ```
- **Coverage Target**: 80%+
- **Artifacts**: `coverage.xml` (1 week retention)
- **Triggers**: All branches, merge requests, tags

#### `test:integration`
- **Purpose**: Run integration tests with MongoDB
- **Image**: `python:3.11-slim`
- **Services**: `mongo:7.0`
- **Commands**:
  ```bash
  pytest tests/integration/ -v
  ```
- **Artifacts**: `test-results.xml` (JUnit format)
- **Triggers**: All branches, merge requests, tags

#### `test:lint`
- **Purpose**: Code quality checks (flake8, black, pylint)
- **Image**: `python:3.11-slim`
- **Failure**: Allowed (warnings only)
- **Triggers**: Branches, merge requests

### Stage 2: Build

#### `build:docker`
- **Purpose**: Build Docker image with proper versioning
- **Image**: `docker:24-dind`
- **Services**: `docker:24-dind`
- **Version Logic**:
  - Main/master: Read from `VERSION` file
  - Feature branches: `{branch}-{sha}`
- **Artifacts**: `image.tar` (1 day retention)
- **Tags Created**:
  - `{version}` - Specific version
  - `latest` - Only for main/master
- **Triggers**: All branches, merge requests, tags
- **Dependencies**: `test:unit`, `test:integration`

### Stage 3: Scan

#### `scan:trivy`
- **Purpose**: Vulnerability scanning of Docker image
- **Image**: `aquasec/trivy:0.48.0`
- **Severity Levels**: CRITICAL, HIGH
- **Artifacts**: `trivy-report.json` (30 days retention)
- **Exit Code**: 0 (report only, doesn't fail pipeline)
- **Triggers**: All branches, merge requests, tags
- **Dependencies**: `build:docker`

#### `scan:secrets`
- **Purpose**: Detect secrets in git history
- **Image**: `trufflesecurity/trufflehog:latest`
- **Artifacts**: `trufflehog-report.json` (30 days retention)
- **Failure**: Allowed (warning only)
- **Triggers**: All branches, merge requests

### Stage 4: Publish

#### `publish:harbor`
- **Purpose**: Push Docker image to Harbor registry
- **Image**: `docker:24-dind`
- **Registry**: `harbor.yourcompany.com`
- **Authentication**: Uses `HARBOR_USERNAME` and `HARBOR_PASSWORD` variables
- **Images Pushed**:
  - `harbor.yourcompany.com/ccr/ccr:{VERSION}`
  - `harbor.yourcompany.com/ccr/ccr:latest` (main/master only)
- **Triggers**: main, master, tags only
- **When**: Manual (requires human approval)
- **Dependencies**: `build:docker`, `scan:trivy`

### Stage 5: Tag

#### `tag:release`
- **Purpose**: Create git tag for the release
- **Image**: `alpine/git:latest`
- **Tag Format**: `v{VERSION}` (e.g., `v2.0.0`)
- **Triggers**: main, master only
- **When**: Manual (after successful publish)

## CI/CD Variables Required

Configure these variables in GitLab CI/CD settings:

### Harbor Registry Credentials
```
HARBOR_USERNAME = "robot$ccr-builder"
HARBOR_PASSWORD = "<robot-account-token>"
```

### Optional Overrides
```
HARBOR_REGISTRY = "harbor.yourcompany.com"  (default)
HARBOR_PROJECT = "ccr"                      (default)
IMAGE_NAME = "ccr"              (default)
PYTHON_VERSION = "3.11"                     (default)
TRIVY_VERSION = "0.48.0"                    (default)
```

## How to Set Up Harbor Robot Account

1. Log in to Harbor: `https://harbor.yourcompany.com`
2. Navigate to project: `ccr`
3. Go to "Robot Accounts" tab
4. Click "New Robot Account"
5. Configure:
   - Name: `ccr-builder`
   - Expiration: 365 days (or never)
   - Permissions:
     - ✅ Push Repository
     - ✅ Pull Repository
6. Copy the token and save to GitLab CI/CD variables

## Pipeline Workflow Examples

### Feature Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/new-endpoint
git push origin feature/new-endpoint

# 2. Pipeline runs automatically:
#    - test:unit ✓
#    - test:integration ✓
#    - test:lint ✓
#    - build:docker ✓ (builds feature-new-endpoint-abc123d)
#    - scan:trivy ✓
#    - scan:secrets ✓

# 3. Review results in GitLab CI/CD pipeline view

# 4. Fix any issues and push again
git add .
git commit -m "fix: address test failures"
git push origin feature/new-endpoint

# 5. Pipeline runs again with updates
```

### Production Release Workflow

```bash
# 1. Update version
echo "2.1.0" > VERSION
git add VERSION
git commit -m "chore: bump version to 2.1.0"
git push origin main

# 2. Pipeline runs automatically:
#    - test:unit ✓
#    - test:integration ✓
#    - test:lint ✓
#    - build:docker ✓ (builds harbor.yourcompany.com/ccr/ccr:2.1.0)
#    - scan:trivy ✓
#    - scan:secrets ✓
#    - publish:harbor ⏸️ (waiting for manual trigger)

# 3. Review scan results
#    - Check trivy-report.json for vulnerabilities
#    - Check test coverage reports
#    - Review code quality warnings

# 4. Manually trigger publish:harbor job in GitLab UI
#    - Go to pipeline view
#    - Click play button on publish:harbor job
#    - Job pushes image to Harbor

# 5. Verify image in Harbor:
#    - Login: harbor.yourcompany.com
#    - Navigate: ccr/ccr
#    - Confirm tag: 2.1.0 and latest

# 6. Manually trigger tag:release job
#    - Click play button on tag:release job
#    - Creates git tag: v2.1.0

# 7. Image is now ready for deployment pipeline to use
```

### Merge Request Workflow

```bash
# 1. Create merge request from feature branch to main

# 2. Pipeline runs for merge request:
#    - All test and scan jobs run
#    - Build job creates temporary image
#    - No publish to Harbor

# 3. Review pipeline results in MR

# 4. After MR approval and merge:
#    - New pipeline runs on main branch
#    - Can trigger publish:harbor manually
```

## Troubleshooting

### Test Failures

**Problem**: Unit tests failing
```
Solution:
1. Check test logs in GitLab CI/CD
2. Run tests locally:
   pytest tests/unit/ -v
3. Fix failing tests
4. Push changes
```

**Problem**: Integration tests failing with MongoDB connection error
```
Solution:
1. Verify MongoDB service is defined in .gitlab-ci.yml
2. Check MONGO_URI variable is correct
3. Ensure tests wait for MongoDB to be ready
```

### Build Failures

**Problem**: Docker build fails with dependency errors
```
Solution:
1. Check requirements.txt is up to date
2. Test build locally:
   docker build -t test .
3. Review build logs for specific error
```

**Problem**: VERSION file not found
```
Solution:
1. Ensure VERSION file exists in repository root
2. Check VERSION file is committed:
   git add VERSION
   git commit -m "Add VERSION file"
```

### Scan Failures

**Problem**: Trivy reports HIGH/CRITICAL vulnerabilities
```
Solution:
1. Review trivy-report.json artifact
2. Update base image if needed:
   FROM python:3.11-slim  # Use latest patch
3. Update Python dependencies:
   pip install --upgrade <vulnerable-package>
4. If no fix available, document as known issue
```

**Problem**: TruffleHog detects secrets
```
Solution:
1. Review trufflehog-report.json
2. If false positive, add to .trufflehogignore
3. If real secret:
   - Revoke the secret immediately
   - Remove from git history (git filter-repo)
   - Add to .gitignore
   - Use environment variables instead
```

### Publish Failures

**Problem**: Harbor authentication failed
```
Solution:
1. Verify HARBOR_USERNAME and HARBOR_PASSWORD variables
2. Check robot account token hasn't expired
3. Verify robot account has push permissions
4. Test credentials:
   docker login harbor.yourcompany.com -u <username> -p <password>
```

**Problem**: Image push failed - quota exceeded
```
Solution:
1. Contact Harbor administrator
2. Clean up old images in Harbor
3. Increase project quota
```

### Tag Failures

**Problem**: Git tag already exists
```
Solution:
1. Check if version was already tagged:
   git tag -l
2. If duplicate, update VERSION to next version
3. If need to replace tag:
   git tag -d v2.1.0
   git push origin :refs/tags/v2.1.0
   # Then re-run tag:release job
```

## Pipeline Performance

### Typical Execution Times

- **test:unit**: 2-3 minutes
- **test:integration**: 3-4 minutes
- **test:lint**: 1-2 minutes
- **build:docker**: 4-6 minutes
- **scan:trivy**: 2-3 minutes
- **scan:secrets**: 1-2 minutes
- **publish:harbor**: 2-3 minutes
- **tag:release**: <1 minute

**Total Pipeline Time (automatic stages)**: ~15-20 minutes
**Total Pipeline Time (with manual publish/tag)**: ~20-25 minutes

### Optimization Tips

1. **Use pipeline caching**: Already configured for pip and trivy caches
2. **Parallel execution**: Test jobs run in parallel automatically
3. **Docker layer caching**: Use multi-stage builds (already implemented)
4. **Artifact management**: Old artifacts auto-expire (1 day to 30 days)

## Security Best Practices

### Image Security
- ✅ Multi-stage build to minimize image size
- ✅ Non-root user (appuser) for runtime
- ✅ Security updates in base image
- ✅ Vulnerability scanning with Trivy
- ✅ Minimal base image (python:3.11-slim)

### Secret Management
- ✅ Harbor credentials stored in GitLab CI/CD variables (masked)
- ✅ Secret scanning with TruffleHog
- ✅ No secrets in Dockerfile or source code
- ✅ Environment variables for runtime secrets

### Code Quality
- ✅ Automated testing (unit + integration)
- ✅ Code coverage reporting (80% target)
- ✅ Linting and formatting checks
- ✅ Dependency management with requirements.txt

## Integration with Deployment Pipeline

Once an image is published to Harbor, the deployment pipeline can use it:

```yaml
# In deployment repository's .gitlab-ci.yml
deploy:dev:
  script:
    - IMAGE_TAG="2.1.0"
    - helm upgrade ccr ./helm/ccr \
        --set image.tag=${IMAGE_TAG} \
        --values values-dev.yaml
```

See `DEPLOYMENT_PIPELINE.md` in the deployment repository for details.

## Maintenance

### Weekly Tasks
- Review security scan reports
- Clean up old feature branch images in Harbor
- Monitor pipeline execution times
- Review and update dependencies

### Monthly Tasks
- Update base Docker images
- Review and update Python dependencies
- Rotate Harbor robot account credentials
- Review pipeline performance metrics

### Quarterly Tasks
- Update GitLab Runner version
- Review and optimize pipeline stages
- Security audit of pipeline configuration
- Update documentation

## Support

- **Pipeline Issues**: Contact DevOps team
- **Test Failures**: Contact development team
- **Harbor Access**: Contact infrastructure team
- **Documentation**: jibran@yourcompany.com

## References

- GitLab CI/CD Documentation: https://docs.gitlab.com/ee/ci/
- Docker Multi-Stage Builds: https://docs.docker.com/build/building/multi-stage/
- Trivy Documentation: https://aquasecurity.github.io/trivy/
- Harbor Documentation: https://goharbor.io/docs/
- Semantic Versioning: https://semver.org/
