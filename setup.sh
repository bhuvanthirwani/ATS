#!/bin/bash

# Setup Script for ATS System

echo "🔧 Initializing ATS Workspace..."

# 1. Create Data Directory for Persistence
if [ ! -d "./data" ]; then
    echo "📂 Creating data directory..."
    mkdir -p ./data/users
    mkdir -p ./data/configs
else
    echo "✅ Data directory exists."
fi

# Add Docker's official GPG key:
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update -y

sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin tmux net-tools git -y

sudo docker run hello-world

# 2. Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  docker-compose not found, assuming 'docker compose' plugin is available."
fi

echo "✅ Environment Ready. Run ./docker_manager.sh build to start."
