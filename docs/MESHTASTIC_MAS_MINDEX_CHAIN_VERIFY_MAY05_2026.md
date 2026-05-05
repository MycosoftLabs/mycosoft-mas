# Meshtastic MAS ↔ MINDEX chain verify — May 05, 2026

**Status:** Verified on LAN  
**Related:** `docs/MESHTASTIC_TENNMESH_INTEGRATION_COMPLETE_MAY03_2026.md`, migration `migrations/0037_meshtastic_mesh.sql` (MINDEX repo)

## What was wrong

1. **MAS** built MINDEX URLs as `{MINDEX_API_URL}/api/mindex/internal/meshtastic/...` while production `.env` sets `MINDEX_API_URL=http://192.168.0.189:8000/api/mindex`, producing a **double `/api/mindex`** segment and **404** from MINDEX.
2. After URL fix, MINDEX returned **500** on `/stats` because the **`meshtastic` schema was not applied** on VM 189 Postgres (migration 0037 not run for that cluster; DB user was **mycosoft**, not `mindex`).

## Fixes shipped

- **MAS:** `mycosoft_mas/core/routers/meshtastic_api.py` — `_mindex_meshtastic_base()` normalizes origin-only vs `/api/mindex` suffix. Commit on `main`; VM **188** `git pull` + `systemctl restart mas-orchestrator`.
- **MINDEX VM 189:** Run `0037_meshtastic_mesh.sql` against the live DB (script: `scripts/_apply_meshtastic_migration_189.py` — sources `.env` for `MINDEX_DB_USER` / `MINDEX_DB_NAME`, falls back to `postgres` superuser if needed).

## Verification commands

```text
curl -s http://192.168.0.188:8001/api/meshtastic/stats
# Expect 200 JSON: node_count, packets_last_1m, packets_last_60m, observers_online

curl -s http://192.168.0.188:8001/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print([k for k in d.get('paths',{}) if 'meshtastic' in k])"
# Expect paths under /api/meshtastic/*
```

## Redis (optional)

Stream key `mesh:packets` on MINDEX Redis: use `scripts/_probe_redis_mesh_189.py`. Empty stream (`XLEN 0`) is normal until MQTT bridge ingests packets.

## Follow-ups

- Ensure **VM 189** `.env`-doc’d standard DB role (`mindex` vs `mycosoft`) to avoid ops confusion.
- **MAS** `REDIS_URL` on **188** should point at **189** Redis if `/api/meshtastic/stream` is used from MAS.
