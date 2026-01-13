#!/bin/bash
# Setup Cloudflare Tunnel on myca-api VM
# Run after setup_api_vm.sh

set -e

echo "=================================================="
echo "  Cloudflare Tunnel Setup"
echo "=================================================="

TUNNEL_NAME="mycosoft-tunnel"

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "Installing cloudflared..."
    curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    dpkg -i cloudflared.deb
    rm cloudflared.deb
fi

echo ""
echo "Step 1: Authenticate with Cloudflare"
echo "======================================"
echo "This will open a browser window to authenticate."
echo "If running headless, copy the URL and open in a browser."
echo ""
read -p "Press Enter to continue..."

cloudflared tunnel login

echo ""
echo "Step 2: Create Tunnel"
echo "====================="

# Check if tunnel already exists
if cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
    echo "Tunnel '$TUNNEL_NAME' already exists."
else
    echo "Creating tunnel '$TUNNEL_NAME'..."
    cloudflared tunnel create $TUNNEL_NAME
fi

# Get tunnel ID
TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
echo "Tunnel ID: $TUNNEL_ID"

echo ""
echo "Step 3: Configure Tunnel"
echo "========================"

# Create config directory
mkdir -p /etc/cloudflared

# Copy credentials
CRED_FILE=$(ls ~/.cloudflared/*.json 2>/dev/null | head -1)
if [ -n "$CRED_FILE" ]; then
    cp "$CRED_FILE" /etc/cloudflared/credentials.json
    chmod 600 /etc/cloudflared/credentials.json
    echo "Credentials copied to /etc/cloudflared/"
fi

# Create tunnel config
cat > /etc/cloudflared/config.yml << EOF
# Cloudflare Tunnel Configuration for mycosoft.com
tunnel: $TUNNEL_NAME
credentials-file: /etc/cloudflared/credentials.json

ingress:
  # Main website (Next.js on website VM)
  - hostname: mycosoft.com
    service: http://192.168.20.11:80
  
  - hostname: www.mycosoft.com
    service: http://192.168.20.11:80
  
  # Staging
  - hostname: staging.mycosoft.com
    service: http://192.168.20.11:80
  
  # MYCA API
  - hostname: api.mycosoft.com
    service: http://localhost:8001
  
  # Dashboard (staff only - protected by Cloudflare Access)
  - hostname: dashboard.mycosoft.com
    service: http://localhost:3100
  
  # N8N Webhooks
  - hostname: webhooks.mycosoft.com
    service: http://localhost:5678
    originRequest:
      noTLSVerify: true
  
  # Catch-all
  - service: http_status:404

originRequest:
  connectTimeout: 30s
  noTLSVerify: false
  keepAliveTimeout: 90s
  keepAliveConnections: 100
  http2Origin: true
EOF

echo "Config created at /etc/cloudflared/config.yml"

echo ""
echo "Step 4: Create DNS Routes"
echo "========================="

# Route DNS for each hostname
echo "Creating DNS routes..."
cloudflared tunnel route dns $TUNNEL_NAME mycosoft.com || true
cloudflared tunnel route dns $TUNNEL_NAME www.mycosoft.com || true
cloudflared tunnel route dns $TUNNEL_NAME staging.mycosoft.com || true
cloudflared tunnel route dns $TUNNEL_NAME api.mycosoft.com || true
cloudflared tunnel route dns $TUNNEL_NAME dashboard.mycosoft.com || true
cloudflared tunnel route dns $TUNNEL_NAME webhooks.mycosoft.com || true

echo ""
echo "Step 5: Install as Service"
echo "=========================="

cloudflared service install
systemctl enable cloudflared
systemctl start cloudflared

echo ""
echo "Step 6: Verify"
echo "=============="

sleep 3
systemctl status cloudflared --no-pager

echo ""
echo "=================================================="
echo "  Cloudflare Tunnel Setup Complete!"
echo "=================================================="
echo ""
echo "  Tunnel ID: $TUNNEL_ID"
echo "  Config: /etc/cloudflared/config.yml"
echo ""
echo "  DNS Records created for:"
echo "    - mycosoft.com"
echo "    - www.mycosoft.com"
echo "    - staging.mycosoft.com"
echo "    - api.mycosoft.com"
echo "    - dashboard.mycosoft.com"
echo "    - webhooks.mycosoft.com"
echo ""
echo "  Next steps:"
echo "    1. Verify at Cloudflare dashboard"
echo "    2. Test: curl https://mycosoft.com"
echo "    3. Set up Cloudflare Access for dashboard.mycosoft.com"
echo ""
