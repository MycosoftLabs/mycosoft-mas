# Pre-Production Checklist — Cloudflare, Supabase, API Routes

**Date:** March 13, 2026  
**Status:** Reference  
**Related:** `PHASE2_MANUAL_CLOUDFLARE_RECOVERY_MAR13_2026.md`, `mycosoft.org_production_vm_clone_ci_cd_b787e37b.plan.md`

---

## Purpose

Before going live with mycosoft.com / mycosoft.org, verify Cloudflare tunnels/DNS, Supabase auth redirect URLs, and all API/MAS/MINDEX routes for both production and sandbox.

---

## 1. Cloudflare Tunnels and DNS

### Production (VM 186)
| Item | Expected | Verification |
|------|----------|--------------|
| Tunnel | `mycosoft-production` | Cloudflare Zero Trust → Networks → Tunnels |
| Hostnames | `mycosoft.com`, `www.mycosoft.com` | Both → `http://localhost:3000` |
| cloudflared | Running on VM 186 | `ssh 186; systemctl status cloudflared` |
| Token | `CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION` | In `.credentials.local` |

### Sandbox (VM 187)
| Item | Expected | Verification |
|------|----------|--------------|
| Tunnel | Sandbox tunnel (separate) | Cloudflare Zero Trust → Tunnels |
| Hostname | `sandbox.mycosoft.com` only | → `http://localhost:3000` |
| Restriction | Must NOT have `mycosoft.com` or `www.mycosoft.com` | Remove if present |

### mycosoft.org
| Item | Expected | Verification |
|------|----------|--------------|
| Redirect | 301 → `https://mycosoft.com/about` | Rules → Redirect Rules → Single Redirects |
| Match | `(http.host eq "mycosoft.org") or (http.host eq "www.mycosoft.org")` | Custom filter expression |
| Action | Dynamic redirect, 301, URL: `https://mycosoft.com/about` | |

### Manual Steps (if API returns 403)
See `PHASE2_MANUAL_CLOUDFLARE_RECOVERY_MAR13_2026.md`.

---

## 2. Supabase Auth (Live mycosoft.com)

### Redirect URLs (Supabase Dashboard)
In **Supabase** → **Authentication** → **URL Configuration** → **Redirect URLs**, add:
- `https://mycosoft.com`
- `https://www.mycosoft.com`
- `https://mycosoft.com/**`
- `https://www.mycosoft.com/**`
- `https://sandbox.mycosoft.com`
- `https://sandbox.mycosoft.com/**`

### Site URL
Set **Site URL** to `https://mycosoft.com` (or leave default if it matches).

### Build-Time Variables (Required)
The website container needs these at **build time** (baked into client JS):
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

**Source:** `.env.local` or `.credentials.local` in website repo. Rebuild scripts pass them via `--build-arg` when present.

### Runtime Variables (Optional)
- `NEXTAUTH_SECRET` — for NextAuth
- `NEXTAUTH_URL` — set to site base URL (production: `https://mycosoft.com`, sandbox: `https://sandbox.mycosoft.com`)

---

## 3. API and VM Routes

### MAS (192.168.0.188:8001)
| Use | URL | Used By |
|-----|-----|---------|
| MAS API | `http://192.168.0.188:8001` | Website proxy routes `/api/mas/*` |
| Health | `http://192.168.0.188:8001/health` | Preflight, health checks |

### MINDEX (192.168.0.189:8000)
| Use | URL | Used By |
|-----|-----|---------|
| MINDEX API | `http://192.168.0.189:8000` | Website proxy routes `/api/mindex/*` |
| Health | `http://192.168.0.189:8000/health` | Preflight |

### Container Environment (docker run -e)
Both production and sandbox containers receive:
- `MAS_API_URL=http://192.168.0.188:8001`
- `MINDEX_API_URL=http://192.168.0.189:8000`
- `OLLAMA_BASE_URL=http://192.168.0.188:11434`
- `N8N_URL=http://192.168.0.188:5678`

Production also:
- `NEXT_PUBLIC_BASE_URL=https://mycosoft.com`
- `NEXTAUTH_URL=https://mycosoft.com`

Sandbox also (after fix):
- `NEXT_PUBLIC_BASE_URL=https://sandbox.mycosoft.com`
- `NEXTAUTH_URL=https://sandbox.mycosoft.com`
- `MYCOBRAIN_SERVICE_URL`, `MYCOBRAIN_API_URL` (host.docker.internal:8003)

### api-urls.ts
`lib/config/api-urls.ts` uses env vars with defaults. No hardcoded production URLs; defaults point to VM IPs.

---

## 4. Verification Commands

```powershell
# VM reachability
ping 192.168.0.186
ping 192.168.0.187
ping 192.168.0.188
ping 192.168.0.189

# API health (from dev machine)
Invoke-RestMethod http://192.168.0.188:8001/health
Invoke-RestMethod http://192.168.0.189:8000/health

# Live sites (browser)
# https://mycosoft.com → 200
# https://www.mycosoft.com → 200
# https://mycosoft.org → 301 → mycosoft.com/about
# https://sandbox.mycosoft.com → 200

# Preflight script
cd MAS
python scripts/_preflight_production_live.py
```

---

## 5. Credentials Checklist

| Variable | Purpose | Where |
|----------|---------|-------|
| `VM_PASSWORD` | SSH to 186, 187 | `.credentials.local` |
| `CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION` | Production tunnel | After creating tunnel |
| `CLOUDFLARE_ZONE_ID_PRODUCTION` | mycosoft.com zone (purge) | Cloudflare zone overview |
| `CLOUDFLARE_API_TOKEN` | Purge cache | Create token with Zone.Cache Purge |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase (build) | `.env.local` or `.credentials.local` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase (build) | `.env.local` or `.credentials.local` |
| `NEXTAUTH_SECRET` | NextAuth | `.env.local` |

---

## 6. Deploy Order

1. Run `python scripts/_preflight_production_live.py`
2. Bootstrap cloudflared on VM 186: `python scripts/_bootstrap_production_cloudflared_186.py`
3. Deploy website: `cd WEBSITE/website && python _rebuild_production.py`
4. Purge Cloudflare cache (automatic when zone/token configured)
5. Verify all URLs in browser
