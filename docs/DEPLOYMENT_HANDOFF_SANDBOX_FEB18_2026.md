# Deployment Handoff – Sandbox (February 18, 2026)

**Purpose:** This document is for the **deploying agent**. All code is prepared and pushed to GitHub. **Deployment will happen in another agent** (not in the development environment). Deployment = Sandbox website container + Cloudflare purge; execute on the VMs only.

---

## Status

- **Website repo:** Committed and pushed to `main` (MycosoftLabs/website). Latest includes CREP, fungi-compute, test-voice (MYCA Brain flow), unified search, responsive UI.
- **MAS repo:** Documentation and bridge/voice changes pushed. No deployment of MAS VM required for Sandbox site to go live; MAS (188) and MINDEX (189) and GPU node (190) are expected to already be running.
- **Sandbox (192.168.0.187):** Website container must be deployed by the deploying agent using the steps below.

---

## Single Reference for Deployment

**Use this document:** `docs/SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md`

It contains:

1. **VM and GPU node layout** – Sandbox 187, MAS 188, MINDEX 189, GPU node 190; roles and ports.
2. **What must be running** – Website container on Sandbox, orchestrator on MAS, MINDEX API, PersonaPlex Bridge on GPU node.
3. **Deployment checklist** – SSH to Sandbox, pull from GitHub, stop/rm container, build image, run container **with NAS mount**, verify, purge Cloudflare.
4. **Paths and image names** – `/opt/mycosoft/website`, `mycosoft-website`, `mycosoft-always-on-mycosoft-website:latest`, NAS mount path.
5. **Test-voice** – Bridge at 190:8999, MAS at 188:8001.
6. **Env vars** – MAS_API_URL, MINDEX_API_URL, NEXT_PUBLIC_PERSONAPLEX_BRIDGE_WS_URL.
7. **Related docs** – VM layout, pipeline, runbook, voice quick start, deploy skill.

---

## Quick Checklist for Deploying Agent

1. Load credentials from `.credentials.local` (VM_SSH_PASSWORD / VM_PASSWORD).
2. SSH to `mycosoft@192.168.0.187`.
3. `cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main`.
4. `docker stop mycosoft-website 2>/dev/null || true` then `docker rm mycosoft-website 2>/dev/null || true`.
5. `docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .`
6. Start container **with NAS mount:**
   ```bash
   docker run -d --name mycosoft-website -p 3000:3000 \
     -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
     -e MAS_API_URL=http://192.168.0.188:8001 \
     --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
   ```
7. Verify: `docker ps | grep mycosoft-website` and `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000` (expect 200).
8. **Purge Cloudflare** (Purge Everything for mycosoft.com).
9. Verify live: https://sandbox.mycosoft.com/ and https://sandbox.mycosoft.com/test-voice.

---

## GitHub Repos (Source of Truth)

- **Website:** https://github.com/MycosoftLabs/website (branch `main`)
- **MAS:** https://github.com/MycosoftLabs/mycosoft-mas (branch `main`)

Deployment must use code from GitHub after pull; do not deploy from local-only changes.
