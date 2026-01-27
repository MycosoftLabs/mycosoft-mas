#!/bin/bash
# Update Cloudflare Tunnel Configuration
# Date: January 27, 2026
# Purpose: Route n8n traffic to MAS VM (192.168.0.188) instead of localhost

# This script should be run on the Sandbox VM (192.168.0.187)

CONFIG_FILE="/opt/mycosoft/cloudflared/config.yml"
BACKUP_FILE="/opt/mycosoft/cloudflared/config.yml.bak.$(date +%Y%m%d)"

echo "=== Cloudflare Tunnel Configuration Update ==="
echo "Date: $(date)"
echo ""

# Backup existing config
if [ -f "$CONFIG_FILE" ]; then
    echo "[+] Backing up current config to $BACKUP_FILE"
    cp "$CONFIG_FILE" "$BACKUP_FILE"
else
    echo "[!] Config file not found at $CONFIG_FILE"
    echo "    Please update /etc/cloudflared/config.yml instead"
    CONFIG_FILE="/etc/cloudflared/config.yml"
fi

# Create updated config
cat > /tmp/cloudflared-config-new.yml << 'EOF'
# Cloudflare Tunnel Configuration
# Updated: January 27, 2026
# n8n moved from Sandbox to MAS VM

tunnel: YOUR_TUNNEL_ID_HERE
credentials-file: /opt/mycosoft/cloudflared/credentials.json

ingress:
  # Main website (stays on Sandbox VM)
  - hostname: sandbox.mycosoft.com
    service: http://localhost:3000
  
  - hostname: www.sandbox.mycosoft.com
    service: http://localhost:3000

  # n8n - NOW ROUTES TO MAS VM (192.168.0.188)
  - hostname: n8n.mycosoft.com
    service: http://192.168.0.188:5678

  # Grafana - routes to MAS VM
  - hostname: grafana.mycosoft.com
    service: http://192.168.0.188:3002

  # MAS Orchestrator API - routes to MAS VM
  - hostname: orchestrator.mycosoft.com
    service: http://192.168.0.188:8001

  # Catch-all
  - service: http_status:404
EOF

echo ""
echo "[i] New configuration prepared at /tmp/cloudflared-config-new.yml"
echo ""
echo "To apply the update, run:"
echo "  1. sudo cp /tmp/cloudflared-config-new.yml $CONFIG_FILE"
echo "  2. sudo systemctl restart cloudflared"
echo "  3. cloudflared tunnel info"
echo ""
echo "Or if using Docker:"
echo "  1. sudo cp /tmp/cloudflared-config-new.yml $CONFIG_FILE"
echo "  2. docker restart cloudflared"
echo ""
echo "Note: Replace YOUR_TUNNEL_ID_HERE with your actual tunnel ID"
EOF
