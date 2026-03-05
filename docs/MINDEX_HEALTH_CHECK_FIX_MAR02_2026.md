# MINDEX Health Check Fix — Complete

**Date:** March 2, 2026  
**Status:** Complete  
**Related:** Signal spam fix (Mar 4), MYCA OS heartbeat

---

## Problem

MYCA was repeatedly reporting **"CRITICAL: MINDEX databases unreachable"** every 30 seconds. The health check required **all four** services to be reachable:

1. MINDEX API (http://192.168.0.189:8000)
2. Redis (192.168.0.189:6379)
3. PostgreSQL (192.168.0.189:5432)
4. Qdrant (192.168.0.189:6333)

Redis, PostgreSQL, and Qdrant live inside VM 189's Docker network. They are **not exposed** to other VMs (e.g. MYCA on 191). Only the MINDEX API (port 8000) is intended to be reachable cross-VM. So the health check was always failing.

---

## Root Cause

- **MINDEXBridge** in `mycosoft_mas/myca/os/mindex_bridge.py` used `checks["healthy"] = all(checks.values())`.
- Redis, Postgres, and Qdrant are backend services for MINDEX; MYCA accesses MINDEX only via the **MINDEX API**.
- Cross-VM, MYCA cannot reach Redis/Postgres/Qdrant (and should not need to).

---

## Fix

**File:** `mycosoft_mas/myca/os/mindex_bridge.py`

- **Before:** `checks["healthy"] = all(checks.values())` — required all four.
- **After:** `checks["healthy"] = checks.get("api", False)` — healthy if MINDEX API is reachable.

The API is the primary interface. If it responds, MINDEX is usable by MYCA.

---

## Verification

1. MINDEX API at `http://192.168.0.189:8000/health` returns 200.
2. MYCA health check no longer reports "MINDEX databases unreachable" when the API is up.
3. Redis/Postgres/Qdrant checks remain in the response for diagnostics but no longer gate `healthy`.

---

## Deployment

1. Commit and push MAS changes.
2. Restart MAS orchestrator on VM 188: `sudo systemctl restart mas-orchestrator`.
3. If MYCA runs on VM 191, restart MYCA OS there.
4. Verify health endpoint no longer shows MINDEX critical.
