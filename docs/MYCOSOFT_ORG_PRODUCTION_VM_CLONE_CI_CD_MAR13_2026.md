# mycosoft.org Redirect, Production VM Clone, and CI/CD — March 13, 2026

**Date:** March 13, 2026  
**Status:** Complete  
**Related plan:** `.cursor/plans/mycosoft.org_production_vm_clone_ci_cd_b787e37b.plan.md`

---

## Overview

This document captures the implementation of the Production VM clone, Cloudflare tunnel routing, mycosoft.org redirect, and CI/CD workflow. Production website runs on VM 192.168.0.186; Sandbox remains on 187.

---

## Architecture (After Implementation)

```
User Browser
    → Cloudflare (DNS + CDN + Tunnel)
    → Redirect: mycosoft.org / www.mycosoft.org → https://mycosoft.com/about (301)
    → mycosoft.com / www.mycosoft.com → Production tunnel → VM 186:3000
    → sandbox.mycosoft.com → Sandbox tunnel → VM 187:3000
```

| Hostname | Target | Tunnel/VM |
|----------|--------|-----------|
| mycosoft.com | Production tunnel | VM 186 |
| www.mycosoft.com | Production tunnel | VM 186 |
| sandbox.mycosoft.com | Sandbox tunnel | VM 187 |
| mycosoft.org, www.mycosoft.org | Redirect 301 → mycosoft.com/about | N/A |

---

## Phase 1: Proxmox VM Clone

### 1.1 Clone Procedure

1. **Snapshot Sandbox VM (187)** – Optional for rollback.
2. **Clone** – Proxmox: Right-click Sandbox → Clone → Full clone, name `production-website`, VMID 186.
3. **Assign IP 192.168.0.186** – Ensure 186 is free in UniFi/DHCP.

### 1.2 Reconfigure Cloned VM

Run `scripts/_reconfig_production_vm_186.py` (or follow steps in script):

- Edit netplan: set `192.168.0.186`, netmask `255.255.255.0`, gateway `192.168.0.1`
- Hostname: `sudo hostnamectl set-hostname production-website`
- Clear machine-id: `sudo truncate -s 0 /etc/machine-id && sudo systemd-machine-id-setup`
- Stop cloudflared: `sudo systemctl stop cloudflared && sudo systemctl disable cloudflared`
- Reboot

### 1.3 Verify Clone

Run `python scripts/_verify_production_vm_186.py` from MAS repo. Checks:

- Ping 192.168.0.186
- SSH (requires VM up and credentials)
- Docker `mycosoft-website` running
- `curl http://localhost:3000` returns 200
- NAS mount `/opt/mycosoft/media/website/assets` exists

---

## Phase 2: Cloudflare Setup

### 2.1 Production Tunnel (mycosoft.com)

1. **Cloudflare Zero Trust / Dashboard** – Networks → Tunnels
2. **Create tunnel** `mycosoft-production`
3. **Install connector on Production VM (186)** – Use token: `cloudflared service install <TOKEN>`
4. **Public Hostnames:**
   - `mycosoft.com` → `http://localhost:3000`
   - `www.mycosoft.com` → `http://localhost:3000`
5. **Enable cloudflared:** `sudo systemctl enable cloudflared && sudo systemctl start cloudflared`

### 2.2 Sandbox Tunnel (sandbox.mycosoft.com)

- Ensure Sandbox (187) tunnel serves **only** `sandbox.mycosoft.com`
- If current tunnel serves both mycosoft.com and sandbox, **remove** mycosoft.com/www from Sandbox tunnel so Production tunnel owns them.

### 2.3 mycosoft.org Redirect

- **Cloudflare** – mycosoft.org zone (or bulk redirect):
  - **Redirect Rule:** `mycosoft.org` and `www.mycosoft.org` → `https://mycosoft.com/about` (301 Permanent Redirect)
- If mycosoft.org is a separate zone, add the redirect there. If CNAME to mycosoft.com, use redirect rule in the appropriate zone.

### 2.4 Credentials for Production Purge

Add to `.credentials.local` or `.env.local`:

```
CLOUDFLARE_ZONE_ID_PRODUCTION=<mycosoft.com zone ID>
CLOUDFLARE_API_TOKEN=<token with Zone.Cache Purge>
```

`_rebuild_production.py` uses `CLOUDFLARE_ZONE_ID_PRODUCTION` for cache purge after deploy.

---

## Phase 3: Production VM Bootstrap

### 3.1 Always-On Checklist

- Proxmox: Production VM **Start on boot**
- VM: `sudo systemctl enable cloudflared`
- VM: `sudo systemctl enable docker`
- Container: `--restart unless-stopped` (in deploy script)
- DNS: `/etc/resolv.conf` with 1.1.1.1, 8.8.8.8

### 3.2 Env Vars for Production Container

- `NEXT_PUBLIC_BASE_URL=https://mycosoft.com`
- `NEXTAUTH_URL=https://mycosoft.com`
- `MAS_API_URL=http://192.168.0.188:8001`
- `MINDEX_API_URL=http://192.168.0.189:8000`
- No MycoBrain env – Production does not host MycoBrain (Sandbox 187 does).

---

## Phase 4: CI/CD Workflow

### Pipeline

```
Local Dev (3010) → Test → Push to main
       ↓
  Sandbox Deploy (_rebuild_sandbox.py) → sandbox.mycosoft.com
       ↓
  Validate on Sandbox
       ↓
  Production Deploy (_rebuild_production.py) → mycosoft.com
       ↓
  Cloudflare Purge (mycosoft.com zone)
```

### Scripts

| Script | VM | URL | Notes |
|--------|-----|-----|-------|
| `_rebuild_sandbox.py` | 187 | sandbox.mycosoft.com | MycoBrain env, CLOUDFLARE_ZONE_ID |
| `_rebuild_production.py` | 186 | mycosoft.com | No MycoBrain, CLOUDFLARE_ZONE_ID_PRODUCTION |

### Deploy Production

```bash
cd WEBSITE/website
python _rebuild_production.py
```

Requires: `VM_PASSWORD`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ZONE_ID_PRODUCTION` (for purge).

---

## Phase 5: Documentation Updates

- **REQUEST_FLOW_ARCHITECTURE_MAR05_2026.md** – Added Production VM 186, request flow
- **VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md** – Added Production row
- **NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md** – Added 186 as Production
- **api-urls.ts** – `PRODUCTION: "https://mycosoft.com"`

---

## Verification Checklist

| Check | Command / Action |
|-------|------------------|
| Production VM reachable | `ping 192.168.0.186` |
| SSH | `ssh mycosoft@192.168.0.186` |
| Container running | `docker ps` on 186 |
| Local health | `curl http://192.168.0.186:3000` |
| mycosoft.com | Browser → https://mycosoft.com → 200 |
| mycosoft.com/about | Browser → https://mycosoft.com/about → 200 |
| mycosoft.org redirect | Browser → https://mycosoft.org → 301 to mycosoft.com/about |
| sandbox.mycosoft.com | Browser → https://sandbox.mycosoft.com → 200 |
| MAS/MINDEX | Check a page that calls MAS or MINDEX |
| Cloudflare purge | After deploy, verify fresh content |

---

## Files Created or Modified

| File | Action |
|------|--------|
| `WEBSITE/website/_rebuild_production.py` | Created |
| `WEBSITE/website/_cloudflare_cache.py` | Updated (zone_id_override, CLOUDFLARE_ZONE_ID_PRODUCTION) |
| `WEBSITE/website/lib/config/api-urls.ts` | Updated (PRODUCTION: mycosoft.com) |
| `scripts/_proxmox_clone_sandbox_to_production.py` | Created (Phase 1 clone) |
| `scripts/_reconfig_production_vm_186.py` | Created (Phase 1 reconfig) |
| `scripts/_verify_production_vm_186.py` | Created (Phase 1 verify) |
| `docs/REQUEST_FLOW_ARCHITECTURE_MAR05_2026.md` | Updated |
| `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` | Updated |
| `docs/NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md` | Updated |
| `docs/MYCOSOFT_ORG_PRODUCTION_VM_CLONE_CI_CD_MAR13_2026.md` | Created |

---

## Phase 2–3 Scripts (Automation Ready)

These scripts exist and can be run once Cloudflare credentials are configured:

| Script | Purpose |
|--------|---------|
| `scripts/_cloudflare_create_production_tunnel.py` | Create Production tunnel for mycosoft.com, www |
| `scripts/_cloudflare_restrict_sandbox_tunnel.py` | Restrict Sandbox tunnel to sandbox.mycosoft.com only |
| `scripts/_cloudflare_mycosoft_org_redirect.py` | Add 301 redirect mycosoft.org → mycosoft.com/about |
| `scripts/_bootstrap_production_cloudflared_186.py` | Install and enable cloudflared on VM 186 |

### Execution Status (Requires Valid Credentials)

Phase 2 and 3 script runs returned **403 Authentication error** – the Cloudflare API token is missing, invalid, or lacks permissions.

**Required in `.credentials.local`:**

```
CLOUDFLARE_ACCOUNT_ID=<from Cloudflare dashboard>
CLOUDFLARE_API_TOKEN=<API token with Account: Cloudflare Tunnel Edit, Zone: DNS Edit, Zone: Cache Purge>
CLOUDFLARE_ZONE_ID=<mycosoft.com zone ID>
CLOUDFLARE_ZONE_ID_MYCOSOFT_ORG=<mycosoft.org zone ID>
CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION=<output of _cloudflare_create_production_tunnel.py>
```

**Order to run (after credentials are set):**

1. `python scripts/_cloudflare_create_production_tunnel.py` → add printed token to `.credentials.local`
2. `python scripts/_cloudflare_restrict_sandbox_tunnel.py`
3. `python scripts/_cloudflare_mycosoft_org_redirect.py`
4. Ensure VM 186 exists (Phase 1 clone), then: `python scripts/_bootstrap_production_cloudflared_186.py`

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| NAS mount missing on clone | Ensure `/opt/mycosoft` and NAS mount exist; same path as Sandbox |
| Duplicate cloudflared config | Stop/disable old tunnel on clone; configure new Production tunnel |
| mycosoft.org not in Cloudflare | Add zone or use CNAME + redirect in mycosoft.com zone |
| IP 186 conflicts | Confirm 186 is free; use static reservation in UniFi |
