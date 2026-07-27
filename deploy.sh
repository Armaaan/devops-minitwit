#!/bin/bash
# deploy.sh
# Deploys ITU-MiniTwit to the server.
# Session 05 task 4: idempotent — safe to run multiple times.
#
# Usage: ./deploy.sh
# Run on the server after provision.sh has set up the VM.

set -e

DOCKER_IMAGE="armaaan/devops-minitwit:latest"
APP_DIR="/minitwit"

echo "==> Starting ITU-MiniTwit deployment..."

# ── Install Docker if not already installed (idempotent) ─────────────────────
if ! command -v docker &> /dev/null; then
    echo "==> Installing Docker..."
    apt-get update -q
    apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker
else
    echo "==> Docker already installed: $(docker --version)"
fi

# ── Install Docker Compose plugin if not already installed (idempotent) ──────
if ! docker compose version &> /dev/null; then
    echo "==> Installing Docker Compose plugin..."
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
else
    echo "==> Docker Compose already installed: $(docker compose version)"
fi

# ── Create app directory if not exists (idempotent) ──────────────────────────
mkdir -p "$APP_DIR"

# ── Write docker-compose.yml (idempotent — overwrites with correct version) ──
cat > "$APP_DIR/docker-compose.yml" << 'COMPOSE'
services:
  minitwit:
    image: armaaan/devops-minitwit:latest
    ports:
      - "5000:5000"
    volumes:
      - minitwit-data:/data
    restart: unless-stopped

volumes:
  minitwit-data:
COMPOSE

# ── Pull latest image and restart (idempotent) ────────────────────────────────
echo "==> Pulling latest Docker image..."
cd "$APP_DIR"
docker pull "$DOCKER_IMAGE"

echo "==> Starting/restarting application..."
docker compose up -d --remove-orphans

# ── Clean up old images (idempotent) ─────────────────────────────────────────
docker image prune -f

echo ""
echo "✓ Deployment complete!"
echo "  App running at: http://$(curl -s ifconfig.me):5000"
docker compose ps
