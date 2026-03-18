# MYCA2: Plasticity router mounted on MAS — Mar 18, 2026

**Status:** Fix applied (local)  
**Related:** `scripts/myca2_vm_rollout.py`, `mycosoft_mas/core/routers/plasticity_api.py`

## Problem

Smoke test `POST http://192.168.0.188:8001/api/plasticity/psilo/session/start` returned **404** while the route existed in code. Root cause: **`plasticity_router` was never `include_router`’d** in `mycosoft_mas/core/myca_main.py`.

## Fix

- Import `plasticity_router` from `plasticity_api`.
- `app.include_router(plasticity_router, tags=["plasticity", "myca2"])` (router already uses prefix `/api/plasticity`).

## Deploy

After push to `main`, redeploy MAS on 188 (`python scripts/myca2_vm_rollout.py --mas` or your usual Docker/systemd flow). Then re-run:

```powershell
python scripts/myca2_vm_rollout.py --test
```

## Other smoke notes (Mar 18 run)

- **MAS `/health`**: may show `postgresql` unhealthy if MAS expects a local Postgres on 188; memory/session layers use MINDEX on 189 — align env or health checks separately.
- **MINDEX `/health`**: `db: error` until migration 0023 + API env point at healthy Postgres.
- **PSILO start**: expects JSON `{"dose_profile":{},"phase_profile":{}}` (see `PsiloSessionStartBody`).
