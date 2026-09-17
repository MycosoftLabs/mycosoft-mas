# ITDX v2.0 — ChatGPT slide-deck handoff — 17 Sep 2026

**Software-builder contract (read first if ChatGPT is implementing routes / APIs / banners / WEKA I/O / Fusarium shell):** [`ITDX_V2_CHATGPT_BUILDER_HANDOFF_SEP17_2026.md`](ITDX_V2_CHATGPT_BUILDER_HANDOFF_SEP17_2026.md). This file remains the **slide-deck** brief only.  
**GitHub code map:** [`ITDX_V2_CHATGPT_GITHUB_CODE_MAP_SEP17_2026.md`](ITDX_V2_CHATGPT_GITHUB_CODE_MAP_SEP17_2026.md) — website `ship/trail-ar-itdx-sep17` @ `20bf2b068591f7de16487ca03e77efb6b5785c4e`. **Not live.**

**Date:** Thursday 17 September 2026  
**Status:** Handoff only for a slide deck. Local ITDX 2.0 demo is scaffolded on localhost:3010. Code is on GitHub; **not deployed.** Instant Deploy **HELD.**  
**Classification:** UNCLASSIFIED commercial. No CUI. No Army FOUO.  
**Audience:** ChatGPT building a slide deck with **no Mycosoft repo access**.  
**Owner:** Morgan Rockcoons — CEO / CTO / COO / SAO  
**CFO:** RJ Ricasata — **never COO**  
**CMMC:** Mycosoft is **pursuing** CMMC Level 2 — **not** “CMMC compliant.”

Paste this entire file into ChatGPT. Treat numbers below as the only allowed WEKA figures. If a figure is not in the honesty table, do not put it on a slide.

---

## 1. What ITDX is

ITDX is Mycosoft’s **Fusarium terrain / decision exercise** — a laboratory and demo of algorithms that read terrain, abstain when evidence is missing, and score distributions in WEKA.

It is **not**:

- a chatbot
- a live Common Operating Picture
- a calibrated travel-probability model
- NLM (Nature Learning Model) itself

**WEKA ≠ NLM.** WEKA classifies, clusters, and filters ARFF tables. NLM is a separate FormSpace environmental model. `forecast_p` is **null**. Never print 0.85 or 0.5 as skill.

Working title for slides: **ITDX — terrain decision exercise (local demo + WEKA pipeline).**  
Do **not** use Brain™ brand copy.

---

## 2. What v1 already proved locally (3010)

These are **capabilities**, not field accuracy claims.

| Surface | What is real |
|---|---|
| Trail AR | `http://localhost:3010/natureos/bluesight-trail` (ungated). Replay + glass math console. Banner `SIMULATION · live: false`. |
| Fusarium lab | `http://localhost:3010/fusarium/itdx` — same Trail AR lab inside Fusarium. **May 307 to Google owner login.** |
| FormSpace / NLM backbone | Terrain cell `F_t`, novelty `r`, elapsed `ℓ`, AVANI dispositions (DENY/PAUSE/PASS/REVIEW). NLM **abstains** when channels are simulation/absent. `p` stays null. |
| Two clocks | Source video fps vs overlay Hz. Foothold / contact pips vs object perimeters — do not collapse them into one “accuracy.” |
| Glass rail + overhead map | Present on Trail AR. Overlay contrast / visibility pass is **in flight on 3010** — do not invent screenshots or “high contrast proven.” |
| WEKA 149 schemes | 56 classifiers + 85 filters + 8 clusterers. Compatibility receipts **149/149**. Scientific readiness **false**. |
| Campaign BFF | `GET/POST /api/fusarium/bluesight-trail/weka-campaign` reads/writes `website/.data/weka-campaign/SEP14_2026/`. |

Fort Stewart AO, if mentioned: **SYNTHETIC EXERCISE** only. Civil / non-US Part B is later.

---

## 3. Dual-mode (must be on the deck)

ITDX 2.0 works **both** ways. This is the v2.0 product story.

### ONLINE (machine can reach the LAN backends)

Chosen when **MAS `GET /health` returns HTTP 200 within 3.5 seconds** (degraded collectors still count as bound). MINDEX `GET /health` is probed in parallel and shown separately.

Uses the **full live backend already wired**:

- MAS `http://192.168.0.188:8001` (orchestrator, NLM `/api/nlm/*`, HITs)
- MINDEX `http://192.168.0.189:8000` (taxonomy / catalogs — empty stays empty)
- Website BFFs on 3010 (`/api/fusarium/bluesight-trail/*`, `/api/fusarium/itdx/*`)
- WEKA campaign runner (local Java) plus NLM bind when loaded

Banner: **ONLINE (backends bound)**  
Still: **LOCAL DEMO · SYNTHETIC EXERCISE · live: false** for sim sensors.

### OFFLINE LOCAL WEKA (WAN isolated or MAS `/health` failed)

Chosen when MAS health **fails, times out, or is forced** (`?force=offline` or `ITDX_FORCE_OFFLINE=1`). Probes **abort at 3.5s** — do not hang 45s per call.

**NLM is not unbound in this mode.** LAN `192.168.0.188:8001/api/nlm` still runs the existing weights. Slide chip: **NLM ONLINE / weights loaded** · `forecast_p: null` (ABSTAIN). Only `MAS_NLM_DOWN` means the NLM service is down. Do not print UNBOUND because WEKA is offline.

Full WEKA score capability **remains**:

- Portable Temurin 17 JRE: `website/.data/weka-runtime/jdk-17.0.20.1+1-jre/bin/java.exe`
- `weka.jar` from the Algorithm Lab kit `formspace/weka/deps/`
- Campaign ARFFs + receipts: `website/.data/weka-campaign/SEP14_2026/`
- Trail ARFFs: `website/.data/trail-ar/weka/trail-ar-session.arff` and `trail-ar-predictions.arff`
- Focused CLI ledger: `website/.data/weka-campaign/SEP17_2026_LOCAL/` (`scores.json`, `scores.csv`, filtered ARFF)

Does **not** require MAS or MINDEX. Does **not** invent F1.

Banner: **OFFLINE LOCAL WEKA**  
`live: false`. `forecast_p: null`.

### How the software chooses

1. Parallel fetch MAS `/health` and MINDEX `/health` with a **3500 ms** abort.  
2. If MAS is OK → **ONLINE**. Else → **OFFLINE_LOCAL_WEKA**.  
3. Trail AR / campaign JSON on disk always render.  
4. NLM fetch runs **only** in ONLINE mode.  
5. “Run local WEKA CLI” always talks to **local Java**, both modes.

---

## 4. Exact URLs (localhost:3010)

| URL | Notes |
|---|---|
| `http://localhost:3010/natureos/bluesight-trail` | Ungated Trail AR v1 |
| `http://localhost:3010/fusarium/itdx` | Fusarium Trail AR lab; **may 307 login** |
| `http://localhost:3010/fusarium/itdx/v2` | **ITDX 2.0 demo board** (dual-mode + WEKA + Trail AR iframe) |
| `http://localhost:3010/api/fusarium/itdx/connectivity` | Mode probe (3.5s abort) |
| `http://localhost:3010/api/fusarium/itdx/local-weka` | GET ledger / POST run local CLI |
| `http://localhost:3010/api/fusarium/bluesight-trail/weka-campaign` | Sep 14 campaign status (now includes `mode`) |
| `http://localhost:3010/api/fusarium/bluesight-trail/nlm` | NLM honesty; `forecast_p` null |

**Not deployed** to sandbox / mycosoft.com from this pass.

---

## 5. Slide outline (12 slides)

Use this order. One idea per slide.

1. **Title** — ITDX 2.0 local demo: Fusarium terrain / decision exercise. Date 17 Sep 2026. Pursuing CMMC L2. RJ Ricasata, CFO.
2. **Problem** — Terrain decisions need an honest stack: what is there, what is unknown, what cannot be scored yet. Not a chatbot. Not a live COP.
3. **Stack** — Trail AR (3010) → FormSpace / NLM abstain → AVANI gate → WEKA classify / cluster / filter. Fusarium shell. Dual-mode ONLINE vs OFFLINE LOCAL WEKA.
4. **Algorithms** — FormSpace `F_t`, novelty `r`, elapsed `ℓ`. NLM abstains; `forecast_p` null. AVANI DENY/PAUSE/PASS/REVIEW. WEKA 56 / 85 / 8 schemes.
5. **Trail AR layers** — Replay video, glass rail, overhead map, corridor / horizon, contact footholds vs perimeters, two clocks. `SIMULATION · live: false`. Visibility pass in flight on 3010.
6. **Fusarium integration** — Same lab on `/fusarium/itdx` + v2 board. Scenario clock on this tree is the Trail AR replay clock (scenario-sim BFF not in this working tree).
7. **Local demo vs live** — 3010 proves the pipeline. Overlay sensors stay `live: false`. No Instant Deploy in this handoff. No live COP claim.
8. **Dual-mode** — ONLINE = MAS + MINDEX + NLM + BFFs. OFFLINE = local Java + `weka.jar` + on-disk ARFFs. 3.5s probe. Same honesty labels.
9. **WEKA honesty table** — Use **only** §6. Title the slide “pipeline + receipts,” not “high accuracy.”
10. **What we will not claim** — Copy §7 onto the slide in short bullets.
11. **Gaps** — Trail F1 not yet scored. Scientific readiness false. Planned 4,760 filter×classifier cells not run. Civil Part B later. Overlay visibility in flight.
12. **v2.0 ask** — Keep proving the pipeline. Next scientific step: independently labeled hike vs ZeroR (grouped holdout). Label synthetic separately. Do not promote Task 12 / fixture F1.

Optional 13th: **People / locks** — Morgan CEO/CTO/COO/SAO; RJ Ricasata CFO; CUI only in PreVeil.

---

## 6. WEKA numbers allowed on slides (cited)

Source: `website/.data/weka-campaign/SEP14_2026/` (`status.json`, `coverage.json`, `correlation` inside status). Campaign run document: MAS `docs/WEKA_ITDX_CAMPAIGN_RUN_SEP14_2026.md` (14 Sep 2026).

| Claim | Number | Label required on the slide |
|---|---|---|
| ARFFs inventoried | **10** found | Campaign ZIP itself has zero ARFFs |
| ARFF views executed | **9** | One inventoried view was not a worker view |
| Schemes with compatibility receipts | **149 / 149** | Compatibility only |
| Scientific readiness | **false** | Write the word false |
| Ledger jobs | **1052** | Not 4,760 planned matrix cells |
| `RAN_*` | **821** (710 compatibility + 111 scientific-lane / representation) | Status `ran` field |
| Failed or timeout | **87** in status.json (run doc also notes 86 FAILED + 1 TIMEOUT) | Not “models failed” |
| Blocked / inapplicable | **144** status (`blocked_or_inapplicable`); run doc splits 88 INAPPLICABLE + 56 BLOCKED_DATA | Trail unlabeled |
| `forecast_p` | **null** | Every receipt |
| Trail F1 / Brier / confusion | **not yet scored** | `actual` and `p` are `?` on prediction ARFF |
| Trail clusters ARI/NMI | **not yet scored** | No reference partition |
| J48 on `fixture_numeric_nominal` | F1 **0.975** / **97.5%** | **SYNTHETIC** fixture |
| J48 on `task12_raw_train` | F1 **0.99922** / **99.921875%** | **SYNTHETIC** archived Task 12 |
| J48 on `task12_coordinates` | F1 **0.99875** / **99.875%** | **SYNTHETIC** FormSpace coords — not NLM |
| Many fixture / Task 12 rows | F1 **1.000** | **SYNTHETIC only** — never “achieved accuracy” |
| Date fixture (many classifiers) | about **0.45–0.62** F1 | **SYNTHETIC**; timestamps were not a class signal |
| DecisionStump on date fixture | F1 **0.287** / **27.5%** | **SYNTHETIC**; shows WEKA can sit near/below chance |
| NLM weights SHA-256 (ONLINE bind) | `0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2` | Real file on MAS when bound; **not** a WEKA score |
| NLM params | **25,728** / 47 tensors / `bound_to_ollama: false` | Algorithm replay; `forecast_qualified: false` |

If you need one sentence for WEKA: **“149/149 schemes produced compatibility receipts; scientific readiness is false; measured F1 exists only on synthetic fixtures and archived Task 12.”**

Local 17 Sep CLI (`SEP17_2026_LOCAL/scores.json`) — **real Java weka.jar stdout**, same honesty rules:

| 17 Sep local CLI | Number | Label |
|---|---|---|
| ZeroR on `fixture_numeric_nominal` | **57.5%** correct; weighted F1 **null** (candidate F-Measure is `?`) | **SYNTHETIC** |
| J48 on same fixture (10-fold CV) | F1 **0.975** / **97.5%** | **SYNTHETIC** · reconfirms Sep 14 |
| J48 on `trail-ar-predictions.arff` | scored instances **0**; ignored unknown class **489222** | **NOT_YET_SCORED** |
| Normalize filter on fixture | wrote `normalize_fixture_numeric_nominal.arff` | **SYNTHETIC** · filters have no F1 |
| SimpleKMeans on trail subsample 2000 (after RemoveType string) | 3 clusters **848 / 796 / 356**; WCSS **1860.8336391374733** | unsupervised partition; ARI/NMI **not yet scored** |

If you cite 17 Sep local numbers, say **SYNTHETIC or NOT_YET_SCORED · real WEKA CLI · 17 Sep local**. Do not treat them as trail skill.

---

## 7. What ChatGPT must **not** claim

- “Mycosoft is CMMC compliant” / “CMMC L2 certified”
- “High accuracy WEKA” as an achieved field metric
- Any F1, accuracy, or 0.85 / 0.5 as NLM or travel probability
- Trail AR F1 scored
- Scientific readiness established
- WEKA = NLM
- Live COP / live sensors when the banner is `live: false`
- RJ Ricasata as COO
- Brain™ marketing copy
- CUI, FOUO, or real Army intel
- Fort Stewart as a live operational AO
- That the 4,760-cell planned matrix was executed (those cells stay **PLANNED**)
- Screenshots proving overlay contrast (visibility pass **in flight on 3010**)
- Instant Deploy / production ship from this 17 Sep pass

If Morgan asked for “high accuracy” slides: **prove the pipeline; do not put unmeasured F1 on slides; label synthetic separately; next step is a labeled hike vs ZeroR.**

---

## 8. v2.0 local demo requirements (for the ask slide)

Already the design of `/fusarium/itdx/v2`:

- Fusarium-integrated demo board (glass, collapsible sections)
- Trail AR iframe + links to `/natureos/bluesight-trail` and `/fusarium/itdx`
- FormSpace / NLM honesty (`p` null; ONLINE bind vs OFFLINE unbound)
- WEKA campaign from the **real** BFF (no mock rows)
- Local WEKA CLI that writes CSV/ARFF
- Banner **LOCAL DEMO · SYNTHETIC EXERCISE · live: false**
- Second banner **ONLINE (backends bound)** vs **OFFLINE LOCAL WEKA**
- Offline-capable scores without MAS/MINDEX
- No Instant Deploy, no marketing hero edits, no CUI

---

## 9. People / locks (footer of the deck)

| Person | Role |
|---|---|
| Morgan Rockcoons | CEO, CTO, COO, SAO. Sole GitHub approver. |
| RJ Ricasata | **CFO**. MYCA 2nd Key. Never COO. |

CUI lives only in PreVeil. This deck and the public site stay unclassified. Mycosoft is **pursuing** CMMC L2.

---

## 10. Operator pointers (not for slides)

- Sep 14 campaign: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.data\weka-campaign\SEP14_2026\`
- Local 17 Sep CLI: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.data\weka-campaign\SEP17_2026_LOCAL\`
- Trail ARFFs: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.data\trail-ar\weka\`
- Connectivity BFF: `/api/fusarium/itdx/connectivity`
- Force offline: `/api/fusarium/itdx/connectivity?force=offline`

**Deploy status: not deployed.**
