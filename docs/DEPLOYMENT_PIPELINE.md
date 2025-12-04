# Common Configuration Repository (CCR) - Deployment Pipeline Documentation

## Overview

This document describes the deployment pipeline for Common Configuration Repository (CCR). The deployment pipeline runs in a **separate deployment repository** and is responsible for deploying Docker images (built by the build pipeline) to Kubernetes clusters across multiple environments.

## Repository Structure

### Source Code Repository (ccr)
- Contains application code
- Build pipeline (`.gitlab-ci.yml`)
- Builds and publishes images to Harbor
- See `BUILD_PIPELINE.md` for details

### Deployment Repository (ccr-deployment)
```
ccr-deployment/
├── .gitlab-ci.yml              # Deployment pipeline (use deployment-gitlab-ci.yml)
├── helm/
│   └── ccr/       # Helm chart (copy from source repo)
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-dev.yaml
│       ├── values-tst.yaml
│       ├── values-acc.yaml
│       ├── values-prd.yaml
│       └── templates/
├── scripts/
│   ├── smoke-test.sh          # Smoke tests after deployment
│   └── integration-test.sh    # Integration tests
└── README.md
```

## Pipeline Architecture

### Deployment Flow

```
┌──────────────────────────────────────────────────────────────┐
│  TRIGGER: Manual or Automated                                 │
│  INPUT: IMAGE_TAG (e.g., "2.0.0")                            │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 1: VALIDATE                                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │  Lint      │  │  Template  │  │  Dry Run   │             │
│  │  Chart     │  │  Render    │  │  Apply     │             │
│  └────────────┘  └────────────┘  └────────────┘             │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 2: DEPLOY TO DEV (Manual)                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  helm upgrade --install ccr                │  │
│  │    --namespace ccr-dev                                 │  │
│  │    --values values-dev.yaml                            │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 3: DEPLOY TO TST (Manual, main branch only)           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  helm upgrade --install ccr                │  │
│  │    --namespace ccr-tst                                 │  │
│  │    --values values-tst.yaml                            │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 4: DEPLOY TO ACC (Manual, needs TST success)          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  helm upgrade --install ccr                │  │
│  │    --namespace ccr-acc                                 │  │
│  │    --values values-acc.yaml                            │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 5: DEPLOY TO PRD (Manual, needs ACC success)          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  - Verify image exists in Harbor                       │  │
│  │  - helm upgrade --install ccr              │  │
│  │    --namespace ccr-prd                                 │  │
│  │    --values values-prd.yaml                            │  │
│  │  - Save deployment metadata                            │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 6: VERIFY                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │  Health    │  │  Smoke     │  │  Monitor   │             │
│  │  Checks    │  │  Tests     │  │  Metrics   │             │
│  └────────────┘  └────────────┘  └────────────┘             │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 7: ROLLBACK (Manual, if needed)                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  helm rollback ccr                         │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Pipeline Stages

### Stage 1: Validate

#### `validate:chart`
- **Purpose**: Lint Helm chart for syntax errors
- **Command**: `helm lint ./helm/ccr`
- **Triggers**: All branches, merge requests, tags
- **Failure**: Blocks pipeline

#### `validate:manifests:dev`
- **Purpose**: Render and validate dev manifests
- **Commands**:
  ```bash
  helm template ccr ./helm/ccr \
    --values values-dev.yaml \
    --set image.tag=${IMAGE_TAG}
  kubectl apply --dry-run=client -f rendered-manifests-dev.yaml
  ```
- **Artifacts**: `rendered-manifests-dev.yaml` (1 week retention)
- **Triggers**: Branches, merge requests

#### `validate:manifests:prd`
- **Purpose**: Render and validate production manifests
- **Triggers**: main, master, tags only
- **Artifacts**: `rendered-manifests-prd.yaml` (1 week retention)

### Stage 2-5: Deploy to Environments

All deployment jobs follow the same pattern:

```bash
helm upgrade --install ${RELEASE_NAME} ${HELM_CHART_PATH} \
  --namespace ${NAMESPACE} \
  --create-namespace \
  --values ${HELM_CHART_PATH}/values-${ENV}.yaml \
  --set image.registry=${HARBOR_REGISTRY} \
  --set image.repository=${HARBOR_PROJECT}/${IMAGE_NAME} \
  --set image.tag=${IMAGE_TAG} \
  --wait \
  --timeout 5m \
  --atomic \
  --cleanup-on-fail
```

#### Flags Explained:
- `--upgrade --install`: Install if not exists, upgrade if exists
- `--create-namespace`: Create namespace if it doesn't exist
- `--wait`: Wait for all pods to be ready
- `--timeout 5m`: Maximum wait time
- `--atomic`: Rollback on failure
- `--cleanup-on-fail`: Delete resources if deployment fails

#### Environment Progression:

1. **DEV** (`deploy:dev`)
   - Namespace: `ccr-dev`
   - URL: `http://ccr-dev.yourcompany.com`
   - Trigger: Manual (any branch)
   - Purpose: Developer testing

2. **TST** (`deploy:tst`)
   - Namespace: `ccr-tst`
   - URL: `https://ccr-tst.yourcompany.com`
   - Trigger: Manual (main/master only)
   - Purpose: QA testing

3. **ACC** (`deploy:acc`)
   - Namespace: `ccr-acc`
   - URL: `https://ccr-acc.yourcompany.com`
   - Trigger: Manual (needs TST success)
   - Purpose: Acceptance/UAT testing

4. **PRD** (`deploy:prd`)
   - Namespace: `ccr-prd`
   - URL: `https://ccr.yourcompany.com`
   - Trigger: Manual (needs ACC success)
   - Purpose: Production
   - Additional checks:
     - Verifies image exists in Harbor
     - Saves deployment metadata

### Stage 6: Verify

#### `verify:dev`, `verify:tst`, `verify:prd`
- **Purpose**: Health check after deployment
- **Commands**:
  ```bash
  sleep 30  # Wait for stabilization
  curl -f https://ccr-${ENV}.yourcompany.com/health
  ```
- **Failure**: `allow_failure: true` (warning only for dev/tst)

### Stage 7: Rollback

#### `rollback:dev`, `rollback:tst`, `rollback:prd`
- **Purpose**: Rollback to previous Helm revision
- **Command**: `helm rollback ${RELEASE_NAME} --namespace ${NAMESPACE}`
- **Trigger**: Manual (emergency use)
- **Effect**: Restores previous deployment

## CI/CD Variables Required

Configure these variables in GitLab deployment repository settings:

### Required Variables

```bash
# Harbor Registry Credentials
HARBOR_USERNAME = "robot$ccr-deployer"
HARBOR_PASSWORD = "<robot-account-token>"

# Kubernetes Configuration
KUBECONFIG_CONTENT = "<base64-encoded-kubeconfig>"

# Harbor Registry Configuration
HARBOR_REGISTRY = "harbor.yourcompany.com"
HARBOR_PROJECT = "ccr"
IMAGE_NAME = "ccr"

# Deployment Image Tag (set per deployment)
IMAGE_TAG = "2.0.0"  # Update this before each deployment
```

### Optional Overrides

```bash
HELM_VERSION = "3.13.0"
HELM_TIMEOUT = "5m"
RELEASE_NAME = "ccr"
```

## Setting Up Deployment Repository

### Step 1: Create Deployment Repository

```bash
# Create new repository
mkdir ccr-deployment
cd ccr-deployment
git init
git remote add origin https://gitlab.yourcompany.com/devops/ccr-deployment.git
```

### Step 2: Copy Helm Chart

```bash
# Copy helm chart from source repository
cp -r /path/to/ccr/helm ./

# Commit helm chart
git add helm/
git commit -m "Add Helm chart for Common Configuration Repository (CCR)"
```

### Step 3: Setup GitLab CI/CD

```bash
# Copy deployment pipeline configuration
cp /path/to/ccr/deployment-gitlab-ci.yml .gitlab-ci.yml

# Commit pipeline configuration
git add .gitlab-ci.yml
git commit -m "Add deployment pipeline"
git push origin main
```

### Step 4: Configure GitLab Variables

1. Go to: GitLab → ccr-deployment → Settings → CI/CD → Variables

2. Add KUBECONFIG_CONTENT:
   ```bash
   # On your local machine with kubectl configured
   cat ~/.kube/config | base64 -w 0
   # Copy output and paste as KUBECONFIG_CONTENT variable
   ```

3. Add Harbor credentials (same as build pipeline)

4. Add IMAGE_TAG variable (initially set to latest stable version)

### Step 5: Setup GitLab Runner

Your GitLab runner on VM needs:

```bash
# Install Docker (for running pipeline containers)
sudo apt-get update
sudo apt-get install -y docker.io

# Install GitLab Runner
curl -L https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh | sudo bash
sudo apt-get install gitlab-runner

# Register runner
sudo gitlab-runner register \
  --url https://gitlab.yourcompany.com \
  --token <your-runner-token> \
  --executor docker \
  --docker-image alpine:latest \
  --description "ccr-deployment-runner" \
  --tag-list "deployment,kubernetes"

# Start runner
sudo gitlab-runner start
```

## Deployment Workflows

### Feature Branch Deployment to DEV

```bash
# 1. Developer wants to test feature branch
#    Go to deployment repository pipeline

# 2. Set IMAGE_TAG variable for this pipeline:
#    Settings → CI/CD → Variables → IMAGE_TAG
#    Set to: feature-auth-abc123d (from build pipeline)

# 3. Run pipeline for main branch

# 4. Manually trigger deploy:dev job

# 5. Wait for deployment and verification

# 6. Test feature at: http://ccr-dev.yourcompany.com
```

### Production Release Workflow

```bash
# 1. Image 2.1.0 has been built and published to Harbor
#    (via build pipeline)

# 2. Update IMAGE_TAG in deployment repository:
#    Go to Settings → CI/CD → Variables
#    Set IMAGE_TAG = "2.1.0"

# 3. Run pipeline on main branch

# 4. Deploy to TST:
#    - Manually trigger deploy:tst
#    - Wait for completion
#    - Verify deployment with verify:tst

# 5. Run smoke tests on TST:
#    - Manual testing by QA team
#    - Automated tests if available

# 6. Deploy to ACC:
#    - Manually trigger deploy:acc
#    - Wait for completion
#    - User acceptance testing

# 7. Deploy to PRODUCTION:
#    - Get approval from stakeholders
#    - Manually trigger deploy:prd
#    - Monitor deployment closely
#    - Verify deployment with verify:prd

# 8. Post-deployment:
#    - Monitor application metrics
#    - Check logs for errors
#    - Run smoke tests
#    - Update documentation
```

### Rollback Workflow

```bash
# If production deployment fails or has issues:

# 1. Immediately trigger rollback:prd job
#    This restores previous Helm revision

# 2. Verify rollback successful:
#    curl https://ccr.yourcompany.com/health

# 3. Investigate issue:
#    - Check Helm history: helm history ccr -n ccr-prd
#    - Check pod logs: kubectl logs -n ccr-prd deployment/ccr-flask
#    - Review deployment artifacts

# 4. Fix issue in source code

# 5. Re-run build pipeline with fix

# 6. Deploy fixed version following normal workflow
```

## Environment-Specific Configurations

### Development (DEV)
- **Values File**: `values-dev.yaml`
- **Characteristics**:
  - Single replica
  - Auth disabled
  - Minimal resources (128Mi memory, 50m CPU)
  - NodePort service (port 30500)
  - No auto-scaling
  - Latest image tag
- **Use Case**: Developer feature testing

### Test (TST)
- **Values File**: `values-tst.yaml`
- **Characteristics**:
  - 2 replicas
  - Auth enabled
  - Production-like resources
  - Ingress with staging TLS
  - Auto-scaling (2-4 replicas)
- **Use Case**: QA testing, integration testing

### Acceptance (ACC)
- **Values File**: `values-acc.yaml`
- **Characteristics**:
  - 2 replicas
  - Full security enabled
  - Production resources
  - Ingress with production TLS
  - Auto-scaling (2-5 replicas)
  - Monitoring enabled
- **Use Case**: UAT, pre-production testing

### Production (PRD)
- **Values File**: `values-prd.yaml`
- **Characteristics**:
  - 3 replicas (minimum)
  - Full security + network policies
  - Premium storage
  - Higher resource limits (1Gi memory, 1000m CPU)
  - Auto-scaling (3-10 replicas)
  - Monitoring + alerting
  - External secrets integration
- **Use Case**: Production workload

## Monitoring Deployments

### Check Deployment Status

```bash
# View Helm releases
helm list -A

# Check specific release
helm status ccr -n ccr-prd

# View Helm history
helm history ccr -n ccr-prd

# Check pod status
kubectl get pods -n ccr-prd -l app.kubernetes.io/instance=ccr

# View pod logs
kubectl logs -n ccr-prd -l app.kubernetes.io/component=flask --tail=100 -f

# Check HPA status
kubectl get hpa -n ccr-prd

# Check ingress
kubectl get ingress -n ccr-prd
```

### Health Checks

```bash
# Overall health
curl https://ccr.yourcompany.com/health

# Liveness probe
curl https://ccr.yourcompany.com/health/live

# Readiness probe
curl https://ccr.yourcompany.com/health/ready

# Application metrics
curl https://ccr.yourcompany.com/metrics
```

## Troubleshooting

### Deployment Hangs During Helm Install

**Problem**: `helm upgrade --install` times out waiting for pods

**Solution**:
```bash
# 1. Check pod status
kubectl get pods -n ccr-prd

# 2. Describe failing pod
kubectl describe pod <pod-name> -n ccr-prd

# 3. Common issues:
#    - ImagePullBackOff: Check image exists in Harbor
#    - CrashLoopBackOff: Check pod logs
#    - Pending: Check resource availability (CPU/memory/storage)

# 4. If needed, rollback manually
helm rollback ccr -n ccr-prd
```

### Image Not Found in Harbor

**Problem**: Deployment fails with ErrImagePull

**Solution**:
```bash
# 1. Verify image exists in Harbor
curl -u ${HARBOR_USERNAME}:${HARBOR_PASSWORD} \
  "https://harbor.yourcompany.com/api/v2.0/projects/ccr/repositories/ccr/artifacts/2.0.0"

# 2. Check image tag matches
#    IMAGE_TAG variable: 2.0.0
#    Harbor artifact tag: 2.0.0

# 3. Verify pull secrets
kubectl get secret harbor-registry-secret -n ccr-prd
kubectl get secret harbor-registry-secret -n ccr-prd -o yaml

# 4. Test image pull manually
kubectl run test-pull --image=harbor.yourcompany.com/ccr/ccr:2.0.0 \
  --image-pull-policy=Always --rm -it -- /bin/bash
```

### Health Checks Failing

**Problem**: verify:prd job fails with health check error

**Solution**:
```bash
# 1. Check if pods are running
kubectl get pods -n ccr-prd

# 2. Check service endpoints
kubectl get endpoints ccr-flask -n ccr-prd

# 3. Check ingress
kubectl describe ingress ccr -n ccr-prd

# 4. Test health endpoint directly from pod
kubectl exec -n ccr-prd deployment/ccr-flask -- curl localhost:5000/health

# 5. Check application logs
kubectl logs -n ccr-prd deployment/ccr-flask --tail=50
```

### Rollback Not Working

**Problem**: `helm rollback` fails or doesn't restore previous state

**Solution**:
```bash
# 1. Check Helm history
helm history ccr -n ccr-prd

# 2. Rollback to specific revision
helm rollback ccr 3 -n ccr-prd

# 3. If rollback fails, manually delete and reinstall
helm uninstall ccr -n ccr-prd
helm install ccr ./helm/ccr \
  --namespace ccr-prd \
  --values values-prd.yaml \
  --set image.tag=<previous-working-version>
```

### GitLab Runner Issues

**Problem**: Pipeline jobs stuck in "pending" state

**Solution**:
```bash
# 1. Check runner status on VM
sudo gitlab-runner status

# 2. Check runner logs
sudo journalctl -u gitlab-runner -f

# 3. Restart runner
sudo gitlab-runner restart

# 4. Verify runner registration
sudo gitlab-runner verify

# 5. Check runner tags match job requirements
#    Job: tags: ["deployment", "kubernetes"]
#    Runner: tag-list: "deployment,kubernetes"
```

## Security Considerations

### Secrets Management

1. **Never commit secrets to git**
   - Use GitLab CI/CD variables (masked)
   - Use Kubernetes secrets
   - Use external secret management (Azure Key Vault, Vault)

2. **KUBECONFIG Protection**
   - Base64 encode before storing
   - Use masked variable in GitLab
   - Limit access to CI/CD variables
   - Rotate credentials quarterly

3. **Harbor Credentials**
   - Use robot accounts (not personal accounts)
   - Minimum required permissions
   - Set expiration dates
   - Rotate regularly

### Network Security

1. **Ingress Configuration**
   - Use TLS for all non-dev environments
   - Valid certificates (Let's Encrypt or internal CA)
   - Redirect HTTP to HTTPS

2. **Network Policies**
   - Enable in production (`networkPolicy.enabled: true`)
   - Restrict pod-to-pod communication
   - Allow only necessary ingress/egress

### RBAC

1. **Service Account**
   - Dedicated service account per environment
   - Minimum required permissions
   - No cluster-admin access

2. **GitLab Runner**
   - Separate runner for deployment
   - Isolated from build runners
   - Tagged for deployment jobs only

## Performance Optimization

### Helm Deployment Speed

1. **Use `--atomic` flag**: Automatic rollback on failure
2. **Set appropriate `--timeout`**: 5m is usually sufficient
3. **Enable `--cleanup-on-fail`**: Removes resources on failure

### Image Pull Optimization

1. **imagePullPolicy**: Use `IfNotPresent` in production
2. **Image caching**: Kubernetes nodes cache images
3. **Private registry**: Harbor within firewall reduces pull time

### Resource Allocation

1. **Requests vs Limits**: Set appropriate values per environment
2. **Auto-scaling**: Configure HPA for production
3. **Resource quotas**: Set per namespace to prevent over-allocation

## Maintenance

### Daily Tasks
- Monitor deployment pipeline executions
- Review failed deployments and fix issues
- Check Kubernetes cluster health

### Weekly Tasks
- Review Helm release history
- Clean up old/failed releases
- Update IMAGE_TAG variable for dev/tst environments
- Review deployment logs

### Monthly Tasks
- Update Helm charts from source repository
- Review and update environment configurations
- Test rollback procedures
- Update deployment documentation

### Quarterly Tasks
- Rotate KUBECONFIG credentials
- Rotate Harbor robot account tokens
- Review and update network policies
- Disaster recovery drill

## Support

- **Deployment Issues**: Contact DevOps team
- **Application Issues**: Contact development team
- **Infrastructure Issues**: Contact infrastructure team
- **Documentation**: jibran@yourcompany.com

## References

- Helm Documentation: https://helm.sh/docs/
- Kubectl Documentation: https://kubernetes.io/docs/reference/kubectl/
- GitLab CI/CD: https://docs.gitlab.com/ee/ci/
- Harbor API: https://goharbor.io/docs/2.9.0/working-with-projects/working-with-images/pulling-pushing-images/
