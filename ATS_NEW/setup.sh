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

# 2. Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  docker-compose not found, assuming 'docker compose' plugin is available."
fi

echo "✅ Environment Ready. Run ./docker_manager.sh build to start."
