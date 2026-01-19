# Mycosoft SOC Setup, Deployment & Implementation Guide

**Version:** 2.0.0  
**Last Updated:** January 18, 2026  
**Target Environments:** Development (localhost), Sandbox (sandbox.mycosoft.com), Production

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Development Deployment](#development-deployment)
4. [Sandbox Deployment](#sandbox-deployment)
5. [Production Deployment](#production-deployment)
6. [Docker Services Setup](#docker-services-setup)
7. [UniFi Integration Setup](#unifi-integration-setup)
8. [Post-Deployment Verification](#post-deployment-verification)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements

| Environment | CPU | RAM | Storage |
|-------------|-----|-----|---------|
| Development | 4 cores | 8 GB | 50 GB SSD |
| Sandbox | 8 cores | 16 GB | 100 GB SSD |
| Production | 16 cores | 32 GB | 500 GB NVMe |

### Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Node.js | 20.x LTS | Runtime |
| npm | 10.x | Package manager |
| Docker | 24.x | Container runtime |
| Docker Compose | 2.x | Container orchestration |
| Redis | 7.0 | Cache/Queue |
| Git | 2.x | Version control |

### Network Requirements

| Service | Port | Protocol | Direction |
|---------|------|----------|-----------|
| Next.js Dev | 3000-3004 | TCP | Inbound |
| UniFi API | 443 | HTTPS | Outbound |
| Redis | 6379 | TCP | Internal |
| AbuseIPDB | 443 | HTTPS | Outbound |
| VirusTotal | 443 | HTTPS | Outbound |

### API Keys Required

| Service | How to Obtain | Required |
|---------|---------------|----------|
| UniFi | UniFi Network > Settings > API | ✅ Yes |
| AbuseIPDB | abuseipdb.com/account/api | ⚠️ Recommended |
| VirusTotal | virustotal.com/gui/my-apikey | ⚠️ Recommended |
| Cloudflare | dash.cloudflare.com/profile/api-tokens | Future |

---

## Environment Setup

### Step 1: Clone Repository

```bash
# Navigate to project directory
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website

# Ensure on correct branch
git checkout main
git pull origin main
```

### Step 2: Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Verify installation
npm list --depth=0
```

### Step 3: Configure Environment Variables

Create or update `.env.local`:

```bash
# =================================
# MYCOSOFT SOC CONFIGURATION
# =================================

# UniFi Dream Machine Pro API
UNIFI_HOST=192.168.0.1
UNIFI_API_KEY=BfRgo4k9aS0-yo8BKqXpEtdo4k2jzM8k
UNIFI_SITE=default

# Threat Intelligence APIs
ABUSEIPDB_API_KEY=your_abuseipdb_api_key_here
VIRUSTOTAL_API_KEY=your_virustotal_api_key_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Suricata Configuration
SURICATA_LOG_PATH=/var/log/suricata/eve.json

# Security Settings
ALLOWED_COUNTRIES=US
HIGH_RISK_COUNTRIES=CN,RU,KP,IR,BY,VE,SY,CU
AUTO_BLOCK_THRESHOLD=high
GEO_FENCING_ENABLED=true

# Monitoring
MONITORING_ENABLED=true
THREAT_INTEL_UPDATE_INTERVAL=21600000

# Alert Configuration
ALERT_EMAIL_ENABLED=true
ALERT_DASHBOARD_ENABLED=true
```

### Step 4: Verify Configuration Files

Check authorized users configuration:

```bash
# Location: config/security/authorized-users.json
# Verify all users have correct US-based locations
```

Check security configuration:

```bash
# Location: config/security/security-config.json
# Verify allowed_countries includes only "US"
# Verify no Slack references exist
```

---

## Development Deployment

### Quick Start

```powershell
# Navigate to website directory
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website

# Start development server
npm run dev

# Server will start on first available port (3000-3004)
# Watch console for actual port assignment
```

### Development URLs

| Page | URL | Description |
|------|-----|-------------|
| SOC Dashboard | http://localhost:3000/security | Main security overview |
| Network Monitor | http://localhost:3000/security/network | UniFi integration |
| Incidents | http://localhost:3000/security/incidents | Incident management |
| Red Team | http://localhost:3000/security/redteam | Penetration testing |
| Compliance | http://localhost:3000/security/compliance | NIST compliance |

### Development Mode Features

- Hot module reloading
- Detailed error messages
- Mock data fallback when APIs unavailable
- No authentication required (dev only)

### Common Development Issues

**Port Already in Use:**
```powershell
# Find process using port
netstat -ano | findstr :3000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

**Module Not Found:**
```powershell
# Clear cache and reinstall
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
```

**TypeScript Errors:**
```powershell
# Run type check
npx tsc --noEmit

# Check specific file
npx tsc --noEmit app/api/security/route.ts
```

---

## Sandbox Deployment

### Pre-Deployment Checklist

- [ ] All local tests passing
- [ ] Environment variables configured
- [ ] SSL certificates valid
- [ ] Database migrations applied
- [ ] UniFi API key tested
- [ ] No hardcoded localhost references

### Deployment Steps

#### Step 1: Build Application

```powershell
# Create production build
npm run build

# Verify build output
dir .next
```

#### Step 2: Deploy to Sandbox

```powershell
# Using your deployment method (e.g., Vercel, Docker, manual)

# Option A: Vercel (if configured)
vercel --prod

# Option B: Docker
docker build -t mycosoft-soc:sandbox .
docker push your-registry/mycosoft-soc:sandbox

# Option C: Manual deployment to Proxmox VM
# Copy build to VM and restart service
```

#### Step 3: Configure Sandbox Environment

On the sandbox server:

```bash
# Set production environment variables
export NODE_ENV=production
export UNIFI_HOST=192.168.0.1
export UNIFI_API_KEY=BfRgo4k9aS0-yo8BKqXpEtdo4k2jzM8k
# ... other variables
```

#### Step 4: Start Service

```bash
# Using PM2 (recommended)
pm2 start npm --name "mycosoft-soc" -- start
pm2 save

# Or using systemd
sudo systemctl start mycosoft-soc
sudo systemctl enable mycosoft-soc
```

### Sandbox URLs

| Page | URL |
|------|-----|
| SOC Dashboard | https://sandbox.mycosoft.com/security |
| Network Monitor | https://sandbox.mycosoft.com/security/network |
| Incidents | https://sandbox.mycosoft.com/security/incidents |
| Red Team | https://sandbox.mycosoft.com/security/redteam |
| Compliance | https://sandbox.mycosoft.com/security/compliance |

---

## Production Deployment

### ⚠️ Production Deployment Requirements

Before deploying to production:

1. **Security Audit Required**
   - Code review by at least 2 team members
   - All critical vulnerabilities addressed
   - Penetration test completed

2. **Documentation Required**
   - All runbooks updated
   - Rollback procedure documented
   - On-call schedule confirmed

3. **Testing Required**
   - All integration tests passing
   - Load testing completed
   - Sandbox deployment verified for 48+ hours

### Production Architecture

```
                    ┌─────────────────┐
                    │   Cloudflare    │
                    │   WAF + CDN     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Load Balancer  │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼───────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   SOC App 1   │ │  SOC App 2  │ │  SOC App 3  │
    └───────────────┘ └─────────────┘ └─────────────┘
            │                │                │
            └────────────────┼────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Redis Cluster  │
                    └─────────────────┘
```

### Production Deployment Steps

1. **Create Release Tag**
   ```bash
   git tag -a v2.0.0 -m "SOC v2.0.0 release"
   git push origin v2.0.0
   ```

2. **Build Production Image**
   ```bash
   docker build -t mycosoft-soc:v2.0.0 .
   docker tag mycosoft-soc:v2.0.0 registry.mycosoft.com/soc:v2.0.0
   docker push registry.mycosoft.com/soc:v2.0.0
   ```

3. **Deploy with Zero Downtime**
   ```bash
   # Rolling update
   kubectl set image deployment/soc soc=registry.mycosoft.com/soc:v2.0.0
   
   # Or using Docker Swarm
   docker service update --image registry.mycosoft.com/soc:v2.0.0 soc
   ```

4. **Verify Deployment**
   ```bash
   # Check health endpoint
   curl https://mycosoft.com/api/security?action=status
   
   # Check logs
   kubectl logs -f deployment/soc
   ```

---

## Docker Services Setup

### Security Tools Stack

Location: `website/services/security/docker-compose.security-tools.yml`

#### Start Security Services

```powershell
# Navigate to services directory
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\services\security

# Create required directories
mkdir -p suricata/config suricata/rules suricata/logs nmap_results

# Start all services
docker-compose -f docker-compose.security-tools.yml up -d

# Verify services
docker-compose -f docker-compose.security-tools.yml ps
```

#### Individual Service Configuration

**Redis:**
```yaml
redis:
  image: redis:7.0-alpine
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
  ports:
    - "6379:6379"
```

**Nmap Scanner:**
```yaml
nmap-scanner:
  build:
    context: .
    dockerfile: Dockerfile.nmap
  environment:
    - REDIS_HOST=redis
    - SCAN_TARGET=192.168.0.0/24
    - SCAN_INTERVAL_SECONDS=3600
```

**Suricata IDS:**
```yaml
suricata:
  build:
    context: .
    dockerfile: Dockerfile.suricata
  cap_add:
    - NET_ADMIN
    - NET_RAW
  network_mode: host
```

**Threat Intel Service:**
```yaml
threat-intel-service:
  build:
    context: .
    dockerfile: Dockerfile.threat-intel
  environment:
    - ABUSEIPDB_API_KEY=${ABUSEIPDB_API_KEY}
    - VIRUSTOTAL_API_KEY=${VIRUSTOTAL_API_KEY}
```

#### Monitor Service Logs

```powershell
# All services
docker-compose -f docker-compose.security-tools.yml logs -f

# Specific service
docker-compose -f docker-compose.security-tools.yml logs -f nmap-scanner
```

---

## UniFi Integration Setup

### Step 1: Create API Key

1. Log into UniFi Network Console
2. Navigate to **Settings** → **System** → **Advanced**
3. Enable **Local API Access**
4. Go to **Settings** → **API**
5. Create new API key with read permissions
6. Copy the API key

### Step 2: Configure SSL Bypass

The UniFi controller uses a self-signed certificate. The API client handles this:

```typescript
// In app/api/unifi/route.ts
const httpsAgent = new https.Agent({
  rejectUnauthorized: false,
});
```

### Step 3: Test Connection

```powershell
# Test API directly
curl -k -H "X-API-Key: YOUR_API_KEY" https://192.168.0.1/proxy/network/v2/api/site/default/device

# Or use the browser
# Navigate to http://localhost:3000/security/network
```

### Step 4: Verify Data Flow

Check that these endpoints return data:

| Endpoint | Expected Data |
|----------|---------------|
| `/api/unifi?action=dashboard` | WAN status, clients, devices |
| `/api/unifi?action=devices` | Network devices list |
| `/api/unifi?action=clients` | Connected clients |
| `/api/unifi?action=alarms` | Recent alarms |

### UniFi API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `/v2/api/site/{site}/device` | Network devices |
| `/v2/api/site/{site}/clients/active` | Active clients |
| `/v2/api/site/{site}/events` | Network events |
| `/v2/api/site/{site}/stat/report/hourly.site` | Traffic stats |
| `/v2/api/site/{site}/wlan` | WiFi networks |

---

## Post-Deployment Verification

### Verification Checklist

#### 1. API Health Checks

```bash
# Security API
curl http://localhost:3000/api/security?action=status
# Expected: {"status":"active","threat_level":"low"...}

# UniFi API
curl http://localhost:3000/api/unifi?action=dashboard
# Expected: {"wan":{"ip":"192.168.1.141"...}

# Geo-IP Lookup
curl "http://localhost:3000/api/security?action=geo-lookup&ip=8.8.8.8"
# Expected: {"ip":"8.8.8.8","country":"United States"...}
```

#### 2. UI Verification

| Page | Verification |
|------|--------------|
| `/security` | Threat level displays, users load |
| `/security/network` | Live data from UniFi |
| `/security/incidents` | Incidents list displays |
| `/security/redteam` | Scanner form loads |
| `/security/compliance` | NIST controls display |

#### 3. Functional Tests

| Test | Steps | Expected |
|------|-------|----------|
| IP Lookup | Enter 8.8.8.8, click Lookup | Shows Google, US, LOW risk |
| High-risk IP | Enter CN IP, click Lookup | Shows HIGH risk |
| Refresh Data | Click refresh on Network Monitor | Data updates |

#### 4. Performance Checks

```bash
# Response time check
time curl http://localhost:3000/api/security?action=status

# Should complete in < 500ms
```

---

## Troubleshooting

### Common Issues

#### 1. "Loading Security Operations Center..." Stuck

**Cause:** API not responding

**Solution:**
```powershell
# Check if API is running
curl http://localhost:3000/api/security?action=status

# If not, restart dev server
npm run dev

# Check for TypeScript errors
npx tsc --noEmit
```

#### 2. UniFi Data Not Loading

**Cause:** SSL certificate or API key issue

**Solution:**
```powershell
# Verify API key is set
echo $env:UNIFI_API_KEY

# Test direct connection
curl -k -H "X-API-Key: $env:UNIFI_API_KEY" https://192.168.0.1/proxy/network/v2/api/site/default/device
```

#### 3. "Port Already in Use"

**Cause:** Another process using port 3000

**Solution:**
```powershell
# Find and kill process
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

#### 4. Mock Data Showing Instead of Real Data

**Cause:** `USE_MOCK_DATA` flag is true or API failing

**Solution:**
```typescript
// In app/api/unifi/route.ts
const USE_MOCK_DATA = false; // Ensure this is false
```

#### 5. Threat Intelligence Not Working

**Cause:** Missing API keys

**Solution:**
```bash
# Add API keys to .env.local
ABUSEIPDB_API_KEY=your_key
VIRUSTOTAL_API_KEY=your_key
```

### Debug Mode

Enable debug logging:

```typescript
// Add to any file
console.log('[DEBUG]', data);

// Check browser console
// Check terminal output
```

### Getting Help

1. Check logs: Terminal output, browser console
2. Review this documentation
3. Contact Morgan (super_admin)
4. Create issue in GitHub

---

## Appendix: Quick Reference Commands

```powershell
# Start development
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev

# Build for production
npm run build

# Start Docker services
cd website\services\security
docker-compose -f docker-compose.security-tools.yml up -d

# Check service status
docker-compose -f docker-compose.security-tools.yml ps

# View logs
docker-compose -f docker-compose.security-tools.yml logs -f

# Stop services
docker-compose -f docker-compose.security-tools.yml down

# Test API
curl http://localhost:3000/api/security?action=status
curl http://localhost:3000/api/unifi?action=dashboard
```

---

**Document Control:**
- Created: January 18, 2026
- Author: Security Team
- Next Review: February 18, 2026
