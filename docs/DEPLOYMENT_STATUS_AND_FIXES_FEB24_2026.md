# Deployment Status and Fixes – February 24, 2026

**Purpose:** Summary of deployment checks, fixes, and current VM status after Cursor crashes and build failures.

---

## Current Status (as of last check)

| VM | Service | Status | Notes |
|----|---------|--------|-------|
| **Sandbox (187)** | Website | **UP** (HTTP 200) | Serving from existing image; full rebuild for latest code still needed |
| **MAS (188)** | Orchestrator | **UP** | Latest code deployed |
| **MINDEX (189)** | API | **UP** | Latest code deployed |

---

## What Happened

### Build failures
- Docker build for the website failed repeatedly at `pnpm install` (~499 packages) with:
  - `ERROR: failed to build: failed to solve: Canceled: context canceled`
  - Exit code -1 (legacy and BuildKit attempts)
- Possible causes: OOM, SSH timeout, npm registry slowness, Cursor crash killing the process

### Docker zombie
- Docker on Sandbox had a zombie `dockerd` process (PID 1328) that blocked restart
- VM was rebooted to clear the zombie

### Duplicate builds
- At one point, two concurrent `docker build` processes were running (PIDs 974402/974406 and 980783/980787)
- One was killed to avoid conflicts

---

## Fixes Applied

1. **Killed orphan build processes** – Stopped stuck `docker build` after Cursor crash
2. **Rebooted Sandbox VM** – Cleared zombie dockerd so Docker could start
3. **Restarted Docker** – `sudo systemctl restart docker` after reboot
4. **Started website container** – Using existing image with NAS mount and env vars

---

## Website Container Command (for reference)

```bash
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  -e MAS_API_URL=http://192.168.0.188:8001 \
  -e MYCOBRAIN_SERVICE_URL=http://192.168.0.187:8003 \
  -e MYCOBRAIN_API_URL=http://192.168.0.187:8003 \
  --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
```

---

## Still Needed: Full Website Rebuild for Latest Code

The website is serving from the **last successfully built image** (before the failures). To deploy the latest code (creator memory, floating button, flow edge fix):

1. **Option A – Build on Sandbox with nohup**
   ```bash
   ssh mycosoft@192.168.0.187
   cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main
   nohup docker build --network host --no-cache -t mycosoft-always-on-mycosoft-website:latest . > /tmp/build.log 2>&1 &
   # Monitor: tail -f /tmp/build.log
   ```

2. **Option B – Build locally, push to registry, pull on VM**
   - Build the image on a machine with more RAM
   - Push to Docker Hub or private registry
   - Pull and run on Sandbox

3. **Option C – Increase VM RAM** (if OOM)
   - Check `free -m` during build
   - Increase Proxmox VM RAM if needed

4. **Post-build steps** (after successful build)
   ```bash
   docker stop mycosoft-website; docker rm mycosoft-website
   docker run -d --name mycosoft-website ... # (same command as above)
   # Purge Cloudflare cache
   ```

---

## Related Docs

- `docs/DEPLOY_ALL_THREE_VMS_FEB19_2026.md` – Full deploy checklist
- `docs/SANDBOX_WEBSITE_RESTART_RESULT_FEB24_2026.md` – Zombie Docker fix details
