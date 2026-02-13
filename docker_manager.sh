#!/usr/bin/env bash

# ATS Docker Manager
# Usage: ./docker_manager.sh [command]
# Commands: build, up, down, logs, restart, clean

# Configuration
DOCKER_USER="devhaxcodes"
DOCKER_PASS="Docker@123"
BACKEND_Image="devhaxcodes/ats-backend:latest"
FRONTEND_Image="devhaxcodes/ats-frontend:latest"

# Function to run docker compose command
compose_cmd() {
    if docker compose version >/dev/null 2>&1; then
        docker compose "$@"
    else
        docker-compose "$@"
    fi
}

show_menu() {
    echo "======================================"
    echo "   ATS Docker Management Script"
    echo "======================================"
    echo "1) 🏗️  Build Images (docker compose build)"
    echo "2) 🚀 Run Containers (docker compose up -d)"
    echo "3) 🛑 Stop Containers (docker compose down)"
    echo "4) 📜 View Logs (docker compose logs -f)"
    echo "5) ♻️  Restart (down + up)"
    echo "6) 🧹 Clean Data (down -v)"
    echo "7) ⬆️  Push to Docker Hub"
    echo "8) ⬇️  Pull from Docker Hub"
    echo "9) 🚪 Exit"
    echo "10) 🛠️  Run in Dev Mode (hot-reload)"
    echo "======================================"
}

execute_choice() {
    case $1 in
        1|build)
            echo "🔨 Building images..."
            compose_cmd build
            ;;
        2|up)
            echo "🚀 Starting services..."
            compose_cmd up
            echo "✅ Services started. Frontend at http://localhost:3000"
            ;;
        3|down)
            echo "🛑 Stopping services..."
            compose_cmd down
            ;;
        4|logs)
            echo "📜 Showing logs (Ctrl+C to exit)..."
            compose_cmd logs -f
            ;;
        5|restart)
            echo "♻️  Restarting..."
            compose_cmd down
            sleep 1
            compose_cmd up -d
            ;;
        6|clean)
            echo "⚠️  WARNING: This will delete the database volume."
            read -p "Are you sure? (y/N) " confirm
            if [[ $confirm =~ ^[Yy]$ ]]; then
                compose_cmd down -v
                echo "🧹 cleaned."
            fi
            ;;
        7|push)
            echo "🔑 Logging into Docker Hub..."
            echo "$DOCKER_PASS" | docker login --username "$DOCKER_USER" --password-stdin
            
            echo "🏷️  Tagging Images..."
            # Get Image IDs from compose
            BACKEND_ID=$(docker compose images -q backend)
            FRONTEND_ID=$(docker compose images -q frontend)
            
            if [ -z "$BACKEND_ID" ] || [ -z "$FRONTEND_ID" ]; then
                echo "❌ Could not find running images. Please build first (Option 1)."
            else
                docker tag "$BACKEND_ID" "$BACKEND_Image"
                docker tag "$FRONTEND_ID" "$FRONTEND_Image"
                
                echo "⬆️  Pushing Backend: $BACKEND_Image..."
                docker push "$BACKEND_Image"
                
                echo "⬆️  Pushing Frontend: $FRONTEND_Image..."
                docker push "$FRONTEND_Image"
                
                echo "✅ Done!"
            fi
            ;;
        8|pull)
            echo "🔑 Logging into Docker Hub..."
            echo "$DOCKER_PASS" | docker login --username "$DOCKER_USER" --password-stdin

            echo "⬇️  Pulling Backend: $BACKEND_Image..."
            docker pull "$BACKEND_Image"
            
            echo "⬇️  Pulling Frontend: $FRONTEND_Image..."
            docker pull "$FRONTEND_Image"
            
            echo "✅ Done! To run these, you may need to adjust docker-compose.yml to use 'image:' instead of 'build:', or manually tag them."
            ;;
        9)
            exit 0
            ;;
        10|dev)
            echo "🛠️  Starting in Dev Mode... (Cleaning up first)"
            # Force remove known named containers to prevent conflicts
            # We also try to remove by project name prefix just in case
            docker rm -f ats_core_backend ats_client_frontend ats_worker ats-redis-1 >/dev/null 2>&1
            docker rm -f /ats_client_frontend /ats_core_backend /ats_worker >/dev/null 2>&1
            compose_cmd down --remove-orphans
            compose_cmd -f docker-compose.yml -f docker-compose.dev.yml up --build
            ;;
        *)
            echo "❌ Invalid option."
            ;;
    esac
}

# Main logic
if [ -z "$1" ]; then
    # Interactive mode
    show_menu
    read -p "Select an option [1-7]: " choice
    execute_choice "$choice"
else
    # CLI mode
    execute_choice "$1"
fi
