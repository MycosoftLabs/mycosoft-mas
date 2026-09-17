# ITDX v2 — ChatGPT EVERYTHING pack — 17 Sep 2026

```
ITDX v2 EVERYTHING — 17 Sep 2026. Instant Deploy HELD. Do not merge website PR #322.
Website ship/trail-ar-itdx-sep17 @ d5180f414a07baa637103fbcd4405806eaef15b2 (loop-refine WORKS on da00d0c2 + NLM bind on tip; do not merge #322).
mycosoft.com / sandbox / 187:3000 HTTP 200 = last Instant Deploy ~13 Sep — NOT Trail AR v2.
force=offline ≠ NLM off. Always GET LAN 192.168.0.188:8001/api/nlm (health+runtime). model loaded ≠ forecast issued.
forecast_p is null. FORECAST_ABSTAIN. WEKA ≠ NLM. Never print 0.85. RJ Ricasata is CFO. No CUI.
Cursor campaign receipts + trail ARFF labels are NOT in GitHub (website .gitignore `.data/`).
Hess package = fresh POST /api/fusarium/itdx/local-weka only — do not copy Cursor `.data` receipts.
Three slides / four tasks: FormSpace equations, NLM abstain, WEKA 149, Trail AR two-clock + loop-refine.
```

**Date:** Thursday 17 September 2026  
**Status:** Paste-complete pack for ChatGPT. Inspect pinned GitHub, reconcile with the local app, revise a **three-slide** deck. **Not deployed. Do not merge. Instant Deploy HELD.**  
**Classification:** UNCLASSIFIED commercial. No CUI. No Army FOUO PDFs. No secrets.  
**Owner:** Morgan Rockcoons — CEO / CTO / COO / SAO  
**CFO:** RJ Ricasata — **never COO**  
**CMMC:** Mycosoft is **pursuing** CMMC Level 2 — **not** “CMMC compliant.”

`forecast_p` is **null**. `live` is **false**. `forecast_qualified` is **false**. **WEKA ≠ NLM.** Never stub **0.85**.

This file **supersedes** needing the four earlier Sep 17 ChatGPT briefs for a first paste. Those remain implementation companions (builder / slides / code map / FINAL). One error in the older slide brief is **void**: “NLM fetch runs only in ONLINE mode” is **false**. SHA `d5180f41` probes LAN `/api/nlm` health+runtime under `?force=offline` and chips **NLM ONLINE / weights loaded** vs **MAS_NLM_DOWN** vs **FORECAST_ABSTAIN**.

---

## 0. What you must do (ChatGPT)

1. Fetch the **pinned GitHub SHAs** in §1 (raw.githubusercontent.com). Do **not** treat `main` or mycosoft.com as v2.
2. Reconcile those files with **local 3010** if you have the app (`/fusarium/itdx/v2`, `/natureos/bluesight-trail`). GitHub wins for source; localhost wins for “what this PC is serving.”
3. Revise a **three-slide** deck that covers the **four tasks** in §3 (equations, measured results, full system flow).
4. Keep **deployment hold**. Do not say v2 is live. Do not merge PR #322.
5. Split every number: **Cursor-reported** vs **reproducible on this PC** vs **Label** (SYNTHETIC / NOT_YET_SCORED / measured). See §4–§5.

---

## 1. Repos / SHAs / PRs

### Website (implement / inspect this)

| Field | Value |
|---|---|
| Org/repo | [MycosoftLabs/website](https://github.com/MycosoftLabs/website) |
| Branch | `ship/trail-ar-itdx-sep17` |
| Full SHA | `d5180f414a07baa637103fbcd4405806eaef15b2` |
| `git log -1` | `fix(itdx): keep LAN NLM bind when WEKA is force=offline.` — 17 Sep 2026 |
| Commits after `d5180f41` | **None** (origin `ship/trail-ar-itdx-sep17` as of 17 Sep ~14:15 Pacific) |
| Prior commits | `da00d0c2` loop-refine IoU · `20bf2b06` LAN NLM bind · `fcec0e50` Trail AR + dual-mode |
| PR | **[#322](https://github.com/MycosoftLabs/website/pull/322)** — “Ship Trail AR / ITDX 2.0 dual-mode (Instant Deploy HELD)” — **OPEN. Do not merge.** |
| Tree | https://github.com/MycosoftLabs/website/tree/d5180f414a07baa637103fbcd4405806eaef15b2 |
| Commit | https://github.com/MycosoftLabs/website/commit/d5180f414a07baa637103fbcd4405806eaef15b2 |

Raw prefix:

```text
https://raw.githubusercontent.com/MycosoftLabs/website/d5180f414a07baa637103fbcd4405806eaef15b2/<path>
```

Must-fetch (parentheses in path are literal; encode as `%28dashboard%29` if a client breaks):

| Path | Why |
|---|---|
| `lib/fusarium/itdx/connectivity.ts` | Dual-mode; **always** `GET /api/nlm/health` + `/api/nlm/runtime` even when `force=offline` |
| `lib/fusarium/itdx/lan-json.ts` | BFF Node `http`/`https` to 188 (bypasses patched fetch) |
| `app/api/fusarium/itdx/connectivity/route.ts` | `?force=offline` → `probeItdxConnectivity(true)` |
| `components/fusarium/itdx-v2-demo-board.tsx` | v2 chips: **NLM ONLINE / weights loaded** · always fetches `/nlm` |
| `lib/fusarium/bluesight/formspace-nlm.ts` | Equations + `nlmServiceChip` (**ONLINE / weights loaded** vs **MAS_NLM_DOWN**) |
| `lib/fusarium/bluesight/loop-refine.ts` | Loop-refine **works**: wrap increments loop; accept/reject IoU logged |
| `lib/fusarium/itdx/local-weka.ts` | Fresh Hess-reproducible CLI jobs |
| `app/api/fusarium/bluesight-trail/nlm/route.ts` | LAN NLM BFF (Node `http` to 188) |
| `app/api/fusarium/bluesight-trail/math-log/route.ts` | Cap math-log reads at 8 MB; do not ingest the 512 MB dump |
| `app/api/fusarium/itdx/local-weka/route.ts` | GET ledger / POST run |
| `app/api/fusarium/bluesight-trail/loop-refine/route.ts` | JSONL append |
| `app/fusarium/%28dashboard%29/itdx/v2/page.tsx` | ITDX 2.0 page |
| `components/fusarium/bluesight-trail-lab.tsx` | Trail AR lab |
| `docs/ITDX_TRAIL_AR_FORMSPACE_NLM_BACKBONE_SEP14_2026.md` | Backbone honesty (PDFs not in repo) |

Working copy `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website` is often on **`fix/launchpad-ingest-bearer-alias`** with **unrelated dirty files**. **Do not git reset.** Fetch **only** SHA `d5180f41`.

### MAS (handoffs + WEKA narrative + this pack)

| Field | Value |
|---|---|
| Org/repo | [MycosoftLabs/mycosoft-mas](https://github.com/MycosoftLabs/mycosoft-mas) |
| PR | **[#156](https://github.com/MycosoftLabs/mycosoft-mas/pull/156)** — “ITDX v2 ChatGPT GitHub code map — 17 Sep 2026” — **OPEN. Do not merge.** |
| PR branch | `docs/itdx-v2-chatgpt-map-from-main` |
| PR head (before this pin) | `dda25a5affea3b826b31b1eb0b1b30b2c3de9763` |
| Sibling docs branch | `docs/itdx-v2-chatgpt-github-map-sep17` |

Code-map raw (PR branch; pin commit after this pack is pushed):

```text
https://raw.githubusercontent.com/MycosoftLabs/mycosoft-mas/docs/itdx-v2-chatgpt-map-from-main/docs/ITDX_V2_CHATGPT_GITHUB_CODE_MAP_SEP17_2026.md
```

This pack (after push):

```text
https://raw.githubusercontent.com/MycosoftLabs/mycosoft-mas/docs/itdx-v2-chatgpt-map-from-main/docs/ITDX_V2_CHATGPT_EVERYTHING_SEP17_2026.md
```

Companion MAS docs (already on PR #156): builder, slide, FINAL, `WEKA_ITDX_CAMPAIGN_RUN_SEP14_2026.md`.

---

## 2. LIVE vs HELD vs LOCAL

| Lane | What | Trail AR v2 / ITDX dual-mode / loop-refine? |
|---|---|---|
| **LIVE** | https://mycosoft.com **200** | **No.** Last Instant Deploy **~13 Sep 2026**. |
| **LIVE** | https://sandbox.mycosoft.com **200** | **No.** Same origin generation. |
| **LIVE** | http://192.168.0.187:3000 **200** | **No.** Sandbox Docker origin. Same rule. |
| **HELD** | Website PR **#322** | Code is on GitHub only. **Do not merge. Do not Instant Deploy.** |
| **LOCAL** | http://localhost:3010 only | **Yes** — if this PC is on the ship SHA / has those files served. |

### LOCAL 3010 URLs

| URL | Role |
|---|---|
| `http://localhost:3010/fusarium/itdx/v2` | ITDX 2.0 board + NLM chips + WEKA + Trail AR |
| `http://localhost:3010/fusarium/itdx/v2?force=offline` | Force WAN-down / OFFLINE LOCAL WEKA **without** turning NLM off |
| `http://localhost:3010/natureos/bluesight-trail` | Ungated Trail AR lab (glass Loop refine) |
| `http://localhost:3010/natureos/bluesight-trail?embed=1` | Player-only embed |
| `http://localhost:3010/fusarium/itdx` | Fusarium lab — **may 307 to Google owner login** |
| `GET /api/fusarium/itdx/connectivity` | Dual-mode probe (3.5 s). `?force=offline` supported |
| `GET /api/fusarium/bluesight-trail/nlm` | LAN NLM honesty — **always call** |
| `GET/POST /api/fusarium/itdx/local-weka` | Fresh local Java WEKA (Hess path) |
| `GET /api/fusarium/itdx/local-weka/file?name=scores.json` | Download fresh ledger |
| `GET/POST /api/fusarium/bluesight-trail/weka-campaign` | Sep 14 campaign BFF (on-disk receipts **gitignored**) |
| `GET/POST /api/fusarium/bluesight-trail/loop-refine` | Loop-refine JSONL |
| `GET /api/fusarium/bluesight-trail/weka` | Session ARFF export — **not F1** |
| `GET /api/fusarium/bluesight-trail/video` | Replay clip |

LAN backends (BFFs use env; defaults):

- MAS `http://192.168.0.188:8001` — `/health` flips WEKA **mode**; `/api/nlm/health` + `/api/nlm/runtime` are **independent**
- MINDEX `http://192.168.0.189:8000` — display only; empty stays empty

---

## 3. Four tasks the three slides must cover

Pack **four tasks** into **three slides**:

| Slide | Must contain |
|---|---|
| **1 — Equations** | Task 1 FormSpace + Task 2 NLM/AVANI (+ loop-refine IoU from Task 4) |
| **2 — Measured results** | Task 3 WEKA 149 + honesty table (§4). No “high accuracy.” |
| **3 — Full system flow** | Task 4 Trail AR two clocks + loop-refine + the one-page pipeline (§7) |

Do **not** invent equations. Use only symbols already encoded in-repo (`formspace-nlm.ts` `PAPER_FORMULA_MAP`, MAS FormSpace docs). Army FOUO PDFs were **not** copied into git. The Sep 14 backbone note says five Mycosoft ITDX papers were shown to Dr. Hess; **PDFs are not in this repo**. If a derivation is not in the files below, write “see handoff — not in-repo” and **stop**.

### Task 1 — FormSpace \(F_t\), \(\ell_t\), \(u_t\in\mathbb{R}^{24}\)

**In-repo source:** website `lib/fusarium/bluesight/formspace-nlm.ts` (`PAPER_FORMULA_MAP`, `FormSpaceRecord`, `elapsedFeature`). MAS: `docs/FORMSPACE_NLM_REPOSITORY_MAP_SEP09_2026.md`, `docs/FORMSPACE_NLM_IMPLEMENTATION_STATUS_SEP09_2026.md`. Website: `docs/ITDX_TRAIL_AR_FORMSPACE_NLM_BACKBONE_SEP14_2026.md`.

White-paper symbols **as encoded in code** (not reconstructed from missing PDFs):

\[
F_t=(s,k,f_t,c_t,U_t,E_t)
\]

\[
\ell_t=\frac{\log(1+\min(\delta,86400))}{\log(1+86400)}
\]

\[
u_t=[v;m;\ell]\in\mathbb{R}^{24}
\]

**What the PXL Trail AR demo actually computes (honest):**

- Terrain chart is **4-D ADE20K appearance** \(f_t=(\mathrm{earth},\mathrm{tree},\mathrm{rock},\mathrm{plant})\) — **not** the 32-D SSM chart and **not** a filled 24-D \(u_t\).
- Standardized: \(\tilde f=(f-\mu)/\max(s,0.02)\) with \(\mu=[70,20,3,0.2]\), \(s=[12,8,3,0.4]\).
- Prototype cell \(c(\tilde f)=\arg\min_k\|\tilde f-\mu_k\|\) (4 hand-authored protos). Novelty \(r=\|\tilde f-\mu_{c}\|\); novel if \(r>2.8\).
- Elapsed \(\ell_t\) is computed from **video time** via `elapsedFeature`.
- On PXL, NLM environmental channels (temp / humidity / pressure / gas / IAQ / FCI / audio) are **absent**. Code comment: **all-missing \(u_t\) → ABSTAIN**. Do not draw a filled \(\mathbb{R}^{24}\) vector as if it were measured.

Record fields in code: `s="pxl-trail-20260913"`, `k="terrain-ade20k-pxl/v1"`, `c_t.live=false`, `U_t.metres` is `UNQUALIFIED` unless `channel_source="simulation"`.

### Task 2 — NLM SSM / AVANI abstain

**In-repo source:** same `formspace-nlm.ts` (`ssmDecayA`, `ssmStep`, `nlmBeliefFromRuntime`, `avaniTerrain`, `decideTerrain`). MAS `/api/nlm` router: `mycosoft_mas/core/routers/nlm_api.py` (not required for slides).

SSM (paper §3 / weights §8, as coded — **native scan, not exact ZOH**):

\[
A=-\exp(A_{\log}),\qquad H_t=\mathrm{e}^{\Delta A}H_{t-1}+\Delta B\,v
\]

Forecast head (paper §4) exists as `sigmoid` \(p=\sigma(z/T)\) in code — **ITDX never emits it**. `forecast_p`, `p_candidate`, `p_background` stay **null**. `forecast_qualified: false`.

AVANI dispositions: **DENY / PAUSE / PASS / REVIEW**. Terrain rule in code:

- simulation channels present → `REVIEW`
- `!model_loaded` **or** `abstained` → `PAUSE`
- else `REVIEW`

Decision loop (loop paper §1 as coded): \(b=\) NLM belief, \(F=\) FormSpace, \(a^*\in\{\mathrm{HOLD},\mathrm{COLLECT\_EVIDENCE}\}\), \(d=\) AVANI, \(u_t=\mathrm{none}\). Abstain ⇒ \(a^*=\mathrm{COLLECT\_EVIDENCE}\).

**Weights (bind, not skill):** SHA-256 `0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2`, **25,728** params / 47 tensors, `bound_to_ollama: false`, schema `formspace-environmental-reference/0.1.0`. Origin of that file is **legacy_reference / SYNTHETIC_TEST** replay (MAS FormSpace map 09 Sep). **Model loaded ≠ forecast issued.**

### Task 3 — WEKA 149 classify / cluster / filter

**In-repo narrative:** MAS `docs/WEKA_ITDX_CAMPAIGN_RUN_SEP14_2026.md`. **Receipt binaries are gitignored** (§5).

| Family | Count | Role |
|---|---|---|
| Classifiers | **56** | Compatibility receipts on applicable ARFF views |
| Filters | **85** | No F1 (filters rewrite ARFF) |
| Clusterers | **8** | Unsupervised; ARI/NMI **not yet scored** on trail |
| **Total schemes** | **149 / 149** | Compatibility **only** |
| Scientific readiness | **false** | Write the word false |
| Planned Cartesian | **4,760** filter×classifier cells | **PLANNED — not executed** |

WEKA scores **tables**. NLM is a **separate** FormSpace model. Opening an ARFF in desktop Weka is **not** “running NLM.”

F1 / Brier (WEKA runbook §8, as coded; only when labels exist):

\[
F_1=\frac{2\,\mathrm{TP}}{2\,\mathrm{TP}+\mathrm{FP}+\mathrm{FN}},\qquad \mathrm{Brier}=\mathrm{mean}((p-y)^2)
\]

Trail prediction ARFF has `actual=?` and `p=?` → those formulas **return null / not yet scored**.

### Task 4 — Trail AR foothold + perimeter + loop-refine

**In-repo source:** `loop-refine.ts`, `docs/TRAIL_TWO_CLOCK_OVERLAY_SEP14_2026.md` (on website SHA), FINAL handoff.

| Layer | Clock | What |
|---|---|---|
| Objects / contours | **every `requestAnimationFrame`** | Detect + draw perimeters |
| Steps / footholds | **280 ms** (`STEP_PLACE_MS`) | GREEN / CYAN / RED contact placement |
| React UI | ≤ 10 Hz | Do not `setState` every rAF |

Clip constants (builder): `PXL_SOURCE_FPS=30`, `PXL_NATIVE_FRAMES=422`, `PXL_DURATION_S=14.0691`, `OVERLAY_HZ_TARGET=120`, `INSTANCE_CAP=5`.  
**Footholds ≠ perimeters.** Do not collapse into one “accuracy.”

Loop-refine (session last-good perimeters, key `kind@rounded_center`):

- IoU via `contourMaskIou` (need ≥3 points; else **not yet scored** → reject / keep last-good).
- `LOOP_STABILITY_LO = 0.72`, `LOOP_IMPROVE_EPS = 0.02`.
- **accept** if IoU improved (or held within ε) **or** IoU ≥ 0.72; else **reject** and keep last-good.
- **seed** if no last-good for that instance.
- Append-only JSONL; `forecast_p: null`; **no F1**.

---

## 4. Results table (three columns)

**Rule:** If a figure is not in this table, **do not put it on a slide.**  
**Hess package** = output of a **fresh** `POST /api/fusarium/itdx/local-weka` on this PC (Java + `weka.jar` present). **Do not copy** Cursor `.data/weka-campaign` folders into the Hess zip.

| Claim | Cursor-reported (this lab, gitignored disk / prior Cursor session) | Reproducible on this PC (Hess) | Label |
|---|---|---|---|
| Schemes with compatibility receipts | **149 / 149** (56 / 85 / 8) from Sep 14 campaign `coverage.json` | **Not** unless Hess re-runs the full campaign worker (long; **not** the Hess path) | Compatibility only — **not** “measured skill” |
| Scientific readiness | **false** | **false** (BFF always) | **false** |
| Ledger jobs / `RAN_*` / fail / blocked | 1052 jobs; 821 `RAN_*`; 87 fail-or-timeout; 144 blocked/inapplicable | Not in Hess package | Cursor-reported campaign accounting |
| ARFFs inventoried / views executed | 10 found / 9 executed | Not in Hess package | Campaign ZIP itself has **zero** ARFFs |
| `forecast_p` | **null** | **null** | Abstain — every receipt |
| J48 `fixture_numeric_nominal` 10-fold F1 | **0.975** / 97.5% (Sep 14 + Sep 17 local CLI) | **Only if** fresh `POST /local-weka` completes J48 fixture | **SYNTHETIC** |
| ZeroR same fixture | 57.5% correct; weighted F1 null | Same — fresh POST | **SYNTHETIC** |
| J48 `task12_raw_train` F1 | **0.99922** | **Not** in `local-weka` five-job set | **SYNTHETIC** archived Task 12 |
| J48 `task12_coordinates` F1 | **0.99875** | **Not** in five-job set | **SYNTHETIC** FormSpace coords — **not NLM** |
| Many fixture / Task 12 F1 | **1.000** | Do not cite as Hess | **SYNTHETIC only** |
| Date fixture F1 (many clf) | ~0.45–0.62 | Not in five-job set | **SYNTHETIC** |
| DecisionStump date fixture | F1 **0.287** | Not in five-job set | **SYNTHETIC** |
| J48 on `trail-ar-predictions.arff` | scored instances **0**; ignored unknown class **489222** (17 Sep CLI) | Fresh POST should again be **unlabeled** | **NOT_YET_SCORED** |
| Trail F1 / Brier / confusion | **not yet scored** (`actual` and `p` are `?`) | **not yet scored** | **NOT_YET_SCORED** |
| Trail clusters ARI/NMI | **not yet scored** | SimpleKMeans may emit sizes/WCSS; ARI/NMI still none | **NOT_YET_SCORED** |
| SimpleKMeans trail subsample 2000 | 3 clusters 848 / 796 / 356; WCSS 1860.8336391374733 | Only if trail ARFF exists **on this PC** (gitignored) | unsupervised; **NOT_YET_SCORED** |
| Normalize filter | wrote `normalize_fixture_numeric_nominal.arff` | Fresh POST | **SYNTHETIC** · no F1 |
| NLM weights SHA / 25,728 params | SHA `0c5fb815…` when 188 answers | `GET /api/fusarium/bluesight-trail/nlm` if LAN up | Bind receipt — **not** a WEKA score |
| Overlay contrast / “high accuracy” | **Not proven** | **Not proven** | Do not claim |
| Trail AR v2 on mycosoft.com | **false** | **false** | LIVE ≠ this SHA |

One WEKA sentence: **“149/149 schemes produced compatibility receipts (Cursor campaign, not in git); scientific readiness is false; measured F1 exists only on synthetic fixtures and archived Task 12; trail F1 is NOT_YET_SCORED.”**

---

## 5. Not in GitHub (gitignored `.data/`)

Website `.gitignore` contains **`.data/`**. These paths are **on the lab PC only**. ChatGPT cannot `curl` them from GitHub.

| Absolute / repo-relative path | What Cursor stored | Hess? |
|---|---|---|
| `WEBSITE/website/.data/weka-campaign/SEP14_2026/` | Full campaign `status.json`, `coverage.json`, `results.jsonl`, `results.csv`, `correlation.json`, `receipts/`, `filtered/`, fixtures | **No — do not copy** |
| `WEBSITE/website/.data/weka-campaign/SEP17_2026_LOCAL/` | Prior Cursor local CLI `scores.json` / `scores.csv` / stdout | **No — regenerate** |
| `WEBSITE/website/.data/trail-ar/loop-refine.jsonl` | Session accept/reject/seed log | **No.** Regenerated by play-through |
| `WEBSITE/website/.data/trail-ar/weka/` | `trail-ar-session.arff`, `trail-ar-predictions.arff` (labels `?`) | **No** labels in git. Export is local-only |
| `WEBSITE/website/.data/weka-runtime/` | Portable Temurin 17 + MTJ | Runtime, not a result |

Absolute lab roots:

```text
D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.data\weka-campaign\SEP14_2026\
D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.data\weka-campaign\SEP17_2026_LOCAL\
D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.data\trail-ar\loop-refine.jsonl
D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.data\trail-ar\weka\
```

### How to regenerate (Hess-reproducible)

**A. Fresh local WEKA (the only Hess score path)**

1. Dev server on **3010** (`npm run dev:next-only` in `WEBSITE/website`). Portable Java + `weka.jar` must exist (runtime is also under `.data/`, not git).
2. `POST http://localhost:3010/api/fusarium/itdx/local-weka` (no body).
3. Five real CLI jobs: ZeroR fixture, J48 fixture, J48 trail predictions, Normalize fixture, SimpleKMeans trail.
4. Writes a **new** `SEP17_2026_LOCAL/scores.json` + `scores.csv`.
5. Download: `GET /api/fusarium/itdx/local-weka/file?name=scores.json`.
6. Label every F1 **SYNTHETIC** or **NOT_YET_SCORED**. **503** if Java/`weka.jar` missing — that is honest, not a stub.

**B. Loop-refine JSONL (not a score)**

1. Open `http://localhost:3010/natureos/bluesight-trail`.
2. Play through one clip (~14.07 s) or **Close loop**.
3. Expect `window.__trailLoop.loop` to increment; `POST /api/fusarium/bluesight-trail/loop-refine` appends rows; glass accept/reject/seed change.
4. `GET /api/fusarium/bluesight-trail/loop-refine` returns path, bytes, counts. IoU only — **no F1**.

**C. Sep 14 149-scheme campaign**

`POST /api/fusarium/bluesight-trail/weka-campaign` respawns `MAS/scripts/itdx_weka_campaign/run_campaign.py --out SEP14_2026`. **Do not treat a prior Cursor `SEP14_2026/` folder as Hess-reproducible** unless Hess himself re-runs it. Default Hess package **omits** that folder.

---

## 6. NLM contract (on GitHub as of `d5180f41`)

ChatGPT already stated this. **Confirm and keep it on every slide/chip.**

| Statement | Truth |
|---|---|
| Forcing offline turns NLM off | **False** |
| `?force=offline` / `ITDX_FORCE_OFFLINE=1` / no WAN | Isolates **WAN / public-demo WEKA mode** → banner `OFFLINE LOCAL WEKA`, `wan_status: WAN_DOWN` |
| LAN NLM | **Still probed:** MAS `GET http://192.168.0.188:8001/api/nlm/health` **and** `/api/nlm/runtime` (connectivity, 3.5 s, Node `http`) **and** BFF `GET /api/fusarium/bluesight-trail/nlm` |
| NLM chip | **`NLM ONLINE / weights loaded`** (or `/ weights not loaded`) vs **`NLM MAS_NLM_DOWN`** |
| Forecast chip | `forecast_p: null` / **forecast abstained** / `FORECAST_ABSTAIN` / `forecast_qualified: false` |
| Never | Stub **0.85** or **0.5**. Equate WEKA with NLM. Paint **UNBOUND** because WEKA is offline |

Three chips — **do not collapse:**

| Chip | Meaning | Red? |
|---|---|---|
| `WAN_DOWN` | Forced offline / demo WAN isolation. LAN may be up. | No |
| `MAS_NLM_DOWN` | `GET /api/nlm/health` (and runtime) failed. **This** is “NLM not running.” | Yes |
| `FORECAST_ABSTAIN` | Service answered; `forecast_p` is null; AVANI **PAUSE**. Show **model loaded** separately. | No |

v2 board (`itdx-v2-demo-board.tsx`) comment: “LAN NLM is independent of WAN / force=offline WEKA mode.” It **always** fetches `/api/fusarium/bluesight-trail/nlm`.  
`probeItdxConnectivity` **always** `Promise.all`s MAS health, MINDEX health, **and** `probeNlm()`.

**NLM bind/label is now ON GITHUB** at ship SHA `d5180f41` (PR **#322** pushed, **not merged**). Live mycosoft.com is still **~13 Sep**. Instant Deploy **HELD**. `probeNlm()` hits health+runtime even under `WAN_DOWN`. Math-log GET/POST skip files over 8 MB. Do **not** commit `.data/` or the 512 MB math-log.

Older slide handoff §3 step 4 (“NLM fetch runs only in ONLINE mode”) is a **superseded error**. Ignore it.

---

## 7. System flow (slide 3 — one page)

```text
PXL replay video (14.0691 s, 30 fps, 422 native frames)
        │
        ▼
  Trail AR player  ── two clocks ─────────────────────────────┐
        │                                                     │
        │  clock B: requestAnimationFrame → object perimeters │
        │  clock A: 280 ms → foothold / contact steps         │
        │                                                     │
        ▼                                                     │
  loop-refine (last-good per-instance)                        │
        │  IoU vs last-good → accept | reject | seed          │
        │  append .data/trail-ar/loop-refine.jsonl (gitignored)
        │
        ▼
  FormSpace record F_t + ℓ_t from video time
        │  u_t ∈ R^{24} channels missing on PXL → ABSTAIN
        ▼
  NLM on MAS 188  GET /api/nlm  (model may be LOADED)
        │  forecast_p = null  (forecast abstained)
        ▼
  AVANI  PAUSE (or REVIEW if sim traces only)
        │  a* = COLLECT_EVIDENCE when abstaining
        ▼
  WEKA ARFF export (session + predictions; actual=? p=?)
        │  local Java CLI  and/or  Army desktop Weka
        ▼
  Army operator opens ARFF in desktop Weka Explorer
        (classify/cluster/filter the TABLE — this is not NLM)
```

Banners on that slide: `LOCAL DEMO · SYNTHETIC EXERCISE · live: false · forecast_p: null` plus `ONLINE (backends bound)` **or** `OFFLINE LOCAL WEKA`.

---

## 8. Forbidden

Do **not** write, say, or imply:

- “High accuracy” as an achieved field metric
- **0.85** or **0.5** as NLM / travel probability / skill
- Trail F1 scored / Brier scored / confusion scored
- **WEKA = NLM**
- “CMMC compliant” / “CMMC L2 certified”
- RJ Ricasata as **COO** (he is **CFO**)
- CUI, FOUO, or real Army intel in this deck or repo
- Trail AR v2 / ITDX dual-mode is **live** on mycosoft.com
- Merging website **#322** or Instant Deploy / production cutover
- That the **4,760**-cell planned matrix was executed
- Inventing `forecast_p`
- Fort Stewart as a live operational AO (SYNTHETIC EXERCISE only if named)
- Brain™ marketing copy
- Live COP / live sensors when `live: false`
- That Cursor `.data` receipts are in GitHub or Hess-reproducible without a fresh run

---

## 9. Dual-mode + BFF envelopes (short)

### Connectivity `GET /api/fusarium/itdx/connectivity?force=offline`

```json
{
  "schema": "itdx-connectivity/v1",
  "live": false,
  "forecast_p": null,
  "weka_is_not_nlm": true,
  "mode": "OFFLINE_LOCAL_WEKA",
  "banner": "OFFLINE LOCAL WEKA",
  "forced_offline": true,
  "wan_status": "WAN_DOWN",
  "forecast_status": "FORECAST_ABSTAIN",
  "nlm": {
    "url": "http://192.168.0.188:8001/api/nlm/health",
    "ok": true,
    "bind": "BOUND",
    "nlm_status": "NLM_ONLINE",
    "model_loaded": true,
    "forecast_status": "FORECAST_ABSTAIN"
  },
  "probe_timeout_ms": 3500
}
```

`mode` is `ONLINE` only when **not** forced **and** MAS `/health` is ok. Forced offline **still probes** LAN MAS / MINDEX / NLM.

### NLM `GET /api/fusarium/bluesight-trail/nlm`

```json
{
  "live": false,
  "forecast_p": null,
  "forecast_status": "FORECAST_ABSTAIN",
  "bound_to_ollama": false,
  "bind": "BOUND",
  "nlm_status": "NLM_ONLINE",
  "belief": {
    "model_loaded": true,
    "abstained": true,
    "forecast_p": null,
    "weights_sha256": "0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2",
    "parameter_count": 25728
  }
}
```

---

## 10. People / deploy gate

| Person | Role |
|---|---|
| Morgan Rockcoons | CEO, CTO, COO, SAO. Sole GitHub approver. |
| RJ Ricasata | **CFO**. MYCA 2nd Key. **Never COO.** |

| Gate | 17 Sep 2026 |
|---|---|
| Instant Deploy | **HELD** |
| Merge website #322 | **No** |
| Merge MAS #156 | **No** (docs only; still do not treat as a product ship) |
| Public cutover | **No** |
| CUI | **PreVeil only** — not this pack |

**No Instant Deploy. No git reset. No secrets.**

---

## 11. Companion files (optional second paste)

| File | Use |
|---|---|
| `docs/ITDX_V2_CHATGPT_GITHUB_CODE_MAP_SEP17_2026.md` | Full blob/raw file list |
| `docs/ITDX_V2_CHATGPT_BUILDER_HANDOFF_SEP17_2026.md` | Software contract / JSON |
| `docs/ITDX_V2_CHATGPT_SLIDE_HANDOFF_SEP17_2026.md` | Older 12-slide outline — **override** §3 NLM-only-online |
| `docs/ITDX_V2_CHATGPT_FINAL_HANDOFF_SEP17_2026.md` | Loop-refine / freeze notes |
| `docs/WEKA_ITDX_CAMPAIGN_RUN_SEP14_2026.md` | 149-scheme narrative |
| `docs/FORMSPACE_NLM_REPOSITORY_MAP_SEP09_2026.md` | Where FormSpace lives; PDFs not in repo |

Mirror of this pack: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\docs\ITDX_V2_CHATGPT_EVERYTHING_SEP17_2026.md`
