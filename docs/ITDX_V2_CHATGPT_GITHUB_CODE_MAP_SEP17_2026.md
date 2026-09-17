# ITDX v2 ChatGPT GitHub code map — 17 Sep 2026

**Date:** Thursday 17 September 2026  
**Status:** Fetch map for ChatGPT. Code is on GitHub **feature branches**. **Not cut over. Instant Deploy HELD.**  
**Classification:** UNCLASSIFIED commercial. No CUI. No secrets.  
**Owner:** Morgan Rockcoons — CEO / CTO / COO / SAO  
**CFO:** RJ Ricasata — **never COO**  
**CMMC:** Mycosoft is **pursuing** CMMC Level 2 — **not** “CMMC compliant.”

`forecast_p` is **null**. `live` is **false**. **WEKA ≠ NLM.** Do **not** print **0.85**.

Companion briefs (paste after this map if you still need contracts / slides):

- Builder: `docs/ITDX_V2_CHATGPT_BUILDER_HANDOFF_SEP17_2026.md`
- Slides: `docs/ITDX_V2_CHATGPT_SLIDE_HANDOFF_SEP17_2026.md`

---

## 1. Org / repo / branch / SHA

| Surface | Org/repo | Branch | Full SHA | Compare / tree |
|---|---|---|---|---|
| **Website (implement this)** | [MycosoftLabs/website](https://github.com/MycosoftLabs/website) | `ship/trail-ar-itdx-sep17` | `20bf2b068591f7de16487ca03e77efb6b5785c4e` | [tree](https://github.com/MycosoftLabs/website/tree/20bf2b068591f7de16487ca03e77efb6b5785c4e) · [commit](https://github.com/MycosoftLabs/website/commit/20bf2b068591f7de16487ca03e77efb6b5785c4e) |
| **MAS (handoffs + WEKA narrative)** | [MycosoftLabs/mycosoft-mas](https://github.com/MycosoftLabs/mycosoft-mas) | `docs/itdx-v2-chatgpt-github-map-sep17` | `8bbdbfcfeaa0272cbbee235366e5a4f2226e5f18` | [tree](https://github.com/MycosoftLabs/mycosoft-mas/tree/8bbdbfcfeaa0272cbbee235366e5a4f2226e5f18) · [commit](https://github.com/MycosoftLabs/mycosoft-mas/commit/8bbdbfcfeaa0272cbbee235366e5a4f2226e5f18) |

Website clone:

```text
https://github.com/MycosoftLabs/website/tree/ship/trail-ar-itdx-sep17
https://github.com/MycosoftLabs/website/commit/20bf2b068591f7de16487ca03e77efb6b5785c4e
```

MAS clone (docs branch; created with this map):

```text
https://github.com/MycosoftLabs/mycosoft-mas/tree/docs/itdx-v2-chatgpt-github-map-sep17
https://github.com/MycosoftLabs/mycosoft-mas/commit/8bbdbfcfeaa0272cbbee235366e5a4f2226e5f18
```

Do **not** treat `main` as Trail AR v2. Production `main` last Instant Deploy is **~13 Sep 2026** and does **not** include this SHA.

---

## 2. LIVE vs IN PROGRESS (do not collapse)

### LIVE now (public 200 — last Instant Deploy ~13 Sep 2026)

Probed 17 Sep 2026 ~13:45 Pacific:

| URL | HTTP | What it is |
|---|---|---|
| https://mycosoft.com | **200** | Public site. **Not** Trail AR v2 / ITDX dual-mode / loop-refine. |
| https://sandbox.mycosoft.com | **200** | Sandbox hostname. Same rule: **not** this branch. |
| http://192.168.0.187:3000 | **200** | Sandbox Docker origin. Same rule. |

Trail AR v2 is **not live**. Do not claim `/natureos/bluesight-trail`, `/fusarium/itdx/v2`, WEKA Army ARFF, or LAN NLM chips exist on mycosoft.com from this pass.

### IN PROGRESS (on GitHub as of website `20bf2b06`)

On GitHub **now** (after `git push` of `ship/trail-ar-itdx-sep17`):

- Trail AR lab + two-clock overlay + glass dock
- ITDX 2.0 dual-mode board (`/fusarium/itdx/v2`)
- Connectivity BFF (3.5 s abort, WAN vs MAS vs NLM chips)
- WEKA campaign BFF + local Java WEKA BFF
- NLM honesty BFF (LAN `188:8001/api/nlm` — `forecast_p` null = ABSTAIN)
- Loop-refine module + `/loop-refine` BFF (IoU only; no fake F1)
- Dual-mode + FormSpace backbone notes

**Still mid-e2e / not proven** (sibling `f6976835`; Instant Deploy **HELD** until freeze-free + WEKA + NLM pass):

- Ungated Trail AR rAF freeze after Play
- v2 Trail AR embed (`?embed=1` vs full-page iframe)
- Overlay contrast / halo “proven”
- WEKA Army / trail ARFF **scored** F1 (still `not yet scored`; `actual` and `p` are `?`)
- Scientific readiness (stays **false**)

### Still dirty locally — **not** in `20bf2b06`

Working copy `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website` is still on `fix/launchpad-ingest-bearer-alias` with **unrelated** dirty files (auth, Eagle, Launchpad, `_bg_*` cutover scripts, Psathyrella notes). **Do not git reset.** Those files are **not** this ship. ChatGPT should fetch **only** the blob URLs below.

MAS working tree still has many untracked ops/CMMC/WEKA binary receipts. This commit is **ChatGPT docs + indexes + Sep 14 campaign narrative** only. `.data/weka-campaign` binaries stay **gitignored**.

---

## 3. How ChatGPT should fetch

### A. `raw.githubusercontent.com` (no clone)

Pattern:

```text
https://raw.githubusercontent.com/MycosoftLabs/website/20bf2b068591f7de16487ca03e77efb6b5785c4e/<path>
https://raw.githubusercontent.com/MycosoftLabs/mycosoft-mas/8bbdbfcfeaa0272cbbee235366e5a4f2226e5f18/<path>
```

Example:

```text
https://raw.githubusercontent.com/MycosoftLabs/website/20bf2b068591f7de16487ca03e77efb6b5785c4e/app/natureos/bluesight-trail/page.tsx
https://raw.githubusercontent.com/MycosoftLabs/website/20bf2b068591f7de16487ca03e77efb6b5785c4e/lib/fusarium/itdx/connectivity.ts
```

HTML view (same SHA):

```text
https://github.com/MycosoftLabs/website/blob/20bf2b068591f7de16487ca03e77efb6b5785c4e/<path>
```

### B. Sparse clone (if you can run git)

```bash
git clone --depth 1 --branch ship/trail-ar-itdx-sep17 https://github.com/MycosoftLabs/website.git
git clone --depth 1 --branch docs/itdx-v2-chatgpt-github-map-sep17 https://github.com/MycosoftLabs/mycosoft-mas.git
```

Pin website after clone: `git checkout 20bf2b068591f7de16487ca03e77efb6b5785c4e`

Do **not** download `.data/weka-campaign` (not in git). Do **not** invent F1 from missing ARFFs.

---

## 4. Website files to fetch (blob + raw)

Base blob: `https://github.com/MycosoftLabs/website/blob/20bf2b068591f7de16487ca03e77efb6b5785c4e/`  
Base raw: `https://raw.githubusercontent.com/MycosoftLabs/website/20bf2b068591f7de16487ca03e77efb6b5785c4e/`

### Pages / board

| Path | Why |
|---|---|
| `app/natureos/bluesight-trail/page.tsx` | Ungated Trail AR |
| `app/fusarium/(dashboard)/itdx/v2/page.tsx` | ITDX 2.0 page (actual path — not `app/fusarium/itdx/v2`) |
| `app/fusarium/(dashboard)/itdx/page.tsx` | Fusarium Trail AR mount (may 307 to owner login) |
| `components/fusarium/itdx-v2-demo-board.tsx` | Dual-mode board + docks |
| `components/fusarium/bluesight-trail-lab.tsx` | Trail AR lab / overlay / embed |
| `components/fusarium/trail-glass-dock.tsx` | Glass rail |
| `components/fusarium/local-weka-panel.tsx` | Local Java WEKA UI |
| `components/fusarium/weka-campaign-panel.tsx` | Sep 14 campaign UI |

### Trail AR math / HUD / path / contact / loop-refine

| Path | Why |
|---|---|
| `lib/fusarium/bluesight/trail-ar-hud.ts` | HUD |
| `lib/fusarium/bluesight/trail-ar.ts` | Core AR |
| `lib/fusarium/bluesight/trail-contact.ts` | Contact / footholds |
| `lib/fusarium/bluesight/contact-hud.ts` | Contact HUD |
| `lib/fusarium/bluesight/path-corridor.ts` | Path / corridor |
| `lib/fusarium/bluesight/loop-refine.ts` | Loop-refine IoU (new on this SHA) |
| `lib/fusarium/bluesight/trail-contours.ts` | Contours / IoU helper |
| `lib/fusarium/bluesight/trail-lock.ts` | Lock |
| `lib/fusarium/bluesight/trail-next-step.ts` | Next step |
| `lib/fusarium/bluesight/trail-route.ts` | Route |
| `lib/fusarium/bluesight/formspace-nlm.ts` | NLM honesty helpers |
| `lib/fusarium/bluesight/trail-sim.ts` | Sim clock |
| `lib/fusarium/bluesight/trail-litmus.ts` | Litmus |
| `lib/fusarium/bluesight/horizon-line.ts` | Horizon |

### Connectivity / WEKA / NLM BFFs

| Path | Why |
|---|---|
| `lib/fusarium/itdx/connectivity.ts` | Dual-mode 3.5 s probe |
| `lib/fusarium/itdx/local-weka.ts` | Local Java CLI ledger |
| `lib/fusarium/itdx/runtime-paths.ts` | JRE / jar / ARFF paths (no binaries) |
| `app/api/fusarium/itdx/connectivity/route.ts` | Connectivity BFF |
| `app/api/fusarium/itdx/local-weka/route.ts` | Local WEKA BFF |
| `app/api/fusarium/itdx/local-weka/file/route.ts` | Local WEKA file download |
| `app/api/fusarium/bluesight-trail/weka-campaign/route.ts` | Campaign BFF |
| `app/api/fusarium/bluesight-trail/weka-campaign/file/route.ts` | Campaign file download |
| `app/api/fusarium/bluesight-trail/nlm/route.ts` | NLM honesty BFF |
| `app/api/fusarium/bluesight-trail/weka/route.ts` | Session ARFF export (not F1) |
| `app/api/fusarium/bluesight-trail/loop-refine/route.ts` | Loop-refine JSONL BFF |
| `app/api/fusarium/bluesight-trail/video/route.ts` | Replay video |
| `app/api/fusarium/bluesight-trail/session/route.ts` | Session |
| `app/api/fusarium/itdx/weka-receipt/route.ts` | Receipt helper |

### Website notes + e2e harness (local only)

| Path | Why |
|---|---|
| `docs/ITDX_V2_LOCAL_DEMO_DUAL_MODE_SEP17_2026.md` | Dual-mode note |
| `docs/ITDX_TRAIL_AR_FORMSPACE_NLM_BACKBONE_SEP14_2026.md` | FormSpace / NLM backbone |
| `docs/TRAIL_AR_ITDX_LIVE_DEPLOY_SEP17_2026.md` | Deploy hold note |
| `docs/TRAIL_TWO_CLOCK_OVERLAY_SEP14_2026.md` | Two clocks |
| `scripts/itdx-e2e-sep17-2026.mjs` | Local e2e (not green Instant Deploy) |
| `scripts/trail-ar-sidecar.py` | Sidecar helper |

Raw URL recipe: prefix every path with  
`https://raw.githubusercontent.com/MycosoftLabs/website/20bf2b068591f7de16487ca03e77efb6b5785c4e/`

Parentheses in `app/fusarium/(dashboard)/itdx/v2/page.tsx` are literal. If a client breaks on `(` `)`, use:

`app/fusarium/%28dashboard%29/itdx/v2/page.tsx`

---

## 5. MAS files to fetch (after this branch is pushed)

MAS SHA `8bbdbfcfeaa0272cbbee235366e5a4f2226e5f18` on branch `docs/itdx-v2-chatgpt-github-map-sep17`. The follow-up commit that pins this SHA in the table is on the same branch.

| Path | Why |
|---|---|
| `docs/ITDX_V2_CHATGPT_GITHUB_CODE_MAP_SEP17_2026.md` | **This map** |
| `docs/ITDX_V2_CHATGPT_BUILDER_HANDOFF_SEP17_2026.md` | Software contract / BFF JSON |
| `docs/ITDX_V2_CHATGPT_SLIDE_HANDOFF_SEP17_2026.md` | Slide deck only |
| `docs/WEKA_ITDX_CAMPAIGN_RUN_SEP14_2026.md` | Sep 14 honesty narrative (149/149 compatibility; scientific readiness false) |

Raw pattern:

```text
https://raw.githubusercontent.com/MycosoftLabs/mycosoft-mas/8bbdbfcfeaa0272cbbee235366e5a4f2226e5f18/docs/ITDX_V2_CHATGPT_BUILDER_HANDOFF_SEP17_2026.md
```

Mirrors (not a third GitHub source of truth): `CODE/docs/` copies of the three ChatGPT Sep 17 files.

---

## 6. Forbidden claims (unchanged)

- **0.85** or **0.5** as NLM / travel probability / skill
- Trail AR F1 scored / “high accuracy” as a field metric
- **WEKA = NLM**
- RJ Ricasata as **COO** (he is **CFO**)
- “CMMC compliant” / “CMMC L2 certified”
- Live COP / live sensors when the banner is `live: false`
- Instant Deploy / “Trail AR v2 is on mycosoft.com”
- Inventing `forecast_p`
- CUI, FOUO, or real Army intel
- That the 4,760-cell planned matrix was executed

---

## 7. Deploy gate

| Gate | State 17 Sep 2026 |
|---|---|
| Instant Deploy | **HELD** |
| Merge to `main` | **No** until freeze-free + WEKA + NLM e2e |
| Sibling e2e `f6976835` | **Not** accepted as green in this pass |
| Public cutover | **No** |

Local demo only: `http://localhost:3010/fusarium/itdx/v2` and `http://localhost:3010/natureos/bluesight-trail`.
