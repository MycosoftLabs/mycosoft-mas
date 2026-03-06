# Grounding Production Enable — Mar 5, 2026

**Status:** Complete — deployment notes for enabling Grounded Cognition in production

---

## Overview

Grounded Cognition (Phase 1) is code-complete but behind a feature flag. To enable it in production:

1. Set `MYCA_GROUNDED_COGNITION=1` in MAS and MYCA OS `.env`
2. Set `STATE_SERVICE_URL` when StateService is deployed
3. Ensure MINDEX grounding endpoints are reachable

---

## Environment Variables

### MAS VM (192.168.0.188)

Add or set in `/opt/mycosoft/mas/.env` (or equivalent):

```bash
# Grounded Cognition
MYCA_GROUNDED_COGNITION=1

# StateService (optional; enables richer self/world state)
# STATE_SERVICE_URL=http://192.168.0.188:8010
```

### MYCA OS VM (192.168.0.191)

Add or set in MYCA workspace `.env`:

```bash
MYCA_GROUNDED_COGNITION=1
# STATE_SERVICE_URL=http://192.168.0.188:8010
```

### Website (Sandbox / local dev)

For the Grounding Dashboard at `/dashboard/grounding`, ensure:

- `MAS_API_URL` — MAS API base (e.g. `http://192.168.0.188:8001`)
- `MINDEX_API_URL` — MINDEX API base (e.g. `http://192.168.0.189:8000`)
- `MINDEX_API_KEY` (optional) — if MINDEX grounding endpoints require API key

---

## StateService (Optional)

StateService runs on port 8010 and exposes:

- `GET /health` — health check
- `GET /state` — current MYCA self-state (active goals, resource usage, emotional valence)
- `GET /world` — cached world state from MINDEX, CREP, device telemetry

**Deploy StateService** (when ready):

```bash
# On MAS VM or a dedicated host
python -m mycosoft_mas.engines.state_service
# Listens on 0.0.0.0:8010
```

Then set `STATE_SERVICE_URL` in MAS/MYCA `.env`.

---

## MINDEX Grounding Endpoints

MINDEX must expose:

- `GET /api/mindex/grounding/experience-packets?limit=50`
- `GET /api/mindex/grounding/thought-objects?limit=50`

Ensure `mindex_api/routers/grounding.py` is included in the MINDEX app and migrations for `experience_packets` and `thought_objects` tables are applied.

---

## Grounding Dashboard

- **URL:** `/dashboard/grounding` on the website
- **API:** `/api/grounding` — proxies to MAS and MINDEX
- **Features:** EP stream, ThoughtObject evidence chains, grounding status

---

## Verification

1. MAS health: `curl http://192.168.0.188:8001/health`
2. Grounding status: `curl http://192.168.0.188:8001/api/myca/grounding/status`
3. MINDEX EPs: `curl "http://192.168.0.189:8000/api/mindex/grounding/experience-packets?limit=5"`
4. Dashboard: Open `https://sandbox.mycosoft.com/dashboard/grounding` (or localhost:3010)

---

## Related Docs

- `docs/GROUNDED_COGNITION_FULL_SPRINT_COMPLETE_FEB17_2026.md` — Phase 1 implementation
- `docs/PROXMOX_CREP_RESTORE_MAR05_2026.md` — CREP collectors (world state source)
