#!/bin/bash
# provision.sh
# Provisions a DigitalOcean droplet for ITU-MiniTwit
# Session 03 task: encode VM creation — no clicking in UIs
#
# Usage: DO_API_TOKEN=<token> SSH_KEY_ID=<key_id> ./provision.sh
#
# To get your SSH key ID:
#   curl -X GET -H "Authorization: Bearer $DO_API_TOKEN" \
#     "https://api.digitalocean.com/v2/account/keys"

set -e

# ── Configuration ─────────────────────────────────────────────────────────────
DROPLET_NAME="minitwit"
REGION="fra1"
SIZE="s-1vcpu-1gb"
IMAGE="ubuntu-22-04-x64"

# ── Validate required env vars ────────────────────────────────────────────────
if [ -z "$DO_API_TOKEN" ]; then
    echo "Error: DO_API_TOKEN environment variable is required"
    echo "Usage: DO_API_TOKEN=<token> SSH_KEY_ID=<key_id> ./provision.sh"
    exit 1
fi

if [ -z "$SSH_KEY_ID" ]; then
    echo "Error: SSH_KEY_ID environment variable is required"
    echo "Find your key ID with:"
    echo "  curl -X GET -H \"Authorization: Bearer \$DO_API_TOKEN\" https://api.digitalocean.com/v2/account/keys"
    exit 1
fi

# ── Create droplet ────────────────────────────────────────────────────────────
echo "Creating DigitalOcean droplet '$DROPLET_NAME' in $REGION..."

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
    echo "Error: Failed to create droplet"
    echo "$RESPONSE"
    exit 1
fi

echo "Droplet created with ID: $DROPLET_ID"
echo "Waiting for droplet to become active..."

# ── Wait for droplet to be active and get IP ──────────────────────────────────
while true; do
    STATUS=$(curl -s \
        -H "Authorization: Bearer $DO_API_TOKEN" \
        "https://api.digitalocean.com/v2/droplets/$DROPLET_ID" \
        | python3 -c "import sys,json; d=json.load(sys.stdin)['droplet']; print(d['status'])")

    if [ "$STATUS" = "active" ]; then
        break
    fi
    echo "Status: $STATUS — waiting 5 seconds..."
    sleep 5
done

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

echo ""
echo "✓ Droplet is ready!"
echo "  Name:  $DROPLET_NAME"
echo "  ID:    $DROPLET_ID"
echo "  IP:    $IP"
echo "  Region: $REGION"
echo ""
echo "Next steps:"
echo "  1. SSH in:       ssh root@$IP"
echo "  2. Install Docker and deploy per README.md"
