#!/bin/bash
# 🚀 GuideWire Production Deployment Script
# Use this script on your EC2 instance to deploy the latest version.

set -e

echo "📥 pulling latest changes (if using git)..."
# git pull origin main

echo "🏗️ building and starting services..."
docker compose up -d --build --remove-orphans

echo "🧹 cleaning up old images..."
docker image prune -f

echo "✅ deployment complete!"
echo "📡 access your dashboard at http://18.60.19.96"
echo "🩺 check health: http://18.60.19.96/health"
