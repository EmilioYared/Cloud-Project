# RAG API Helm Chart

This Helm chart deploys a RAG (Retrieval-Augmented Generation) API with ChromaDB on Kubernetes.

## Components

- **rag-api**: FastAPI application for document upload and question answering
- **chromadb**: Vector database for storing document embeddings with persistent storage

## Prerequisites

- Kubernetes cluster (k3s, EKS, or any K8s distribution)
- Helm 3.x
- Docker (for building images)
- Google Gemini API key

## Quick Start

### 1. Build Docker Image

```bash
docker build -t rag-api:latest .
```

For k3s, import the image:
```bash
docker save rag-api:latest | sudo k3s ctr images import -
```

### 2. Create values file with your API key

Create `my-values.yaml`:
```yaml
secrets:
  geminiApiKey: "your-actual-api-key-here"

image:
  repository: rag-api
  tag: latest
```

### 3. Install the Helm chart

```bash
helm install rag-api ./helm/rag-api -f my-values.yaml
```

### 4. Check deployment status

```bash
kubectl get pods
kubectl get svc
```

### 5. Access the API

Port-forward to access locally:
```bash
kubectl port-forward svc/rag-api 8000:8000
```

Then access at: http://localhost:8000

## Configuration

### Key Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of API replicas | `1` |
| `image.repository` | API Docker image | `rag-api` |
| `image.tag` | Image tag | `latest` |
| `secrets.geminiApiKey` | Google Gemini API key | `""` |
| `chromadb.enabled` | Enable ChromaDB deployment | `true` |
| `chromadb.persistence.enabled` | Enable persistent storage | `true` |
| `chromadb.persistence.size` | PVC size | `10Gi` |
| `chromadb.persistence.storageClass` | Storage class | `""` (default) |

### AWS Deployment

For AWS EKS, specify storage class:

```yaml
chromadb:
  persistence:
    storageClass: gp3
    size: 20Gi
```

### Resource Limits

Adjust based on your workload:

```yaml
resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 500m
    memory: 2Gi

chromadb:
  resources:
    limits:
      cpu: 1000m
      memory: 2Gi
    requests:
      cpu: 250m
      memory: 512Mi
```

## Usage

### Upload a document

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf" \
  -F "doc_name=My Document"
```

Response:
```json
{
  "doc_id": "uuid-here",
  "doc_name": "My Document",
  "message": "PDF uploaded and ingested successfully"
}
```

### Ask a question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this document about?",
    "doc_id": "uuid-from-upload"
  }'
```

## Uninstall

```bash
helm uninstall rag-api
```

To also delete PVC:
```bash
kubectl delete pvc -l app.kubernetes.io/instance=rag-api
```

## Troubleshooting

Check logs:
```bash
kubectl logs -l app.kubernetes.io/component=api
kubectl logs -l app.kubernetes.io/component=chromadb
```

Check ChromaDB connection:
```bash
kubectl exec -it deployment/rag-api -- curl http://chromadb:8000/api/v1/heartbeat
```
