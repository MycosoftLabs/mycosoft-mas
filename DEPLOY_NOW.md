# MYCA Production Deployment - Action Required

## Current Status ✅
- **Local Website**: Running on localhost:3000
- **MINDEX API**: Running on localhost:8000 (5,558+ taxa)
- **MYCA Dashboard**: Running on localhost:3100 (42 agents)
- **All Docker Services**: 16 containers running
- **Proxmox Build Node**: Online at 192.168.0.202
- **Dream Machine**: Online at 192.168.0.1
- **Public IP**: 38.78.169.199
- **Domain**: mycosoft.com (currently parked at GoDaddy)

---

## 🔴 ACTION 1: Login to GoDaddy and Configure DNS

**Browser tab is already open at GoDaddy login.**

1. **Enter your GoDaddy credentials** in the open browser tab
2. After login, you'll be taken to DNS management for mycosoft.com
3. **Change DNS records:**

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | 38.78.169.199 | 600 |
| CNAME | www | mycosoft.com | 600 |
| CNAME | api | mycosoft.com | 600 |
| CNAME | dashboard | mycosoft.com | 600 |

Or for Cloudflare (BETTER - more security):
- In GoDaddy, change **Nameservers** to Cloudflare's
- Then configure DNS in Cloudflare

---

## 🔴 ACTION 2: Open Proxmox and Create API Token

**Manual step (self-signed certificate):**

1. Open browser manually: **https://192.168.0.202:8006**
2. Click "Advanced" → "Proceed to 192.168.0.202 (unsafe)"
3. Login with your Proxmox credentials
4. Navigate to: **Datacenter → Permissions → API Tokens**
5. Click **Add**:
   - User: `root@pam` (or your admin user)
   - Token ID: `myca-deploy`
   - Privilege Separation: **Uncheck** (full permissions)
6. **COPY THE SECRET** (shown only once!)
7. Come back here and run:

```powershell
$env:PROXMOX_TOKEN_ID = "root@pam!myca-deploy"
$env:PROXMOX_TOKEN_SECRET = "your-copied-secret"
.\scripts\automated_deployment.ps1 -Interactive
```

---

## 🔴 ACTION 3: Enable SMB on UniFi Dream Machine

**Manual step (self-signed certificate):**

1. Open browser manually: **https://192.168.0.1**
2. Click "Advanced" → "Proceed to 192.168.0.1 (unsafe)"  
3. Login to UniFi OS
4. Go to: **Console Settings → Storage**
5. Enable **Windows File Sharing (SMB)**
6. Create share named `mycosoft`
7. Set credentials for access

After enabling, run:
```powershell
.\scripts\mount_nas.ps1
```

---

## 🟢 ONCE ALL ACTIONS COMPLETE

Run the full automated deployment:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\automated_deployment.ps1 -Interactive
```

Or manually:

```powershell
# 1. Create production VMs
python scripts/production/create_all_vms.py --start

# 2. Deploy website to production
.\scripts\production\deploy_all.ps1

# 3. Verify
Start-Process "https://mycosoft.com"
```

---

## Quick Reference

| System | URL | Purpose |
|--------|-----|---------|
| GoDaddy | https://dcc.godaddy.com | Domain DNS |
| Proxmox | https://192.168.0.202:8006 | VM Management |
| UniFi | https://192.168.0.1 | NAS Storage |
| Cloudflare | https://dash.cloudflare.com | CDN/Security |

| Your Info | Value |
|-----------|-------|
| Public IP | 38.78.169.199 |
| Domain | mycosoft.com |
| Build Node | 192.168.0.202 |
| Dream Machine | 192.168.0.1 |

---

## After DNS Propagation (1-24 hours)

Your site will be live at:
- https://mycosoft.com - Main website
- https://api.mycosoft.com - API endpoints
- https://dashboard.mycosoft.com - MYCA Dashboard

Run verification:
```powershell
.\scripts\production\go_live_checklist.sh
```
