# ITDX Fusarium Live Ship — 09 September 2026

**Date:** 09 September 2026  
**Status:** LIVE on `mycosoft.com` (slot **blue**, image `manual-045eaa29637135c932829df36e862c832f3eb7d0`). Hot data/math stay on MAS 188 + MINDEX 189.  
**Backends (source of truth):** [ITDX_VM_BACKENDS_SEP09_2026.md](ITDX_VM_BACKENDS_SEP09_2026.md)  
**CMMC:** Mycosoft is **pursuing** CMMC L2 — not compliant. **RJ Ricasata is CFO.**  
**CUI:** Outside the CUI boundary. No FOUO ingest. Official Army injects stay **NOT_SUPPLIED**.

---

## What was tested (local worktree on :3010)

Owner: `morgan@mycosoft.org`. Password values were never printed.

| Surface | Result |
|---|---|
| Unauth `/api/fusarium/itdx/*` | **401** |
| Unauth `/fusarium/itdx` and `/fusarium/earth-simulator` | **307** → `/fusarium/login?redirectTo=…` (no 307 loop) |
| `/fusarium/login` | **200** |
| Owner session → `/fusarium/itdx` and `/fusarium/earth-simulator` | **200** (not login, not 401) |
| Owner `/api/fusarium/itdx/weka-receipt` | **200** `verify_status=PASS` `arithmetic_checks=14` `trial_criteria_status=TRIAL_CRITERIA_NOT_MET` |
| Owner `/api/fusarium/itdx/situation` | **200** Fort Stewart, `synthetic=true` `live_cop=false` |
| Owner truth / task8 / evidence / run-state | **200** |
| Node ITDX tests (`test_map_layer`, gateway, truth, narration, evidence) | **19/19 PASS** |
| Browser tabs + Earth Sim ITDX (Play/focus/layers) | **19/19 PASS** |
| ITDX sidecar `127.0.0.1:8765/api/health` | **403** without Bearer (correct) |
| FormSpace `127.0.0.1:8766` | **200** when the lab pack is serving |

Local env password-key names did not match Supabase (`grant_type=password` last **400**). Owner session was proven via the existing Fusarium / Supabase path (same project as [CURSOR_FUSARIUM_OWNER_AUTH_LIVE_SEP02_2026.md](CURSOR_FUSARIUM_OWNER_AUTH_LIVE_SEP02_2026.md)). Public login remains `morgan@mycosoft.org` on `/fusarium/login`.

---

## Live vs NOT_SUPPLIED (MAS `188:8001`)

`GET/POST http://192.168.0.188:8001/api/itdx/situation-assessment` — in-process, `self_http=false`, `origin=SYNTHETIC_EXERCISE`, `live_cop=false`, `fouo=false`.

| Channel | Status | Notes |
|---|---|---|
| weather | **SUPPLIED** | Open-Meteo at **31.8697,-81.6072**. Earth-2 **249 down** — not required. |
| biology | **SUPPLIED** | Live GBIF + iNaturalist. MINDEX 189 `/health` 200; taxa/observations still 404. |
| information / equipment_weapons_assets | **SUPPLIED** | Public names / roads only. Exercise tracks `live=false`. |
| NLM | **BOUND** `model_loaded=true` | Not stub-only. Stub **0.85 is never Fusarium p**. |
| chemistry / physics | **UNQUALIFIED** | Loaded NLM is not a labeled chemistry/physics p. `p=null`. No `SCORED` until a labeled checkpoint is ops-loaded. PhysicsNeMo unset. |
| traffic / pathways / navigation | **NOT_SUPPLIED** | Google Directions / Distance Matrix **REQUEST_DENIED**. Key present. Do not invent traffic. |
| official injects / FOUO PDFs | **NOT_SUPPLIED** / refused | STOP_INGEST outside CUI boundary. |
| fusion p_truth / p_deception | **NOT_SUPPLIED** | Website geometry owns demo P(truth). |

MAS health **200 degraded** is intentional: skip-startup ON, collectors off so 8001 does not wedge. Registry **48** agents. `health.agents` empty by design. AVANI **200**. n8n **5678** ok. MINDEX **189:8000** + Postgres/Redis/Qdrant healthy. Do **not** run huge GBIF syncs (188 disk was 94% after journal vacuum).

---

## URLs

| Where | URL |
|---|---|
| Local Earth Sim | `http://localhost:3010/fusarium/earth-simulator` |
| Local ITDX | `http://localhost:3010/fusarium/itdx` |
| Local login | `http://localhost:3010/fusarium/login` |
| MAS ITDX health | `http://192.168.0.188:8001/api/itdx/health` |
| MAS situation | `http://192.168.0.188:8001/api/itdx/situation-assessment` |
| NLM health | `http://192.168.0.188:8001/api/nlm/health` |
| MINDEX health | `http://192.168.0.189:8000/health` |
| Origin | `http://192.168.0.187:3000` |
| Public | `https://sandbox.mycosoft.com` / `https://mycosoft.com` |
| Public Fusarium | `https://mycosoft.com/fusarium/login` → `/fusarium/earth-simulator` and `/fusarium/itdx` |

Overlay stays **`live: false`**. No mock COP.

---

## How to add data / math without a website rebuild

Keep Fusarium pointing at **live MAS 188 + MINDEX 189**. Do **not** bake NLM weights, GBIF dumps, or Weka JARs into the Next image.

| Add | Where | Website rebuild? |
|---|---|---|
| Weather / biology / public OSINT | MAS `itdx_public_sources.py` + public APIs; or MINDEX taxa/observations when those routes exist | **No** |
| NLM labeled score (`SCORED`) | Ops-load a labeled checkpoint on 188; situation-assessment may then emit `p` only if it is not stub `0.85` | **No** |
| Traffic / pathways | Enable Directions + Distance Matrix on the existing Google key (GCP console). Until then stay **NOT_SUPPLIED** | **No** |
| Weka / FormSpace receipts | Drop `receipt.json` on the v1.4 kit `local_data/cli_runs/*` path or replace `itdx/artifacts/weka-v14-replay-pass.json` via a mounted/API path | **No** for kit path; UI-only if the walkthrough component changes |
| New UI chrome / tabs / iframe policy | Website worktree | **Yes** (blue-green only) |

---

## GitHub

| Repo | PR | Merge SHA | Notes |
|---|---|---|---|
| `MycosoftLabs/website` | [#300](https://github.com/MycosoftLabs/website/pull/300) | `045eaa29637135c932829df36e862c832f3eb7d0` | Fusarium Intel Feed, Weka walkthrough, owner-gated APIs |
| `MycosoftLabs/mycosoft-mas` | [#133](https://github.com/MycosoftLabs/mycosoft-mas/pull/133) | `ee094c75741fcf4f6295fc189d8ba7108e362a07` | situation-assessment + this doc |

---

## Blue-green (187) — done 09 Sep 2026 ~19:39 UTC

- Instant Deploy [34392868545](https://github.com/MycosoftLabs/website/actions/runs/34392868545) built `Dockerfile.production` **no-cache** and pushed `ghcr.io/mycosoftlabs/website:manual-045eaa29637135c932829df36e862c832f3eb7d0`.
- GH cutover hung: idle `mycosoft-website-blue` was kernel **D-state**; leftover compose name `a22d1420a982_mycosoft-website-blue` was **Created**. Primary **green** stayed healthy and kept serving.
- Leftover Created container removed. D-state idle **renamed** (not stopped) to `mycosoft-website-blue-wedged-sep09`, then disconnected from `website_mycosoft-network` so `website-blue` DNS has one address.
- New idle **blue** started with NAS `/opt/mycosoft/media/website/assets` → `/app/public/assets:ro`.
- Candidate `docker exec` `/api/health` **3× 200**. Auth gate `/login?redirectTo=/natureos/mycobrain` (not `config_missing`).
- Nginx flipped **green → blue**. Cloudflare `purge_everything` **OK**. Green left running as rollback window.

### Live prove (after cutover)

| Surface | Result |
|---|---|
| Origin `http://192.168.0.187:3000/api/health` | **200** |
| `https://mycosoft.com/api/health` + `/fusarium/login` | **200** |
| `https://sandbox.mycosoft.com/api/health` + `/fusarium/login` | **200** (brief 504 during purge/DNS isolate, then recovered) |
| Unauth `/fusarium/itdx` and `/fusarium/earth-simulator` | **307** (origin + mycosoft.com) |
| Unauth `/api/fusarium/itdx/situation` and `/weka-receipt` | **401** |
| MAS 188 ITDX / NLM + MINDEX 189 | **200** (hot data; no 188 restart) |

Login as `morgan@mycosoft.org` on `https://mycosoft.com/fusarium/login`, then open `/fusarium/itdx` and `/fusarium/earth-simulator`. Overlay stays **`live: false`**.

---

## Related

- [ITDX_VM_BACKENDS_SEP09_2026.md](ITDX_VM_BACKENDS_SEP09_2026.md)
- [ITDX_EXTERNAL_SOURCES_INTEGRATION_SEP09_2026.md](ITDX_EXTERNAL_SOURCES_INTEGRATION_SEP09_2026.md)
- [ITDX_V14_LAB_INTEGRATION_SEP09_2026.md](ITDX_V14_LAB_INTEGRATION_SEP09_2026.md)
- [CURSOR_FUSARIUM_OWNER_AUTH_LIVE_SEP02_2026.md](CURSOR_FUSARIUM_OWNER_AUTH_LIVE_SEP02_2026.md)
