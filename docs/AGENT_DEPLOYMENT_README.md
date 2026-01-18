# 🤖 Agent Deployment Instructions

> **READ THIS FIRST BEFORE ANY DEPLOYMENT ACTION**

This document contains mandatory requirements for any AI agent deploying to the Mycosoft sandbox environment.

---

## ⛔ STOP - Pre-Deployment Requirements

Before running ANY deployment commands, you MUST:

### 1. Check Windows Cloudflared Status

```powershell
# Run this on Windows FIRST
Get-Process cloudflared -ErrorAction SilentlyContinue
Get-Service cloudflared -ErrorAction SilentlyContinue
```

**If cloudflared is running on Windows, STOP IT:**
```powershell
taskkill /F /IM cloudflared.exe
sc.exe stop cloudflared
```

**Why this is critical:** The Cloudflare tunnel token is shared. If cloudflared runs on Windows, Cloudflare will route traffic to Windows instead of the VM. This causes 502 errors that appear random and are hard to diagnose.

### 2. Read the Full Requirements Document

Before proceeding, read:
- `docs/DEPLOYMENT_REQUIREMENTS.md` - Complete checklist and troubleshooting

---

## 🔧 Deployment Quick Reference

### Connection Details
```
VM IP: 192.168.0.187
User: mycosoft
Password: REDACTED_VM_SSH_PASSWORD
Tunnel ID: bd385313-a44a-47ae-8f8a-581608118127
```

### Deploy Script
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts\deploy_sandbox_now.py
```

### Post-Deployment Verification
```bash
# On VM
curl http://127.0.0.1:20241/ready  # Tunnel health
curl http://127.0.0.1:20241/metrics | grep tunnel_total_requests  # Should be > 0 after test
curl http://localhost:3000/  # Website working
```

---

## 🚨 Common Issues & Solutions

### Issue: 502 Bad Gateway

| Symptom | Cause | Fix |
|---------|-------|-----|
| 502 error, tunnel shows healthy | Cloudflared on Windows intercepting traffic | Stop Windows cloudflared |
| 502 error, tunnel_total_requests = 0 | Wrong connector active | Check Cloudflare Connector Diagnostics |
| 502 error after cache clear | Old JS chunks | Clear Cloudflare cache (Purge Everything) |

### Issue: ChunkLoadError

| Symptom | Cause | Fix |
|---------|-------|-----|
| Pages partially load | Cloudflare caching old assets | Purge Cloudflare cache |
| 502 for .js files | Stale static files | Hard refresh + cache purge |

---

## ✅ Deployment Checklist

Copy and verify each item:

```
Pre-Deployment:
[ ] Cloudflared NOT running on Windows
[ ] Code committed and pushed to GitHub
[ ] No local port conflicts

Deployment:
[ ] SSH connected to 192.168.0.187
[ ] Code pulled from GitHub
[ ] Container rebuilt with --no-cache
[ ] Container restarted
[ ] Cloudflared restarted on VM

Post-Deployment:
[ ] Container shows as running
[ ] Port 3000 returns 200
[ ] Tunnel health shows 4 connections
[ ] Cloudflare cache purged
[ ] Public URL accessible
[ ] Connector Diagnostics shows VM (not Windows)
```

---

## 📚 Documentation Index

| Document | Purpose |
|----------|---------|
| `DEPLOYMENT_REQUIREMENTS.md` | **Mandatory pre-flight checklist** |
| `SANDBOX_DEPLOYMENT_PROCESS.md` | Step-by-step deployment guide |
| `SANDBOX_DEPLOYMENT_JAN18_2026.md` | Recent deployment log with issue resolution |

---

## ⚠️ Known Gotchas

1. **Cloudflared on Windows** - WILL intercept tunnel traffic silently
2. **Container "unhealthy"** - Often false alarm (curl not installed in container)
3. **Tunnel shows healthy but 0 requests** - Check connector, not just status
4. **DNS A records to private IPs** - Won't work, must use CNAME to cfargotunnel.com
5. **Cloudflare cache** - Must purge after EVERY rebuild

---

*Document created: January 18, 2026*
*Purpose: Prevent deployment failures from known issues*
