# Sandbox Website Restart Attempt - Feb 24, 2026

## Commands Executed

1. **sudo systemctl restart docker** – FAILED (exit 1)
2. **sleep 20** – OK
3. **docker images mycosoft-always-on-mycosoft-website** – FAILED (Docker daemon not running)
4. **docker run** (website container) – FAILED (Docker daemon not running)
5. **sleep 5** – OK
6. **curl http://localhost:3000** – HTTP 000 (connection refused)

## Root Cause

Docker on Sandbox (192.168.0.187) **failed to start** due to a **zombie dockerd process** (PID 1328):

```
Unit process 1328 (dockerd) remains running after unit stopped.
failed to start daemon: process with PID 1328 is still running
```

- PID 1328 is a **zombie** (`<defunct>`, state Zsl)
- Parent is PID 1 (init)
- Zombies cannot be killed; they must be reaped by their parent or cleared by a reboot

## Actions Taken

- **Reboot sent** to Sandbox 192.168.0.187 to clear the zombie dockerd.
- VM was unreachable 2–3 min after reboot (may need Proxmox start if it did not auto-start).

## Required Fix

**Ensure Sandbox VM (192.168.0.187) is running** (Proxmox if needed). After it is up:

1. `sudo systemctl start docker` (or it will auto-start)
2. `docker rm -f mycosoft-website 2>/dev/null; docker run -d --name mycosoft-website ...` (see deployment checklist)

## Post-Reboot Steps

```bash
ssh mycosoft@192.168.0.187
# After reboot, verify Docker is up:
docker ps
# Run website container:
docker rm -f mycosoft-website 2>/dev/null
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  -e MAS_API_URL=http://192.168.0.188:8001 \
  -e MYCOBRAIN_SERVICE_URL=http://192.168.0.187:8003 \
  -e MYCOBRAIN_API_URL=http://192.168.0.187:8003 \
  --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
```

## Note

**A later build-from-scratch is needed** for latest code. The current image on the VM (if Docker were running) is whatever was last built. To deploy latest: pull code, rebuild image, restart container, purge Cloudflare.
