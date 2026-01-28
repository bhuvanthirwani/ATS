#!/usr/bin/bash

set -e

echo "======================================"
echo " Ubuntu 24 Server Setup Script"
echo " Docker + Compose + tmux + nginx"
echo " Proxy :80 -> localhost:8501"
echo "======================================"

# Must run as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Run as root or sudo"
  exit 1
fi

echo "🔄 Updating system..."
apt update && apt upgrade -y

echo "📦 Installing base packages..."
apt install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  git \
  ufw \
  tmux \
  nginx

# -----------------------------
# Docker Install
# -----------------------------

echo "🐳 Installing Docker..."

# Remove conflicting packages (Official Doc Recommendation)
echo "🧹 Removing potential conflicting packages..."
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do 
    apt-get remove -y $pkg || true
done

mkdir -p /etc/apt/keyrings

if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
     | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
fi

echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu \
$(lsb_release -cs) stable" \
| tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update

apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

echo "👤 Adding user to docker group..."
# Use SUDO_USER if available (when running with sudo), otherwise logname
REAL_USER=${SUDO_USER:-$(logname)}
if [ -n "$REAL_USER" ]; then
    usermod -aG docker "$REAL_USER"
    echo "   Added $REAL_USER to docker group."
else
    echo "   Could not determine non-root user. Skipping group add."
fi

# -----------------------------
# Firewall
# -----------------------------

echo "🔥 Configuring firewall..."

ufw allow OpenSSH
ufw allow 80
ufw allow 443
# Ensure external access to Streamlit is blocked (only via Nginx)
# If you want direct access, allow 8501: ufw allow 8501
ufw --force enable


echo ""
echo "✅ Setup Complete!"
echo ""
echo "➡ Logout & login again for docker group to apply:"
echo "   exit"
echo ""
echo "➡ Run your app:"
echo "   docker compose up -d"
echo ""
echo "➡ App should be reachable via:"
echo "   http://YOUR_IP_OR_DOMAIN"
echo ""
