#!/bin/bash

set -e

echo "======================================"
echo " Nginx Setup Script"
echo " Proxy :80 -> localhost:8501"
echo "======================================"

# Must run as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Run as root or sudo"
  exit 1
fi

echo "🧹 Clearing existing Nginx configurations..."
rm -f /etc/nginx/sites-enabled/*
rm -f /etc/nginx/sites-available/*

echo "🌐 Configuring Nginx reverse proxy..."

cat <<EOF >/etc/nginx/sites-available/ats.haxcodes.dev
server {
    listen 80;
    server_name ats.haxcodes.dev;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;

        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

ln -sf /etc/nginx/sites-available/ats.haxcodes.dev /etc/nginx/sites-enabled/

echo "🔍 Testing Nginx configuration..."
nginx -t

echo "🔄 Restarting Nginx..."
systemctl restart nginx

echo "✅ Nginx Setup Complete!"
