# Aerosol / Virus / Radiation Feeds — MVP Complete (May 03, 2026)

**Date:** May 03, 2026  
**Status:** MVP complete (real OpenAQ path + honest Safecast / virus deferral)  
**Related plan shell:** `docs/AEROSOL_VIRUS_RADIATION_FEEDS_PLAN_MAY01_2026.md`

## What shipped

| Feed | Behavior |
|------|----------|
| **OpenAQ** | MAS `GET /api/natureos/feeds/openaq/measurements` via `EnvironmentalClient.get_air_quality_measurements`; website BFF `GET /api/natureos/feeds/openaq/measurements` proxies MAS. **503** on upstream failure — no fabricated PM readings. |
| **Radiation** | MAS `GET /api/natureos/feeds/radiation/status` attempts Safecast; **JSON 503** with provenance and hint when unreachable (no synthetic µSv/h). Website aerosol layer proxies this route. |
| **Virus / aerosol** | MAS `GET /api/natureos/feeds/virus-aerosol/status` returns **503** with explicit deferral message — no surrogate viral metrics. Website proxies same contract. |

## Code references

- MAS: `mycosoft_mas/core/routers/environmental_feeds_mvp_api.py` (included from `myca_main.py`).
- Website: `app/api/natureos/feeds/openaq/measurements/route.ts`, `app/api/natureos/aerosol/radiation/route.ts`, `app/api/natureos/aerosol/virus/route.ts`; aerosol dashboard OpenAQ card consumes measurements proxy.

## Env

- Optional: `OPENAQ_API_KEY` (higher limits).
- Optional: `SAFECAST_API_KEY` when deployment requires authenticated Safecast reads.

## Deferred

- Normalized MINDEX persistence tables for aerosol/radiation time series.
- Map overlay wiring beyond current CREP dashboard cards.
