# Sandbox Deployment Runbook (Website + Services + Media)

**Last updated**: 2026-01-19  
**Sandbox**: `sandbox.mycosoft.com`  
**VM**: `mycosoft@192.168.0.187`  

## What this runbook covers

- Website deploy (code) to sandbox
- Media deploy (videos + images) to sandbox **without** rebuilding
- Cloudflare tunnel routing for APIs (MycoBrain, MINDEX)
- Verification checklist (endpoints + UI)
- Known failure modes we hit and how to fix them

## Required: local pre-flight

- **Local build sanity**:
	- Ensure `pnpm build` succeeds in the website repo.
- **Local UI check**:
	- Compare local vs sandbox where relevant (example):
		- `http://localhost:3010/devices/mushroom-1`
		- `https://sandbox.mycosoft.com/devices/mushroom-1`

## Website code deployment (sandbox)

This is the “code changed” path.

- **Commit + push**
	- Commit your changes and push to GitHub `main`.
- **VM update**
	- SSH to VM:
		- `ssh mycosoft@192.168.0.187`
	- Pull latest:
		- `git reset --hard origin/main`
- **Rebuild container (website)**
	- Build fresh image:
		- `docker build -t website-website:latest --no-cache .`
	- Restart website container:
		- `docker compose -p mycosoft-production up -d mycosoft-website`
- **Cloudflare cache**
	- Purge Everything (if static assets/UI appear stale).

## Media deployment (fast path — no rebuild)

This is the “videos/images changed” path.

### Architecture (as deployed on sandbox)

- **Host**: `/opt/mycosoft/media/website/assets`
- **Container**: mounted read-only at `/app/public/assets`
- **Public URLs**:
	- `/assets/...`

### Sync from Windows → VM

Use the Paramiko sync script:

- `scripts/media/sync_website_media_paramiko.py`
	- Syncs: `WEBSITE/public/assets/**`
	- To VM: `/opt/mycosoft/media/website/assets`
	- Includes: **mp4/webm/mov + jpg/jpeg/png/webp/gif/svg**

### Critical nuance: restart required for newly-synced `/assets/*`

We observed:

- Files can exist on the VM and inside the container at `/app/public/assets/...`
- But Next.js (standalone) can still return **404** for `/assets/*` until restart

Fix:

- `docker restart mycosoft-website`

Verification:

- `HEAD https://sandbox.mycosoft.com/assets/mushroom1/Main%20A.jpg` → **200**

## Cloudflare tunnel routing (APIs)

Current tunnel config on the VM (`/home/mycosoft/.cloudflared/config.yml`) includes:

- **MycoBrain**:
	- `/api/mycobrain*` → `http://192.168.0.172:8003` (Windows LAN service)
- **MINDEX**:
	- `/api/mindex*` → `http://localhost:8000` (VM container/service)
- Catch-all:
	- `http_status:404`

## Verification checklist

### Website UI

- `https://sandbox.mycosoft.com/devices`
	- Mushroom 1 card image loads (no broken image)
- `https://sandbox.mycosoft.com/devices/mushroom-1`
	- Price: **$2,000**
	- Videos load from `/assets/mushroom1/*.mp4`

### Static assets

- `https://sandbox.mycosoft.com/placeholder.svg` → **200**
- `https://sandbox.mycosoft.com/assets/mushroom1/Main%20A.jpg` → **200**
- `https://sandbox.mycosoft.com/assets/mushroom1/waterfall%201.mp4` → **200**

### MycoBrain

- `GET https://sandbox.mycosoft.com/api/mycobrain/ports` → **200**
- `GET https://sandbox.mycosoft.com/api/mycobrain/devices` → **200**

### MINDEX

- `GET https://sandbox.mycosoft.com/api/mindex/health` (or equivalent health route) → **200**

## Hardware: COM ports (what “COM10” means)

- A COM port number (example: COM10) is **just a Windows assignment**, not device identity.
- VID/PID `0x303A/0x1001` means “ESP32-S3 USB serial device” (Espressif) — **not uniquely MycoBrain**.
- To confirm which physical device is which:
	- Unplug/replug and see which COM entry disappears/returns
	- Use Device Manager → Port → Details → Hardware Ids
	- Prefer “verified MycoBrain” by serial handshake/firmware response, not by VID/PID alone

## Known issues & fixes (from this session)

### `/assets/*` returns 404 even though files are present

- Cause: Next.js standalone didn’t pick up newly-synced `public/assets` yet.
- Fix: `docker restart mycosoft-website`, then re-check a known asset.

### MAS orchestrator didn’t start

- Observed failure: build referenced `docker/wait-for-it.sh` but it didn’t exist on the VM under `/home/mycosoft/mycosoft/mas`.
- Workaround: start `n8n` independently (no orchestrator build).
- Fix path: ensure the MAS repo on VM contains the required `docker/` folder + rebuild.

