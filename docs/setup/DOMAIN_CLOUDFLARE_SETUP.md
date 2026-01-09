# Domain and Cloudflare Setup Guide

> **Version**: 1.0.0  
> **Last Updated**: January 2026  
> **Prerequisites**: Cloudflare account, mycosoft.com domain access

This document covers the complete setup of the mycosoft.com domain with Cloudflare for DNS, SSL, and secure tunneling to the local MYCA infrastructure.

---

## Table of Contents

1. [Overview](#overview)
2. [Cloudflare Account Setup](#cloudflare-account-setup)
3. [DNS Configuration](#dns-configuration)
4. [Cloudflare Tunnel Setup](#cloudflare-tunnel-setup)
5. [SSL/TLS Configuration](#ssltls-configuration)
6. [Subdomain Routing](#subdomain-routing)
7. [Nginx Reverse Proxy](#nginx-reverse-proxy)
8. [Security Features](#security-features)
9. [Testing Public Access](#testing-public-access)
10. [Staging vs Production](#staging-vs-production)
11. [Troubleshooting](#troubleshooting)

---

## Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                    │
│                                                                          │
│  User Request: https://mycosoft.com                                     │
│         │                                                                │
│         ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      CLOUDFLARE                                  │    │
│  │                                                                  │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │    │
│  │  │    DNS      │  │   WAF       │  │   SSL/TLS   │             │    │
│  │  │  Resolver   │  │  Firewall   │  │   (Full)    │             │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │    │
│  │         └────────────────┼────────────────┘                     │    │
│  │                          ▼                                       │    │
│  │              ┌───────────────────────┐                          │    │
│  │              │   Cloudflare Tunnel   │                          │    │
│  │              │   (Argo/cloudflared)  │                          │    │
│  │              └───────────┬───────────┘                          │    │
│  └──────────────────────────┼──────────────────────────────────────┘    │
│                             │                                            │
└─────────────────────────────┼────────────────────────────────────────────┘
                              │ Encrypted tunnel (no open ports)
                              │
┌─────────────────────────────┼────────────────────────────────────────────┐
│  LOCAL NETWORK              │                                            │
│                             ▼                                            │
│              ┌───────────────────────┐                                  │
│              │      cloudflared      │ (on myca-core or UDM Pro)        │
│              │     192.168.20.10     │                                  │
│              └───────────┬───────────┘                                  │
│                          │                                               │
│         ┌────────────────┼────────────────┐                             │
│         │                │                │                              │
│         ▼                ▼                ▼                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │
│  │   Website   │  │  MYCA API   │  │  Dashboard  │                     │
│  │   :3000     │  │   :8001     │  │   :3100     │                     │
│  └─────────────┘  └─────────────┘  └─────────────┘                     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Domain Structure

| Domain | Service | Port | Description |
|--------|---------|------|-------------|
| mycosoft.com | Website | 3000 | Next.js frontend |
| www.mycosoft.com | Website | 3000 | Redirect/alias |
| api.mycosoft.com | MYCA API | 8001 | FastAPI orchestrator |
| dashboard.mycosoft.com | Dashboard | 3100 | MICA voice interface |
| webhooks.mycosoft.com | n8n | 5678 | Webhook automations |

---

## Cloudflare Account Setup

### Step 1: Create/Access Cloudflare Account

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com)
2. Sign in or create a new account
3. Verify email address

### Step 2: Add Domain to Cloudflare

1. Click **Add a Site**
2. Enter `mycosoft.com`
3. Select plan (Free tier is sufficient for basic setup)
4. Cloudflare will scan existing DNS records

### Step 3: Update Nameservers

Update your domain registrar with Cloudflare nameservers:

```
Nameserver 1: <provided-by-cloudflare>.ns.cloudflare.com
Nameserver 2: <provided-by-cloudflare>.ns.cloudflare.com
```

Wait for propagation (up to 48 hours, usually faster).

Verify:
```bash
nslookup -type=NS mycosoft.com
```

---

## DNS Configuration

### Required DNS Records

Navigate to **DNS** > **Records** in Cloudflare dashboard.

| Type | Name | Content | Proxy | TTL |
|------|------|---------|-------|-----|
| CNAME | @ | `<tunnel-id>.cfargotunnel.com` | Proxied | Auto |
| CNAME | www | mycosoft.com | Proxied | Auto |
| CNAME | api | `<tunnel-id>.cfargotunnel.com` | Proxied | Auto |
| CNAME | dashboard | `<tunnel-id>.cfargotunnel.com` | Proxied | Auto |
| CNAME | webhooks | `<tunnel-id>.cfargotunnel.com` | Proxied | Auto |

**Note**: The `<tunnel-id>` will be generated when you create the Cloudflare Tunnel.

### Optional Records

| Type | Name | Content | Proxy | Purpose |
|------|------|---------|-------|---------|
| TXT | @ | `v=spf1 -all` | N/A | Email security |
| TXT | _dmarc | `v=DMARC1; p=reject` | N/A | Email security |
| MX | @ | (if using email) | N/A | Email routing |

---

## Cloudflare Tunnel Setup

Cloudflare Tunnel (formerly Argo Tunnel) creates a secure outbound-only connection. No open ports required on your network.

### Step 1: Install cloudflared

**On myca-core VM (Ubuntu):**

```bash
# Download and install
curl -L --output cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Verify installation
cloudflared --version
```

**On Windows (for testing):**

```powershell
# Download installer
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.msi" -OutFile "cloudflared.msi"
msiexec /i cloudflared.msi
```

### Step 2: Authenticate

```bash
cloudflared tunnel login
```

This opens a browser to authenticate with your Cloudflare account. After authentication, a certificate is saved to `~/.cloudflared/cert.pem`.

### Step 3: Create Tunnel

```bash
# Create the tunnel
cloudflared tunnel create mycosoft-tunnel

# This outputs:
# Created tunnel mycosoft-tunnel with id <TUNNEL-UUID>
# Credentials file saved to: /home/myca/.cloudflared/<TUNNEL-UUID>.json
```

**Save the Tunnel ID** - you'll need it for DNS records and configuration.

### Step 4: Configure Tunnel

Create/copy the configuration file:

```bash
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/<TUNNEL-UUID>.json /etc/cloudflared/credentials.json
sudo cp /path/to/mycosoft-mas/config/cloudflared/config.yml /etc/cloudflared/config.yml
```

Edit `/etc/cloudflared/config.yml`:

```yaml
# Cloudflare Tunnel Configuration for mycosoft.com
tunnel: mycosoft-tunnel
credentials-file: /etc/cloudflared/credentials.json

ingress:
  # Main website (Next.js)
  - hostname: mycosoft.com
    service: http://localhost:3000
  
  - hostname: www.mycosoft.com
    service: http://localhost:3000
  
  # MYCA API
  - hostname: api.mycosoft.com
    service: http://localhost:8001
  
  # Dashboard
  - hostname: dashboard.mycosoft.com
    service: http://localhost:3100
  
  # N8N Webhooks
  - hostname: webhooks.mycosoft.com
    service: http://localhost:5678
    originRequest:
      noTLSVerify: true
  
  # Catch-all (required)
  - service: http_status:404

originRequest:
  connectTimeout: 30s
  noTLSVerify: false
  keepAliveTimeout: 90s
  keepAliveConnections: 100
  http2Origin: true
```

### Step 5: Route DNS to Tunnel

```bash
# Create DNS route for each hostname
cloudflared tunnel route dns mycosoft-tunnel mycosoft.com
cloudflared tunnel route dns mycosoft-tunnel www.mycosoft.com
cloudflared tunnel route dns mycosoft-tunnel api.mycosoft.com
cloudflared tunnel route dns mycosoft-tunnel dashboard.mycosoft.com
cloudflared tunnel route dns mycosoft-tunnel webhooks.mycosoft.com
```

### Step 6: Install as System Service

```bash
# Install service
sudo cloudflared service install

# Start and enable
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

# Verify
sudo systemctl status cloudflared
```

### Step 7: Verify Tunnel Status

```bash
# Check tunnel info
cloudflared tunnel info mycosoft-tunnel

# List active connections
cloudflared tunnel list

# View logs
sudo journalctl -u cloudflared -f
```

---

## SSL/TLS Configuration

### Cloudflare SSL Settings

Navigate to **SSL/TLS** in Cloudflare dashboard.

1. **SSL/TLS Mode**: Set to **Full (strict)**
   - Encrypts traffic between visitor and Cloudflare
   - Encrypts traffic between Cloudflare and origin
   - Validates origin certificate

2. **Edge Certificates**:
   - Enable **Always Use HTTPS**
   - Enable **Automatic HTTPS Rewrites**
   - Set **Minimum TLS Version** to **1.2**

3. **Origin Certificates** (Optional for internal services):
   - Generate a Cloudflare Origin Certificate
   - Install on nginx for internal SSL

### HSTS Configuration

Enable HTTP Strict Transport Security:

1. Go to **SSL/TLS** > **Edge Certificates**
2. Enable **HTTP Strict Transport Security (HSTS)**
3. Configure:
   - Max-Age: 6 months (minimum recommended)
   - Include subdomains: Yes
   - Preload: Yes (after testing)

---

## Subdomain Routing

### Current Routing Table

| Hostname | Cloudflare Tunnel | Local Service | Port |
|----------|-------------------|---------------|------|
| mycosoft.com | mycosoft-tunnel | http://localhost:3000 | 3000 |
| www.mycosoft.com | mycosoft-tunnel | http://localhost:3000 | 3000 |
| api.mycosoft.com | mycosoft-tunnel | http://localhost:8001 | 8001 |
| dashboard.mycosoft.com | mycosoft-tunnel | http://localhost:3100 | 3100 |
| webhooks.mycosoft.com | mycosoft-tunnel | http://localhost:5678 | 5678 |

### Adding New Subdomains

1. Add ingress rule to `/etc/cloudflared/config.yml`
2. Add DNS route: `cloudflared tunnel route dns mycosoft-tunnel <subdomain>.mycosoft.com`
3. Restart cloudflared: `sudo systemctl restart cloudflared`

Example for adding a staging environment:

```yaml
# In config.yml, add before catch-all:
- hostname: staging.mycosoft.com
  service: http://localhost:3001
```

```bash
cloudflared tunnel route dns mycosoft-tunnel staging.mycosoft.com
sudo systemctl restart cloudflared
```

---

## Nginx Reverse Proxy

For production, nginx provides additional features like caching and request routing.

### Installation

```bash
sudo apt install nginx
```

### Configuration

Copy the provided nginx config:

```bash
sudo cp /opt/myca/config/nginx/mycosoft.conf /etc/nginx/sites-available/mycosoft
sudo ln -s /etc/nginx/sites-available/mycosoft /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
```

### Key Configuration Features

The nginx configuration at `config/nginx/mycosoft.conf` provides:

1. **Upstream Definitions**:
   ```nginx
   upstream website {
       server 127.0.0.1:3000;
       keepalive 32;
   }
   
   upstream myca_api {
       server 127.0.0.1:8001;
       keepalive 32;
   }
   ```

2. **Rate Limiting**:
   ```nginx
   limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
   limit_req_zone $binary_remote_addr zone=general_limit:10m rate=30r/s;
   ```

3. **Security Headers**:
   ```nginx
   add_header X-Frame-Options "SAMEORIGIN" always;
   add_header X-Content-Type-Options "nosniff" always;
   add_header X-XSS-Protection "1; mode=block" always;
   ```

4. **API Routing**:
   ```nginx
   location /api/mas/ {
       rewrite ^/api/mas/(.*)$ /$1 break;
       proxy_pass http://myca_api;
   }
   ```

### Testing and Reload

```bash
# Test configuration
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Verify
curl http://localhost/nginx-health
```

---

## Security Features

### Cloudflare WAF

Configure Web Application Firewall rules:

1. Go to **Security** > **WAF**
2. Enable **Managed Rules** (free tier includes basic protection)
3. Create custom rules:

**Block bad bots:**
```
(cf.client.bot) and not (cf.client.bot.verified_bot)
```

**Rate limit API:**
```
(http.request.uri.path contains "/api/") and (cf.threat_score gt 10)
```

### Access Policies (Cloudflare Zero Trust)

For sensitive endpoints like dashboard:

1. Go to **Zero Trust** > **Access** > **Applications**
2. Add application for `dashboard.mycosoft.com`
3. Configure authentication (email, SSO, etc.)

### Bot Protection

1. Go to **Security** > **Bots**
2. Enable **Bot Fight Mode**
3. Configure **Super Bot Fight Mode** (Pro plan)

### DDoS Protection

Cloudflare provides automatic DDoS protection. Additional configuration:

1. Go to **Security** > **DDoS**
2. Review default rules
3. Adjust sensitivity if needed

---

## Testing Public Access

### Pre-Launch Checklist

Before making the site publicly accessible:

- [ ] cloudflared service running
- [ ] All local services responding
- [ ] SSL certificate valid
- [ ] DNS records propagated
- [ ] Firewall rules configured
- [ ] Security headers present

### Testing Commands

```bash
# Test from external network (or use phone on cellular)

# Check DNS resolution
nslookup mycosoft.com

# Test HTTPS
curl -I https://mycosoft.com

# Check SSL certificate
openssl s_client -connect mycosoft.com:443 -servername mycosoft.com

# Test API endpoint
curl https://api.mycosoft.com/health

# Check security headers
curl -I https://mycosoft.com | grep -i "x-frame\|x-content\|strict-transport"
```

### Browser Testing

1. Open private/incognito window
2. Navigate to https://mycosoft.com
3. Check for SSL padlock
4. Open DevTools (F12) > Network > verify no errors
5. Check Console for security warnings

### Load Testing

```bash
# Install hey (HTTP load tester)
go install github.com/rakyll/hey@latest

# Basic load test
hey -n 1000 -c 50 https://mycosoft.com

# API load test
hey -n 500 -c 20 https://api.mycosoft.com/health
```

---

## Staging vs Production

### Staging Environment

Create a staging tunnel for testing before production:

```bash
# Create staging tunnel
cloudflared tunnel create mycosoft-staging

# Configure staging ingress (staging-config.yml)
tunnel: mycosoft-staging
credentials-file: /etc/cloudflared/staging-credentials.json

ingress:
  - hostname: staging.mycosoft.com
    service: http://localhost:3001  # Different port
  - service: http_status:404
```

### Environment Variables

**Staging:**
```bash
WEBSITE_URL=https://staging.mycosoft.com
CORS_ORIGINS=https://staging.mycosoft.com
DEBUG_MODE=true
```

**Production:**
```bash
WEBSITE_URL=https://mycosoft.com
CORS_ORIGINS=https://mycosoft.com,https://www.mycosoft.com
DEBUG_MODE=false
```

### Deployment Flow

```
Development (mycocomp)
    │
    │ git push
    ▼
Staging (staging.mycosoft.com)
    │
    │ Manual approval
    ▼
Production (mycosoft.com)
```

---

## Troubleshooting

### Tunnel Connection Issues

**Symptom**: Site shows "Error 1033: Argo Tunnel Error"

```bash
# Check tunnel status
cloudflared tunnel info mycosoft-tunnel

# Check logs
sudo journalctl -u cloudflared -n 100

# Verify config
cloudflared tunnel ingress validate /etc/cloudflared/config.yml

# Test local service
curl http://localhost:3000
```

### DNS Issues

**Symptom**: "DNS_PROBE_FINISHED_NXDOMAIN"

```bash
# Check DNS propagation
dig mycosoft.com @8.8.8.8

# Verify CNAME record points to tunnel
dig CNAME mycosoft.com

# Force DNS refresh
ipconfig /flushdns  # Windows
sudo systemd-resolve --flush-caches  # Linux
```

### SSL Issues

**Symptom**: Certificate errors

1. Verify SSL mode is "Full (strict)" in Cloudflare
2. Check origin server has valid certificate (or use Cloudflare Origin CA)
3. Verify tunnel is configured for HTTPS to origin

```bash
# Test origin certificate
openssl s_client -connect localhost:443 -servername mycosoft.com
```

### Service Unreachable

**Symptom**: 502 Bad Gateway

```bash
# Check if local service is running
systemctl status myca-orchestrator
docker ps

# Test local service
curl http://localhost:3000
curl http://localhost:8001/health

# Check firewall
sudo ufw status
```

---

## Maintenance

### Certificate Renewal

Cloudflare handles certificate renewal automatically. Monitor:

1. **SSL/TLS** > **Edge Certificates** - check expiry dates
2. Set up email alerts for certificate events

### Tunnel Updates

```bash
# Update cloudflared
sudo apt update
sudo apt install --only-upgrade cloudflared

# Restart service
sudo systemctl restart cloudflared
```

### Configuration Changes

```bash
# Edit configuration
sudo nano /etc/cloudflared/config.yml

# Validate
cloudflared tunnel ingress validate /etc/cloudflared/config.yml

# Restart to apply
sudo systemctl restart cloudflared
```

### Monitoring

1. **Cloudflare Analytics**: Traffic, threats, performance
2. **Tunnel Metrics**: `cloudflared tunnel info`
3. **Local Logs**: `journalctl -u cloudflared`

---

## Quick Reference

### Commands

```bash
# Tunnel management
cloudflared tunnel list
cloudflared tunnel info mycosoft-tunnel
cloudflared tunnel run mycosoft-tunnel

# Service management
sudo systemctl status cloudflared
sudo systemctl restart cloudflared
sudo journalctl -u cloudflared -f

# DNS verification
cloudflared tunnel route dns mycosoft-tunnel <hostname>
dig <hostname>
```

### Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| Tunnel config | `/etc/cloudflared/config.yml` | Ingress rules |
| Credentials | `/etc/cloudflared/credentials.json` | Tunnel auth |
| Nginx config | `/etc/nginx/sites-available/mycosoft` | Reverse proxy |

### URLs

| URL | Service |
|-----|---------|
| https://mycosoft.com | Website |
| https://api.mycosoft.com | MYCA API |
| https://dashboard.mycosoft.com | MICA Dashboard |
| https://webhooks.mycosoft.com | n8n Webhooks |

---

## Related Documents

- [MASTER_SETUP_GUIDE.md](./MASTER_SETUP_GUIDE.md) - Overall architecture
- [SECURITY_HARDENING_GUIDE.md](./SECURITY_HARDENING_GUIDE.md) - Security configuration
- [TESTING_DEBUGGING_PROCEDURES.md](./TESTING_DEBUGGING_PROCEDURES.md) - Testing procedures
- [config/cloudflared/config.yml](../../config/cloudflared/config.yml) - Tunnel configuration
- [config/nginx/mycosoft.conf](../../config/nginx/mycosoft.conf) - Nginx configuration

---

*Document maintained by MYCA Infrastructure Team*
