# Cloudflare Tunnel Setup for mycosoft.com

This document describes setting up Cloudflare Tunnel for secure external access to MYCA services without exposing ports.

## Overview

Cloudflare Tunnel creates an encrypted connection from your local network to Cloudflare's edge, allowing external access to:

- **mycosoft.com** - Main website
- **api.mycosoft.com** - MYCA API
- **dashboard.mycosoft.com** - MYCA Dashboard

## Prerequisites

1. Cloudflare account with mycosoft.com domain
2. Domain's nameservers pointed to Cloudflare
3. MYCA Core VM or Website VM running
4. Docker installed on the VM

## Step 1: Create Tunnel in Cloudflare Dashboard

1. Log into [Cloudflare Zero Trust](https://one.dash.cloudflare.com/)
2. Navigate to **Access** → **Tunnels**
3. Click **Create a tunnel**
4. Name: `mycosoft-tunnel`
5. Copy the tunnel token/credentials

## Step 2: Install cloudflared

On the Website VM:

```bash
# Download cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

# Install
sudo dpkg -i cloudflared.deb

# Verify installation
cloudflared --version
```

## Step 3: Configure Tunnel

Create credentials file:

```bash
sudo mkdir -p /etc/cloudflared
sudo nano /etc/cloudflared/credentials.json
```

Content:
```json
{
  "AccountTag": "your-account-id",
  "TunnelID": "your-tunnel-id",
  "TunnelSecret": "your-tunnel-secret"
}
```

Copy configuration:

```bash
sudo cp config/cloudflared/config.yml /etc/cloudflared/config.yml
```

## Step 4: Install as Service

```bash
# Install service
sudo cloudflared service install

# Start service
sudo systemctl start cloudflared

# Enable on boot
sudo systemctl enable cloudflared

# Check status
sudo systemctl status cloudflared
```

## Step 5: Configure DNS Records

In Cloudflare DNS settings for mycosoft.com:

| Type | Name | Target |
|------|------|--------|
| CNAME | @ | `<tunnel-id>.cfargotunnel.com` |
| CNAME | www | `<tunnel-id>.cfargotunnel.com` |
| CNAME | api | `<tunnel-id>.cfargotunnel.com` |
| CNAME | dashboard | `<tunnel-id>.cfargotunnel.com` |
| CNAME | webhooks | `<tunnel-id>.cfargotunnel.com` |

Enable **Proxied** (orange cloud) for all records.

## Step 6: Verify Tunnel

```bash
# Check tunnel status
cloudflared tunnel info mycosoft-tunnel

# Test local connectivity
curl http://localhost:3000  # Website
curl http://localhost:8001/health  # API
curl http://localhost:3100  # Dashboard

# Test external (from different network)
curl https://mycosoft.com
curl https://api.mycosoft.com/health
```

## Routing Configuration

The tunnel routes requests based on hostname:

| Hostname | Local Service | Port |
|----------|---------------|------|
| mycosoft.com | Next.js Website | 3000 |
| www.mycosoft.com | Next.js Website | 3000 |
| api.mycosoft.com | MYCA Orchestrator | 8001 |
| dashboard.mycosoft.com | UniFi Dashboard | 3100 |
| webhooks.mycosoft.com | N8N | 5678 |

## Security Features

Cloudflare Tunnel provides:

1. **No Exposed Ports**: Firewall can block all inbound traffic
2. **SSL/TLS**: Automatic HTTPS for all endpoints
3. **DDoS Protection**: Cloudflare's global network
4. **WAF**: Web Application Firewall (if enabled)
5. **Access Controls**: Cloudflare Access for authentication

## Cloudflare Access (Optional)

Add authentication to sensitive endpoints:

1. In Cloudflare Zero Trust, go to **Access** → **Applications**
2. Create application for `dashboard.mycosoft.com`
3. Configure identity provider (Google, GitHub, etc.)
4. Set access policies

## Troubleshooting

### Tunnel Not Connecting

```bash
# Check logs
sudo journalctl -u cloudflared -f

# Verify credentials
cat /etc/cloudflared/credentials.json

# Test tunnel manually
cloudflared tunnel run mycosoft-tunnel
```

### 502 Bad Gateway

```bash
# Check if local service is running
curl http://localhost:3000
curl http://localhost:8001/health

# Check Docker containers
docker ps
docker compose logs
```

### DNS Not Resolving

1. Verify CNAME records in Cloudflare DNS
2. Ensure records are proxied (orange cloud)
3. Check nameserver configuration
4. Wait for DNS propagation (up to 24 hours)

## Docker Deployment (Alternative)

Run cloudflared in Docker:

```bash
docker run -d --name cloudflared \
  --network host \
  -v /etc/cloudflared:/etc/cloudflared \
  cloudflare/cloudflared:latest \
  tunnel --config /etc/cloudflared/config.yml run
```

## Monitoring

View tunnel metrics in Cloudflare dashboard:

- Connection count
- Request volume
- Error rates
- Response times

## Backup and Recovery

Backup tunnel credentials:

```bash
# Backup credentials (store securely!)
sudo cp /etc/cloudflared/credentials.json /mnt/mycosoft/backups/cloudflared-credentials.json
```

To restore on new VM:

```bash
# Install cloudflared
# Copy credentials and config
# Install service
sudo cloudflared service install
sudo systemctl start cloudflared
```
