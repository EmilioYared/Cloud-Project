# RAG API - Kubernetes Deployment Guide

FastAPI-based RAG application with ChromaDB, ready for k3s deployment on local or AWS EC2.

## Architecture

```
┌─────────────┐      ┌──────────────┐
│   rag-api   │─────▶│   ChromaDB   │
│  (FastAPI)  │      │ (VectorDB)   │
└─────────────┘      └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │     PVC      │
                     │  (Storage)   │
                     └──────────────┘
```

## Components

1. **rag-api**: FastAPI service for PDF ingestion and Q&A
2. **chromadb**: Vector database with persistent storage

## Prerequisites

- AWS EC2 instance (or local machine) with k3s
- Helm 3.x
- Docker
- kubectl configured
- Google Gemini API key

## AWS EC2 Setup

### 1. Launch EC2 Instance

**Recommended Specifications:**
- Instance Type: `t3.large` or `t3.xlarge` (2-4 vCPU, 8-16 GB RAM)
- AMI: Ubuntu 22.04 LTS
- Storage: 50 GB gp3 EBS volume
- Security Group: Allow ports 22 (SSH), 6443 (k3s API), 8000 (API access)

```bash
# Create security group
aws ec2 create-security-group \
  --group-name rag-api-sg \
  --description "Security group for RAG API on k3s"

# Add rules
aws ec2 authorize-security-group-ingress \
  --group-name rag-api-sg \
  --protocol tcp --port 22 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-name rag-api-sg \
  --protocol tcp --port 6443 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-name rag-api-sg \
  --protocol tcp --port 8000 --cidr 0.0.0.0/0

# Launch instance
aws ec2 run-instances \
  --image-id ami-0c7217cdde317cfec \
  --instance-type t3.large \
  --key-name your-key-pair \
  --security-groups rag-api-sg \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=50,VolumeType=gp3}'
```

### 2. Connect and Install k3s

```bash
# SSH into EC2 instance
ssh -i your-key.pem ubuntu@<ec2-public-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install k3s
curl -sfL https://get.k3s.io | sh -

# Configure kubectl
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
export KUBECONFIG=~/.kube/config

# Verify installation
kubectl get nodes
```

### 3. Install Docker

```bash
# Install Docker
sudo apt install -y docker.io
sudo usermod -aG docker $USER
newgrp docker

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Local Deployment (k3s)

### 1. Install k3s (if not installed)

```bash
curl -sfL https://get.k3s.io | sh -
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

### 2. Build and Deploy

```bash
# Set your API key
export GEMINI_API_KEY="your-api-key-here"

# Build image
docker build -t rag-api:latest .

# Import to k3s
docker save rag-api:latest | sudo k3s ctr images import -

# Deploy with Helm
helm install rag-api ./helm/rag-api \
  --set secrets.geminiApiKey="${GEMINI_API_KEY}"
```

### 3. Access the API

```bash
kubectl port-forward svc/rag-api 8000:8000
```

Visit: http://localhost:8000/docs

## AWS EC2 Deployment

### 1. Upload Project to EC2

From your local machine:

```bash
# Copy project files to EC2
scp -i your-key.pem -r . ubuntu@<ec2-public-ip>:~/rag-local/

# Or use git
ssh -i your-key.pem ubuntu@<ec2-public-ip>
git clone https://github.com/your-repo/rag-local.git
cd rag-local
```

### 2. Build Image on EC2

```bash
# On EC2 instance
cd rag-local

# Build Docker image
docker build -t rag-api:latest .

# Import to k3s
docker save rag-api:latest | sudo k3s ctr images import -

# Verify image
sudo k3s ctr images ls | grep rag-api
```

### 3. Deploy with Helm

```bash
# Set your API key
export GEMINI_API_KEY="your-api-key-here"

# Install Helm chart
helm install rag-api ./helm/rag-api \
  --set secrets.geminiApiKey="${GEMINI_API_KEY}" \
  --set image.repository=rag-api \
  --set image.tag=latest

# Check deployment
kubectl get pods
kubectl get svc
kubectl get pvc
```

### 4. Access the API

**Option A: Port forwarding (for testing)**
```bash
kubectl port-forward svc/rag-api 8000:8000
```
Then from local machine:
```bash
ssh -i your-key.pem -L 8000:localhost:8000 ubuntu@<ec2-public-ip>
```
Access at: http://localhost:8000

**Option B: NodePort (for external access)**

Create `ec2-values.yaml`:
```yaml
service:
  type: NodePort
  port: 8000
  nodePort: 30080

secrets:
  geminiApiKey: "your-api-key"
```

Deploy:
```bash
helm upgrade rag-api ./helm/rag-api -f ec2-values.yaml
```

Access at: `http://<ec2-public-ip>:30080`

**Option C: LoadBalancer with MetalLB (recommended for production)**

```bash
# Install MetalLB
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.12/config/manifests/metallb-native.yaml

# Configure IP address pool (use EC2 private IP)
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: default
  namespace: metallb-system
spec:
  addresses:
  - $(hostname -I | awk '{print $1}')/32
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: default
  namespace: metallb-system
EOF

# Set service type to LoadBalancer
helm upgrade rag-api ./helm/rag-api \
  --set service.type=LoadBalancer \
  --set secrets.geminiApiKey="${GEMINI_API_KEY}"
```

## Usage

### Upload Document

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf" \
  -F "doc_name=My Document"
```

### Ask Question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this about?",
    "doc_id": "uuid-from-upload"
  }'
```

## Configuration

### Environment Variables

- `CHROMA_HOST`: ChromaDB hostname (default: `chromadb`)
- `CHROMA_PORT`: ChromaDB port (default: `8000`)
- `GEMINI_API_KEY`: Google Gemini API key (required)

### Helm Values

See [helm/rag-api/values.yaml](helm/rag-api/values.yaml) for all options.

Key configurations:

```yaml
# Replicas
replicaCount: 1

# Resources
resources:
  limits:
    cpu: 2000m
    memory: 4Gi

# ChromaDB storage
chromadb:
  persistence:
    enabled: true
    size: 10Gi
    storageClass: ""  # Use default
```

## Monitoring

### Check Status

```bash
kubectl get pods
kubectl get svc
kubectl get pvc
```

### View Logs

```bash
# API logs
kubectl logs -l app.kubernetes.io/component=api -f

# ChromaDB logs
kubectl logs -l app.kubernetes.io/component=chromadb -f
```

### Health Checks

```bash
kubectl exec -it deployment/rag-api -- curl http://localhost:8000/health
kubectl exec -it deployment/rag-api -- curl http://chromadb:8000/api/v1/heartbeat
```

## Troubleshooting

### Pod not starting

```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### ChromaDB connection issues

```bash
# Test connection from API pod
kubectl exec -it deployment/rag-api -- curl http://chromadb:8000/api/v1/heartbeat

# Check ChromaDB service
# On EC2 instance
sudo k3s-uninstall.sh
```

### Terminate EC2 instance

```bash
# From local machine
aws ec2 terminate-instances --instance-ids <instance-id>
```

## Production Considerations for AWS EC2

1. **Elastic IP**: Attach an Elastic IP to your EC2 instance for consistent access
   ```bash
   aws ec2 allocate-address
   aws ec2 associate-address --instance-id <instance-id> --public-ip <elastic-ip>
   ```

2. **EBS Volume Snapshots**: Regular backups of persistent data
   ```bash
   aws ec2 create-snapshot --volume-id <volume-id> --description "RAG API backup"
   ```

3. **SSL/TLS with Let's Encrypt**:
   ```bash
   # Install cert-manager
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

4. **Secrets Management**: Store API keys in AWS Secrets Manager
   ```bash
   aws secretsmanager create-secret --name gemini-api-key --secret-string "your-key"
   ```

5. **Monitoring with Prometheus**: Install kube-prometheus-stack
   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/kube-prometheus-stack
   ```

6. **CloudWatch Logs**: Forward k3s logs to CloudWatch
   ```bash
   # Install CloudWatch agent
   wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
   sudo dpkg -i amazon-cloudwatch-agent.deb
   ```

7. **Auto-scaling**: Use AWS Auto Scaling Groups for multiple EC2 nodes

8. **Security**:
   - Use IAM roles instead of access keys
   - Enable VPC security groups
   - Regular security updates: `sudo apt update && sudo apt upgrade`
   - Use private subnets with NAT gateway for production

9. **Cost Optimization**:
   - Use Spot Instances for non-production
   - Schedule instance stop/start for dev environments
   - Use gp3 volumes instead of gp2

10. **Backup Strategy**:
    ```bash
    # Automated daily backups
    kubectl get pvc
    # Use Velero for k8s backup
    velero install --provider aws --bucket rag-backup --backup-location-config region=us-east-1
    ```
helm uninstall rag-api
```

### Delete PVC

```bash
kubectl delete pvc -l app.kubernetes.io/instance=rag-api
```

### Delete k3s cluster

```bash
sudo k3s-uninstall.sh
```

### Delete EKS cluster

```bash
eksctl delete cluster --name rag-api-cluster
```

## Production Considerations

1. **Secrets Management**: Use AWS Secrets Manager or HashiCorp Vault
2. **Ingress**: Configure proper ingress with SSL/TLS
3. **Monitoring**: Add Prometheus/Grafana
4. **Backups**: Regular PVC snapshots
5. **Autoscaling**: Enable HPA for the API
6. **Resource Limits**: Tune based on workload
7. **Network Policies**: Restrict pod-to-pod communication

## License

MIT
