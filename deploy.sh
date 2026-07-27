#!/bin/bash
# deploy.sh
# Deploys ITU-MiniTwit with PostgreSQL + monitoring to the server.
# Session 05 task 4: idempotent — safe to run multiple times.
#
# Usage: ./deploy.sh
# Run from your local machine — it copies files and deploys remotely.
#
# Required environment variables:
#   SERVER_IP — IP address of the server (default: 46.101.179.118)

set -e

SERVER_IP="${SERVER_IP:-46.101.179.118}"
SERVER_USER="root"
APP_DIR="/minitwit"

echo "==> Deploying ITU-MiniTwit to $SERVER_IP..."

# ── Copy monitoring config files to server ───────────────────────────────────
echo "==> Copying configuration files..."
ssh "$SERVER_USER@$SERVER_IP" "mkdir -p $APP_DIR/monitoring/prometheus $APP_DIR/monitoring/grafana/provisioning/datasources $APP_DIR/monitoring/grafana/provisioning/dashboards $APP_DIR/monitoring/grafana/dashboards"

scp remote_files/docker-compose.yml "$SERVER_USER@$SERVER_IP:$APP_DIR/docker-compose.yml"
scp monitoring/prometheus/prometheus.yml "$SERVER_USER@$SERVER_IP:$APP_DIR/monitoring/prometheus/prometheus.yml"
scp monitoring/grafana/provisioning/datasources/datasources.yml "$SERVER_USER@$SERVER_IP:$APP_DIR/monitoring/grafana/provisioning/datasources/datasources.yml"
scp monitoring/grafana/provisioning/dashboards/dashboards.yml "$SERVER_USER@$SERVER_IP:$APP_DIR/monitoring/grafana/provisioning/dashboards/dashboards.yml"
scp monitoring/grafana/dashboards/minitwit.json "$SERVER_USER@$SERVER_IP:$APP_DIR/monitoring/grafana/dashboards/minitwit.json"

# ── Install Docker if not already installed (idempotent) ─────────────────────
ssh "$SERVER_USER@$SERVER_IP" << 'SSHEOF'
set -e

if ! command -v docker &> /dev/null; then
    echo "==> Installing Docker..."
    apt-get update -q
    apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker
else
    echo "==> Docker already installed: $(docker --version)"
fi

if ! docker compose version &> /dev/null; then
    echo "==> Installing Docker Compose plugin..."
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
else
    echo "==> Docker Compose already installed"
fi

# ── Pull and deploy ───────────────────────────────────────────────────────────
echo "==> Pulling latest images and deploying..."
cd /minitwit
docker compose pull
docker compose up -d --remove-orphans
docker image prune -f

echo ""
echo "✓ Deployment complete!"
echo "  App:        http://$(curl -s ifconfig.me):5000"
echo "  Grafana:    http://$(curl -s ifconfig.me):3000"
echo "  Prometheus: http://$(curl -s ifconfig.me):9090"
docker compose ps
SSHEOF
