#!/bin/bash
# Complete Local Kubernetes Deployment Simulation
# This script simulates a production deployment using kind with rootful podman

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "========================================="
echo "Production Simulation - Local K8s"
echo "========================================="
echo ""

# Step 1: Stop podman-compose services
print_step "Step 1: Stopping podman-compose services..."
if podman-compose ps | grep -q "Up"; then
    echo "  Stopping existing services..."
    podman-compose stop
    print_success "Podman-compose services stopped (not removed)"
else
    print_success "No podman-compose services running"
fi
echo ""

# Step 2: Check prerequisites
print_step "Step 2: Checking prerequisites..."

if ! command -v kubectl >/dev/null 2>&1; then
    print_error "kubectl not found. Please run: sudo bash install-k8s-tools.sh"
    exit 1
fi
print_success "kubectl found"

if ! command -v kind >/dev/null 2>&1; then
    print_error "kind not found. Please run: sudo bash install-k8s-tools.sh"
    exit 1
fi
print_success "kind found"

if ! command -v sudo >/dev/null 2>&1; then
    print_error "sudo not available"
    exit 1
fi
print_success "sudo available"

echo ""

# Step 3: Build Docker image
print_step "Step 3: Building Docker image..."
if podman images | grep -q "ccr-flask-app"; then
    print_success "Docker image ccr-flask-app:latest already exists"
else
    print_warning "Building Docker image..."
    podman build -f docker/Dockerfile -t ccr-flask-app:latest .
    print_success "Docker image built"
fi
echo ""

# Step 4: Create kind cluster with rootful podman
print_step "Step 4: Creating kind cluster (using rootful podman)..."

# Use full path for kind
KIND_BIN="/usr/local/bin/kind"

# Check if cluster already exists
if sudo KIND_EXPERIMENTAL_PROVIDER=podman $KIND_BIN get clusters 2>/dev/null | grep -q "^ccr-production$"; then
    print_warning "Cluster 'ccr-production' already exists, deleting..."
    sudo KIND_EXPERIMENTAL_PROVIDER=podman $KIND_BIN delete cluster --name ccr-production
    # Wait for cleanup
    sleep 3
fi

# Clean up any leftover kind containers
print_warning "Cleaning up any leftover containers..."
sudo podman ps -a | grep kind | awk '{print $1}' | xargs -r sudo podman rm -f 2>/dev/null || true
sleep 2

# Use a different port (31500 instead of 30500)
NODE_PORT=31500

# Create cluster with port mapping
sudo KIND_EXPERIMENTAL_PROVIDER=podman $KIND_BIN create cluster --name ccr-production --config - <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 30500
    hostPort: $NODE_PORT
    protocol: TCP
EOF

if [ $? -eq 0 ]; then
    print_success "Kind cluster created successfully"
else
    print_error "Failed to create kind cluster"
    exit 1
fi

# Copy kubeconfig for user access
sudo cp /root/.kube/config ~/.kube/config-ccr 2>/dev/null || true
sudo chown $(id -u):$(id -g) ~/.kube/config-ccr 2>/dev/null || true

echo ""

# Step 5: Load Docker image into kind
print_step "Step 5: Loading Docker image into kind..."
sudo KIND_EXPERIMENTAL_PROVIDER=podman $KIND_BIN load docker-image ccr-flask-app:latest --name ccr-production
if [ $? -eq 0 ]; then
    print_success "Docker image loaded into cluster"
else
    print_error "Failed to load Docker image"
    exit 1
fi
echo ""

# Step 6: Generate secrets
print_step "Step 6: Generating secrets..."
if [ -f "k8s/secrets.yaml" ]; then
    print_warning "secrets.yaml already exists, backing up..."
    sudo cp k8s/secrets.yaml k8s/secrets.yaml.backup 2>/dev/null || true
    sudo rm -f k8s/secrets.yaml 2>/dev/null || rm -f k8s/secrets.yaml
fi

SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
ADMIN_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
SECRET_KEY_B64=$(echo -n "$SECRET_KEY" | base64 -w 0)
JWT_SECRET_B64=$(echo -n "$JWT_SECRET" | base64 -w 0)
ADMIN_KEY_B64=$(echo -n "$ADMIN_KEY" | base64 -w 0)

cat > k8s/secrets.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: flask-secrets
  labels:
    app: ccr
type: Opaque
data:
  SECRET_KEY: "$SECRET_KEY_B64"
  JWT_SECRET_KEY: "$JWT_SECRET_B64"
  JWT_ADMIN_KEY: "$ADMIN_KEY_B64"
EOF

print_success "Secrets generated"
echo "  SECRET_KEY: $SECRET_KEY (base64: ${SECRET_KEY_B64:0:20}...)"
echo "  JWT_SECRET_KEY: $JWT_SECRET (base64: ${JWT_SECRET_B64:0:20}...)"
echo "  JWT_ADMIN_KEY: $ADMIN_KEY (base64: ${ADMIN_KEY_B64:0:20}...)"
echo ""

# Step 7: Deploy to Kubernetes
print_step "Step 7: Deploying to Kubernetes..."

export KUBECONFIG=~/.kube/config-ccr

echo "  → Applying ConfigMap..."
sudo kubectl apply -f k8s/configmap.yaml

echo "  → Applying Secrets..."
sudo kubectl apply -f k8s/secrets.yaml

echo "  → Applying Backup PVC..."
sudo kubectl apply -f k8s/backup-pvc.yaml

echo "  → Applying MongoDB Headless Service..."
sudo kubectl apply -f k8s/mongodb-headless-service.yaml

echo "  → Applying MongoDB StatefulSet..."
sudo kubectl apply -f k8s/mongodb-statefulset.yaml

echo "  → Waiting for MongoDB to be ready (timeout: 180s)..."
sudo kubectl wait --for=condition=ready pod -l component=mongodb --timeout=180s
if [ $? -eq 0 ]; then
    print_success "MongoDB is ready"
else
    print_error "MongoDB failed to start"
    echo ""
    echo "MongoDB logs:"
    sudo kubectl logs -l component=mongodb --tail=50
    exit 1
fi

echo "  → Applying MongoDB Service..."
sudo kubectl apply -f k8s/mongodb-service.yaml

echo "  → Applying Flask Deployment..."
sudo kubectl apply -f k8s/flask-deployment.yaml

echo "  → Waiting for Flask to be ready (timeout: 180s)..."
sudo kubectl wait --for=condition=ready pod -l component=flask --timeout=180s
if [ $? -eq 0 ]; then
    print_success "Flask is ready"
else
    print_error "Flask failed to start"
    echo ""
    echo "Flask logs:"
    sudo kubectl logs -l component=flask --tail=50
    exit 1
fi

echo "  → Applying Flask Service..."
sudo kubectl apply -f k8s/flask-service.yaml

echo "  → Applying HPA..."
sudo kubectl apply -f k8s/flask-hpa.yaml

print_success "All resources deployed successfully"
echo ""

# Step 8: Verify deployment
print_step "Step 8: Verifying deployment..."

echo ""
echo "Pods:"
sudo kubectl get pods -o wide

echo ""
echo "Services:"
sudo kubectl get svc

echo ""
echo "PVCs:"
sudo kubectl get pvc

echo ""
echo "HPA:"
sudo kubectl get hpa

echo ""

# Step 9: Test endpoints
print_step "Step 9: Testing application endpoints..."

echo "Waiting for service to be fully ready..."
sleep 10

# Get NodePort
SVC_NODE_PORT=$(sudo kubectl get svc flask-service -o jsonpath='{.spec.ports[0].nodePort}')
echo "Service NodePort: $SVC_NODE_PORT (mapped to host port: $NODE_PORT)"

# Test via localhost (kind exposes NodePort on localhost)
echo ""
echo "Testing /health/live endpoint..."
LIVE_RESPONSE=$(curl -s http://localhost:$NODE_PORT/health/live 2>/dev/null || echo "FAILED")
if echo "$LIVE_RESPONSE" | grep -q "alive"; then
    print_success "Liveness probe working"
    echo "  Response: $LIVE_RESPONSE"
else
    print_warning "Liveness probe not ready yet: $LIVE_RESPONSE"
fi

echo ""
echo "Testing /health/ready endpoint..."
READY_RESPONSE=$(curl -s http://localhost:$NODE_PORT/health/ready 2>/dev/null || echo "FAILED")
if echo "$READY_RESPONSE" | grep -q "ready"; then
    print_success "Readiness probe working"
    echo "  Response: $READY_RESPONSE"
else
    print_warning "Readiness probe not ready yet: $READY_RESPONSE"
fi

echo ""
echo "Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:$NODE_PORT/health 2>/dev/null || echo "FAILED")
if [ ! -z "$HEALTH_RESPONSE" ]; then
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        print_success "Health check working"
    else
        print_warning "Health check returned unexpected response"
    fi
else
    print_warning "Health endpoint not responding yet"
fi

echo ""

# Final summary
echo "========================================="
echo "Deployment Summary"
echo "========================================="
print_success "Production simulation complete!"
echo ""
echo "Your Kubernetes cluster is running with:"
echo "  • Cluster Name: ccr-production"
echo "  • Flask Pods: 2 replicas"
echo "  • MongoDB: StatefulSet with persistent storage"
echo "  • Auto-scaling: HPA enabled (2-5 replicas)"
echo ""
echo "Access your application:"
echo "  → http://localhost:$NODE_PORT"
echo ""
echo "Useful commands:"
echo "  # View all resources"
echo "  sudo kubectl get all -l app=ccr"
echo ""
echo "  # View Flask logs"
echo "  sudo kubectl logs -l component=flask -f"
echo ""
echo "  # View MongoDB logs"
echo "  sudo kubectl logs -l component=mongodb -f"
echo ""
echo "  # Describe a pod"
echo "  sudo kubectl describe pod <pod-name>"
echo ""
echo "  # Get pod shell"
echo "  sudo kubectl exec -it <pod-name> -- /bin/bash"
echo ""
echo "  # Check HPA status"
echo "  sudo kubectl get hpa flask-hpa --watch"
echo ""
echo "  # Scale manually"
echo "  sudo kubectl scale deployment flask-deployment --replicas=3"
echo ""
echo "To clean up:"
echo "  sudo KIND_EXPERIMENTAL_PROVIDER=podman /usr/local/bin/kind delete cluster --name ccr-production"
echo ""
echo "To restart podman-compose:"
echo "  podman-compose up -d"
echo ""
