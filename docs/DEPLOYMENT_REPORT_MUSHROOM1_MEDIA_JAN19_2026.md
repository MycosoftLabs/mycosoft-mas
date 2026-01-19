# Deployment Report — Mushroom 1 Videos + Instant Media Pipeline

**Date**: 2026-01-19  
**Target**: `sandbox.mycosoft.com` (VM: `192.168.0.187`)  

## What was deployed

- Mushroom 1 page updated UI (expected visible signals):
	- Price badge: **Pre-Order Now - $2,000**
	- Background/section videos loading from `/assets/mushroom1/*.mp4`

## Media pipeline change (prevents hour-long deploys)

- Media is synced to VM directory:
	- `/opt/mycosoft/media/website/assets`
- Website container serves media via a volume mount:
	- `/opt/mycosoft/media/website/assets` → `/app/public/assets` (read-only)
- Result:
	- Updating MP4/JPG = **sync files only**, no docker rebuild needed.

## Verification (localhost vs sandbox)

### Localhost

- URL: `http://localhost:3010/devices/mushroom-1`
- Observed: **Pre-Order Now - $2,000** present
- Observed: MP4 requests to `/assets/mushroom1/...` occur

### Sandbox (public)

- URL: `https://sandbox.mycosoft.com/devices/mushroom-1`
- Observed: **Pre-Order Now - $2,000** present
- Observed: MP4 requests to:
	- `/assets/mushroom1/PXL_20250404_210633484.VB-02.MAIN.mp4`
	- `/assets/mushroom1/waterfall 1.mp4`
	- `/assets/mushroom1/mushroom 1 walking.mp4`

### Public media endpoint check (Cloudflare)

- `HEAD https://sandbox.mycosoft.com/assets/mushroom1/waterfall%201.mp4` → **200 OK**

## Notes

- Cloudflare cache was purged (Purge Everything) on the date above.
- Docker compose may show website “unhealthy” if healthcheck tools are missing; HTTP 200 on `/` and MP4 endpoints is the practical validation.

## MycoBrain (live board telemetry on sandbox)

- **Windows MycoBrain service** (LAN): `192.168.0.172:8003` (FastAPI + serial)
- **Cloudflare tunnel route** on VM updated to forward:
	- `https://sandbox.mycosoft.com/api/mycobrain*` → `http://192.168.0.172:8003`
- **Verified (public)**:
	- `GET https://sandbox.mycosoft.com/api/mycobrain` → **200** with live device payload
	- `GET https://sandbox.mycosoft.com/api/mycobrain/devices` → **200**, count=2 (COM7 + COM10)
	- `GET https://sandbox.mycosoft.com/api/mycobrain/ports` → **200**, includes COM7/COM10 marked `is_mycobrain=true`


