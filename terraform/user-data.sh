#!/bin/bash

# Update system
apt-get update
apt-get upgrade -y

# Install k3s
curl -sfL https://get.k3s.io | sh -

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Setup kubectl for ubuntu user
mkdir -p /home/ubuntu/.kube
cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config
chown -R ubuntu:ubuntu /home/ubuntu/.kube
chmod 600 /home/ubuntu/.kube/config

# Add to bashrc
echo 'export KUBECONFIG=~/.kube/config' >> /home/ubuntu/.bashrc

# Wait for k3s to be ready
sleep 30

# Note: Helm chart deployment should be done via CI/CD or manually
# This ensures the chart is available and reduces bootstrap complexity
