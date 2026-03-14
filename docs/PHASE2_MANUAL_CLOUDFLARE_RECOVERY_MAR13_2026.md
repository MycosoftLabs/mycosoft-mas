# Phase 2 Manual Cloudflare Recovery — March 13, 2026

**Date:** March 13, 2026  
**Status:** Reference  
**Related:** `MYCOSOFT_ORG_PRODUCTION_VM_CLONE_CI_CD_MAR13_2026.md`, `.cursor/plans/mycosoft.org_production_vm_clone_ci_cd_b787e37b.plan.md`

---

## When to Use This Document

Use this document when the Phase 2 automation scripts return **403 Authentication error** (Cloudflare API token lacks permissions). Complete Phase 2 manually in the Cloudflare dashboard.

---

## Prerequisites

- VM 186 is reachable (`ping 192.168.0.186` succeeds)
- Cloudflare account access (mycosoft.com and mycosoft.org zones)
- Production tunnel token (from creating a new tunnel in Cloudflare)

---

## Step 1: Create Production Tunnel

1. **Cloudflare Zero Trust / Dashboard** → **Networks** → **Tunnels**
2. Click **Create a tunnel**
3. Name: `mycosoft-production`
4. Click **Save tunnel**
5. **Install connector:** Choose **Debian/Ubuntu**. Copy the command:
   ```
   cloudflared service install <TOKEN>
   ```
6. **Public Hostnames:**
   - Add: `mycosoft.com` → `http://localhost:3000`
   - Add: `www.mycosoft.com` → `http://localhost:3000`
7. Click **Save tunnel**
8. Copy the token and add to `.credentials.local`:
   ```
   CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION=<paste token>
   ```

---

## Step 2: Restrict Sandbox Tunnel

1. **Networks** → **Tunnels** → Select the **Sandbox** tunnel (the one on VM 187)
2. **Public Hostnames:**
   - Remove `mycosoft.com` if present
   - Remove `www.mycosoft.com` if present
   - Keep **only** `sandbox.mycosoft.com` → `http://localhost:3000`
3. Save

---

## Step 3: mycosoft.org Redirect

1. **Cloudflare** → **Websites** → **mycosoft.org** (or the zone that owns mycosoft.org)
2. **Rules** → **Redirect Rules** → **Single Redirects**
3. **Create rule**
4. **Rule name:** `mycosoft.org → mycosoft.com/about`
5. **When incoming requests match:** Custom filter expression:
   ```
   (http.host eq "mycosoft.org") or (http.host eq "www.mycosoft.org")
   ```
6. **Then:** Dynamic redirect, 301, URL: `https://mycosoft.com/about`
7. Save and deploy

---

## Step 4: Bootstrap cloudflared on VM 186

From MAS repo:

```bash
python scripts/_bootstrap_production_cloudflared_186.py
```

Requires: `VM_PASSWORD`, `CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION` in `.credentials.local`.

---

## Step 5: Deploy Website to Production

From website repo:

```bash
cd WEBSITE/website
python _rebuild_production.py
```

Requires: `VM_PASSWORD`, `CLOUDFLARE_ZONE_ID_PRODUCTION` (or `CLOUDFLARE_ZONE_ID`), `CLOUDFLARE_API_TOKEN` for cache purge.

---

## Verification

| Check | Command / Action |
|-------|------------------|
| Production VM | `ping 192.168.0.186` |
| mycosoft.com | Browser → https://mycosoft.com → 200 |
| www.mycosoft.com | Browser → https://www.mycosoft.com → 200 |
| mycosoft.org | Browser → https://mycosoft.org → 301 → mycosoft.com/about |
| sandbox.mycosoft.com | Browser → https://sandbox.mycosoft.com → 200 |

---

## Troubleshooting

### SSH to VM 186 times out (ping OK, port 22 unreachable)

If `ping 192.168.0.186` succeeds but SSH times out:

1. **Use Proxmox console** on VM 186 (no SSH needed).
2. Enable and start SSH:
   ```bash
   sudo systemctl enable ssh
   sudo systemctl start ssh
   sudo systemctl status ssh
   ```
3. If using UFW firewall:
   ```bash
   sudo ufw allow 22
   sudo ufw reload
   sudo ufw status
   ```
4. Test from your PC: `ssh mycosoft@192.168.0.186`

### Pre-flight script

Run before Steps 4–5:

```bash
python scripts/_preflight_production_live.py
```

This checks ping, SSH port 22, and credentials.

---

## Credentials Checklist

| Variable | Purpose | Where |
|----------|---------|-------|
| `VM_PASSWORD` | SSH to 186 | `.credentials.local` |
| `CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION` | Production tunnel connector | After Step 1 |
| `CLOUDFLARE_ZONE_ID_PRODUCTION` | mycosoft.com zone (cache purge) | Cloudflare zone overview |
| `CLOUDFLARE_API_TOKEN` | Purge cache | Create token with Zone.Cache Purge |
