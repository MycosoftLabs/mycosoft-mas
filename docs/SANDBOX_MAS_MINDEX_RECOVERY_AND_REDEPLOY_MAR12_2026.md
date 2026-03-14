# Sandbox MAS MINDEX Recovery and Redeploy (Mar 12, 2026)

**Date:** Mar 12, 2026  
**Status:** Complete  
**Scope:** Recover Sandbox website and Cloudflare tunnel after outage, re-verify MAS/MINDEX runtime health, and complete cache purge + service stabilization.

## What Was Done

1. **Sandbox website recovery**
   - Verified `cloudflared` service on `192.168.0.187` was active.
   - Rebuilt and relaunched `mycosoft-website` container during recovery cycle.
   - Confirmed local service health from Sandbox host: `http://localhost:3000/api/health -> 200`.
   - Resolved unhealthy container state by relaunching with `HOSTNAME=0.0.0.0` to ensure Next.js binds to all interfaces and health checks pass reliably.

2. **Cloudflare restoration and validation**
   - Confirmed public Sandbox route response over HTTPS (`sandbox.mycosoft.com`) with Cloudflare edge headers and `200`.
   - Executed full Cloudflare purge (purge everything) using project credentials from `.env.local`.

3. **MAS verification (`192.168.0.188`)**
   - Confirmed `mas-orchestrator` service active.
   - Confirmed MAS health endpoint returned `200` at `http://localhost:8001/health`.

4. **MINDEX verification (`192.168.0.189`)**
   - Confirmed MINDEX API health endpoint returned `200` at `http://localhost:8000/health`.

5. **Operational cleanup**
   - Removed stale hung deploy terminal process from local operator session.
   - Verified no lingering Sandbox `docker build` processes remained after stabilization.

## Final Runtime State

- **Sandbox VM (187):** online, `cloudflared` active, `mycosoft-website` healthy, local API health `200`.
- **MAS VM (188):** `mas-orchestrator` active, health `200`.
- **MINDEX VM (189):** API health `200`.
- **Cloudflare cache:** purge completed successfully.

## Notes

- A follow-up hardening commit was prepared in website repo:
  - `7e9f58e` – `Dockerfile.production` healthcheck loopback target adjustment.
- During live incident recovery, immediate runtime stability was achieved via container relaunch env binding (`HOSTNAME=0.0.0.0`) so service health and public access were restored without waiting on another long rebuild cycle.

## Verification Commands Used

- Sandbox:
  - `systemctl is-active cloudflared`
  - `docker ps`
  - `curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000/api/health`
- MAS:
  - `systemctl is-active mas-orchestrator`
  - `curl -sS -o /dev/null -w '%{http_code}' http://localhost:8001/health`
- MINDEX:
  - `curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health`
- Cloudflare:
  - `python scripts/_cloudflare_purge.py`
