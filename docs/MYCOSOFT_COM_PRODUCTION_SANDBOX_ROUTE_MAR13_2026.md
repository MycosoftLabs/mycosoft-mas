# mycosoft.com Production via Sandbox VM — March 13, 2026

**Status:** Implementation complete. Manual steps and VM build fix required for full production cutover.

**Related plan:** mycosoft.com Production Sandbox Route (attached plan file)

---

## Summary

Route **mycosoft.com** and **www.mycosoft.com** to the existing Sandbox VM (192.168.0.187) by repurposing it as production, since VM 186 was never created due to Proxmox disk space constraints.

---

## Completed Work

### 1. Cloudflare: mycosoft.com and www.mycosoft.com on Sandbox Tunnel

- **Done.** Tunnel `mycosoft-tunnel` (VM 187) now serves:
  - `mycosoft.com` → http://localhost:3000
  - `www.mycosoft.com` → http://localhost:3000
  - `sandbox.mycosoft.com` → http://localhost:3000

- **Script:** `scripts/_cloudflare_add_mycosoft_com_to_sandbox_tunnel.py`

### 2. Cloudflare: mycosoft.org 301 Redirect

- **Script ready.** `scripts/_cloudflare_mycosoft_org_redirect.py` with zone auto-discovery.
- **API 403:** Current Cloudflare API token lacks Zone Rulesets edit permission. **Manual step required:**
  - Cloudflare Dashboard → **mycosoft.org** zone → Rules → Single Redirects (or Redirect Rules)
  - Create rule: When hostname is `mycosoft.org` OR `www.mycosoft.org` → 301 redirect to `https://mycosoft.com/about`

### 3. Rebuild Script: --production Flag

- **Done.** `WEBSITE/website/_rebuild_sandbox.py` accepts `--production`:
  - Sets `NEXT_PUBLIC_BASE_URL=https://mycosoft.com` and `NEXTAUTH_URL=https://mycosoft.com`
  - Without flag: uses `sandbox.mycosoft.com`

```bash
cd WEBSITE/website
python _rebuild_sandbox.py --production
```

- **Fix applied:** Corrected `_build_supabase_args()` so `--build-arg` is passed to `docker build` (no longer run as a separate shell command).

### 4. Supabase: Auth Redirect URLs

- **Script ready.** `scripts/_supabase_add_mycosoft_com_redirect_urls.py` adds mycosoft.com URLs via Supabase Management API.
- **Requires:** `SUPABASE_ACCESS_TOKEN` (Personal Access Token from https://supabase.com/dashboard/account/tokens). Add to `.credentials.local`, then run:
  ```bash
  python scripts/_supabase_add_mycosoft_com_redirect_urls.py
  ```
- **Manual alternative:** Supabase Dashboard → Mycosoft.com Production → Authentication → URL Configuration:
  - Redirect URLs: add `https://mycosoft.com`, `https://www.mycosoft.com`, `https://mycosoft.com/**`, `https://www.mycosoft.com/**`
  - Site URL: set to `https://mycosoft.com`

### 5. DNS: mycosoft.com and www.mycosoft.com

- **Done.** CNAME records added via `scripts/_cloudflare_add_mycosoft_com_dns.py`:
  - `mycosoft.com` → tunnel `bd385313-a44a-47ae-8f8a-581608118127.cfargotunnel.com`
  - `www.mycosoft.com` → same tunnel
- **Result:** https://mycosoft.com and https://www.mycosoft.com now resolve and serve the website.

### 6. Deploy and Purge

- **Deploy attempted.** Production deploy ran; Docker build on VM 187 failed with:
  - Legacy builder: `dockerfile parse error on line 1: unknown instruction`
  - BuildKit: `stream terminated by RST_STREAM with error code: INTERNAL_ERROR`
- **Current state:** The existing container on VM 187 (built with sandbox URLs) is serving mycosoft.com. For production env vars (NEXT_PUBLIC_BASE_URL=https://mycosoft.com), fix Docker on VM 187 and run `python _rebuild_sandbox.py --production`.
- **Purge:** `purge_everything()` runs automatically on successful deploy.

---

## Verification Checklist

| Check | Command / Action |
|-------|------------------|
| VM 187 reachable | `ping 192.168.0.187` |
| Container running | `ssh mycosoft@192.168.0.187` → `docker ps` |
| mycosoft.com | Browser → https://mycosoft.com → 200 |
| www.mycosoft.com | Browser → https://www.mycosoft.com → 200 |
| mycosoft.org | Browser → https://mycosoft.org → 301 → mycosoft.com/about |
| Auth (Supabase) | Sign in / sign out on mycosoft.com |
| MAS/MINDEX | Open a page that calls MAS or MINDEX |

---

## Files Changed

| File | Change |
|------|--------|
| `WEBSITE/website/_rebuild_sandbox.py` | Added `--production` flag; fixed `_build_supabase_args()` |
| `MAS/scripts/_cloudflare_mycosoft_org_redirect.py` | Zone auto-discovery when `CLOUDFLARE_ZONE_ID_MYCOSOFT_ORG` not set |
| `MAS/scripts/_cloudflare_add_mycosoft_com_dns.py` | **New.** Adds CNAME records for mycosoft.com and www → tunnel |
| `MAS/scripts/_supabase_add_mycosoft_com_redirect_urls.py` | **New.** Updates Supabase auth redirect URLs via Management API (requires SUPABASE_ACCESS_TOKEN) |

---

## Manual Steps Remaining

1. **mycosoft.org redirect:** Add 301 redirect in Cloudflare mycosoft.org zone (Rules → Single Redirects).
2. **Supabase:** Either (a) add `SUPABASE_ACCESS_TOKEN` to `.credentials.local` and run `python scripts/_supabase_add_mycosoft_com_redirect_urls.py`, or (b) add mycosoft.com URLs manually in Supabase Dashboard → Authentication → URL Configuration.
3. **VM build (optional):** For production env vars in the container, resolve Dockerfile/Docker daemon issues on VM 187, then run `python _rebuild_sandbox.py --production`. The site already works with the current container.

---

## Future: Separate Production VM (186)

When Proxmox has space (or R720/NAS is fixed):

1. Complete clone to VM 186 per existing production-clone plan.
2. Create Production tunnel → VM 186.
3. Remove mycosoft.com from Sandbox tunnel.
4. Rebuild and deploy to 186 via a dedicated production deploy script.
