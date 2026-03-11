# MycoBrain Sandbox Always-On — Complete

**Date:** March 7, 2026  
**Status:** Complete  
**Related:** `mycobrain-always-on.mdc`, `docs/MYCOBRAIN_TO_MAS_FLOW_MAR07_2026.md`

---

## Summary

MycoBrain service on Sandbox VM (192.168.0.187:8003) is now resilient and designed to never stay down:

1. **systemd unit** — Infinite restarts (`StartLimitIntervalSec=0`), no restart limit
2. **1-minute watchdog** — Cron runs every minute to restart if unhealthy
3. **Ensure script** — Install/repair on every deploy; auto-runs in `_rebuild_sandbox.py`
4. **Website container** — Uses `host.docker.internal:8003` to reach MycoBrain on host

---

## Files Delivered

| File | Purpose |
|------|---------|
| `WEBSITE/scripts/sandbox/mycobrain-service.service` | systemd unit (infinite restarts, MAS_REGISTRY_URL) |
| `WEBSITE/scripts/sandbox/mycobrain-watchdog.sh` | Cron watchdog (1-min health check + restart) |
| `WEBSITE/_ensure_mycobrain_sandbox.py` | Install/verify MycoBrain on Sandbox; finds MAS repo, installs unit + watchdog |
| `WEBSITE/_rebuild_sandbox.py` | Step 8 calls ensure script; Docker run adds `MYCOBRAIN_SERVICE_URL` |
| `WEBSITE/scripts/_check_mycobrain_sandbox.py` | Quick status check (optional debug helper) |

---

## Verification

```bash
# From dev PC — run ensure (installs + verifies)
cd WEBSITE/website
python _ensure_mycobrain_sandbox.py

# On Sandbox VM
ssh mycosoft@192.168.0.187
sudo systemctl status mycobrain-service
curl -s http://127.0.0.1:8003/health
sudo journalctl -u mycobrain-service -n 50   # if service fails
```

---

## If Service Fails to Start

The service was observed in "activating" state during verification. Possible causes:

1. **Python dependencies** — On the VM: `cd /opt/mycosoft/mas && pip install -r requirements.txt`
2. **Wrong MAS path** — Ensure script auto-discovers; if layout differs, manually fix `WorkingDirectory` in the unit
3. **Serial / port** — MycoBrain may wait for serial; can run without hardware (HTTP health still works once up)

---

## Architecture

| Component | Value |
|-----------|-------|
| Sandbox VM | 192.168.0.187 |
| MycoBrain port | 8003 |
| MAS registry | http://192.168.0.188:8001 |
| Website container | `MYCOBRAIN_SERVICE_URL=http://host.docker.internal:8003` |

---

## Pipeline Integration

Every `_rebuild_sandbox.py` run now:

1. Rebuilds the website Docker image
2. Runs `_ensure_mycobrain_sandbox.py` (Step 8)
3. Restarts the website container with NAS mount and `host.docker.internal` for MycoBrain
