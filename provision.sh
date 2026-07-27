#!/bin/bash
# provision.sh
# Infrastructure as Code (IaC) for ITU-MiniTwit — Session 12
#
# Provisions a DigitalOcean droplet and deploys the full ITU-MiniTwit stack.
# Approach: Bash scripts using the DigitalOcean REST API (doctl-compatible).
#
# Pros of this approach:
#   - No extra tools required beyond bash and curl
#   - Full control over every API call
#   - Easy to read and understand
#   - Works on any OS with curl installed
#
# Cons of this approach:
#   - No state management (unlike Terraform)
#   - Not idempotent by default — running twice creates duplicate resources
#   - No dependency resolution between resources
#   - Error handling must be implemented manually
#
# Usage:
#   export DO_API_TOKEN=<your-digitalocean-api-token>
#   export SSH_KEY_ID=<your-ssh-key-id>
#   ./provision.sh
#
# To find your SSH key ID:
#   curl -X GET -H "Authorization: Bearer $DO_API_TOKEN" \
#     "https://api.digitalocean.com/v2/account/keys"

set -e

# ── Configuration ─────────────────────────────────────────────────────────────
DROPLET_NAME="minitwit"
REGION="fra1"
SIZE="s-1vcpu-2gb"
IMAGE="ubuntu-22-04-x64"
DOCKER_COMPOSE_VERSION="v2.24.0"
APP_DIR="/minitwit"
DOCKER_IMAGE="armaaan/devops-minitwit:latest"

# ── Validate required env vars ────────────────────────────────────────────────
if [ -z "$DO_API_TOKEN" ]; then
    echo "Error: DO_API_TOKEN environment variable is required" >&2
    echo "Usage: DO_API_TOKEN=<token> SSH_KEY_ID=<key_id> ./provision.sh" >&2
    exit 1
fi

if [ -z "$SSH_KEY_ID" ]; then
    echo "Error: SSH_KEY_ID environment variable is required" >&2
    echo "Find your key ID with:" >&2
    echo "  curl -X GET -H \"Authorization: Bearer \$DO_API_TOKEN\" https://api.digitalocean.com/v2/account/keys" >&2
    exit 1
fi

# ── Step 1: Create droplet ────────────────────────────────────────────────────
echo "==> Creating DigitalOcean droplet '$DROPLET_NAME' in $REGION..."

RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer $DO_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"$DROPLET_NAME\",
        \"region\": \"$REGION\",
        \"size\": \"$SIZE\",
        \"image\": \"$IMAGE\",
        \"ssh_keys\": [$SSH_KEY_ID],
        \"tags\": [\"minitwit\"]
    }" \
    "https://api.digitalocean.com/v2/droplets")

DROPLET_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['droplet']['id'])")

if [ -z "$DROPLET_ID" ]; then
    echo "Error: Failed to create droplet" >&2
    echo "$RESPONSE" >&2
    exit 1
fi

echo "==> Droplet created with ID: $DROPLET_ID"
echo "==> Waiting for droplet to become active..."

# ── Step 2: Wait for droplet to be active ────────────────────────────────────
while true; do
    STATUS=$(curl -s \
        -H "Authorization: Bearer $DO_API_TOKEN" \
        "https://api.digitalocean.com/v2/droplets/$DROPLET_ID" \
        | python3 -c "import sys,json; d=json.load(sys.stdin)['droplet']; print(d['status'])")

    if [ "$STATUS" = "active" ]; then
        break
    fi
    echo "    Status: $STATUS — waiting 5 seconds..."
    sleep 5
done

# ── Step 3: Get IP address ────────────────────────────────────────────────────
IP=$(curl -s \
    -H "Authorization: Bearer $DO_API_TOKEN" \
    "https://api.digitalocean.com/v2/droplets/$DROPLET_ID" \
    | python3 -c "
import sys, json
d = json.load(sys.stdin)['droplet']
for net in d['networks']['v4']:
    if net['type'] == 'public':
        print(net['ip_address'])
")

echo "==> Droplet is active at $IP"
echo "==> Waiting 30 seconds for SSH to become available..."
sleep 30

# ── Step 4: Install Docker and deploy the stack ───────────────────────────────
echo "==> Installing Docker and deploying MiniTwit..."

ssh -o StrictHostKeyChecking=no "root@$IP" << SSHEOF
set -e

echo "Installing Docker..."
apt-get update -q
apt-get install -y docker.io

mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

systemctl start docker
systemctl enable docker

echo "Deploying MiniTwit..."
mkdir -p $APP_DIR

cat > $APP_DIR/docker-compose.yml << 'COMPOSE'
services:
  minitwit:
    image: armaaan/devops-minitwit:latest
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://minitwit:minitwit@db:5432/minitwit
      - LATEST_FILE=/data/latest_processed_sim_action_id.txt
    volumes:
      - minitwit-data:/data
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=minitwit
      - POSTGRES_PASSWORD=minitwit
      - POSTGRES_DB=minitwit
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U minitwit"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  minitwit-data:
  postgres-data:
COMPOSE

cd $APP_DIR
docker compose pull
docker compose up -d

echo "MiniTwit deployed successfully!"
SSHEOF

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "✓ Provisioning complete!"
echo "  Droplet ID: $DROPLET_ID"
echo "  IP Address: $IP"
echo "  App URL:    http://$IP:5000"
echo ""
echo "Next steps:"
echo "  1. Point your domain DNS to $IP"
echo "  2. Run ./deploy.sh to deploy with monitoring and logging"
