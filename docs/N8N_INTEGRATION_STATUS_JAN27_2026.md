# n8n Integration Status Report
**Date:** January 27, 2026  
**Purpose:** Verify n8n migration from Sandbox VM to MAS VM and Cloudflare configuration

---

## Current Infrastructure Status

### VM Overview

| VM | IP Address | Role | Status |
|----|------------|------|--------|
| VM 103 (Sandbox) | 192.168.0.187 | Website (production via Cloudflare) | Running |
| VM 188 (MAS) | 192.168.0.188 | MAS Core + n8n + Website (dev) | Running |

### Service Status (Verified)

#### MAS VM (192.168.0.188)
| Service | Port | Status | Notes |
|---------|------|--------|-------|
| n8n | 5678 | ✅ Running | **PRIMARY n8n instance** |
| Website | 3000 | ✅ Running | Development instance |
| MAS API | 8000 | ⚠️ Timeout | Needs investigation |
| Grafana | 3002 | ❌ Not running | Not started |

#### Sandbox VM (192.168.0.187)
| Service | Port | Status | Notes |
|---------|------|--------|-------|
| Website | 3000 | ✅ Running | Production via Cloudflare |
| n8n | 5678 | ✅ Running | **DUPLICATE - should be disabled** |

---

## n8n Configuration

### API Keys Configured

| Key | Location | Purpose |
|-----|----------|---------|
| Local n8n API Key | `.env.local` | MAS VM n8n access |
| n8n Cloud API Key | `.env.local` | Cloud sync |

### Credentials in n8n (MAS VM)
- ✅ ElevenLabs API (Header Auth)
- ✅ OpenAI API
- ✅ Anthropic API

### Active Workflows (11 total)
1. MYCA: Tools Hub
2. MYCA: Jarvis Unified Interface
3. MYCA Comprehensive Integration
4. MYCA: System Control
5. MYCA Orchestrator
6. MYCA: Master Brain
7. MYCA: Proactive Monitor
8. MYCA: Business Ops
9. MYCA Command API
10. MYCA Event Intake
11. MYCA Speech Complete

---

## Cloudflare Configuration

### Current Tunnel Setup (VM 103 - Sandbox)

The Cloudflare tunnel is configured on VM 103 (Sandbox) with these routes:

| Subdomain | Target | Port | Status |
|-----------|--------|------|--------|
| sandbox.mycosoft.com | localhost:3000 | Website | ✅ Active |
| n8n.mycosoft.com | localhost:5678 | n8n | ⚠️ Points to Sandbox |

### Required Updates

Since n8n was moved to MAS VM (192.168.0.188), the Cloudflare tunnel needs to be updated:

#### Option 1: Update tunnel ingress rules (Recommended)
```yaml
# In cloudflared config on Sandbox VM
ingress:
  - hostname: sandbox.mycosoft.com
    service: http://localhost:3000
  
  # Route n8n to MAS VM instead of localhost
  - hostname: n8n.mycosoft.com
    service: http://192.168.0.188:5678
  
  - service: http_status:404
```

#### Option 2: Create separate tunnel on MAS VM
1. Install cloudflared on MAS VM
2. Create new tunnel for MAS services
3. Route n8n.mycosoft.com to MAS tunnel

---

## Webhook Endpoints

### Working Webhooks (MAS VM n8n)
| Webhook Path | Status | Notes |
|--------------|--------|-------|
| `/webhook/myca/command` | ✅ 500 | Responds (internal auth error) |
| `/webhook/myca/speech` | ❌ 404 | Not registering properly |

### Required Webhook Paths (from website code)
| Path | Used By |
|------|---------|
| `/webhook/myca-chat` | Chat API |
| `/webhook/myca/speech_safety` | Voice orchestrator |
| `/webhook/myca/speech_turn` | Voice orchestrator |
| `/webhook/myca/speech_confirm` | Voice confirm |

---

## Action Items

### Immediate
1. [ ] **Disable n8n on Sandbox VM** - Prevent conflicts
2. [ ] **Update Cloudflare tunnel** - Route n8n.mycosoft.com to MAS VM
3. [ ] **Fix MAS API (port 8000)** - Investigate timeout

### Short-term
4. [ ] **Align webhook paths** - Update n8n workflows or website code
5. [ ] **Start Grafana** - Enable monitoring
6. [ ] **Test voice pipeline** - End-to-end verification

### Configuration
7. [ ] **Sync environment files** - Ensure website has correct n8n URL
8. [ ] **Deploy to sandbox** - Push changes and clear Cloudflare cache

---

## Environment Configuration Reference

### MAS VM (.env.local)
```bash
# n8n Integration (Updated Jan 27, 2026)
N8N_URL=http://192.168.0.188:5678
N8N_LOCAL_URL=http://192.168.0.188:5678
N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
N8N_USERNAME=morgan@mycosoft.org
N8N_PASSWORD=REDACTED_VM_SSH_PASSWORD

# n8n Cloud
N8N_CLOUD_URL=https://mycosoft.app.n8n.cloud
N8N_CLOUD_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Website (.env.local)
```bash
N8N_URL=http://192.168.0.188:5678
N8N_CLOUD_URL=https://mycosoft.app.n8n.cloud
```

---

## Deployment Protocol

1. Make code changes locally
2. Test on localhost (npm run dev)
3. Commit and push to GitHub
4. SSH to Sandbox VM: `ssh mycosoft@192.168.0.187`
5. Pull code: `git reset --hard origin/main`
6. Rebuild container: `docker build -t website-website:latest --no-cache .`
7. Restart container: `docker compose -p mycosoft-production up -d mycosoft-website`
8. Purge Cloudflare cache
9. Verify: Compare localhost vs sandbox.mycosoft.com

---

*Document Version: 1.0*  
*Last Updated: January 27, 2026*
