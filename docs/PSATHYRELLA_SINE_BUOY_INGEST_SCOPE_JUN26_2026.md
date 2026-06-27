# Psathyrella SINE Buoy Acoustic Ingest — Scope (Jun 26, 2026)

**Status:** Scoped / stub only  
**Related:** P0-#4 in `docs/PSATHYRELLA_CURSOR_HANDOFF_JUN26_2026.md`

## Widget chain (already live)

1. `GET /api/mindex/sine/status` → website BFF → MINDEX `189:8000/api/mindex/sine/status`
2. `GET /api/natureos/mindex/library?category=acoustic&q=psathyrella`
3. `GET /api/mindex/sine/blobs/{analysis_id}/analysis`

SINE has ~2,180 blobs globally but **none** are buoy-scoped today → GCS shows honest STANDBY.

## Required ingest tokens

| Field | Example | Purpose |
|-------|---------|---------|
| `source_id` | `psathyrella-psathyrella-buoy-com4-hydrophone` | Library filter `q=psathyrella` |
| `recording_group` | `psathyrella-buoy-com4:hydrophone-lf` | Group sessions per sensor |
| `sensor_type` | `hydrophone` or `mems` | `inferEnvironment` → `acoustic_domain` |
| `acoustic_domain` | `water` / `air` | GCS hydrophone(below) vs MEMS(above) panels |

## Sensor mapping

| Hardware | sensor_type token | acoustic_domain |
|----------|-------------------|-----------------|
| Underwater hydrophone (Side A) | `hydrophone` | `water` |
| Tower MEMS mic (above water) | `mems` | `air` |

## MAS stub

`mycosoft_mas/devices/psathyrella/sine_ingest.py`:

- `build_sine_ingest_metadata()` — canonical metadata envelope
- `ingest_acoustic_blob_stub()` — returns `pending` until MINDEX ingest wired

## Integration points to wire (Cursor follow-up)

1. **Capture:** MycoBrain `hydrophone record` / MEMS record commands → blob file on NAS or MINDEX blob store
2. **Ingest:** POST to MINDEX SINE library with metadata above
3. **Analysis:** Trigger SINE detector pipeline; ensure `detector_events[]` carry `event_type`, `acoustic_domain`, `confidence`
4. **Verify:** `curl http://localhost:3010/api/mindex/sine/status` and library query returns psathyrella-scoped blobs

## Website contract refs

- `WEBSITE/website/lib/mindex/sine-contract.ts`
- `WEBSITE/website/lib/psathyrella/sineClasses.ts`
