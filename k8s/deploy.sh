#!/bin/bash
# Production deployment script for Kubernetes

set -e

NAMESPACE="antigravity"
VERSION="${1:-3.0.0}"
REGISTRY="${2:-antigravity}"

echo "🚀 Deploying Antigravity Runtime v${VERSION}"
echo "Registry: ${REGISTRY}"
echo "Namespace: ${NAMESPACE}"
echo ""

# Step 1: Build and push image
echo "📦 Building Docker image..."
docker build -f Dockerfile.prod -t ${REGISTRY}/runtime:${VERSION} .
docker push ${REGISTRY}/runtime:${VERSION}

# Step 2: Create namespace if not exists
echo "📁 Setting up namespace..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace ${NAMESPACE}-sandbox --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Apply RBAC
echo "🔐 Setting up RBAC..."
kubectl apply -f k8s/rbac.yaml

# Step 4: Apply secrets (manual step - ensure secrets are set)
echo "🔑 Applying secrets..."
if kubectl get secret antigravity-secrets -n ${NAMESPACE} > /dev/null 2>&1; then
    echo "   Secrets already exist, skipping..."
else
    echo "   ⚠️  WARNING: Please set secrets manually:"
    echo "   kubectl apply -f k8s/secret.yaml"
fi

# Step 5: Apply ConfigMap
echo "⚙️  Applying configuration..."
kubectl apply -f k8s/configmap.yaml

# Step 6: Apply infrastructure
echo "🗄️  Setting up infrastructure..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/network-policies.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

# Step 7: Wait for infrastructure
echo "⏳ Waiting for infrastructure..."
kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n ${NAMESPACE} --timeout=300s

# Step 8: Apply application deployments
echo "🎬 Deploying application..."
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/brain-worker.yaml
kubectl apply -f k8s/tool-worker.yaml

# Step 9: Apply ingress
echo "🌐 Setting up ingress..."
kubectl apply -f k8s/ingress.yaml

# Step 10: Wait for rollout
echo "⏳ Waiting for deployment rollout..."
kubectl rollout status deployment/antigravity-api -n ${NAMESPACE} --timeout=300s
kubectl rollout status deployment/antigravity-brain-worker -n ${NAMESPACE} --timeout=300s
kubectl rollout status deployment/antigravity-tool-worker -n ${NAMESPACE} --timeout=300s

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access your application at:"
echo "   API: https://api.antigravity.ai"
echo "   App: https://app.antigravity.ai"
echo ""
echo "📊 Check status:"
echo "   kubectl get pods -n ${NAMESPACE}"
echo "   kubectl get svc -n ${NAMESPACE}"
echo "   kubectl logs -l app=antigravity-api -n ${NAMESPACE} --tail=100"