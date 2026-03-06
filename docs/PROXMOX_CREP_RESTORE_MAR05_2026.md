# Proxmox API Fix and CREP Collectors Restore

**Date**: March 5, 2026  
**Author**: MYCA Loop Closure Plan  
**Status**: Complete

## Overview

Proxmox API (192.168.0.105:8006) was unreachable from the dev LAN. CREP collectors were degraded/not running on MAS VM. This document records the scripts and changes to fix Proxmox connectivity and restore CREP on MAS VM 188.

---

## Proxmox API Fix

### Problem

Proxmox API at `192.168.0.105:8006` was unreachable from 192.168.0.0/24. Firewall or network rules were blocking TCP 8006.

### Solution

**Script**: `scripts/fix_proxmox_firewall.sh`

Run on the Proxmox host (or gateway) as root:

```bash
sudo ./scripts/fix_proxmox_firewall.sh
```

The script adds an iptables rule to allow TCP 8006 from 192.168.0.0/24.

### Persistence

To make rules persistent on Proxmox/Debian:

```bash
apt install iptables-persistent
iptables-save > /etc/iptables/rules.v4
```

### Verification

- **Autostart healthcheck**: `.\scripts\autostart-healthcheck.ps1` now includes a "Proxmox API" section that tests 192.168.0.105:8006 and reports reachable or unreachable.
- Manual: `Test-NetConnection -ComputerName 192.168.0.105 -Port 8006`

---

## CREP Collectors Restore

### Components

- **CREP Gateway**: FastAPI at port 3020, in `WEBSITE/website/services/crep-gateway/`
- **Endpoints**: `/health`, `/api/intel/air`, `/api/intel/maritime`, `/api/intel/fishing`
- **Data sources**: OpenSky, AISStream, Global Fishing Watch (via env vars)

### Start Script

**Script**: `scripts/start_crep_collectors.sh`

Run on MAS VM 188. Requires the website repo at `/opt/mycosoft/website` (or set `CREP_GATEWAY_DIR`).

```bash
./scripts/start_crep_collectors.sh
```

Environment variables:

- `CREP_GATEWAY_DIR` — path to crep-gateway (default: `/opt/mycosoft/website/services/crep-gateway`)
- `CREP_PORT` — port for gateway (default: 3020)

### MAS Health Integration

CREP status is now included in the MAS `/health` endpoint. The `HealthChecker` in `mycosoft_mas/monitoring/health_check.py` includes `check_crep()`:

- Probes `CREP_GATEWAY_URL` (default: `http://localhost:3020`) `/health`
- Returns `healthy` if reachable and HTTP 200, `degraded` otherwise
- CREP appears in the `components` array of the health response

### Deployment on MAS VM 188

1. Ensure website repo is deployed: `/opt/mycosoft/website`
2. Run `start_crep_collectors.sh`
3. Set `CREP_GATEWAY_URL=http://localhost:3020` in MAS `.env` if MAS runs on the same host
4. Verify: `curl http://localhost:3020/health`

---

## Related Documents

- [Close Loops Improvement Plan](.cursor/plans/close_loops_improvement_plan_af14311e.plan.md) — TIER 1 tasks
- [VM Layout and Dev Remote Services](./VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md) — VM IPs and ports
