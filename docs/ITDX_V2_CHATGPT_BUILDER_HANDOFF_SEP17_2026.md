# ITDX v2.0 — ChatGPT software-builder handoff — 17 Sep 2026

**Date:** Thursday 17 September 2026  
**Status:** Integration brief for **software** ChatGPT is implementing **now**. Local demo is scaffolded on **localhost:3010**. Code is on GitHub **`ship/trail-ar-itdx-sep17` @ `d5180f414a07baa637103fbcd4405806eaef15b2`**. **Not deployed.** Instant Deploy **HELD**. Do **not** wait for Cursor e2e.  
**Classification:** UNCLASSIFIED commercial. No CUI. No Army FOUO. No secrets.  
**Audience:** ChatGPT building a **local ITDX 2.0 + Fusarium-integrated demo + slide deck**. Repo access is via the GitHub code map (raw.githubusercontent.com / clone).  
**Companion (slides only):** `docs/ITDX_V2_CHATGPT_SLIDE_HANDOFF_SEP17_2026.md` — use that file for deck copy; **this file is the implementation contract**.  
**GitHub code map (fetch files):** `docs/ITDX_V2_CHATGPT_GITHUB_CODE_MAP_SEP17_2026.md`  
**Owner:** Morgan Rockcoons — CEO / CTO / COO / SAO  
**CFO:** RJ Ricasata — **never COO**  
**CMMC:** Mycosoft is **pursuing** CMMC Level 2 — **not** “CMMC compliant.”

`forecast_p` is **null**. `live` is **false**. **WEKA ≠ NLM.**

Paste the **GitHub code map** first so you can `curl` / clone the real files. Then paste this entire file. Then paste the slide handoff if you need the 12-slide outline.

**Website SHA to fetch:** `d5180f414a07baa637103fbcd4405806eaef15b2` on `ship/trail-ar-itdx-sep17`  
https://github.com/MycosoftLabs/website/commit/d5180f414a07baa637103fbcd4405806eaef15b2

**LIVE vs this SHA:** https://mycosoft.com and sandbox origin are **200** from the last Instant Deploy **~13 Sep 2026**. That is **not** Trail AR v2. This SHA is **IN PROGRESS** on GitHub only.

**Loop-refine (landed in `da00d0c2`, still on tip `d5180f41`):** wrap-hook increments loop; last-good keys persist across wrap; batched POST to `/api/fusarium/bluesight-trail/loop-refine` logs accept/reject IoU. `forecast_p` stays null. Instant Deploy still **HELD**.

---

## 1. Purpose (what you are implementing)

You are writing **software**, not inventing science.

Build / finish a **local Fusarium-integrated ITDX 2.0 demo board** that:

1. Serves on **localhost:3010** only.
2. Shows **dual-mode banners** (ONLINE vs OFFLINE LOCAL WEKA).
3. Calls **existing website BFFs** for connectivity, Sep 14 campaign receipts, and Sep 17 local Java WEKA scores.
4. Shows Trail AR (replay + overlay) **without** designing around a frozen rAF.
5. Stays inside the Fusarium shell (glass, collapsible docks, honesty chips).
6. Ships a **slide deck** using **only** the honesty table in §5.

You are **not** rewriting the WEKA Java CLI, the 149-scheme campaign worker, or NLM. You **call our BFFs**.

---

## 2. Local URLs (3010 only — not deployed)

Dev server: `npm run dev:next-only` in `WEBSITE/website`. Port **3010** only.

| URL | What it is (repo as of 17 Sep 2026) |
|---|---|
| `http://localhost:3010/fusarium/itdx/v2` | **ITDX 2.0 demo board** (`ItdxV2DemoBoard`). Dual-mode banners + WEKA panels + Trail AR iframe. |
| `http://localhost:3010/natureos/bluesight-trail` | **Ungated** Trail AR v1 (`BlueSightTrailLab` `surface="natureos"`). Banner `SIMULATION · live: false`. |
| `http://localhost:3010/natureos/bluesight-trail?embed=1` | Same lab, **player-only** chrome (`embedMode` hides the math-console aside). Prefer this (or mount the component with `embed`) if you embed Trail AR. |
| `http://localhost:3010/fusarium/itdx` | Same Trail AR lab inside Fusarium (`surface="fusarium"`). **May 307 to Google owner login.** Use the ungated NatureOS URL for demos. |
| `http://localhost:3010/api/fusarium/itdx/connectivity` | Dual-mode probe (3.5 s abort). `?force=offline` supported. |
| `http://localhost:3010/api/fusarium/itdx/local-weka` | GET ledger / POST run **local Java** WEKA CLI. Writes Sep 17 scores. |
| `http://localhost:3010/api/fusarium/itdx/local-weka/file?name=scores.json` | Download local CLI artifacts (`scores.csv`, `normalize_fixture_numeric_nominal.arff` also allowed). |
| `http://localhost:3010/api/fusarium/bluesight-trail/weka-campaign` | Sep 14 campaign status (includes `mode` / `banner`). POST starts/resumes the **existing** Python runner. |
| `http://localhost:3010/api/fusarium/bluesight-trail/weka-campaign/file?name=status.json` | Allowed: `results.jsonl`, `results.csv`, `correlation.json`, `arff_inventory.json`, `status.json`, `progress.json`, `datasets.json`, `worker_stdout.log`, `coverage.json`. |
| `http://localhost:3010/api/fusarium/bluesight-trail/nlm` | NLM honesty. **Always call** (ONLINE and `?force=offline`). LAN MAS `192.168.0.188:8001/api/nlm`. `forecast_p` null = **FORECAST_ABSTAIN**, not unbound. |
| `http://localhost:3010/api/fusarium/bluesight-trail/weka` | Trail session ARFF export / Instances smoke. **Not** the campaign. Do not treat as F1. |

**Not deployed** to sandbox / mycosoft.com from this pass. No Instant Deploy.

LAN backends (never hardcode in client components — BFFs already use env):

- MAS `http://192.168.0.188:8001` — `GET /health` decides **WEKA/ONLINE mode**. Degraded collectors still count as bound.
- MAS NLM `GET /api/nlm/health` — **independent of WAN**. LAN 192.168.0.x is not “unbound.”
- MINDEX `http://192.168.0.189:8000` — `GET /health` shown separately; empty catalogs stay empty.

### Why the UI said UNBOUND (17 Sep ~13:40)

A sibling gated the v2 NLM fetch on `mode === "ONLINE"`. `?force=offline` (or a failed MAS `/health` probe) skipped `/api/fusarium/bluesight-trail/nlm` and painted **UNBOUND**. MAS NLM on 188 was already healthy: `model_loaded: true`, weights SHA `0c5fb815…`, `forecast_qualified: false`, `forecast_p: null`. Null p is **ABSTAIN / AVANI PAUSE**, not “NLM missing.” **WEKA ≠ NLM.**

Three chips (do not collapse):

| Chip | Meaning | Red? |
|---|---|---|
| `WAN_DOWN` | `?force=offline` / `ITDX_FORCE_OFFLINE=1` (demo WAN isolation). LAN may still be up. | No |
| `MAS_NLM_DOWN` | `GET /api/nlm/health` failed. **This** is “NLM not running.” | Yes |
| `FORECAST_ABSTAIN` | Service answered; `forecast_p` is null; AVANI PAUSE. | No — show **NLM ONLINE / weights loaded** |

---

## 3. Dual-mode (must be in the product)

Source of truth: `WEBSITE/website/lib/fusarium/itdx/connectivity.ts`  
`CONNECTIVITY_TIMEOUT_MS = 3500`. Probes **abort at 3.5 s**. Do **not** hang 45 s.

The v2 board copy currently says “probe ≤ 1.5s” — **that string is wrong**. Use **3.5 s**.

### How the software chooses

1. Parallel fetch MAS `/health` and MINDEX `/health` with a **3500 ms** `AbortController`.
2. If `ITDX_FORCE_OFFLINE=1` or `?force=offline` → skip probes → **OFFLINE_LOCAL_WEKA**.
3. Else if MAS probe `ok` (HTTP 200) → **ONLINE**. Degraded collectors still count as bound.
4. Else (fail / timeout / network) → **OFFLINE_LOCAL_WEKA**.
5. MINDEX is **display only**. It does **not** flip the mode.
6. Trail AR / on-disk campaign JSON always render.
7. NLM fetch (`/api/fusarium/bluesight-trail/nlm`) runs **in both modes**. `force=offline` only flips WEKA/WAN. Still probe LAN `/api/nlm/health`.
8. “Run local WEKA CLI” always talks to **local Java**, both modes.

### Banners (required, stacked)

**Always (top rail):**

`LOCAL DEMO · SYNTHETIC EXERCISE · live: false · forecast_p: null`

**Second rail:**

| Mode | Banner text |
|---|---|
| ONLINE | `ONLINE (backends bound)` |
| OFFLINE | `OFFLINE LOCAL WEKA` |

Plus chips: `MAS bound|unbound` · `MINDEX bound|unbound` · `WAN_DOWN|WAN_UNPROBED` · `NLM ONLINE / weights loaded` (or `MAS_NLM_DOWN`) · `FORECAST_ABSTAIN` · `WEKA ≠ NLM`.

### ONLINE (MAS returns 200 within 3.5 s)

Uses the live backend **already wired**:

- MAS orchestrator + NLM `/api/nlm/*` (via the NLM BFF)
- MINDEX catalogs (empty stays empty)
- Website BFFs on 3010
- Local Java WEKA **plus** NLM bind when loaded

Still: **LOCAL DEMO · SYNTHETIC EXERCISE · live: false** for sim sensors.

### OFFLINE LOCAL WEKA (WAN isolated or MAS `/health` failed)

WEKA score capability **remains**. **NLM is not turned off.** If 188 `/api/nlm/health` answers, the chip is **NLM ONLINE / weights loaded** with `forecast_p: null`.

Full WEKA score capability **remains**:

- Portable Temurin 17: `website/.data/weka-runtime/jdk-17.0.20.1+1-jre/bin/java.exe`
- `weka.jar` from the Algorithm Lab kit `formspace/weka/deps/` (plus bounce / MTJ / java-cup on classpath)
- Campaign ARFFs + receipts: `website/.data/weka-campaign/SEP14_2026/`
- Trail ARFFs: `website/.data/trail-ar/weka/trail-ar-session.arff` and `trail-ar-predictions.arff`
- Focused CLI ledger: `website/.data/weka-campaign/SEP17_2026_LOCAL/`

Does **not** require MAS or MINDEX. Does **not** invent F1. `live: false`. `forecast_p: null`.

---

## 4. Score paths (gitignored; real Java stdout)

| Path | What |
|---|---|
| `WEBSITE/website/.data/weka-campaign/SEP17_2026_LOCAL/` | **17 Sep local CLI.** `scores.json`, `scores.csv`, stdout sidecars, `normalize_fixture_numeric_nominal.arff`, numeric trail subsample. |
| `WEBSITE/website/.data/weka-campaign/SEP14_2026/` | **14 Sep campaign receipts.** `status.json`, `coverage.json`, `results.jsonl`, `results.csv`, `correlation.json`, `arff_inventory.json`, `receipts/`, `filtered/`, `fixtures/`. |
| `WEBSITE/website/.data/trail-ar/weka/` | Growing session + prediction ARFFs. `actual` and `p` are `?` on predictions. |
| `WEBSITE/website/.data/weka-runtime/` | Portable JRE + MTJ libs. Not committed. |

Campaign run narrative: MAS `docs/WEKA_ITDX_CAMPAIGN_RUN_SEP14_2026.md`.

---

## 5. Honesty table (copy onto slides and UI)

Source: `website/.data/weka-campaign/SEP14_2026/` + `docs/WEKA_ITDX_CAMPAIGN_RUN_SEP14_2026.md`.  
If a figure is **not** in this table, **do not print it**.

| Claim | Number | Label required |
|---|---|---|
| ARFFs inventoried | **10** found | Campaign ZIP itself has zero ARFFs |
| ARFF views executed | **9** | One inventoried view was not a worker view |
| Schemes with compatibility receipts | **149 / 149** | Compatibility only (56 classify / 85 filter / 8 cluster) |
| Scientific readiness | **false** | Write the word false |
| Ledger jobs | **1052** | Not 4,760 planned matrix cells |
| `RAN_*` | **821** (710 compatibility + 111 scientific-lane / representation) | Status `ran` field |
| Failed or timeout | **87** in status.json (run doc: 86 FAILED + 1 TIMEOUT) | Not “models failed” |
| Blocked / inapplicable | **144** status (`blocked_or_inapplicable`); run doc: 88 INAPPLICABLE + 56 BLOCKED_DATA | Trail unlabeled |
| `forecast_p` | **null** | Every receipt |
| Trail F1 / Brier / confusion | **not yet scored** | `actual` and `p` are `?` on prediction ARFF |
| Trail clusters ARI/NMI | **not yet scored** | No reference partition |
| J48 on `fixture_numeric_nominal` | F1 **0.975** / **97.5%** | **SYNTHETIC** fixture |
| J48 on `task12_raw_train` | F1 **0.99922** / **99.921875%** | **SYNTHETIC** archived Task 12 |
| J48 on `task12_coordinates` | F1 **0.99875** / **99.875%** | **SYNTHETIC** FormSpace coords — not NLM |
| Many fixture / Task 12 rows | F1 **1.000** | **SYNTHETIC only** — never “achieved accuracy” |
| Date fixture (many classifiers) | about **0.45–0.62** F1 | **SYNTHETIC**; timestamps were not a class signal |
| DecisionStump on date fixture | F1 **0.287** / **27.5%** | **SYNTHETIC**; WEKA can sit near/below chance |
| NLM weights SHA-256 (ONLINE bind) | `0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2` | Real file on MAS when bound; **not** a WEKA score |
| NLM params | **25,728** / 47 tensors / `bound_to_ollama: false` | Algorithm replay; `forecast_qualified: false` |

One sentence for WEKA: **“149/149 schemes produced compatibility receipts; scientific readiness is false; measured F1 exists only on synthetic fixtures and archived Task 12.”**

### 17 Sep local CLI (`SEP17_2026_LOCAL/scores.json`) — real Java weka.jar stdout

| Job | Number | Label |
|---|---|---|
| ZeroR on `fixture_numeric_nominal` | **57.5%** correct; weighted F1 **null** (candidate F-Measure is `?`) | **SYNTHETIC** |
| J48 on same fixture (10-fold CV) | F1 **0.975** / **97.5%** | **SYNTHETIC** · reconfirms Sep 14 |
| J48 on `trail-ar-predictions.arff` | scored instances **0**; ignored unknown class **489222** | **NOT_YET_SCORED** |
| Normalize filter on fixture | wrote `normalize_fixture_numeric_nominal.arff` | **SYNTHETIC** · filters have no F1 |
| SimpleKMeans on trail subsample 2000 (after RemoveType string) | 3 clusters **848 / 796 / 356**; WCSS **1860.8336391374733** | unsupervised; ARI/NMI **not yet scored** |

Cite as **SYNTHETIC or NOT_YET_SCORED · real WEKA CLI · 17 Sep local**. Not trail skill.

### Forbidden (UI, slides, JSON, comments)

- “High accuracy” as an achieved field metric
- **0.85** or **0.5** as NLM / travel probability / skill
- Trail AR F1 scored
- WEKA = NLM
- “CMMC compliant” / “CMMC L2 certified”
- RJ Ricasata as **COO** (he is **CFO**)
- Live COP / live sensors when the banner is `live: false`
- Brain™ marketing copy
- CUI, FOUO, or real Army intel
- Fort Stewart as a live operational AO (SYNTHETIC EXERCISE only if named)
- That the **4,760-cell** planned matrix was executed (those cells stay **PLANNED**)
- Screenshots proving overlay contrast as “done” (visibility pass **in flight**)
- Instant Deploy / production ship from this 17 Sep pass
- Inventing `forecast_p`

If someone asks for “high accuracy” slides: **prove the pipeline; do not put unmeasured F1 on slides; label synthetic separately; next step is a labeled hike vs ZeroR.**

---

## 6. Trail AR (two clocks, contrast halo, `__trailOverlay`)

Ungated page: `/natureos/bluesight-trail`. Component: `components/fusarium/bluesight-trail-lab.tsx`.  
HUD: `lib/fusarium/bluesight/trail-ar-hud.ts`. Contact: `lib/fusarium/bluesight/trail-contact.ts`.

### Two clocks (do not collapse)

| Clock | What | Constant |
|---|---|---|
| **Objects / contours / flow** | `requestAnimationFrame` paint loop. Detect + draw every frame. | `__trailOverlay.clocks.objects = "raf"` |
| **Steps / footholds** | New GREEN/CYAN/RED contact placement + score | `STEP_PLACE_MS = 280` |

Also show **source video fps vs overlay Hz** on the player chrome:

- Source: `PXL_SOURCE_FPS = 30`, `PXL_NATIVE_FRAMES = 422`, `PXL_DURATION_S = 14.0691`
- Overlay target: `OVERLAY_HZ_TARGET = 120`
- Clip: `PXL_20260913_211840104.mp4` via `/fusarium/bluesight-lab/test-pxl-20260913.mp4` or `/api/fusarium/bluesight-trail/video`

Foothold / contact pips ≠ object perimeters. Do not merge them into one “accuracy.”

### Contrast halo (in flight — do not claim proven)

Near-black under-stroke so bright ink reads on sunlit dirt and shade:

- `HALO_INK = rgba(0,0,0,0.94)`
- Default halo width **3.8**; path halo **6.0**; path ink `#ffe600`
- `strokePoly` paints halo first, then color stroke
- Labels use `strokeText` with the same halo ink

Visibility / contrast pass is **in flight on 3010**. Do not invent “high contrast proven” screenshots.

### Debug hook (do not hide)

Each rAF tick writes `window.__trailOverlay`:

```json
{
  "t": 0.0,
  "canvas": { "w": 0, "h": 0, "cssW": 0, "cssH": 0, "dpr": 1 },
  "clocks": { "objects": "raf", "steps_place_ms": 280, "instance_cap": 5 },
  "nContours": 0,
  "contours": [{ "id": "…", "kind": "tree|rock|bush|plant|fungus", "cx": 0, "cy": 0, "n": 0 }],
  "corridor": { "n": 0, "left0": [0, 0], "right0": [0, 0] },
  "steps": [{ "id": "…", "tone": "GREEN|CYAN|RED", "cx": 0, "cy": 0, "xCode": null }]
}
```

`INSTANCE_CAP = 5`. Overlay also writes `window.__trailTick = { n, cw, ch }`.

Banner on the player: `{mode} · live: false · SYNTHETIC EXERCISE · forecast_p: null`.  
Mode toggle SIMULATION vs REAL: REAL paints “no live BFF bind · empty stays empty” — it does **not** invent tracks.

Overhead map is present (ABOVE chip + red corridor photo + green progress). Glass rail / math console lives on the ungated page aside.

---

## 7. Known defects in flight (be honest — do not design around them)

Cursor e2e is fixing these **now**. Keep building the demo board and deck. **Do not wait.**

1. **v2 may not embed Trail AR.**  
   `/fusarium/itdx/v2` currently iframes `/natureos/bluesight-trail` **without** `?embed=1` and **without** mounting `<BlueSightTrailLab embed />`. That nests a **full-page** Trail AR (banner + player + math console) inside the v2 board. The lab **does** support `embed` / `?embed=1` (hides the aside, `data-testid="bluesight-trail-embed"`). Prefer **component embed** or `?embed=1`. Do not assume the iframe is a finished product shot.

2. **Ungated trail may freeze after Play.**  
   Observed: overlay / rAF can **stop updating** after play on `/natureos/bluesight-trail`. Cursor e2e is repairing the loop (current code already `try/catch` + `finally { requestAnimationFrame(tick) }` so a single detect/paint throw should not kill the loop). **Do not design around a frozen rAF.** Assume objects keep painting on rAF and steps keep placing on 280 ms. If you add UI, do not gate animation on a one-shot timer.

3. **`/fusarium/itdx` may 307 to Google owner login.** Use `/natureos/bluesight-trail` for ungated replay.

4. **Fusarium scenario-sim BFF is not in this working tree.** Demo clock = Trail AR replay clock (source fps vs overlay Hz). Civil / non-US Part B is later.

5. **Overlay visibility / contrast is in flight.** Halo code exists; do not claim a finished contrast proof.

6. **Probe copy drift.** v2 board now says **3.5 s** to match `CONNECTIVITY_TIMEOUT_MS`.

7. **Scientific readiness is false.** Trail F1 not yet scored. Planned 4,760 filter×classifier cells not run.

8. **NLM UNBOUND was a website label bug. Fix is ON GITHUB at `d5180f41` (PR #322, not merged, not Instant Deployed).** MAS 188 `/api/nlm/health` was already up. Do not treat `forecast_p: null` as missing NLM. Offline WEKA ≠ NLM off.

---

## 8. What already exists vs what you should build

### Already in the repo (do not duplicate)

| Piece | Where |
|---|---|
| Dual-mode probe | `lib/fusarium/itdx/connectivity.ts` + `GET /api/fusarium/itdx/connectivity` |
| Local Java WEKA CLI + ledger | `lib/fusarium/itdx/local-weka.ts` + `POST /api/fusarium/itdx/local-weka` |
| Runtime paths (JRE, jar, ARFFs) | `lib/fusarium/itdx/runtime-paths.ts` |
| Sep 14 campaign BFF + Python worker spawn | `GET/POST /api/fusarium/bluesight-trail/weka-campaign` → `MAS/scripts/itdx_weka_campaign/run_campaign.py` |
| Campaign / local panels | `WekaCampaignPanel`, `LocalWekaPanel` |
| v2 board scaffold | `app/fusarium/(dashboard)/itdx/v2/page.tsx` → `ItdxV2DemoBoard` |
| Trail AR lab | `BlueSightTrailLab` + `lib/fusarium/bluesight/*` |
| NLM honesty BFF | `GET /api/fusarium/bluesight-trail/nlm` |
| Trail session ARFF export | `POST /api/fusarium/bluesight-trail/weka` |
| Glass dock | `trail-glass-dock.tsx` |

### What ChatGPT should build (software)

- Fusarium-shell polish on `/fusarium/itdx/v2`: banners, docks, honest empty states (no mock rows).
- **Correct Trail AR embed:** mount `<BlueSightTrailLab embed surface="natureos" />` **or** iframe ` /natureos/bluesight-trail?embed=1`. Do not nest the full ungated page if you can avoid it.
- Keep calling **our** BFFs for WEKA I/O. Buttons already exist: “Run local WEKA CLI”, “Run / resume campaign”, file downloads.
- Dual-mode: re-probe via `GET /api/fusarium/itdx/connectivity` (v2 already polls every 20 s).
- Slide deck from the **slide** handoff + **this** honesty table.
- Optional: force-offline control (`?force=offline` or a button that hits the same query).

### What ChatGPT must not build

- A second WEKA Java runner / classpath / subprocess.
- A second 149-scheme campaign worker.
- Stub `forecast_p`, 0.85, 0.5, or trail F1.
- A live COP, Instant Deploy, marketing hero, or CUI surface.
- A frozen-overlay “workaround” that replaces rAF with a still image.

---

## 9. Copy-paste BFF contracts (as implemented)

All envelopes include `live: false` and `forecast_p: null`. No mock rows.

### `GET /api/fusarium/itdx/connectivity`

Query: `?force=offline` (optional).

```json
{
  "schema": "itdx-connectivity/v1",
  "live": false,
  "forecast_p": null,
  "weka_is_not_nlm": true,
  "mode": "ONLINE",
  "banner": "ONLINE (backends bound)",
  "forced_offline": false,
  "wan_status": "WAN_UNPROBED",
  "forecast_status": "FORECAST_ABSTAIN",
  "nlm": {
    "url": "http://192.168.0.188:8001/api/nlm/health",
    "ok": true,
    "bind": "BOUND",
    "nlm_status": "NLM_ONLINE",
    "model_loaded": true,
    "weights_sha256": "0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2",
    "forecast_status": "FORECAST_ABSTAIN"
  },
  "mas": { "url": "http://192.168.0.188:8001/health", "ok": true, "status": 200, "ms": 40, "error": null },
  "mindex": { "url": "http://192.168.0.189:8000/health", "ok": true, "status": 200, "ms": 40, "error": null },
  "probe_timeout_ms": 3500
}
```

`mode` is `"OFFLINE_LOCAL_WEKA"` when MAS `/health` is not ok or `?force=offline`. Forced offline sets `wan_status: "WAN_DOWN"` but **still probes LAN** MAS / MINDEX / NLM. Do not paint NLM UNBOUND because WEKA is offline.

### `GET /api/fusarium/itdx/local-weka`

```json
{
  "live": false,
  "forecast_p": null,
  "weka_is_not_nlm": true,
  "scientific_readiness_established": false,
  "trail_score": "not yet scored",
  "result_dir": "<website>/.data/weka-campaign/SEP17_2026_LOCAL",
  "downloads": {
    "scores_json": "/api/fusarium/itdx/local-weka/file?name=scores.json",
    "scores_csv": "/api/fusarium/itdx/local-weka/file?name=scores.csv"
  },
  "mode": "OFFLINE_LOCAL_WEKA",
  "banner": "OFFLINE LOCAL WEKA",
  "connectivity": { "schema": "itdx-connectivity/v1" },
  "java": "<portable java.exe or null>",
  "weka_jar": "<weka.jar or null>",
  "campaign_on_disk": {
    "campaign_dir": "<website>/.data/weka-campaign/SEP14_2026",
    "status_present": true,
    "coverage_present": true,
    "results_csv": true,
    "results_jsonl": true,
    "scientific_readiness_established": false,
    "trail_score": "not yet scored",
    "coverage": {}
  },
  "local_scores": {
    "schema": "itdx-local-weka/v1",
    "live": false,
    "forecast_p": null,
    "weka_is_not_nlm": true,
    "scientific_readiness_established": false,
    "trail_score": "not yet scored",
    "written_at": "2026-09-17T20:25:00.000Z",
    "java": "…",
    "weka_jar": "…",
    "result_dir": "…/SEP17_2026_LOCAL",
    "jobs": [
      {
        "id": "zeror_fixture_numeric_nominal",
        "family": "classifier",
        "scheme": "weka.classifiers.rules.ZeroR",
        "dataset_id": "fixture_numeric_nominal",
        "honesty": "SYNTHETIC",
        "ran": true,
        "percent_correct": 57.5,
        "f1_weighted": null,
        "detail": "…"
      }
    ]
  }
}
```

`local_scores` is `null` until the first successful POST.

### `POST /api/fusarium/itdx/local-weka`

No body required. Runs **five** real CLI jobs (ZeroR fixture, J48 fixture, J48 trail predictions, Normalize filter, SimpleKMeans trail). Writes `scores.json` + `scores.csv`.

**200** — same envelope plus `"accepted": true` and a fresh `local_scores` ledger.

**503** — Java or `weka.jar` missing:

```json
{
  "accepted": false,
  "error": "Local WEKA runtime missing (portable Java or weka.jar)",
  "live": false,
  "forecast_p": null,
  "mode": "OFFLINE_LOCAL_WEKA",
  "banner": "OFFLINE LOCAL WEKA"
}
```

### `GET /api/fusarium/itdx/local-weka/file?name=`

Allowed: `scores.json` | `scores.csv` | `normalize_fixture_numeric_nominal.arff`.  
400 if not allowed. 404 if not yet written. Always `forecast_p: null` on errors.

### `GET /api/fusarium/bluesight-trail/weka-campaign`

Spreads on-disk `latest.json` or `SEP14_2026/status.json`, then **overrides**:

```json
{
  "forecast_p": null,
  "live": false,
  "weka_is_not_nlm": true,
  "mode": "ONLINE",
  "banner": "ONLINE (backends bound)",
  "connectivity": { "schema": "itdx-connectivity/v1" },
  "itdx_url": "/fusarium/itdx",
  "itdx_v2_url": "/fusarium/itdx/v2",
  "local_weka": "/api/fusarium/itdx/local-weka",
  "downloads": {
    "results_jsonl": "/api/fusarium/bluesight-trail/weka-campaign/file?name=results.jsonl",
    "results_csv": "/api/fusarium/bluesight-trail/weka-campaign/file?name=results.csv",
    "correlation": "/api/fusarium/bluesight-trail/weka-campaign/file?name=correlation.json",
    "inventory": "/api/fusarium/bluesight-trail/weka-campaign/file?name=arff_inventory.json",
    "status": "/api/fusarium/bluesight-trail/weka-campaign/file?name=status.json",
    "coverage": "/api/fusarium/bluesight-trail/weka-campaign/file?name=coverage.json"
  }
}
```

If no status file yet:

```json
{
  "schema": "itdx-weka-campaign-status/v1",
  "state": "NOT_STARTED",
  "forecast_p": null,
  "live": false,
  "trail_score": "not yet scored",
  "result_dir": "<website>/.data/weka-campaign/SEP14_2026"
}
```

Typical live fields from a finished Sep 14 `status.json` (plus the overrides above): `state`, `phase`, `arffs_found`, `arffs_executed`, `correlation.ran`, `correlation.failed_or_timeout`, `correlation.blocked_or_inapplicable`, `correlation.jobs_total`, `correlation.accounted_entries`, `correlation.required_entries` (149), `correlation.schemes_executed.{classifier,filter,clusterer}`, `correlation.honesty.trail_score`, `correlation.improvement_loop`.

### `POST /api/fusarium/bluesight-trail/weka-campaign`

Spawns existing `run_campaign.py --out SEP14_2026`. **Do not reimplement.**

If already `state === "RUNNING"`:

```json
{ "accepted": false, "reason": "already running", "forecast_p": null }
```

Else:

```json
{
  "accepted": true,
  "state": "RUNNING",
  "pid": 12345,
  "forecast_p": null,
  "result_dir": "<website>/.data/weka-campaign/SEP14_2026",
  "weka_is_not_nlm": true
}
```

500 if the Python runner is missing: `{ "error": "Campaign runner not found", "forecast_p": null }`.

### `GET /api/fusarium/bluesight-trail/nlm` (both modes — LAN MAS)

How ChatGPT should call NLM:

1. Always `GET /api/fusarium/bluesight-trail/nlm` from the 3010 BFF (do not talk to 188 from the browser).
2. The BFF proxies `http://192.168.0.188:8001/api/nlm/health|runtime|weights`.
3. If `nlm_status === "NLM_ONLINE"` and `model_loaded`, chip = **NLM ONLINE / weights loaded**.
4. If the health call fails, chip = **MAS_NLM_DOWN** (only then “NLM not running”).
5. `forecast_p` stays **null**. That is `FORECAST_ABSTAIN` / AVANI PAUSE. Never stub 0.85 / 0.5.

```json
{
  "live": false,
  "forecast_p": null,
  "forecast_status": "FORECAST_ABSTAIN",
  "bound_to_ollama": false,
  "bind": "BOUND",
  "nlm_status": "NLM_ONLINE",
  "weight_count": 3,
  "weights_sha256": "0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2",
  "belief": {
    "model_loaded": true,
    "abstained": true,
    "weights_sha256": "0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2",
    "parameter_count": 25728
  }
}
```

Do **not** download new weights (188 disk was fail-closed ~89%). Inventory the three on-disk artifacts only.

### `GET /api/fusarium/bluesight-trail/weka`

Status only (java / jar / `trail_score: "not yet scored"`).  
`POST` expects `{ "schema": "bluesight-trail-ar-session/v1", … }` and writes the session ARFF. Smoke-loads Instances. **No classifier trained. No accuracy claimed.**

---

## 10. Fusarium shell notes

- v2 board: dark `#031018`, amber **LOCAL DEMO** rail, cyan **ONLINE** rail / muted **OFFLINE** rail, `TRAIL_GLASS_PANEL` + `TrailGlassSection` collapsibles (44 px triggers).
- Dock ids already: `trail`, `nlm`, `wekaCampaign`, `localWeka`, `clock`.
- Fusarium ITDX lab reuses the same Trail AR component. Prefer ungated NatureOS for embed.
- Fort Stewart AO, if mentioned: **SYNTHETIC EXERCISE** only.
- No mock data. Empty = empty. Fail = error text, not fixture rows.

---

## 11. People / locks

| Person | Role |
|---|---|
| Morgan Rockcoons | CEO, CTO, COO, SAO. Sole GitHub approver. |
| RJ Ricasata | **CFO**. MYCA 2nd Key. Never COO. |

CUI lives only in PreVeil. This brief, the demo, and the public site stay unclassified.  
**No Instant Deploy. No git reset.** Local 3010 only.

---

## 12. Operator pointers (not for slides)

- This brief: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\docs\ITDX_V2_CHATGPT_BUILDER_HANDOFF_SEP17_2026.md`
- GitHub code map: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\docs\ITDX_V2_CHATGPT_GITHUB_CODE_MAP_SEP17_2026.md`
- Mirror: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\docs\ITDX_V2_CHATGPT_BUILDER_HANDOFF_SEP17_2026.md`
- Slides: `docs/ITDX_V2_CHATGPT_SLIDE_HANDOFF_SEP17_2026.md`
- Dual-mode note: `WEBSITE/website/docs/ITDX_V2_LOCAL_DEMO_DUAL_MODE_SEP17_2026.md` (on ship SHA `d5180f41`)
- Force offline: `/api/fusarium/itdx/connectivity?force=offline`

**Deploy status: not deployed. Instant Deploy HELD.** Website branch `ship/trail-ar-itdx-sep17` @ `d5180f414a07baa637103fbcd4405806eaef15b2`.
