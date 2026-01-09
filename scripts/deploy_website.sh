#!/bin/bash
# Deploy Next.js Website to Production
# Run this on the Website VM

set -e

DEPLOY_DIR="/opt/mycosoft-website"
REPO_URL="https://github.com/mycosoft/mycosoft-mas.git"
BRANCH="main"
NAS_MOUNT="/mnt/mycosoft"

echo "=========================================="
echo "  Mycosoft.com Website Deployment"
echo "=========================================="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo"
    exit 1
fi

# ==============================================
# Prerequisites Check
# ==============================================
echo "Checking prerequisites..."

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi
echo "Node.js version: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "ERROR: npm not found"
    exit 1
fi
echo "npm version: $(npm --version)"

# Check nginx
if ! command -v nginx &> /dev/null; then
    echo "Installing nginx..."
    apt-get update
    apt-get install -y nginx
fi
echo "nginx version: $(nginx -v 2>&1)"

# Check NAS mount
if ! mountpoint -q "$NAS_MOUNT"; then
    echo "WARNING: NAS not mounted at $NAS_MOUNT"
    echo "Website static assets may not persist"
fi

# ==============================================
# Clone/Update Repository
# ==============================================
echo ""
echo "Setting up deployment directory..."

if [ -d "$DEPLOY_DIR" ]; then
    echo "Updating existing deployment..."
    cd "$DEPLOY_DIR"
    git fetch origin
    git reset --hard origin/$BRANCH
else
    echo "Cloning repository..."
    git clone --branch $BRANCH $REPO_URL "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

# ==============================================
# Build Website
# ==============================================
echo ""
echo "Building website..."

# Navigate to dashboard directory
cd "$DEPLOY_DIR/unifi-dashboard"

# Install dependencies
echo "Installing dependencies..."
npm ci --production=false

# Create production environment file
echo "Creating production environment..."
cat > .env.production.local << EOF
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://api.mycosoft.com
NEXT_PUBLIC_MAS_URL=https://api.mycosoft.com
MAS_BACKEND_URL=http://127.0.0.1:8001
N8N_WEBHOOK_URL=http://127.0.0.1:5678/webhook/myca/speech
EOF

# Build
echo "Building production bundle..."
npm run build

# ==============================================
# Configure PM2
# ==============================================
echo ""
echo "Configuring PM2..."

# Install PM2 if not present
if ! command -v pm2 &> /dev/null; then
    npm install -g pm2
fi

# Stop existing process if running
pm2 stop mycosoft-website 2>/dev/null || true
pm2 delete mycosoft-website 2>/dev/null || true

# Start with PM2
pm2 start npm --name "mycosoft-website" -- start

# Save PM2 configuration
pm2 save

# Configure PM2 to start on boot
pm2 startup systemd -u root --hp /root

# ==============================================
# Configure Nginx
# ==============================================
echo ""
echo "Configuring nginx..."

# Copy nginx configuration
cp "$DEPLOY_DIR/config/nginx/mycosoft.conf" /etc/nginx/sites-available/mycosoft.conf

# Enable site
ln -sf /etc/nginx/sites-available/mycosoft.conf /etc/nginx/sites-enabled/

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# Reload nginx
systemctl reload nginx

# ==============================================
# Verify Deployment
# ==============================================
echo ""
echo "Verifying deployment..."

# Wait for Next.js to start
sleep 5

# Check if website is running
if curl -s http://localhost:3000 > /dev/null; then
    echo "✓ Website is running on port 3000"
else
    echo "✗ Website not responding on port 3000"
    pm2 logs mycosoft-website --lines 50
    exit 1
fi

# Check nginx
if curl -s http://localhost/nginx-health | grep -q healthy; then
    echo "✓ Nginx is healthy"
else
    echo "✗ Nginx health check failed"
fi

# ==============================================
# Summary
# ==============================================
echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "Website: http://localhost:3000"
echo "Nginx:   http://localhost (proxied)"
echo ""
echo "PM2 commands:"
echo "  pm2 status              - Check status"
echo "  pm2 logs mycosoft-website - View logs"
echo "  pm2 restart mycosoft-website - Restart"
echo ""
echo "Next: Configure Cloudflare Tunnel to route external traffic"
