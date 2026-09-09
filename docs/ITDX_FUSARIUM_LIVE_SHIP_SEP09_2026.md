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
| biology | **SUPPLIED** | Live GBIF + iNaturalist. MINDEX 189 `/health` 200. Cheap `/api/mindex/taxa` + `/observations` (8 Fusarium rows each, internal token). |
| information / equipment_weapons_assets | **SUPPLIED** | Public names / roads only. Exercise tracks `live=false`. |
| NLM | **UNQUALIFIED** `model_loaded=false` | In-process health after 188 restart. `/api/nlm/predict` still emits stub **0.85** — rejected. No channel is `SCORED`. |
| chemistry / physics | **UNQUALIFIED** | No labeled chemistry/physics p. `p=null`. PhysicsNeMo unset. |
| traffic / pathways / navigation | **NOT_SUPPLIED** | Google Directions / Distance Matrix **REQUEST_DENIED** (key present, API not authorized). `gcloud` is not installed on this workstation — cannot enable Directions/Distance Matrix from here. |
| official injects / FOUO PDFs | **NOT_SUPPLIED** / refused | STOP_INGEST outside CUI boundary. |
| fusion p_truth / p_deception | **NOT_SUPPLIED** | Website geometry owns demo P(truth). |

MAS health **200 degraded** is intentional: skip-startup ON, collectors off so 8001 does not wedge. Registry **48** agents. `health.agents` empty by design. AVANI **200**. n8n **5678** ok. MINDEX **189:8000** + Postgres/Redis/Qdrant healthy. Do **not** run huge GBIF syncs (188 disk was 94% after journal vacuum).

---

## Public Fusarium API 5xx fix (09 Sep 2026)

Hot on MAS **188** before this commit. Persist so the next `git pull` on 188 does not revert production.

**Cause:** `MINDEX_API_URL` on 188 is origin-only (`http://192.168.0.189:8000`). The router treated it as already including `/api/mindex`, called missing paths such as `/species/fungi`, and `raise_for_status()` turned MINDEX **404** into Fusarium **500**.

**Fix:** Prefix `/api/mindex` when missing; species uses `/taxa` (`q=Fusarium`); public GETs return **200** with honest `UNQUALIFIED` when the list is empty or upstream is degraded. No mock rows.

| Live `188:8001` route | Result |
|---|---|
| `GET /api/fusarium/threats` | **200** `UNQUALIFIED` empty (no TACO assessments) |
| `GET /api/fusarium/dispersal` | **200** `UNQUALIFIED` empty |
| `GET /api/fusarium/risk-zones` | **200** `UNQUALIFIED` empty |
| `GET /api/fusarium/species` | **200** ~**100 Fusarium taxa** from MINDEX `/api/mindex/taxa` |

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
| `MycosoftLabs/mycosoft-mas` | [#135](https://github.com/MycosoftLabs/mycosoft-mas/pull/135) | `a34b66a039baf8c9b1e3812bb21bda753ef0167b` | Public Fusarium MINDEX path so 188 pull cannot revert 200s |

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

Login as `morgan@mycosoft.org` on `https://mycosoft.com/fusarium/login` (**Continue with owner Google**). Env passwords fail vs Supabase — do not reset. Owner Earth Sim still needs that Google session. Overlay stays **`live: false`**.

---

## Closed 09 Sep 2026 continue (188 git + Task 8 + MINDEX slice)

188 was still on `fix/cmmc-state-reconciliation-jul27` @ `3388505f` with hot-patched ITDX files. Checkout to **`origin/main` `a34b66a03`** succeeded. Skip-startup **left ON**.

`/api/itdx` then **404**: `itdx_api` imports `NLM_STUB_CONFIDENCE` / `is_usable_nlm_confidence`, which were **not on main**. `except ImportError: pass` swallowed the mount. Task 8 COA proposer also failed: `engines/intention/__init__.py` imported `intention_service.py`, which was **not on main**.

**This commit persists those modules** so the next 188 `git pull` keeps ITDX mounted.

| Check | Result |
|---|---|
| 188 `git rev-parse HEAD` after checkout | `a34b66a03` (then this PR) |
| `GET /health` | **200** `degraded` (skip-startup ON on purpose) |
| `GET /api/itdx/health` | **200** after stub helpers landed |
| `GET /api/itdx/situation-assessment` Fort Stewart | **200** `in_process=true` `self_http=false` |
| weather / biology / information / equipment | **SUPPLIED** |
| MINDEX cheap slice | `/api/mindex/taxa` + `/observations` **200**, 8 Fusarium rows each (internal token). No GBIF full sync (188 disk **94%**). |
| NLM channels | **UNQUALIFIED** / `p=null`. Predict stub 0.85 unused. |
| traffic / pathways / navigation | **NOT_SUPPLIED** `REQUEST_DENIED`. Key present. `gcloud` missing — APIs not enabled from here. |
| Task 8 | **200** `qualification=DEGRADED` `role_count=6`. Intention **bound**. Human handoff stays unbound (`secretary_not_invoked`). Not BOUND. |
| Public `mycosoft.com` threats / dispersal / risk-zones / species | **200** |
| `https://mycosoft.com/fusarium/login` | **200** button **Continue with owner Google** |
| 187 blue-green | **not touched** |
| FOUO / CUI ingest | **not done** |

**RJ Ricasata is CFO.** Mycosoft is **pursuing** CMMC L2 — not compliant.

---

## Closed 09 September 2026 (continue — PR 137)

PR 136 already persisted `intention_service` + NLM stub helpers so 188 `git pull` keeps ITDX mounted. This follow-on **does not invent Fusarium p**.

| Item | Outcome |
|---|---|
| NLM predict | Stub `predict()` now returns `confidence=None` + `confidence_usable=false`. Situation-assessment calls predict **only if already ready** (no auto-load). **SCORED/BOUND** only on a usable non-stub confidence. |
| Chemistry / physics | PhysicsNeMo unset/down → **UNQUALIFIED** + reason. PhysicsNeMo health only → **SUPPLIED** `p=null`. Chemistry stays **UNQUALIFIED** unless PubChem identity rows (**SUPPLIED**, not an NLM p). |
| Task 8 | IntentionAgent default score is `None` (not `1.0`). Seven-role stays **DEGRADED** (secretary unbound). Intention errors stay errors — not fake BOUND. |
| Extra public data | First-wave OSINT adds PubChem fusaric acid, GBIF species match (`Fusarium oxysporum`), Open-Meteo air quality, USGS FDSN (empty bbox is honest). Keeps PR 136 cheap MINDEX `/api/mindex/taxa` + `/observations`. No `full_fungi_sync`. |
| Google Directions | Key present on 188 (`google-maps.conf`). APIs stay **NOT_SUPPLIED** / `REQUEST_DENIED` unless Directions + Distance Matrix are enabled on the existing GCP project. No keys printed. |
| Live UI | No website cutover. Public site was **200**. `/fusarium/login` **200** + owner Google button. Owner-gated ITDX APIs stay **401** unauth. Local :3010 not killed. |
| RJ | **RJ Ricasata is CFO.** |

### Live prove after PR 137 on 188 (`dd64cda3`)

Orchestrator restarted (more than already-hot files). Skip-startup left ON. `fusarium_api.py` not reverted. No 187 cutover. No password reset. No secrets printed.

| Check | Result |
|---|---|
| `GET /health` | **200** `degraded` |
| `GET /api/itdx/health` | **200** |
| `GET /api/nlm/health` | **200** `model_loaded=false` (honest after restart) |
| Task 8 | **200** `qualification=DEGRADED` `role_count=6`. COA proposer **bound**. Human handoff `secretary_not_invoked`. Not fake BOUND. |
| NLM ecology | **UNQUALIFIED** / `p=null` / `ecology_predict_status=NOT_SUPPLIED` (no auto-load stub) |
| chemistry | **SUPPLIED** `p=null` (PubChem fusaric acid identity) |
| physics | **UNQUALIFIED** `PHYSICSNEMO_API_URL unset` |
| biology / information / equipment | **SUPPLIED** |
| weather | **NOT_SUPPLIED** `empty` on first probe (Open-Meteo cancelled by extra first-wave jobs) — follow-on weather-first-wave PR |
| traffic / pathways / navigation | **NOT_SUPPLIED** `REQUEST_DENIED`. `gcloud` missing on 188 and this workstation. |
| `https://mycosoft.com/fusarium/login` | **200** + owner Google button |
| Unauth `/api/fusarium/itdx/situation` + `/weka-receipt` | **401** |
| Origin `http://192.168.0.187:3000/api/health` | **200** — no blue-green |
| Local :3010 | not killed |

### Live prove after PR 138 on 188 (`22efb91c`)

Weather-first OSINT wave pulled. Orchestrator restarted. Skip-startup ON.

| Check | Result |
|---|---|
| weather | **SUPPLIED** `p=null` (Open-Meteo restored) |
| chemistry | **SUPPLIED** `p=null` (PubChem) |
| biology / information / equipment | **SUPPLIED** |
| NLM | **UNQUALIFIED** `p=null` `model_loaded=false` |
| physics | **UNQUALIFIED** PhysicsNeMo unset |
| traffic / pathways / navigation | **NOT_SUPPLIED** `google_maps_api_denied` (`gcloud` missing — APIs not enabled) |
| Task 8 | **DEGRADED**, COA proposer bound, secretary unbound |
| 187 / public login | unchanged — no cutover |

---

## Related

- [ITDX_VM_BACKENDS_SEP09_2026.md](ITDX_VM_BACKENDS_SEP09_2026.md)
- [ITDX_EXTERNAL_SOURCES_INTEGRATION_SEP09_2026.md](ITDX_EXTERNAL_SOURCES_INTEGRATION_SEP09_2026.md)
- [ITDX_V14_LAB_INTEGRATION_SEP09_2026.md](ITDX_V14_LAB_INTEGRATION_SEP09_2026.md)
- [CURSOR_FUSARIUM_OWNER_AUTH_LIVE_SEP02_2026.md](CURSOR_FUSARIUM_OWNER_AUTH_LIVE_SEP02_2026.md)
