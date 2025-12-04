#!/bin/bash
# Cleanup Local Kubernetes Deployment and Restart Podman-Compose

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

echo "========================================="
echo "Cleanup Local K8s & Restore Podman"
echo "========================================="
echo ""

# Step 1: Delete kind cluster
print_step "Step 1: Deleting kind cluster..."

KIND_BIN="/usr/local/bin/kind"

if sudo KIND_EXPERIMENTAL_PROVIDER=podman $KIND_BIN get clusters 2>/dev/null | grep -q "^ccr-production$"; then
    sudo KIND_EXPERIMENTAL_PROVIDER=podman $KIND_BIN delete cluster --name ccr-production
    print_success "Kind cluster deleted"
else
    print_success "No kind cluster found"
fi
echo ""

# Step 2: Clean up kubeconfig
print_step "Step 2: Cleaning up kubeconfig..."
if [ -f ~/.kube/config-ccr ]; then
    rm ~/.kube/config-ccr
    print_success "Kubeconfig removed"
else
    print_success "No kubeconfig to clean"
fi
echo ""

# Step 3: Backup and remove secrets.yaml
print_step "Step 3: Cleaning up generated secrets..."
if [ -f k8s/secrets.yaml ]; then
    echo "  Secrets.yaml will remain (in .gitignore)"
    print_success "Secrets preserved"
else
    print_success "No secrets to clean"
fi
echo ""

# Step 4: Restart podman-compose
print_step "Step 4: Restarting podman-compose..."
if podman-compose ps 2>/dev/null | grep -q "Exited\|stopped"; then
    podman-compose up -d
    print_success "Podman-compose services started"

    # Wait for services to be ready
    echo "  Waiting for services to be ready..."
    sleep 5

    # Check status
    if podman-compose ps | grep -q "Up"; then
        print_success "Services are running"
    fi
else
    podman-compose up -d
    print_success "Podman-compose services started"
fi
echo ""

# Step 5: Verify podman-compose
print_step "Step 5: Verifying podman-compose deployment..."
echo ""
podman-compose ps
echo ""

# Step 6: Test application
print_step "Step 6: Testing application..."
sleep 3

HEALTH=$(curl -s http://localhost:5000/health 2>/dev/null || echo "{}")
if echo "$HEALTH" | grep -q "healthy"; then
    print_success "Application is healthy"
    echo "$HEALTH" | python3 -m json.tool
else
    echo "  Waiting for application to start..."
    sleep 5
    HEALTH=$(curl -s http://localhost:5000/health 2>/dev/null || echo "{}")
    if echo "$HEALTH" | grep -q "healthy"; then
        print_success "Application is healthy"
        echo "$HEALTH" | python3 -m json.tool
    else
        echo -e "${YELLOW}⚠${NC} Application may still be starting..."
    fi
fi

echo ""
echo "========================================="
echo "Cleanup Complete"
echo "========================================="
echo ""
echo "Status:"
echo "  • Kubernetes cluster: Deleted"
echo "  • Podman-compose: Running"
echo "  • Application: http://localhost:5000"
echo ""
echo "Your development environment is restored!"
echo ""
