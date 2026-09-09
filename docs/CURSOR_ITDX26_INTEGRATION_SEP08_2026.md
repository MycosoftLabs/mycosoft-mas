# Cursor ITDX26 integration — 08 September 2026

**Date:** 08 September 2026 (math/walkthrough verification added 09 September 2026)  
**Status:** Fusarium ITDX tab + Codex v1.3 Earth-view hook on isolated website worktree. Not production-deployed. **09 Sep:** FormSpace recorded math on `:8766` matches bundled reference; Weka **not** run; Fusarium 3010 iframe still UNQUALIFIED.  
**Authority:** Morgan override 08 Sep 2026 — **ITDX is a Fusarium operator tab**, owner-only. Codex 08 Sep build plan is the **overlay integration contract**. Handoff folder still governs honesty / frozen v1.2: `C:\Users\Owner1\Downloads\Mycosoft_ITDX_Cursor_Handoff_2026-09-08`.  
**Related:** worktree `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx` branch `cursor/itdx-live-integration-20260908`; `itdx/integration/DEPLOYMENT_INVENTORY.md`; `itdx/integration/GAP_REGISTER.md`; `itdx/integration/v1.3/README.md`; `itdx/integration/ARMY_PACK_INVENTORY_SEP08_2026.md`.  
**09 Sep MAS/MYCA/AVANI plan (why they do not work + M0–M5):** `docs/MAS_MYCA_AVANI_FUSARIUM_ITDX_INTEGRATION_PLAN_SEP09_2026.md` — not a completion badge; no 187 cutover.

## Codex v1.3 contract (do not invent a competing overlay)

| Item | Contract |
|---|---|
| Layer | Clearly labeled **fictional replay**: preset tracks, authored boundaries, timestamps, **uncertainty circles** |
| Accuracy | Position error vs **known synthetic ground truth**; show where stated uncertainty **holds or fails**. Pure math, not generative AI |
| Map | Additive layer on the **shared Fusarium CREP / Earth Simulator map**. Do **not** replace real aircraft / vessels / sats |
| Docs | 10 PDFs remain **cited source documents** (filename + page count). Bodies not mounted |
| Versions | Build **v1.3** while **preserving frozen v1.2.0** (`itdx/local`) as “replay v1.2 results” |
| API flags | `synthetic: true`, `live: false`, `replay: true`, `version: "1.3"` |
| Toggle | **Left Intel Feed tab `ITDX`** (paired with half-width **MYCA LIVE**) is the operator surface. Map paint stays additive (`itdx-v13-*`). Real CREP stays |

Codex had **not** landed v1.3 code in Fusarium, website, or Downloads at implementation time. Cursor built the **Earth-view hook + contract** so Codex can drop tracks into `itdx/integration/v1.3/FICTIONAL_REPLAY.json`. Do not overwrite Codex files mid-write.

## Army pack / CUI (STOP_INGEST)

| Item | Result |
|---|---|
| Pack | `C:\Users\Owner1\Downloads\Army docs-20260908T204250Z-1-001` |
| Count | **10 PDFs, 86 pages**, 0 nested zips |
| Banners | Every file: **UNCLASSIFIED//FOUO** — EXERCISE UNWELCOME GUEST FOR TRAINING USE ONLY |
| Origin | HQ, 3rd Infantry Division (government). **Not** Mycosoft-authored. **EV-SAO-CUI-DET-001 does not apply** |
| Tokens | No `CUI//`, SECRET, CONFIDENTIAL, NOFORN in the filename-level scan |
| Decision | **STOP_INGEST**. Filenames inventoried only. No PDF bytes in git, website, or MINDEX. No FOUO banners on the public site. No incident record created |
| Geometry | Lab instance `ITDX_V13_ARMY_DEMO` / `army-extract-v13`. AO is the **interpolated Fort Stewart box** (no MGRS/lonlat in PDF text). Named areas stay NOT_SUPPLIED unless geocoded. **Not** a second forked story |

### Citation list (filenames only)

1. DRAFT 3ID OPORD 14-06 (OPERATION BULLDOG).pdf — 16p  
2. DRAFT 3ID OPORD 14-06 ANNEX A (Task Organization).pdf — 2p  
3. DRAFT 3ID OPORD 14-06 ANNEX B (Intelligence).pdf — 5p  
4. DRAFT 3ID OPORD 14-06 ANNEX B App 1 (Intel Estimate).pdf — 10p  
5. DRAFT 3ID OPORD 14-06 ANNEX B App 1 TAB A (Terrain).pdf — 4p  
6. DRAFT 3ID OPORD 14-06 ANNEX B App 1 TAB B (Weather).pdf — 4p  
7. DRAFT 3ID OPORD 14-06 ANNEX B App 1 TAB C (Civil Considerations).pdf — 11p  
8. DRAFT 3ID OPORD 14-06 ANNEX B App 1 TAB C ENCL 1 (OE Overview).pdf — 19p  
9. DRAFT 3ID OPORD 14-06 ANNEX C App 2 (Operation Overlay).pdf — 6p  
10. DRAFT 3ID OPORD 14-06 ANNEX L (Information Collection).pdf — 9p  

## Route (Morgan supersedes Codex NatureOS suggestion)

| Item | Value |
|---|---|
| Live path | `/fusarium/itdx` |
| Earth view | `/fusarium/earth-simulator` (shared CREP map + v1.3 layer) |
| Earth left chrome | Fusarium only: **MYCA LIVE \| ITDX** equal halves in the Intel Feed right column. NatureOS Earth Sim keeps full-height MYCA LIVE |
| Chrome | Fusarium `(dashboard)` operator shell |
| Tab | Operations → **ITDX** workspace; Earth Sim left panel **ITDX** tab = layers + insights |
| Auth | Same owner gate as `/fusarium` (`morgan@mycosoft.org`) |
| NatureOS | Stays public. No `/natureos/itdx` orphan |
| Civilian `/login` | Untouched |

### Files

- `app/fusarium/(dashboard)/itdx/page.tsx`
- `components/fusarium/itdx/itdx-workspace.tsx` (v1.2/v1.3 selector, accuracy table, 10 PDF citations)
- `components/fusarium/itdx/itdx-earth-left-panel.tsx` (Earth Sim left-tab operator surface)
- `lib/fusarium/itdx/itdx-layer-bus.ts` (layer toggles → map visibility)
- `components/fusarium/itdx/itdx-v13-replay-layer.tsx` (paints `itdx-v13-*`; no floating overlay chrome)
- `app/dashboard/crep/CREPDashboardClient.tsx` (Fusarium split: `data-crep-left-tab="myca"` + `data-crep-left-tab="itdx"`)
- `lib/fusarium/itdx/accuracy-math.ts` — haversine + `error_m <= claimed_uncertainty_m`
- `lib/fusarium/itdx/build-v13-overlay.ts`
- `app/api/itdx/overlay/route.ts` (owner-only)
- `app/api/itdx/v12/route.ts` (frozen 1.2.0 pointer; does not start `:8765`)
- `app/api/itdx/registry/route.ts`
- `itdx/integration/v1.3/FICTIONAL_REPLAY.json` (Codex drop-in)
- `itdx/local` frozen v1.2.0 (unchanged)

`tsconfig.json` still excludes `itdx/**`. `.dockerignore` still excludes `itdx`. Frozen Python lab is **not** the public demo.

## Accuracy math

```
error_m = haversine(reported, truth)
circle_holds = error_m <= claimed_uncertainty_m
```

Placeholder tracks include at least one designed **FAIL** (Vessel B) so the panel can show hold vs fail. 1–5 Army scale remains **NOT_SUPPLIED**.

## What is live vs inventory-only

| Surface | State |
|---|---|
| `/fusarium/itdx` on isolated worktree | Implemented. Registry + citations + accuracy + v1.2/v1.3 selector |
| Fusarium Earth / CREP overlay | Hook ready (`itdx-v13-*` sources). Real CREP feeds unchanged |
| Earth Sim left panel | Fusarium Intel Feed: **MYCA LIVE \| ITDX** equal halves. ITDX tab layers + insights from **lab extract** (`ITDX_V13_ARMY_DEMO`): 9 tracks, Fort Stewart box, 15 LBS corridors, 22 named areas (0 geocoded), SA `p_awareness` math-only, NLM/MYCA UNQUALIFIED |
| Production / Sandbox `187:3000` | **Left up**. No rebuild, no cutover. Tab is **not** on production |
| Dirty website / dirty Fusarium trees | **Untouched** |
| Codex v1.3 track file | Not landed by Codex; Cursor seed is coastal synthetic for the contract |
| Official inject pack | **MOUNTED_LOCAL_LAB_ONLY** — 10 PDFs in gitignored `itdx/local/docs/army_pack/`; extract JSON gitignored |
| `127.0.0.1:8765` | Loopback lab (v1.2.0). Scenario `ITDX_V13_ARMY_DEMO` runs tasks 8/12/13/14 on the extract. Not the public demo |

## Local lab extract (08 Sep expansion)

Schema for Earth Sim reuse: `website-itdx/itdx/integration/v1.3/SCENARIO_EXTRACT_SCHEMA.json` (`itdx.scenario_extract/v1.3`). Instance `SCENARIO_EXTRACT.json` / `PDF_REPLAY.json` are **gitignored**. Completion note: `website-itdx/itdx/integration/ARMY_PACK_LAB_SCENARIO_SEP08_2026.md`.

All four lab tasks run against the extract. COA comparison labels `math` / `nlm` / `myca` / `NOT_SUPPLIED`. SA math is haversine + circle hold/fail + freshness + corridor; NLM/MYCA do not overwrite it. Bind state on this machine: **NLM `not_bound` / `UNQUALIFIED`**, **MYCA `not_bound` / `UNQUALIFIED`** (no loaded model, no 7-role Task 8 on loopback). LBS clusters/corridors/coincidence computed from extract only.

Coastal v1.2 `clean` / `demo-11` remains replayable. Default 41-case suite excludes `ITDX_V13_ARMY_DEMO`.

## Browser evidence (08 Sep 2026, localhost:3010)

Playwright (`website-itdx/itdx/integration/v1.3/_verify_earth_itdx_chrome.mjs`) against isolated worktree on **3010**. Owner session minted via Supabase admin magic-link (password path invalid). Sandbox `192.168.0.187:3000` left at HTTP **200** — no cutover.

| Check | Result |
|---|---|
| login | PASS (`/fusarium/earth-simulator`) |
| earth | PASS |
| mycaHalf | PASS (`MYCA LIVE` + `ITDX` equal halves) |
| itdxTab | PASS (DATA LAYERS from lab extract) |
| layers | PASS (Fort Stewart box + Collection / LBS) |
| insights | PASS (`ITDX_V13_ARMY_DEMO`, `p_awareness`, NLM/MYCA UNQUALIFIED) |
| ipad (~768) | PASS |

Evidence (gitignored): `website-itdx/itdx/integration/v1.3/_browser_evidence/earth-itdx-desktop-sep08-2026.png`, `earth-itdx-ipad-sep08-2026.png`. Globe paints `itdx-v13-*` (9 tracks, 15 corridors, 9 cluster centroids, Fort Stewart box) and flies once to extract `ao.center`. Real CREP stays.

## What still needs Morgan

1. Official inject mount authorization (FOUO pack stays outside this AI/website path).  
2. Meaning of 1–5 values.  
3. Qualified NLM checkpoint load.  
4. Authorize Sandbox 187 blue-green **only after** a candidate returns HTTP 200 and Morgan says ship.  
5. Disclosure authorization before publishing the full proprietary packet to public GitHub.

RJ remains CFO. Mycosoft is **pursuing** CMMC L2 — not claiming compliant. UNCLASSIFIED commercial.

## 09 September 2026 — algorithm walkthrough + math (before Weka)

**Authority:** Morgan 09 Sep 2026 pasted mathematics + walkthrough contract. FormSpace pack `START_HERE.txt` / `CURSOR_HANDOFF.md` / `ATLAS_SCHEMA.md` / `ALGORITHMS.md`. ITDX v1.3 handoff `CURSOR_V13_HANDOFF.md` / `V13_VALIDATION.md`. Isolated worktree `website-itdx-codex-v13`. **Weka was not run.** Earth base tiles left to the other agent.

**What actually served**

| Surface | Process | Result |
|---|---|---|
| FormSpace observatory `127.0.0.1:8766` | Pack `itdx/app/run.py` (no Torch) | Recorded seed-11 math **PASS**. All observatory tabs rendered. |
| ITDX lab `127.0.0.1:8765` | `service.py` + Bearer | Health/bootstrap **v1.3.0**, 40 documents, tasks 8/12/13/14. Browser without Bearer = **403**. `/api/formspace` is **8766**, not 8765. |
| Fusarium `/fusarium/itdx` on **3010** | **Main website repo**, not the worktree | Owner session opens chrome (Walkthrough / Algorithm lab / Form Space). Iframe stayed **white**; backend **CHECKING**. Main `.env.local` has no `ITDX_BACKEND_*`. |
| MINDEX `192.168.0.189:8000` | Live | `/health` 200. Authenticated `unified-search/earth?q=physarum` **200**, `total_count=0`. |
| MAS/NLM `192.168.0.188:8001` | Live | `/api/nlm/health` 200, **`model_loaded=false`**. No 7-role MYCA Task 8. |

### Section-by-section vs 09 Sep write-up

| # | Contract | Files | Live result |
|---|---|---|---|
| 1 | `F_t` subject/chart/state; atlas of math/algorithms/species/behavior/cognition | Pack `ATLAS_SCHEMA.md`, `nlm_formspace/atlas.py`; UI atlas tab | **PASS** — 41 forms, 1,706 states, 1,600 observations, 3 charts, 32 relations, 3 claims. Kinds include `mathematical_form`, `algorithm`, `species`, `behavior`, `cognitive_construct`, `capability`, `phenomenon`. `form:total-order` state `coordinates=null`. |
| 2 | `u_t=[v_t,m_t,ℓ_t]` 16+7+time → 24 in; 32 learned coords | `nlm_formspace/model.py` `Linear(24,32)` + 2 `SelectiveSSMBlock` | **PASS** — UI observation shows 32 coords, `chart_id=environmental-ssm32/v1`, native sensor vector length 16 (the `v_t` block). |
| 3 | Selective SSM + Task 12 `p=σ(z/T)`; `L=L_cls+0.15 L_next+0.05 L_recon` | `engine.py` `loss=classification+.15*prediction+.05*rec` | **PASS** — live Task 12: 1,600 rows, **F1=1.0**, Brier **1.8110714384205862e-19** identical to bundled `result.json`. SHA `1d3fe486d94507600f5c82e2be527ac9be42ff9a8a59586e7f158397a1a3b792`. |
| 4 | FormSpace geometry + Task 13 typed links, `exp(-d/500)`, no event IDs | `model.py` `TypedEvidenceGraph.decode`; `atlas.py` 4 centers, q99 novelty | **PASS** — Task 13: 2,400 pairs, **F1=1.0**, capture-set coverage **0.8** (4/5), matches bundled + `VALIDATION_REPORT.md`. |
| 5 | Capture-grouped conformal; Task 8 local AVANI DENY/PAUSE/PASS/REVIEW; Borda ≠ P(success) | `calibration.py`; `engine.py` gate + `rank_semantics` | **PASS** — prediction sets present; three options all **PASS** / `ADVISORY_ONLY`; UI: “Borda … is not a success probability.” Local role trace is **not** seven MYCA agents. |
| 6 | Task 14 GeoJSON; `NOT_ESTIMATED`; class p ≠ geo radius | `engine.py` `position_uncertainty_status`; UI map tab | **PASS** — UI warning: “Position uncertainty is not estimated. Class probability is not a geographic accuracy radius.” Offline preview only; Earth tiles not touched. |
| 7 | Behavior `u=0.3(g-x)`, `e≤0.05` for 10 steps; no emergence | `behavior.py`; UI Behavior tab | **PASS** — feedback+memory 24/24; memory-reset 0/24; feedback-off 0/24; `emergence_established=false`. Pytest `test_behavior.py`: **3 passed**. |
| 8 | Weka frozen-prob eval | `weka/evaluate.py` | **NOT RUN**. Internal math matches bundled within tolerance (exact). |

### Walkthrough E2E

| Step | Surface | Result |
|---|---|---|
| Observatory load | `8766/formspace.html` | **PASS** — bundled recorded, no white screen |
| Atlas / Architecture / 12 / 13 / 8 / 14 / Behavior | 8766 tabs | **PASS** — math outputs visible |
| Algorithm lab guided 7-step | `8766/` Prepare→Export | **PASS** — 6 Next clicks; Challenge step shows S13-2 / S8-1 / D-3. Next disables when a run is required (honest, not skipped). |
| 8765 in browser without Bearer | `8765/formspace.html` | **FAIL (expected 403)** |
| 8765 with Bearer | `/api/health`, `/api/bootstrap` | **PASS** |
| Fusarium `/fusarium/itdx` | 3010 owner session | **PARTIAL** — chrome **PASS**; iframe **white** / backend CHECKING. Same math path is **not** proven through the main-site gateway. |

Evidence: `website-itdx-codex-v13/itdx/integration/.browser-proof/sep09-walkthrough/` and `_internal_math_verify_sep09.json`.

### Internal test (ran) vs Weka (later)

**Internal test (ran now):**

```text
python D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13\itdx\integration\_internal_math_verify_sep09.py
cd C:\Users\Owner1\Downloads\Mycosoft_FormSpace_Software_and_Synthetic_Data\itdx\formspace
python -m pytest tests\test_behavior.py -q --rootdir=.
```

Live `/api/formspace` vs zip `result.json`: SHA, Task 12/13 F1/Brier, conformal coverage, Task 8 gates, Task 14 `NOT_ESTIMATED` — exact match. `test_math.py` **not run**: serving CPython 3.12 has **no Torch** (8766 serves the recorded bundle only).

**Weka command (ready, not executed):**

```text
cd C:\Users\Owner1\Downloads\Mycosoft_FormSpace_Software_and_Synthetic_Data
python itdx/formspace/run.py unpack --output itdx/formspace/recorded
python itdx/formspace/weka/evaluate.py --predictions itdx/formspace/recorded/weka --download
```

Optional later cross-check: `python itdx/formspace/verify_evaluation.py itdx/formspace/recorded` (compares Weka JSON to Python; still not a replacement classifier).

**Weka ready:** **YES** for the FormSpace recorded seed-11 environmental run. **NO** as a claim that Fusarium 3010 / production NLM / 7-role MYCA already execute this path.

### Still UNQUALIFIED

- MAS NLM `model_loaded=false` (hit `/api/nlm/health`; do not treat as a 7-role or loaded-weight result).
- Production MYCA-AVANI 7-role Task 8 **unbound**. FormSpace Task 8 is the **local deterministic AVANI** envelope — that is the contract, not a live seven-agent consultation.
- MINDEX is real and authenticated; Physarum/fungi/amanita earth-search returned **0 rows**. Atlas species remains `LITERATURE_REPORTED`; production taxonomy import has not happened.
- Fusarium 3010 iframe / main-site `ITDX_BACKEND_*` bind.
- Torch worker / `test_math.py` / a fresh `validate.py` stress re-infer (needs the FormSpace venv from `START_HERE.txt`).
- Earth Simulator tile paint (other agent). Task 14 GeoJSON attach contract only.
- Official 1–5 Army rubric, 187 deploy, GitHub publish — unchanged, not done.

RJ remains CFO. Mycosoft is **pursuing** CMMC L2 — not claiming compliant. UNCLASSIFIED commercial.

## Lessons

The Codex handoff suggested `/natureos/itdx`. Morgan’s 08 Sep override is execution authority for the **surface**. Codex’s later overlay plan is execution authority for the **Earth layer**. Honesty rules still apply — do not invent official COP, Army geometry, or 1–5 scores. The 09 Sep math contract is proven on the **8766 recorded FormSpace path** before Weka; a green local observatory is not a loaded NLM or a Fusarium-gateway result.
