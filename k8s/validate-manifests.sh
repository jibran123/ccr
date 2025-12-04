#!/bin/bash
# Kubernetes Manifests Validation Script
# This script validates all K8s manifests without requiring a cluster

set -e

echo "========================================="
echo "Kubernetes Manifests Validation"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

MANIFEST_DIR="k8s"
ERRORS=0
WARNINGS=0

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        ((ERRORS++))
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# Check if manifest directory exists
if [ ! -d "$MANIFEST_DIR" ]; then
    echo -e "${RED}Error: $MANIFEST_DIR directory not found${NC}"
    exit 1
fi

echo "Step 1: YAML Syntax Validation"
echo "-----------------------------------"

# Check for Python (has yaml module)
if command_exists python3; then
    for file in $MANIFEST_DIR/*.yaml; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null
            if [ $? -eq 0 ]; then
                print_status 0 "YAML syntax valid: $filename"
            else
                print_status 1 "YAML syntax invalid: $filename"
            fi
        fi
    done
else
    print_warning "Python3 not found, skipping YAML syntax validation"
fi

echo ""
echo "Step 2: Manifest Structure Validation"
echo "-----------------------------------"

# Check required files exist
required_files=(
    "configmap.yaml"
    "secrets.yaml.template"
    "flask-deployment.yaml"
    "flask-service.yaml"
    "mongodb-statefulset.yaml"
    "mongodb-service.yaml"
    "mongodb-headless-service.yaml"
    "backup-pvc.yaml"
    "flask-hpa.yaml"
)

for file in "${required_files[@]}"; do
    if [ -f "$MANIFEST_DIR/$file" ]; then
        print_status 0 "Required file exists: $file"
    else
        print_status 1 "Required file missing: $file"
    fi
done

echo ""
echo "Step 3: Manifest Content Validation"
echo "-----------------------------------"

# Check Flask deployment
if [ -f "$MANIFEST_DIR/flask-deployment.yaml" ]; then
    # Check for required fields
    grep -q "kind: Deployment" "$MANIFEST_DIR/flask-deployment.yaml"
    print_status $? "Flask deployment has correct kind"

    grep -q "replicas: 2" "$MANIFEST_DIR/flask-deployment.yaml"
    print_status $? "Flask deployment has 2 replicas"

    grep -q "livenessProbe" "$MANIFEST_DIR/flask-deployment.yaml"
    print_status $? "Flask deployment has liveness probe"

    grep -q "readinessProbe" "$MANIFEST_DIR/flask-deployment.yaml"
    print_status $? "Flask deployment has readiness probe"

    grep -q "resources:" "$MANIFEST_DIR/flask-deployment.yaml"
    print_status $? "Flask deployment has resource limits"
fi

# Check MongoDB StatefulSet
if [ -f "$MANIFEST_DIR/mongodb-statefulset.yaml" ]; then
    grep -q "kind: StatefulSet" "$MANIFEST_DIR/mongodb-statefulset.yaml"
    print_status $? "MongoDB has correct kind (StatefulSet)"

    grep -q "serviceName: mongodb-headless" "$MANIFEST_DIR/mongodb-statefulset.yaml"
    print_status $? "MongoDB references headless service"

    grep -q "volumeClaimTemplates" "$MANIFEST_DIR/mongodb-statefulset.yaml"
    print_status $? "MongoDB has persistent volume template"
fi

# Check HPA
if [ -f "$MANIFEST_DIR/flask-hpa.yaml" ]; then
    grep -q "kind: HorizontalPodAutoscaler" "$MANIFEST_DIR/flask-hpa.yaml"
    print_status $? "HPA has correct kind"

    grep -q "minReplicas: 2" "$MANIFEST_DIR/flask-hpa.yaml"
    print_status $? "HPA has min replicas: 2"

    grep -q "maxReplicas: 5" "$MANIFEST_DIR/flask-hpa.yaml"
    print_status $? "HPA has max replicas: 5"
fi

# Check Services
if [ -f "$MANIFEST_DIR/flask-service.yaml" ]; then
    grep -q "type: NodePort" "$MANIFEST_DIR/flask-service.yaml"
    print_status $? "Flask service is NodePort type"
fi

if [ -f "$MANIFEST_DIR/mongodb-service.yaml" ]; then
    grep -q "type: ClusterIP" "$MANIFEST_DIR/mongodb-service.yaml"
    print_status $? "MongoDB service is ClusterIP type"
fi

echo ""
echo "Step 4: Security Validation"
echo "-----------------------------------"

# Check if secrets.yaml exists and is in .gitignore
if [ -f "$MANIFEST_DIR/secrets.yaml" ]; then
    if [ -f ".gitignore" ] && grep -q "k8s/secrets.yaml" ".gitignore"; then
        print_status 0 "secrets.yaml exists and is in .gitignore"
    else
        print_warning "secrets.yaml exists but not in .gitignore"
    fi
else
    print_status 0 "secrets.yaml doesn't exist (will be created from template)"
fi

# Check if secrets.yaml.template exists
if [ -f "$MANIFEST_DIR/secrets.yaml.template" ]; then
    print_status 0 "secrets.yaml.template exists"

    # Check if it contains placeholder values
    if grep -q "REPLACE_WITH_BASE64" "$MANIFEST_DIR/secrets.yaml.template"; then
        print_status 0 "Template contains placeholders (not real secrets)"
    else
        print_warning "Template might contain real secrets"
    fi
else
    print_status 1 "secrets.yaml.template is missing"
fi

echo ""
echo "Step 5: Configuration Validation"
echo "-----------------------------------"

# Check ConfigMap
if [ -f "$MANIFEST_DIR/configmap.yaml" ]; then
    grep -q "MONGO_HOST:" "$MANIFEST_DIR/configmap.yaml"
    print_status $? "ConfigMap has MONGO_HOST"

    grep -q "MONGO_PORT:" "$MANIFEST_DIR/configmap.yaml"
    print_status $? "ConfigMap has MONGO_PORT"

    grep -q "AUTH_ENABLED:" "$MANIFEST_DIR/configmap.yaml"
    print_status $? "ConfigMap has AUTH_ENABLED"
fi

echo ""
echo "========================================="
echo "Validation Summary"
echo "========================================="
echo -e "Errors:   ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All validations passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Create secrets.yaml from template"
    echo "2. Test deployment with minikube or kind"
    echo "3. Or commit and deploy to actual cluster"
    exit 0
else
    echo -e "${RED}✗ Validation failed with $ERRORS error(s)${NC}"
    echo "Please fix the errors before deploying"
    exit 1
fi
