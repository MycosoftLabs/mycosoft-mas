#!/bin/bash
# Setup script for myca-website VM (192.168.20.11)
# Run after vm_setup_common.sh

set -e

echo "=================================================="
echo "  MYCA Website VM Setup"
echo "=================================================="

VM_IP="192.168.20.11"
API_IP="192.168.20.10"
NAS_PATH="/mnt/mycosoft"

# Verify NAS mount
echo "[1/7] Verifying NAS mount..."
if ! mountpoint -q $NAS_PATH; then
    echo "ERROR: NAS not mounted at $NAS_PATH"
    exit 1
fi

# Install nginx
echo "[2/7] Installing nginx..."
apt install -y nginx

# Clone repository
echo "[3/7] Cloning MYCA repository..."
if [ ! -d /opt/myca/.git ]; then
    git clone https://github.com/MycosoftLabs/mycosoft-mas.git /opt/myca
else
    cd /opt/myca && git pull
fi
chown -R myca:myca /opt/myca

# Install dependencies
echo "[4/7] Installing Node.js dependencies..."
cd /opt/myca
sudo -u myca npm install

# Create production environment
echo "[5/7] Creating production environment..."
cat > /opt/myca/.env.production << EOF
# Production Environment
NODE_ENV=production

# API URLs
NEXT_PUBLIC_API_URL=https://api.mycosoft.com
NEXT_PUBLIC_WS_URL=wss://api.mycosoft.com

# Internal API (for SSR)
INTERNAL_API_URL=http://$API_IP:8001

# NextAuth
NEXTAUTH_URL=https://mycosoft.com
NEXTAUTH_SECRET=$(openssl rand -base64 32)

# Google OAuth (set these from your Google Cloud Console)
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET

# Database for sessions
DATABASE_URL=postgresql://mas:PASSWORD@192.168.20.12:5432/mas
EOF
chown myca:myca /opt/myca/.env.production

# Build website
echo "[6/7] Building website..."
cd /opt/myca
sudo -u myca npm run build

# Create PM2 ecosystem file
echo "[7/7] Creating PM2 ecosystem..."
cat > /opt/myca/ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'myca-website',
    script: 'npm',
    args: 'start',
    cwd: '/opt/myca',
    instances: 2,
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    env_file: '/opt/myca/.env.production',
    max_memory_restart: '1G',
    error_file: '/var/log/myca/website-error.log',
    out_file: '/var/log/myca/website-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};
EOF
chown myca:myca /opt/myca/ecosystem.config.js

# Configure nginx
cat > /etc/nginx/sites-available/mycosoft << 'EOF'
# MYCA Website - Nginx Configuration

upstream website {
    server 127.0.0.1:3000;
    keepalive 32;
}

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name mycosoft.com www.mycosoft.com;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    # Health check
    location /nginx-health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Main website
    location / {
        proxy_pass http://website;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        proxy_pass http://website;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Error pages
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
        internal;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/mycosoft /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Setup PM2 to start on boot
sudo -u myca pm2 startup systemd -u myca --hp /home/myca
sudo -u myca pm2 start /opt/myca/ecosystem.config.js
sudo -u myca pm2 save

echo ""
echo "=================================================="
echo "  Website VM Setup Complete!"
echo "=================================================="
echo ""
echo "  IMPORTANT: Update .env.production with:"
echo "    - Google OAuth credentials"
echo "    - Database password"
echo "    - NEXTAUTH_SECRET"
echo ""
echo "  Website is now running at: http://$VM_IP"
echo ""
echo "  PM2 commands:"
echo "    pm2 status        - Check status"
echo "    pm2 logs          - View logs"
echo "    pm2 restart all   - Restart"
echo ""
