# Site Outage — Jun 26, 2026

**Date:** Jun 26, 2026  
**Status:** Resolved (sites verified HTTP 200)  
**Affected:** sandbox.mycosoft.com, mycosoft.com (VM 192.168.0.187)

## Summary

A hotfix deploy bypassed the blue/green nginx proxy and started a standalone `mycosoft-website` container directly on host port `:3000`. That left Cloudflare/tunnel traffic hitting an app on the wrong Docker network without `mycosoft-website-proxy`, causing public 502/1033-style outages until manual recovery.

## Root cause

1. **Skipped nginx proxy** — `_rebuild_sandbox.py` used `docker run -p 3000:3000 mycosoft-website`, binding the app directly on `:3000` instead of routing through `mycosoft-website-proxy`.
2. **Wrong Docker network** — The standalone container was not on the compose `mycosoft-network` that nginx expects for upstream `mycosoft-website-blue` / `mycosoft-website-green`.
3. **No public URL gate** — Deploy declared success after origin `:3000` responded, without verifying `https://sandbox.mycosoft.com/` (or prod URL) returned HTTP 200.

## Fix applied (Jun 26, 2026)

| Area | Change |
|------|--------|
| `_rebuild_sandbox.py` | Requires `blue-green-bootstrap.sh` + `blue-green-deploy.sh`; refuses direct `docker run` on `:3000`; fails if public HTTPS ≠ 200 |
| `site-health-monitor.yml` | Sandbox down = CRITICAL; `notify-on-down` job emails Morgan + GitHub issue |
| `production-watchdog.yml` | Probe exits non-zero on failure; `notify-on-down` emails Morgan |
| `.cursor/rules/site-never-down.mdc` | Agent policy: fix first, email Morgan, no proxy bypass |

## Recovery steps (if it happens again)

On VM 187:

```bash
cd /opt/mycosoft/website
bash scripts/blue-green-bootstrap.sh
IMAGE=mycosoft-always-on-mycosoft-website:latest PUBLIC_HOST=sandbox.mycosoft.com bash scripts/blue-green-deploy.sh
curl -fsS -o /dev/null -w '%{http_code}\n' https://sandbox.mycosoft.com/
```

## Verification

```powershell
curl.exe -sS -o NUL -w "sandbox=%{http_code}`n" https://sandbox.mycosoft.com/
curl.exe -sS -o NUL -w "mycosoft=%{http_code}`n" https://mycosoft.com/
```

Expected: both `200`.

## Related

- `scripts/blue-green-bootstrap.sh`
- `scripts/blue-green-deploy.sh`
- `docker-compose.production.blue-green.yml`
- `.github/workflows/site-health-monitor.yml`
- `.github/workflows/production-watchdog.yml`
