# Mycosoft Devices Registry — May 03, 2026

**Status:** Living document  
**Owner:** `@device-tracker` (see `.cursor/agents/device-tracker.md`)  
**Machine catalog:** `WEBSITE/website/lib/devices/catalog.ts` (must stay aligned with this table)

## Purpose

Single human-readable roster of **device types** and **variants**: marketing name, stable `id` for APIs, MAS `device_role` for heartbeats, public page, firmware location, program status. **No fabricated GPS** — Earth Simulator markers only appear when live telemetry includes coordinates.

## Master table

| Marketing name | Catalog `id` | `device_role` (heartbeat) | Public page | Firmware / hardware notes | Status |
|----------------|---------------|---------------------------|-------------|-----------------------------|--------|
| Mushroom 1 | `mushroom-1` | `mushroom1` | `/devices/mushroom-1` | `mycobrain/firmware` (walking ground droid) | Development |
| SporeBase | `sporebase` | `sporebase` | `/devices/sporebase` | `mycobrain/firmware` | In production |
| Hyphae 1 | `hyphae-1` | `hyphae1` | `/devices/hyphae-1` | `mycobrain/firmware` | In production |
| MycoNode | `myconode` | `myconode` | `/devices/myconode` | `mycobrain/firmware` | Enterprise |
| Psathyrella | `psathyrella` | `psathyrella` | `/devices/psathyrella` | `mycobrain/firmware` (marine buoy) | Program |
| ALARM | `alarm` | `alarm` | `/devices/alarm` | `mycobrain/firmware` | Coming soon |
| MycoBrain gateway (host) | `mycobrain-gateway` | `gateway` | `/natureos/devices/network` | Service + gateway firmware family | Always-on (host) |
| Agaric Mini | `agaric-mini` | `agaric_mini` | `/devices/agaric` | `mycobrain/firmware/features/mycodrone` (MAVLink bridge, etc.) | Development |
| Agaric Standard | `agaric-standard` | `agaric_standard` | `/devices/agaric` | Same | Development |
| Agaric Heavy-Lift | `agaric-heavy` | `agaric_heavy` | `/devices/agaric` | Same | Development |

### Agaric note

Three catalog rows share one marketing page (`/devices/agaric`) so Earth Simulator and APIs can distinguish variants before physical serials are assigned. Generic airframe role **`mycodrone`** remains documented in MAS for non–variant-specific builds.

## NAS media (website)

Device pages load assets from `public/assets/...` with NAS fallbacks per `mergeWithNasFallbacks`. **Agaric** folder (Morgan): `\\192.168.0.105\mycosoft.com\website\assets\agaric\` — see completion doc `docs/AGARIC_DEVICE_AND_DEVICE_TRACKER_MAY03_2026.md`.

## Change process

1. Edit `lib/devices/catalog.ts` first (IDs and roles are contract).
2. Update portal + nav if the product is customer-facing on mycosoft.com.
3. Update MAS `device_registry_api.py` role description if a new `device_role` string is introduced.
4. Refresh this doc and `docs/AGARIC_DEVICE_AND_DEVICE_TRACKER_MAY03_2026.md` (or successor dated doc) when scope changes.
