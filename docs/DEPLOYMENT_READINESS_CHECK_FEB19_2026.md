# Deployment Readiness Check

**Date**: February 19, 2026  
**Status**: Pre-deploy verification for handoff to deploy agent  
**Scope**: Website, MAS, MINDEX — multi-agent work readiness

## Overview

Verification performed to ensure all repos are ready for deployment by another agent. **Do not deploy from this agent** — this doc is a handoff checklist.

---

## 1. Git Status

### Website (WEBSITE/website)

| Check | Status |
|-------|--------|
| Branch | `main` |
| Working tree | Clean |
| Latest commit | `d16dbb0` — security: purge hardcoded secrets from working tree and history |
| Previous | `ce84cec` — chore: stage remaining mobile + team changes for sandbox deploy (FEB18_2026) |

### MAS (mycosoft-mas)

| Check | Status |
|-------|--------|
| Branch | `main` |
| Working tree | Clean (untracked: `_fix_working_secrets.py`, `_secret_replacements.txt`, data logs — safe to ignore) |
| Latest commit | `3c34f4f5e` — security: harden SSH/sudo password rule |
| Previous | `ae67cdc39` — security: replace 298 hardcoded secrets with env vars |

### GitHub Sync

| Repo | Fetch | Notes |
|------|-------|-------|
| Website | Connection reset | Retry fetch/push before deploy if needed |
| MAS | OK | Fetched from origin |

**Action for deploy agent:** Verify `git fetch origin` and `git status` show local main == origin/main before deploying.

---

## 2. Website Build

| Check | Result |
|-------|--------|
| Config | `output: 'standalone'` (Docker-ready) |
| Clean build | After `rm -rf .next`, build compiled successfully |
| Static pages | 307 pages generated |
| Known warnings | STRIPE_SECRET_KEY not set (Stripe disabled — expected in dev) |

**Note:** An earlier build (with stale `.next` cache) failed with "Cannot find module" on some routes. A clean build succeeded. **Deploy agent should use `--no-cache` when running `docker build`** to avoid cache-related failures.

---

## 3. Deployment Checklist (for Deploy Agent)

### Website → Sandbox VM (192.168.0.187)

1. SSH: `ssh mycosoft@192.168.0.187`
2. Pull: `cd /opt/mycosoft/website && git reset --hard origin/main`
3. Build: `docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .`
4. Run container (MUST include NAS mount):
   ```bash
   docker run -d --name mycosoft-website -p 3000:3000 \
     -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
     --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
   ```
5. Purge Cloudflare cache (Purge Everything)
6. Verify: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000` → 200

### MAS (if deploying)

- VM: 192.168.0.188
- Restart: `sudo systemctl restart mas-orchestrator`

### MINDEX (if deploying)

- VM: 192.168.0.189
- Restart API container as per `deploy-mindex` skill

---

## 4. Credentials

Load from `.credentials.local` (MAS or Website repo root):
- `VM_SSH_PASSWORD` / `VM_PASSWORD`
- `VM_SSH_USER=mycosoft`

Never commit credentials. Deploy scripts should load them automatically.

---

## 5. Included Work (Mobile + Multi-Agent)

- Mobile overhaul (viewport, touch targets, responsive layouts, devices portal UX)
- Security: hardcoded secrets purged, env vars
- CREP dashboard: WebGL/SSR fix (dynamic import with `ssr: false`)
- About, pricing, auth, NatureOS, defense, fungi-compute, search pages — mobile-first updates
- Device selection: sticky tab strip on mobile (no scroll-up/down to switch)

---

## 6. Related Docs

- [DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md](./DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md)
- [SANDBOX_PREP_AND_HANDOFF_FEB18_2026.md](./SANDBOX_PREP_AND_HANDOFF_FEB18_2026.md)
- [SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md](./SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md)
