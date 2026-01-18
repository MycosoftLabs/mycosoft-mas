# Cloudflare Tunnel Setup Guide

*Created: January 17, 2026*  
*For: VM 103 (mycosoft-sandbox) → mycosoft.com*

---

## 📋 Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Install Cloudflared](#3-install-cloudflared)
4. [Create Tunnel](#4-create-tunnel)
5. [Configure Routes](#5-configure-routes)
6. [DNS Configuration](#6-dns-configuration)
7. [Run as Service](#7-run-as-service)
8. [Verification](#8-verification)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Overview

Cloudflare Tunnel securely connects your VM to the internet without exposing ports or requiring a public IP.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERNET                                      │
│                            │                                          │
│                   ┌────────▼────────┐                                │
│                   │   Cloudflare    │                                │
│                   │   Edge Network  │                                │
│                   └────────┬────────┘                                │
│                            │                                          │
│              ┌─────────────┼─────────────┐                           │
│              ▼             ▼             ▼                           │
│     mycosoft.com   api.mycosoft.com  n8n.mycosoft.com               │
│                                                                       │
└───────────────────────────┬───────────────────────────────────────────┘
                            │ Encrypted Tunnel
                            │
┌───────────────────────────▼───────────────────────────────────────────┐
│                    VM 103 (mycosoft-sandbox)                          │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                     cloudflared daemon                            │ │
│  │                           │                                       │ │
│  │    ┌──────────────────────┼──────────────────────┐               │ │
│  │    ▼                      ▼                      ▼               │ │
│  │ localhost:3000      localhost:8000        localhost:5678         │ │
│  │   (Website)          (MINDEX API)            (n8n)               │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

### Subdomain Mapping

| Subdomain | Internal Service | Port |
|-----------|-----------------|------|
| mycosoft.com | Website (Next.js) | 3000 |
| api.mycosoft.com | MINDEX API | 8000 |
| n8n.mycosoft.com | n8n Workflows | 5678 |
| grafana.mycosoft.com | Grafana Dashboard | 3002 |
| crep.mycosoft.com | CREP Dashboard | 3000/crep |

---

## 2. Prerequisites

- Cloudflare account with mycosoft.com domain
- Domain DNS managed by Cloudflare
- VM with Docker installed and services running

---

## 3. Install Cloudflared

### Option A: Direct Installation

```bash
# Download and install
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Verify installation
cloudflared --version
```

### Option B: Docker Installation

```bash
# Pull the image
docker pull cloudflare/cloudflared:latest
```

---

## 4. Create Tunnel

### Authenticate with Cloudflare

```bash
# This opens a browser for authentication
cloudflared tunnel login

# The certificate is saved to ~/.cloudflared/cert.pem
```

### Create Named Tunnel

```bash
# Create tunnel
cloudflared tunnel create mycosoft-sandbox

# This creates:
# - Tunnel ID (UUID)
# - Credentials file at ~/.cloudflared/<TUNNEL_ID>.json
```

### Note Your Tunnel ID

```bash
# List tunnels
cloudflared tunnel list

# Example output:
# ID                                   NAME              CREATED
# a1b2c3d4-e5f6-7890-abcd-ef1234567890 mycosoft-sandbox 2026-01-17T00:00:00Z
```

---

## 5. Configure Routes

### Create Configuration File

```bash
mkdir -p /opt/mycosoft/cloudflared

cat > /opt/mycosoft/cloudflared/config.yml << 'EOF'
# Cloudflare Tunnel Configuration
# Tunnel ID: Replace with your actual tunnel ID
tunnel: YOUR_TUNNEL_ID_HERE
credentials-file: /opt/mycosoft/cloudflared/credentials.json

# Ingress rules - order matters!
ingress:
  # Main website
  - hostname: mycosoft.com
    service: http://localhost:3000
  
  - hostname: www.mycosoft.com
    service: http://localhost:3000

  # API endpoint
  - hostname: api.mycosoft.com
    service: http://localhost:8000

  # n8n workflows
  - hostname: n8n.mycosoft.com
    service: http://localhost:5678

  # Grafana monitoring
  - hostname: grafana.mycosoft.com
    service: http://localhost:3002

  # MAS Orchestrator
  - hostname: orchestrator.mycosoft.com
    service: http://localhost:8001

  # MycoBrain AI
  - hostname: brain.mycosoft.com
    service: http://localhost:8003

  # Catch-all (required)
  - service: http_status:404
EOF
```

### Copy Credentials

```bash
# Copy the credentials file created during tunnel creation
cp ~/.cloudflared/<YOUR_TUNNEL_ID>.json /opt/mycosoft/cloudflared/credentials.json

# Set permissions
chmod 600 /opt/mycosoft/cloudflared/credentials.json
```

### Validate Configuration

```bash
cloudflared tunnel --config /opt/mycosoft/cloudflared/config.yml ingress validate
```

---

## 6. DNS Configuration

### Route DNS to Tunnel

```bash
# For each hostname, create a CNAME record pointing to the tunnel
cloudflared tunnel route dns mycosoft-sandbox mycosoft.com
cloudflared tunnel route dns mycosoft-sandbox www.mycosoft.com
cloudflared tunnel route dns mycosoft-sandbox api.mycosoft.com
cloudflared tunnel route dns mycosoft-sandbox n8n.mycosoft.com
cloudflared tunnel route dns mycosoft-sandbox grafana.mycosoft.com
cloudflared tunnel route dns mycosoft-sandbox orchestrator.mycosoft.com
cloudflared tunnel route dns mycosoft-sandbox brain.mycosoft.com
```

### Verify DNS Records

In Cloudflare Dashboard, you should see CNAME records like:
```
mycosoft.com        CNAME   <TUNNEL_ID>.cfargotunnel.com
api.mycosoft.com    CNAME   <TUNNEL_ID>.cfargotunnel.com
n8n.mycosoft.com    CNAME   <TUNNEL_ID>.cfargotunnel.com
...
```

---

## 7. Run as Service

### Install as Systemd Service

```bash
# Install the tunnel as a service
sudo cloudflared service install

# Or manually create the service file
sudo tee /etc/systemd/system/cloudflared.service << 'EOF'
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=notify
ExecStart=/usr/bin/cloudflared tunnel --config /opt/mycosoft/cloudflared/config.yml run
Restart=on-failure
RestartSec=5s
User=root

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

# Check status
sudo systemctl status cloudflared
```

### Docker-based Service

Alternatively, run cloudflared in Docker:

```bash
cat >> /opt/mycosoft/mas/docker-compose.always-on.yml << 'EOF'

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: unless-stopped
    command: tunnel --config /etc/cloudflared/config.yml run
    volumes:
      - /opt/mycosoft/cloudflared:/etc/cloudflared
    network_mode: host
EOF
```

---

## 8. Verification

### Check Tunnel Status

```bash
# View tunnel status
cloudflared tunnel info mycosoft-sandbox

# Check running connections
cloudflared tunnel list

# View logs
sudo journalctl -u cloudflared -f
```

### Test Endpoints

```bash
# Test from external network or using curl
curl -I https://mycosoft.com
curl -I https://api.mycosoft.com/health
curl -I https://n8n.mycosoft.com/healthz
curl -I https://grafana.mycosoft.com/api/health
```

### Expected Results

| URL | Expected Status |
|-----|-----------------|
| https://mycosoft.com | 200 OK |
| https://api.mycosoft.com/health | 200 OK |
| https://n8n.mycosoft.com | 200 OK (or 401 if auth required) |
| https://grafana.mycosoft.com | 302 (redirect to login) |

---

## 9. Troubleshooting

### Common Issues

#### Tunnel Not Connecting

```bash
# Check cloudflared status
sudo systemctl status cloudflared

# View detailed logs
sudo journalctl -u cloudflared -n 100

# Test configuration
cloudflared tunnel --config /opt/mycosoft/cloudflared/config.yml run --loglevel debug
```

#### DNS Not Resolving

```bash
# Check DNS propagation
dig mycosoft.com
nslookup mycosoft.com

# Verify CNAME records in Cloudflare dashboard
```

#### Service Not Accessible

```bash
# Verify local service is running
curl http://localhost:3000/api/health

# Check Docker containers
docker ps

# Test from tunnel perspective
cloudflared tunnel --config /opt/mycosoft/cloudflared/config.yml ingress rule mycosoft.com
```

### Useful Commands

```bash
# Restart tunnel
sudo systemctl restart cloudflared

# View real-time metrics
cloudflared tunnel info mycosoft-sandbox

# Delete and recreate tunnel
cloudflared tunnel delete mycosoft-sandbox
cloudflared tunnel create mycosoft-sandbox
```

---

## 🔐 Security Considerations

### Cloudflare Access (Zero Trust)

For additional security, configure Cloudflare Access:

1. Go to Cloudflare Dashboard → Zero Trust → Access
2. Create an Access Application for sensitive endpoints:
   - n8n.mycosoft.com
   - grafana.mycosoft.com
   - orchestrator.mycosoft.com
3. Configure authentication (email, SSO, etc.)

### IP Allowlist

In your application or firewall:
```bash
# Allow only Cloudflare IPs for public ports
# https://www.cloudflare.com/ips/
```

---

## 📊 Monitoring

### Add to Grafana Dashboard

Import Cloudflare tunnel metrics to Grafana:

1. Enable metrics endpoint in cloudflared config
2. Add Prometheus scrape target
3. Import Cloudflare tunnel dashboard

```yaml
# Add to config.yml
metrics: localhost:2000
```

---

*Document Version: 1.0*  
*Last Updated: January 17, 2026*
