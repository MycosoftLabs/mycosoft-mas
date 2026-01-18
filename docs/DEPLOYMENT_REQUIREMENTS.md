# Deployment Requirements & Pre-Flight Checklist

> ⚠️ **MANDATORY READING FOR ALL AGENTS BEFORE DEPLOYMENT**
> 
> This document contains critical requirements learned from production issues.
> Failure to follow these requirements WILL cause deployment failures.

---

## 🔴 Critical Pre-Deployment Checks

### 1. Verify No Cloudflared Running on Windows

**BEFORE deploying, check if cloudflared is running on the local Windows machine:**

```powershell
# Check for cloudflared process
Get-Process cloudflared -ErrorAction SilentlyContinue

# Check for cloudflared service
Get-Service cloudflared -ErrorAction SilentlyContinue
```

**If cloudflared is running on Windows, STOP IT:**

```powershell
taskkill /F /IM cloudflared.exe
sc.exe stop cloudflared
```

**Why:** The production tunnel token should ONLY be used on the Proxmox VM. If cloudflared runs on Windows with the same token, Cloudflare will route traffic to Windows instead of the VM, causing 502 errors.

---

### 2. Verify Cloudflare Connector Diagnostics

After deployment, verify in Cloudflare Zero Trust Dashboard:

1. Go to: **Networks → Tunnels → mycosoft-tunnel**
2. Click **Configure** → **Connectors**
3. Verify the active connector shows:
   - **Private IP:** `192.168.0.187` (VM IP, NOT 192.168.0.172)
   - **Platform:** `linux_amd64` (NOT windows_amd64)
   - **Hostname:** `mycosoft-sandbox` (NOT MycoComp)

**If you see Windows/MycoComp:** Stop cloudflared on Windows immediately.

---

### 3. Verify DNS Records

In Cloudflare DNS for `mycosoft.com`:

| Subdomain | Type | Target | Proxy |
|-----------|------|--------|-------|
| sandbox | CNAME | `bd385313-a44a-47ae-8f8a-581608118127.cfargotunnel.com` | ✅ ON |
| api-sandbox | CNAME | `bd385313-a44a-47ae-8f8a-581608118127.cfargotunnel.com` | ✅ ON |
| brain-sandbox | CNAME | `bd385313-a44a-47ae-8f8a-581608118127.cfargotunnel.com` | ✅ ON |

**DO NOT create A records pointing to private IPs (192.168.x.x)** - they won't work from the internet.

---

### 4. Clear Cloudflare Cache After Rebuild

**Every time the website container is rebuilt, purge Cloudflare cache:**

1. Go to: https://dash.cloudflare.com
2. Select domain: `mycosoft.com`
3. Navigate to: **Caching** → **Configuration**
4. Click: **Purge Everything**
5. Wait 60 seconds before testing

**Why:** Old JavaScript chunks cached by Cloudflare will cause `ChunkLoadError` failures.

---

## 📋 Deployment Checklist

### Pre-Deployment

- [ ] Verify cloudflared is NOT running on Windows
- [ ] Verify no port conflicts on local machine
- [ ] Commit and push all code to GitHub
- [ ] Note the current commit hash

### Deployment Steps

- [ ] SSH to VM: `ssh mycosoft@192.168.0.187`
- [ ] Pull code: `cd /opt/mycosoft/website && git pull origin main`
- [ ] Rebuild: `docker compose -p mycosoft-production build mycosoft-website --no-cache`
- [ ] Restart: `docker compose -p mycosoft-production up -d mycosoft-website`
- [ ] Restart tunnel: `sudo systemctl restart cloudflared`
- [ ] Wait 30 seconds for startup

### Post-Deployment Verification

- [ ] Check container health: `docker ps --filter name=mycosoft-website`
- [ ] Check port 3000: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/`
- [ ] Check tunnel health: `curl -s http://127.0.0.1:20241/ready`
- [ ] Check tunnel requests: `curl -s http://127.0.0.1:20241/metrics | grep tunnel_total_requests`
- [ ] Verify Cloudflare Connector shows VM (not Windows)
- [ ] Clear Cloudflare cache
- [ ] Test public URL: https://sandbox.mycosoft.com
- [ ] Test devices page: https://sandbox.mycosoft.com/devices

---

## 🔧 Troubleshooting Guide

### Issue: 502 Bad Gateway

**Symptoms:**
- Cloudflare shows "Host Error"
- Website unreachable via public URL
- Works fine via direct IP (192.168.0.187:3000)

**Diagnostic Steps:**

1. **Check tunnel requests:**
   ```bash
   curl -s http://127.0.0.1:20241/metrics | grep tunnel_total_requests
   ```
   If `tunnel_total_requests 0` - Cloudflare isn't routing to this tunnel

2. **Check Cloudflare Connector Diagnostics:**
   - Look for Private IP and Hostname
   - If it shows Windows/MycoComp - that's the problem

3. **Check for duplicate cloudflared:**
   ```powershell
   # On Windows
   Get-Process cloudflared -ErrorAction SilentlyContinue
   ```

**Fix:**
```powershell
# Stop Windows cloudflared
taskkill /F /IM cloudflared.exe
sc.exe stop cloudflared

# Then restart VM tunnel
ssh mycosoft@192.168.0.187 "sudo systemctl restart cloudflared"
```

---

### Issue: ChunkLoadError

**Symptoms:**
- Pages partially load then show error
- Console shows `ChunkLoadError: Loading chunk XXXX failed`
- 502 errors for `.js` files

**Fix:**
1. Clear Cloudflare cache (Purge Everything)
2. Hard refresh browser (Ctrl+Shift+R)

---

### Issue: Container Shows "unhealthy"

**Note:** The `unhealthy` status is often a false alarm because the Docker healthcheck uses `curl` which isn't installed in the Next.js container.

**Verify manually:**
```bash
curl -s http://localhost:3000/
curl -s http://localhost:3000/api/health
```

If these return 200, the container is fine.

---

## 🔑 Connection Details

### VM (Proxmox)
```
Host: 192.168.0.187
User: mycosoft
Password: Mushroom1!Mushroom1!
Website Path: /opt/mycosoft/website
Docker Compose Path: /opt/mycosoft/docker-compose.yml
Project Name: mycosoft-production
```

### Cloudflare Tunnel
```
Tunnel Name: mycosoft-tunnel
Tunnel ID: bd385313-a44a-47ae-8f8a-581608118127
Account ID: c30faf87aff14a9a75ad9efa5a432f37
Token Location: /etc/systemd/system/cloudflared.service
```

### Public Hostnames
```
sandbox.mycosoft.com → http://localhost:3000
api-sandbox.mycosoft.com → http://localhost:8000
brain-sandbox.mycosoft.com → http://localhost:8003
```

---

## 📝 Deployment Scripts

### Automated Deployment
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts\deploy_sandbox_now.py
```

### Manual SSH Commands
```bash
# Full deployment
ssh mycosoft@192.168.0.187 << 'EOF'
cd /opt/mycosoft/website
git fetch origin main
git reset --hard origin/main
cd /opt/mycosoft
docker compose -p mycosoft-production build mycosoft-website --no-cache
docker compose -p mycosoft-production up -d mycosoft-website
sudo systemctl restart cloudflared
docker ps --filter name=mycosoft-website
EOF
```

---

## 📚 Related Documentation

- `SANDBOX_DEPLOYMENT_JAN18_2026.md` - Detailed deployment log with issue resolution
- `SANDBOX_DEPLOYMENT_PROCESS.md` - Step-by-step deployment guide
- `SANDBOX_DEPLOYMENT_TROUBLESHOOTING.md` - Additional troubleshooting steps

---

*Last Updated: January 18, 2026*
*Author: Cursor AI Agent*
*Reviewed After: 502 Error Resolution - Cloudflared Windows Conflict*
