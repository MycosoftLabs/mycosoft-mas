#!/bin/bash
# Cloudflare Tunnel Setup Script
# Run this on VM1 to setup Cloudflare tunnel

set -e

echo "=========================================="
echo "Cloudflare Tunnel Setup"
echo "=========================================="

# Install cloudflared
echo "[1/5] Installing cloudflared..."
if ! command -v cloudflared &> /dev/null; then
    wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    sudo dpkg -i cloudflared-linux-amd64.deb
    rm cloudflared-linux-amd64.deb
    echo "cloudflared installed"
else
    echo "cloudflared already installed"
fi

# Authenticate
echo "[2/5] Authenticating with Cloudflare..."
echo "Please login to Cloudflare in the browser that opens..."
cloudflared tunnel login

# Create tunnel
echo "[3/5] Creating tunnel..."
TUNNEL_NAME="mycosoft-production"
TUNNEL_OUTPUT=$(cloudflared tunnel create $TUNNEL_NAME 2>&1)
TUNNEL_ID=$(echo "$TUNNEL_OUTPUT" | grep -oP '(?<=Created tunnel )[a-f0-9-]+' || echo "")

if [ -z "$TUNNEL_ID" ]; then
    # Try to get existing tunnel ID
    TUNNEL_ID=$(cloudflared tunnel list | grep $TUNNEL_NAME | awk '{print $1}' || echo "")
fi

if [ -z "$TUNNEL_ID" ]; then
    echo "ERROR: Could not create or find tunnel. Please create manually."
    exit 1
fi

echo "Tunnel ID: $TUNNEL_ID"

# Create config directory
sudo mkdir -p /etc/cloudflared

# Create config file
echo "[4/5] Creating tunnel configuration..."
sudo tee /etc/cloudflared/config.yml > /dev/null <<EOF
tunnel: $TUNNEL_ID
credentials-file: /root/.cloudflared/$TUNNEL_ID.json

ingress:
  # Website
  - hostname: mycosoft.com
    service: http://localhost:3000
  - hostname: www.mycosoft.com
    service: http://localhost:3000
  
  # API endpoints (optional)
  - hostname: api.mycosoft.com
    service: http://localhost:8001
  
  # Catch-all
  - service: http_status:404
EOF

echo "Configuration saved to /etc/cloudflared/config.yml"

# Setup DNS routes
echo "[5/5] Setting up DNS routes..."
read -p "Setup DNS routes automatically? (y/n): " SETUP_DNS

if [ "$SETUP_DNS" = "y" ]; then
    cloudflared tunnel route dns $TUNNEL_NAME mycosoft.com || echo "DNS route for mycosoft.com may already exist"
    cloudflared tunnel route dns $TUNNEL_NAME www.mycosoft.com || echo "DNS route for www.mycosoft.com may already exist"
    echo "DNS routes configured"
else
    echo "Please configure DNS routes manually in Cloudflare dashboard:"
    echo "  - mycosoft.com -> $TUNNEL_ID"
    echo "  - www.mycosoft.com -> $TUNNEL_ID"
fi

# Install as systemd service
echo ""
echo "Installing cloudflared as systemd service..."
sudo cloudflared service install

# Start service
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Check status
echo ""
echo "=========================================="
echo "Cloudflare Tunnel Setup Complete!"
echo "=========================================="
echo ""
sudo systemctl status cloudflared --no-pager
echo ""
echo "Tunnel configuration: /etc/cloudflared/config.yml"
echo "Service status: sudo systemctl status cloudflared"
echo "View logs: sudo journalctl -u cloudflared -f"
