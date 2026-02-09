# MyceliumSeg Integration Plan – February 6, 2026

## Purpose

Plan for end-to-end integration of the **MyceliumSeg** scientific dataset and boundary-aware evaluation into Mycosoft’s Petri Dish Simulator, MINDEX, NatureOS, and MAS.

**Sources:** [Nature paper](https://www.nature.com/articles/s41597-025-06265-1), [Zenodo 15224240](https://zenodo.org/records/15224240), [MyceliumSeg-benchmark](https://github.com/nodefather/MyceliumSeg-benchmark), [Mycelium Dataset.md](./Mycelium%20Dataset.md), [Mycelium Sim Data integration plan.docx.md](./Mycelium%20Sim%20Data%20integration%20plan.docx.md).

---

## Goals

1. **Scientific validation:** Run segmentation metrics (IoU, F1, Boundary IoU, HD95, ASSD) on real/mycelium data and surface results in the Petri Dish Simulator.
2. **Minimal user input:** One-click “Run validation” and full automation (create job, run, show results).
3. **MYCA automation:** Voice tool so MYCA can run validation experiments on request.
4. **Single source of truth:** Website repo for the live site; unifi-dashboard is not used for the website.

---

## Phases (plan)

| Phase | Scope | Status |
|-------|--------|--------|
| **Phase 0** | MINDEX schema, ingest, metrics engine, validation API, one-shot `POST /validation/run`, MYCA voice tool, standalone HTML panel | Done |
| **Phase 1** | Full job queue, per-sample overlays, aggregate reporting | Planned |
| **Phase 2** | Validation panel in Petri Dish Simulator (Website), NLM dashboards, apps listing | Done (simulator panel) |
| **Phase 3** | Simulator calibration; mask export | Planned |
| **Phase 4** | MAS nightly validation, regression gate, science report | Planned |

---

## Implementation (done)

### MAS repo (this repo)

- **Backend / API:** `scripts/myceliumseg/` — api_routes, metrics, run_validation_job, serve_api (port 8010).
- **Migration:** `migrations/021_myceliumseg.sql`.
- **Ingest:** `scripts/ingest_myceliumseg.py` (`--fixture` / `--dir`).
- **MYCA voice tool:** `run_myceliumseg_validation` in `mycosoft_mas/core/routers/voice_tools_api.py` (apply via `scripts/myceliumseg/apply_voice_tool.py`).
- **Standalone UI:** `docs/myceliumseg_validation_panel.html` (one-click run + results).

### Website repo (Petri Dish Simulator integration)

- **Petri Dish Simulator page:** [sandbox.mycosoft.com/apps/petri-dish-sim](https://sandbox.mycosoft.com/apps/petri-dish-sim).
- **MyceliumSeg validation panel (built in):**
  - `components/scientific/myceliumseg-validation-panel.tsx` — one-button “Run validation now”, calls `POST {apiUrl}/validation/run`, displays aggregate + per-sample metrics (real data only).
  - `app/apps/petri-dish-sim/page.tsx` — includes `<MyceliumsegValidationPanel />` below the mycelium simulator.
- **Env:** `lib/env.ts` — `myceliumsegApiUrl` (NEXT_PUBLIC_MYCELIUMSEG_API_URL or MYCELIUMSEG_API_URL, default `http://localhost:8010/mindex/myceliumseg`).

To see validation on the live simulator: set the MyceliumSeg API base URL for the environment (e.g. sandbox) and ensure the MyceliumSeg API is reachable from the browser or via a proxy.

---

## Quick reference

- **One-shot validation:** `POST /mindex/myceliumseg/validation/run` with body `{ "dataset_slice": { "limit": 5 } }`.
- **MYCA:** Invoke tool `run_myceliumseg_validation` (optional query e.g. “limit 10”).
- **Website:** Live site = Website repo only; unifi-dashboard is not used for the website.

---

## References

- Paper: [A Mycelium Dataset with Edge-Precise Annotation for Semantic Segmentation](https://www.nature.com/articles/s41597-025-06265-1) (Scientific Data, 2025).
- Dataset: [Zenodo 15224240](https://zenodo.org/records/15224240).
- Code: [MyceliumSeg-benchmark](https://github.com/nodefather/MyceliumSeg-benchmark).
