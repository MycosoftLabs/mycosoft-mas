# Sandbox Deployment Complete - January 18, 2026

## Summary

Successfully deployed the latest Mycosoft website to `sandbox.mycosoft.com` (VM 103).

**Final Status: ✅ FULLY OPERATIONAL**

---

## ✅ All Tasks Completed

### 1. Code Pushed to GitHub
- **Commit**: `4eec829` - "feat: Super Admin Control Center, access control, Supabase integration, CREP improvements"
- All changes from local development pushed to main branch

### 2. Website Container Rebuilt
- Code pulled from GitHub: `git reset --hard origin/main`
- Container restarted successfully
- All 16 Docker containers running

### 3. PostGIS Extension Enabled
- Executed: `CREATE EXTENSION IF NOT EXISTS postgis;`
- MINDEX Postgres database ready for geospatial queries

### 4. Cloudflare Tunnel Fixed
- **Critical Issue Found**: Cloudflared was running on Windows PC, intercepting tunnel traffic
- **Resolution**: Stopped cloudflared on Windows, allowing VM connector to receive traffic
- Tunnel now properly routing to VM

### 5. Cloudflare Cache Cleared
- Purged all cached content from Cloudflare
- Resolved ChunkLoadError issues

### 6. All Pages Verified Working

| Page | Status | Notes |
|------|--------|-------|
| Homepage (`/`) | ✅ Works | Full functionality |
| NatureOS (`/natureos`) | ✅ Works | Complete |
| Devices (`/devices`) | ✅ Works | All hardware displayed |
| Apps (`/apps`) | ✅ Works | Complete |
| Admin (`/admin`) | ✅ Works | Requires super admin auth |

---

## 🚨 Critical Issue Encountered & Resolved

### Problem: 502 Bad Gateway Error

**Symptoms:**
- `sandbox.mycosoft.com` returned 502 Bad Gateway
- Cloudflare showed "Host Error"
- Tunnel logs showed 0 requests received despite being "healthy"

**Root Cause:**
Cloudflared was running on the **Windows development PC (MycoComp)** with the same tunnel token as the VM. Cloudflare was routing traffic to Windows (IP: 192.168.0.172) instead of the Proxmox VM (IP: 192.168.0.187).

**Evidence Found:**
- Cloudflare Connector Diagnostics showed:
  - Connector ID: `749f3bb2-11f3-45e9-833c-de4a39801493`
  - Private IP: `192.168.0.172` (Windows PC)
  - Hostname: `MycoComp`
  - Platform: `windows_amd64`

**Resolution:**
```powershell
# On Windows PC - stop cloudflared
taskkill /F /IM cloudflared.exe
sc.exe stop cloudflared
```

After stopping the Windows cloudflared, Cloudflare automatically routed to the VM connector.

---

## Deployment Details

### Connection Information
```python
VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"
```

### Tunnel Information
```
Tunnel ID: bd385313-a44a-47ae-8f8a-581608118127
Account ID: c30faf87aff14a9a75ad9efa5a432f37
VM Connector ID: 2de2d4c3-25ab-4335-991b-7b3b4259e93a
```

### Key Commands Used
```bash
# Pull latest code
git fetch origin main && git reset --hard origin/main

# Rebuild container
docker compose -p mycosoft-production build mycosoft-website --no-cache
docker compose -p mycosoft-production up -d mycosoft-website

# Restart tunnel
sudo systemctl restart cloudflared

# Check tunnel health
curl http://127.0.0.1:20241/ready

# Check tunnel requests
curl http://127.0.0.1:20241/metrics | grep tunnel_total_requests
```

---

## Running Containers on VM 103

| Container | Status | Port |
|-----------|--------|------|
| mycosoft-website | Up (healthy) | 3000 |
| mas-orchestrator | Up (healthy) | 8001 |
| mindex-api | Up (healthy) | 8000 |
| mas-postgres | Up (healthy) | 5433 |
| redis | Up (healthy) | 6379 |
| qdrant | Up | 6333 |
| n8n | Up | 5678 |
| openedai-speech | Up | 5500 |
| myca-dashboard | Up (healthy) | 3100 |
| mycobrain | Up (healthy) | 8003 |
| prometheus | Up | 9090 |
| whisper | Up | 8765 |
| ollama | Up | 11434 |
| tts | Up | 10200 |
| grafana | Up | 3002 |
| mindex-postgres | Up (healthy) | (internal) |

---

## Service URLs

### Public (via Cloudflare Tunnel)
- https://sandbox.mycosoft.com
- https://sandbox.mycosoft.com/natureos
- https://sandbox.mycosoft.com/devices
- https://sandbox.mycosoft.com/apps
- https://api-sandbox.mycosoft.com (MINDEX API)
- https://brain-sandbox.mycosoft.com (MycoBrain)

### Internal (Local Network)
- http://192.168.0.187:3000 (Website)
- http://192.168.0.187:8000 (MINDEX API)
- http://192.168.0.187:8003 (MycoBrain)
- http://192.168.0.187:5678 (n8n)
- http://192.168.0.187:3100 (MYCA Dashboard)

---

## Lessons Learned

1. **Never run cloudflared on Windows with production tunnel token** - it will intercept all traffic
2. **Check Cloudflare Connector Diagnostics** to verify which machine is receiving traffic
3. **Tunnel can show "healthy" but receive 0 requests** - check connector details, not just status
4. **DNS A records pointing to private IPs** will cause 502 errors - use CNAME to cfargotunnel.com
5. **Always clear Cloudflare cache after rebuilding** - old static assets cause ChunkLoadErrors

---

*Deployment completed: January 18, 2026 02:20 UTC*
*Deployed by: Cursor AI Agent via Paramiko SSH*
*Issue resolved: Cloudflared conflict with Windows PC*
