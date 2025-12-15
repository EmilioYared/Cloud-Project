#!/bin/bash

set -e

echo "=== RAG API Deployment Script ==="
echo ""

# Configuration
NAMESPACE="${NAMESPACE:-default}"
RELEASE_NAME="${RELEASE_NAME:-rag-api}"
IMAGE_NAME="${IMAGE_NAME:-rag-api}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"

if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY environment variable is required"
    echo "Usage: GEMINI_API_KEY=your-key ./deploy.sh"
    exit 1
fi

echo "Building Docker image..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo "Checking if running on k3s..."
if command -v k3s &> /dev/null; then
    echo "Detected k3s, importing image..."
    docker save ${IMAGE_NAME}:${IMAGE_TAG} | sudo k3s ctr images import -
else
    echo "Not running on k3s, skipping image import"
    echo "Make sure your image is available to your cluster"
fi

echo "Creating temporary values file..."
cat > /tmp/rag-values.yaml <<EOF
image:
  repository: ${IMAGE_NAME}
  tag: ${IMAGE_TAG}

secrets:
  geminiApiKey: "${GEMINI_API_KEY}"
EOF

echo "Installing/Upgrading Helm release..."
helm upgrade --install ${RELEASE_NAME} ./helm/rag-api \
    -f /tmp/rag-values.yaml \
    --namespace ${NAMESPACE} \
    --create-namespace \
    --wait

echo "Cleaning up temporary files..."
rm /tmp/rag-values.yaml

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Check status:"
echo "  kubectl get pods -n ${NAMESPACE}"
echo ""
echo "Access the API:"
echo "  kubectl port-forward -n ${NAMESPACE} svc/${RELEASE_NAME} 8000:8000"
echo ""
echo "View logs:"
echo "  kubectl logs -n ${NAMESPACE} -l app.kubernetes.io/component=api -f"
echo ""
