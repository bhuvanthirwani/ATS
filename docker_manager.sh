#!/usr/bin/bash

# Configuration
IMAGE_NAME="devhaxcodes/ats-app:latest"
DOCKER_USER="devhaxcodes"
DOCKER_PASS="Docker@123"

echo "======================================"
echo "   ATS Docker Management Script"
echo "======================================"
echo "1) Build Image"
echo "2) Run Container (Local)"
echo "3) Push to Docker Hub"
echo "4) Pull from Docker Hub"
echo "5) Exit"
echo "======================================"
read -p "Select an option [1-5]: " choice

case $choice in
    1)
        echo "🚀 Building Docker image: $IMAGE_NAME..."
        docker build -t $IMAGE_NAME .
        ;;
    2)
        echo "🏃 Starting container using docker-compose..."
        docker compose up --no-build
        echo "✅ App is running at http://localhost:8501"
        ;;
    3)
        echo "🔑 Logging into Docker Hub..."
        echo "$DOCKER_PASS" | docker login --username "$DOCKER_USER" --password-stdin
        echo "⬆️ Pushing image: $IMAGE_NAME..."
        docker push $IMAGE_NAME
        ;;
    4)
        echo "⬇️ Pulling image: $IMAGE_NAME..."
        docker pull $IMAGE_NAME
        ;;
    5)
        echo "Bye!"
        exit 0
        ;;
    *)
        echo "❌ Invalid option"
        ;;
esac
