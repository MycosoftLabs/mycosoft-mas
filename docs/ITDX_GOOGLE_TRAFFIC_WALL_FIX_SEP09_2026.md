# ITDX Google Traffic Wall Fix — 09 September 2026

**Date:** 09 September 2026  
**Status:** Complete  
**Related:** `docs/ITDX_EXTERNAL_SOURCES_INTEGRATION_SEP09_2026.md`  
**CMMC:** Mycosoft is **pursuing** CMMC L2 — not compliant. **RJ Ricasata is CFO.**  
**CUI:** Outside the CUI boundary. Official injects stay NOT_SUPPLIED.

---

## Problem

Fusarium Google Maps key (`FUSARIUM_GOOGLE_MAPS_API_KEY`, sha256_12 `8655e95ff59e`) is live on MAS 188. Standalone Directions and Distance Matrix return **OK**.

`POST /api/itdx/situation-assessment` still marked `traffic` / `pathways` / `navigation` **NOT_SUPPLIED** because of a **4.8s** assessment wall (and a **3.3s / 3.6s** OSINT cancel), not `REQUEST_DENIED`. Google calls were cancelled before ETA / polyline cites arrived. No scores were invented.

---

## Fix (in-process, no self-HTTP)

| Constant | Was | Now |
|---|---|---|
| `ASSESSMENT_WALL_S` | 4.8 | **14.0** |
| `GOOGLE_MAPS_WALL_S` / `GOOGLE_PROBE_S` | buried in 3.3s OSINT cut | **12.0** |
| Other public OSINT | 3.3–3.6s | **3.6s** (unchanged) |

- Google Directions + Distance Matrix start **first** (task created before other probes) and run **in parallel** with weather/GBIF/etc.
- Device-registry probe is now `_safe`-bounded so it cannot discard a finished Google result.
- Timeout reason is **`google_maps_timeout`**, never a fake `p` and not mislabeled `REQUEST_DENIED`.
- Prefer `FUSARIUM_GOOGLE_MAPS_API_KEY` over the Map Tiles alias.
- NLM / Ollama compartmentalization unchanged (NAS scientific NLM vs 188 `:11434` MYCA chat). Protected orchestrator / soul / security files not edited. No 187.
- `itdx_api.py` imports NLM stub-rejection helpers with a local fallback so 188 can mount ITDX without shipping a newer `nlm/inference/service.py`.

---

## How to verify

```bash
curl -sS -m 45 -X POST http://192.168.0.188:8001/api/itdx/situation-assessment \
  -H "Content-Type: application/json" \
  -d '{"slice":{"name":"Fort Stewart","bbox":[-81.70,31.80,-81.45,32.05],"center":[31.88,-81.61]}}'
```

Expect `channels.traffic.status=SUPPLIED` and `channels.pathways.status=SUPPLIED` with `duration_in_traffic` / polyline cites when Google returns OK. If Google still exceeds 12s, those channels stay **NOT_SUPPLIED** with `reason=google_maps_timeout`.

**188 Fort Stewart proof (2026-09-09, after remount):** HTTP 200 in ~6.7s; `in_process=true`, `self_http=false`, `p=null`. `traffic` / `pathways` / `navigation` **SUPPLIED** with Distance Matrix / Directions cites (Hunter AAF **52 mins**, Hinesville **10 mins**, Directions polyline ~1224). Weather and biology stayed **SUPPLIED**. No invented scores.

---

## Files

- `mycosoft_mas/core/routers/itdx_api.py`
- `mycosoft_mas/core/routers/itdx_public_sources.py`
- `tests/test_itdx_task8_api.py`
