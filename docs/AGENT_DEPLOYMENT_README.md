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
6. **Docker image vs Git commit** - Git commit may match but Docker image may be stale. **ALWAYS rebuild Docker image** after code changes
7. **Environment variables** - `.env.local` is gitignored. Supabase env vars must be in `docker-compose.yml` environment section
8. **Module-level code** - Any code that runs at module load time (like `createClient()`) will fail during Docker build if env vars aren't set. Use lazy initialization patterns
9. **ALWAYS compare pages** - After deployment, compare sandbox vs local to verify code is actually deployed
10. **Supabase Site URL** - Must be set to production domain (`https://sandbox.mycosoft.com`) in Supabase dashboard → Authentication → URL Configuration. If set to localhost, OAuth will redirect to localhost after authentication
11. **OAuth callback origin** - Docker containers use `HOSTNAME=0.0.0.0` internally. Auth callbacks must use `X-Forwarded-Host` header or `NEXT_PUBLIC_SITE_URL` env var to get the correct external origin
12. **NEXT_PUBLIC_* env vars** - Are baked into the build at compile time. Must be set in `Dockerfile` during build stage, not just in docker-compose.yml

---

## 📋 Post-Deployment Verification

**Always run this check after deployment:**

```bash
# Compare login page - should match local
curl -s http://localhost:3000/login | grep -io 'continue with google'
```

If sandbox doesn't match local:
1. Verify git commit matches
2. **Rebuild Docker image with --no-cache**
3. Restart container
4. Clear Cloudflare cache

---

## 🚀 VM Specifications (Current)

| Resource | Value | Notes |
|----------|-------|-------|
| RAM | 64GB | Upgraded Jan 18, 2026 |
| Disk | 2TB | LVM expanded to use full disk |
| CPUs | 8 cores | Pending upgrade to 16 |
| IP | 192.168.0.187 | Internal network |

---

*Document created: January 18, 2026*
*Updated: January 18, 2026 12:26 AM - Added OAuth fixes, VM specs, comprehensive gotchas*
*Purpose: Prevent deployment failures from known issues*
