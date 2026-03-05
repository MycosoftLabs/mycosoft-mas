# Sandbox Deployment Diagnosis — Mar 4, 2026

**Date:** Mar 4, 2026  
**Status:** Site restored; fresh rebuild failed  
**VMs:** 187 (Sandbox), 188 (MAS)

---

## What Happened

1. **Deploy script ran** (`deploy_sandbox_rebuild_FEB09_2026.py`) — git pull succeeded, code updated.
2. **Container removed** — Old website container was stopped and removed.
3. **Docker build failed** during `npm run build` (Step 35/49):
   - Font fetch to `fonts.gstatic.com` failed (Geist fonts).
   - Process exited with **143** (SIGTERM — likely timeout or OOM).
4. **No new image** — Because the build failed, the `mycosoft-always-on-mycosoft-website:latest` image was not updated.
5. **Site down** — No container was running, so sandbox.mycosoft.com returned 502.

---

## Fix Applied

- **Container restarted** from existing image via `scripts/_diagnose_and_fix_sandbox.py`.
- **Cloudflare purged** — Cache cleared.
- **HTTP 200** — Site is responding.

---

## Root Cause (Build Failure)

```
request to https://fonts.gstatic.com/s/geist/v4/... failed
The command '/bin/sh -c npm run build' returned a non-zero code: 143
```

- **143** = 128 + 15 = SIGTERM (process killed).
- Likely causes: SSH/paramiko timeout (30 min), or OOM during Next.js build.
- Font fetches may fail if Docker has restricted network access during build.

---

## Recommendations for Next Deploy

1. **Build with host network** (if fonts/network are the issue):
   ```bash
   docker build --network=host -t mycosoft-always-on-mycosoft-website:latest --no-cache .
   ```

2. **Increase build timeout** — Deploy script uses 1800s; Next.js builds can exceed that on slower VMs.

3. **Pre-bundle fonts** — Use `next/font` or local font files to avoid fetching from Google during build.

4. **Build in background with log** — Run build in `nohup` with output to a file so it survives SSH disconnects:
   ```bash
   nohup docker build -t ... . > /tmp/build.log 2>&1 &
   ```

---

## Verification Commands

```bash
# Check container
docker ps --filter name=mycosoft-website

# Check image age
docker images mycosoft-always-on-mycosoft-website

# Health
curl -s -o /dev/null -w '%{http_code}' http://localhost:3000
```

---

## Files

- Diagnostic script: `scripts/_diagnose_and_fix_sandbox.py`
- Deploy script: `WEBSITE/website/deploy_sandbox_rebuild_FEB09_2026.py`
