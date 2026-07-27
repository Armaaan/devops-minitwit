#!/bin/bash
# deploy.sh
# Deploys ITU-MiniTwit with PostgreSQL + monitoring to the server.
# Session 05 task 4: idempotent — safe to run multiple times.
# Session 06: includes PostgreSQL + Prometheus + Grafana stack.
#
# Usage: ./deploy.sh
# Run from your local machine.

set -e

SERVER_IP="${SERVER_IP:-46.101.179.118}"
SERVER_USER="root"
APP_DIR="/minitwit"

echo "==> Deploying ITU-MiniTwit to $SERVER_IP..."

# ── Copy configuration files to server ───────────────────────────────────────
echo "==> Copying configuration files..."
ssh "$SERVER_USER@$SERVER_IP" "mkdir -p $APP_DIR/monitoring/prometheus $APP_DIR/monitoring/grafana/dashboards"

scp remote_files/docker-compose.yml "$SERVER_USER@$SERVER_IP:$APP_DIR/docker-compose.yml"
scp monitoring/prometheus/prometheus.yml "$SERVER_USER@$SERVER_IP:$APP_DIR/monitoring/prometheus/prometheus.yml"
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

# ── Wait for Grafana to be ready ─────────────────────────────────────────────
echo "==> Waiting for Grafana to start..."
sleep 15

# ── Import Grafana dashboard as code (session 06) ─────────────────────────────
echo "==> Importing Grafana dashboard..."
# Add Prometheus datasource if not exists
curl -s -X POST http://admin:admin@localhost:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{"name":"Prometheus","type":"prometheus","url":"http://prometheus:9090","access":"proxy","isDefault":true}' \
  2>/dev/null || true

# Get datasource UID
DS_UID=$(curl -s http://admin:admin@localhost:3000/api/datasources/name/Prometheus | python3 -c "import sys,json; print(json.load(sys.stdin).get('uid',''))" 2>/dev/null)

# Update dashboard JSON with correct UID and import
python3 -c "
import json, sys
with open('/minitwit/monitoring/grafana/dashboards/minitwit.json') as f:
    d = json.load(f)

def fix(obj, uid):
    if isinstance(obj, dict):
        if isinstance(obj.get('datasource'), dict):
            obj['datasource']['uid'] = uid
        if obj.get('type') == 'prometheus' and 'uid' in obj:
            obj['uid'] = uid
        for v in obj.values():
            fix(v, uid)
    elif isinstance(obj, list):
        for i in obj:
            fix(i, uid)

fix(d, '$DS_UID')
print(json.dumps(d))
" | curl -s -X POST http://admin:admin@localhost:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d "{\"dashboard\": $(cat), \"overwrite\": true, \"folderId\": 0}" 2>/dev/null || true

echo ""
echo "✓ Deployment complete!"
echo "  App:        http://$(curl -s ifconfig.me 2>/dev/null):5000"
echo "  Grafana:    http://$(curl -s ifconfig.me 2>/dev/null):3000"
echo "  Prometheus: http://$(curl -s ifconfig.me 2>/dev/null):9090"
docker compose ps
SSHEOF
