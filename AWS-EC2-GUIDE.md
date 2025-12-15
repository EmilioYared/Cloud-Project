# RAG API - AWS EC2 with k3s Quick Start

Complete guide for deploying RAG API on AWS EC2 with k3s.

## Quick Deploy (Automated)

```bash
# Set required variables
export KEY_NAME="your-ec2-key-pair"
export GEMINI_API_KEY="your-gemini-api-key"

# Optional: customize instance
export INSTANCE_TYPE="t3.large"
export REGION="us-east-1"

# Run automated deployment
bash deploy-ec2.sh
```

This will:
1. Create security group with required ports
2. Launch EC2 instance (Ubuntu 22.04)
3. Install k3s, Docker, and Helm
4. Build and deploy RAG API
5. Output access URLs

## Manual Deployment

### Step 1: Launch EC2 Instance

```bash
# Create security group
aws ec2 create-security-group \
  --group-name rag-api-sg \
  --description "RAG API on k3s" \
  --region us-east-1

# Allow SSH, k3s API, and application ports
aws ec2 authorize-security-group-ingress --group-name rag-api-sg \
  --ip-permissions \
  IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges='[{CidrIp=0.0.0.0/0}]' \
  IpProtocol=tcp,FromPort=6443,ToPort=6443,IpRanges='[{CidrIp=0.0.0.0/0}]' \
  IpProtocol=tcp,FromPort=8000,ToPort=8000,IpRanges='[{CidrIp=0.0.0.0/0}]' \
  IpProtocol=tcp,FromPort=30080,ToPort=30080,IpRanges='[{CidrIp=0.0.0.0/0}]' \
  --region us-east-1

# Launch instance
aws ec2 run-instances \
  --image-id ami-0c7217cdde317cfec \
  --instance-type t3.large \
  --key-name your-key-pair \
  --security-groups rag-api-sg \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=50,VolumeType=gp3}' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=rag-api-k3s}]' \
  --region us-east-1
```

### Step 2: Connect and Setup

```bash
# SSH to instance
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>

# Install k3s
curl -sfL https://get.k3s.io | sh -
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config

# Install Docker
sudo apt update
sudo apt install -y docker.io
sudo usermod -aG docker $USER
newgrp docker

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Step 3: Deploy Application

```bash
# Clone/copy your project
git clone <your-repo> rag-local
cd rag-local

# Build image
docker build -t rag-api:latest .

# Import to k3s
docker save rag-api:latest | sudo k3s ctr images import -

# Deploy with Helm
export GEMINI_API_KEY="your-key"
helm install rag-api ./helm/rag-api \
  --set secrets.geminiApiKey="${GEMINI_API_KEY}" \
  --set service.type=NodePort \
  --set service.nodePort=30080

# Check status
kubectl get pods
```

### Step 4: Access API

**API URL**: `http://<EC2_PUBLIC_IP>:30080`

**Test endpoints**:
```bash
# Health check
curl http://<EC2_PUBLIC_IP>:30080/health

# API documentation
open http://<EC2_PUBLIC_IP>:30080/docs

# Upload document
curl -X POST http://<EC2_PUBLIC_IP>:30080/upload \
  -F "file=@document.pdf" \
  -F "doc_name=Test Document"

# Ask question
curl -X POST http://<EC2_PUBLIC_IP>:30080/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is this about?","doc_id":"<doc_id>"}'
```

## Instance Sizing

| Instance Type | vCPU | RAM | Best For | Monthly Cost |
|---------------|------|-----|----------|--------------|
| t3.medium | 2 | 4 GB | Testing | ~$30 |
| t3.large | 2 | 8 GB | Development | ~$60 |
| t3.xlarge | 4 | 16 GB | Production | ~$120 |
| t3.2xlarge | 8 | 32 GB | Heavy workload | ~$240 |

## Cost Optimization

### Use Elastic IP
```bash
# Allocate and associate
aws ec2 allocate-address --region us-east-1
aws ec2 associate-address --instance-id <instance-id> --public-ip <elastic-ip>
```

### Scheduled Stop/Start
```bash
# Stop during off-hours (save ~70% on compute)
aws ec2 stop-instances --instance-ids <instance-id>
aws ec2 start-instances --instance-ids <instance-id>

# Automate with Lambda
# Event: CloudWatch Events (cron)
# Actions: StopInstances at 18:00, StartInstances at 08:00
```

### Spot Instances
```bash
# Use spot instances for 70-90% discount (non-production)
aws ec2 request-spot-instances \
  --spot-price "0.05" \
  --instance-count 1 \
  --type "one-time" \
  --launch-specification file://spot-config.json
```

## Production Setup

### 1. Use Elastic IP (Static IP)
```bash
aws ec2 allocate-address
aws ec2 associate-address --instance-id <id> --public-ip <ip>
```

### 2. Setup Custom Domain
```bash
# Point your domain to Elastic IP
# A record: api.yourdomain.com -> <Elastic-IP>
```

### 3. Enable SSL with Let's Encrypt
```bash
# On EC2
sudo apt install -y certbot
sudo certbot certonly --standalone -d api.yourdomain.com

# Update Helm values
helm upgrade rag-api ./helm/rag-api \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=api.yourdomain.com
```

### 4. Configure CloudWatch Monitoring
```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure metrics
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s -c ssm:AmazonCloudWatch-linux
```

### 5. Setup Backups
```bash
# Automated snapshots
aws dlm create-lifecycle-policy \
  --description "Daily snapshots" \
  --state ENABLED \
  --execution-role-arn <role-arn> \
  --policy-details file://snapshot-policy.json
```

## Monitoring Commands

```bash
# SSH to instance
ssh -i your-key.pem ubuntu@<EC2_IP>

# Check k3s status
sudo systemctl status k3s

# Check pods
kubectl get pods -A

# View API logs
kubectl logs -l app.kubernetes.io/component=api -f

# View ChromaDB logs
kubectl logs -l app.kubernetes.io/component=chromadb -f

# Check resource usage
kubectl top nodes
kubectl top pods

# Check storage
df -h
kubectl get pvc
```

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Out of memory
```bash
# Upgrade instance type
aws ec2 stop-instances --instance-ids <id>
aws ec2 modify-instance-attribute --instance-id <id> --instance-type t3.xlarge
aws ec2 start-instances --instance-ids <id>
```

### Storage full
```bash
# Clean Docker
docker system prune -a

# Expand EBS volume
aws ec2 modify-volume --volume-id <vol-id> --size 100
sudo growpart /dev/xvda 1
sudo resize2fs /dev/xvda1
```

## Cleanup

```bash
# Uninstall app
helm uninstall rag-api

# Delete PVCs
kubectl delete pvc --all

# Terminate instance
aws ec2 terminate-instances --instance-ids <instance-id>

# Delete security group
aws ec2 delete-security-group --group-name rag-api-sg

# Release Elastic IP
aws ec2 release-address --allocation-id <allocation-id>
```

## Security Best Practices

1. **Restrict SSH**: Update security group to allow SSH only from your IP
2. **Use IAM Roles**: Attach IAM role to EC2 instead of access keys
3. **Enable VPC**: Run in private subnet with NAT gateway
4. **Update regularly**: `sudo apt update && sudo apt upgrade`
5. **Use Secrets Manager**: Store API keys in AWS Secrets Manager
6. **Enable CloudTrail**: Audit API calls
7. **Setup CloudWatch Alarms**: Monitor CPU, memory, disk usage

## Support

For issues:
1. Check logs: `kubectl logs -l app.kubernetes.io/component=api`
2. Verify connectivity: `kubectl exec -it deployment/rag-api -- curl chromadb:8000/api/v1/heartbeat`
3. Check resources: `kubectl describe pod <pod-name>`
