#!/bin/bash

# RAG API - AWS EC2 with k3s Deployment Script
# This script sets up the complete RAG API stack on AWS EC2

set -e

echo "=== RAG API AWS EC2 Deployment ==="
echo ""

# Configuration
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.large}"
KEY_NAME="${KEY_NAME:-}"
SECURITY_GROUP="${SECURITY_GROUP:-rag-api-sg}"
AMI_ID="${AMI_ID:-ami-0c7217cdde317cfec}"  # Ubuntu 22.04 LTS us-east-1
REGION="${REGION:-us-east-1}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"

# Validation
if [ -z "$KEY_NAME" ]; then
    echo "Error: KEY_NAME environment variable is required"
    echo "Usage: KEY_NAME=your-key-pair GEMINI_API_KEY=your-key ./deploy-ec2.sh"
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY environment variable is required"
    exit 1
fi

echo "Configuration:"
echo "  Instance Type: ${INSTANCE_TYPE}"
echo "  Key Name: ${KEY_NAME}"
echo "  Security Group: ${SECURITY_GROUP}"
echo "  Region: ${REGION}"
echo ""

# Check if security group exists
echo "Checking security group..."
if ! aws ec2 describe-security-groups --group-names ${SECURITY_GROUP} --region ${REGION} 2>/dev/null; then
    echo "Creating security group..."
    aws ec2 create-security-group \
        --group-name ${SECURITY_GROUP} \
        --description "Security group for RAG API on k3s" \
        --region ${REGION}
    
    # Add ingress rules
    echo "Adding ingress rules..."
    aws ec2 authorize-security-group-ingress \
        --group-name ${SECURITY_GROUP} \
        --protocol tcp --port 22 --cidr 0.0.0.0/0 \
        --region ${REGION}
    
    aws ec2 authorize-security-group-ingress \
        --group-name ${SECURITY_GROUP} \
        --protocol tcp --port 6443 --cidr 0.0.0.0/0 \
        --region ${REGION}
    
    aws ec2 authorize-security-group-ingress \
        --group-name ${SECURITY_GROUP} \
        --protocol tcp --port 8000 --cidr 0.0.0.0/0 \
        --region ${REGION}
    
    aws ec2 authorize-security-group-ingress \
        --group-name ${SECURITY_GROUP} \
        --protocol tcp --port 30080 --cidr 0.0.0.0/0 \
        --region ${REGION}
else
    echo "Security group ${SECURITY_GROUP} already exists"
fi

# Launch EC2 instance
echo ""
echo "Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id ${AMI_ID} \
    --instance-type ${INSTANCE_TYPE} \
    --key-name ${KEY_NAME} \
    --security-groups ${SECURITY_GROUP} \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=50,VolumeType=gp3}' \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=rag-api-k3s}]' \
    --region ${REGION} \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "Instance ID: ${INSTANCE_ID}"
echo "Waiting for instance to be running..."

aws ec2 wait instance-running --instance-ids ${INSTANCE_ID} --region ${REGION}

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids ${INSTANCE_ID} \
    --region ${REGION} \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "Instance is running at: ${PUBLIC_IP}"
echo "Waiting for SSH to be ready (this may take 2-3 minutes)..."
sleep 60

# Create deployment script for EC2
cat > /tmp/setup-k3s.sh <<'EOFSCRIPT'
#!/bin/bash
set -e

echo "=== Installing k3s ==="
curl -sfL https://get.k3s.io | sh -

echo "=== Configuring kubectl ==="
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
export KUBECONFIG=~/.kube/config

echo "=== Installing Docker ==="
sudo apt update
sudo apt install -y docker.io
sudo usermod -aG docker $USER

echo "=== Installing Helm ==="
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

echo "=== Setup complete ==="
kubectl get nodes
EOFSCRIPT

# Copy and execute setup script
echo ""
echo "Setting up k3s on EC2 instance..."
scp -o StrictHostKeyChecking=no -i ${KEY_NAME}.pem /tmp/setup-k3s.sh ubuntu@${PUBLIC_IP}:~/
ssh -o StrictHostKeyChecking=no -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP} 'bash ~/setup-k3s.sh'

# Copy project files
echo ""
echo "Copying project files..."
rsync -avz -e "ssh -i ${KEY_NAME}.pem -o StrictHostKeyChecking=no" \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude 'chroma_db' \
    --exclude 'uploads' \
    --exclude 'models' \
    --exclude '*.pyc' \
    ./ ubuntu@${PUBLIC_IP}:~/rag-local/

# Deploy application
cat > /tmp/deploy-app.sh <<EOFSCRIPT
#!/bin/bash
set -e
export KUBECONFIG=~/.kube/config

cd ~/rag-local

echo "=== Building Docker image ==="
docker build -t rag-api:latest .

echo "=== Importing image to k3s ==="
docker save rag-api:latest | sudo k3s ctr images import -

echo "=== Deploying with Helm ==="
helm install rag-api ./helm/rag-api \
    --set secrets.geminiApiKey="${GEMINI_API_KEY}" \
    --set image.repository=rag-api \
    --set image.tag=latest \
    --set service.type=NodePort \
    --set service.nodePort=30080

echo "=== Waiting for pods to be ready ==="
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=api --timeout=300s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=chromadb --timeout=300s

echo "=== Deployment status ==="
kubectl get pods
kubectl get svc
kubectl get pvc

echo ""
echo "=== Deployment Complete ==="
echo "API URL: http://${PUBLIC_IP}:30080"
echo "Health check: http://${PUBLIC_IP}:30080/health"
echo "API docs: http://${PUBLIC_IP}:30080/docs"
EOFSCRIPT

echo ""
echo "Deploying application..."
scp -i ${KEY_NAME}.pem /tmp/deploy-app.sh ubuntu@${PUBLIC_IP}:~/
ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP} "bash ~/deploy-app.sh"

# Cleanup temp files
rm /tmp/setup-k3s.sh /tmp/deploy-app.sh

echo ""
echo "=========================================="
echo "=== AWS EC2 Deployment Complete! ==="
echo "=========================================="
echo ""
echo "Instance Details:"
echo "  Instance ID: ${INSTANCE_ID}"
echo "  Public IP: ${PUBLIC_IP}"
echo "  SSH: ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP}"
echo ""
echo "API Access:"
echo "  URL: http://${PUBLIC_IP}:30080"
echo "  Health: http://${PUBLIC_IP}:30080/health"
echo "  Docs: http://${PUBLIC_IP}:30080/docs"
echo ""
echo "Useful Commands:"
echo "  Check status: ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP} 'kubectl get pods'"
echo "  View logs: ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP} 'kubectl logs -l app.kubernetes.io/component=api'"
echo "  Uninstall: ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP} 'helm uninstall rag-api'"
echo ""
echo "To terminate instance:"
echo "  aws ec2 terminate-instances --instance-ids ${INSTANCE_ID} --region ${REGION}"
echo ""
