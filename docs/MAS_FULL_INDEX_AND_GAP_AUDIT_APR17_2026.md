# MAS Full Index + Gap Audit (MYCA / MINDEX / AVANI / MYCOBRAIN / Website)

**Date:** 2026-04-17  
**Scope:** `mycosoft_mas` monorepo only (code + docs pointers), focused on “what is finished vs what is still unfinished/vital”.

## 1) Current MAS index view (high-level)

### Core runtime and API surfaces
- MAS API entrypoint is `mycosoft_mas/core/myca_main.py` and mounts the major router surfaces (agents, search, memory, integrations, scientific, world/voice streams, etc.).
- Router footprint is large (`mycosoft_mas/core/routers`: **127** Python files).

### Key MYCA execution planes
- `mycosoft_mas/harness` (**17** Python files): Nemotron, PersonaPlex ASR/TTS bridge, MINDEX grounding path, intention brain, NLM interface.
- `mycosoft_mas/myca/os` (**28** Python files): MYCA OS gateways, bridges, comms, orchestration.
- `mycosoft_mas/llm` (**45** Python files): backend selection, provider abstractions, routing.

### Knowledge / governance / intelligence planes
- `mycosoft_mas/mindex` (**28** Python files): MINDEX clients/bridge/sync helpers.
- `mycosoft_mas/nlm` (**29** Python files): training, inference, calibration, model wrappers.
- `mycosoft_mas/avani` (**14** Python files): AVANI constitutional/governor layers.

### Integration and edge planes
- `mycosoft_mas/integrations` (**101** Python files): external systems, infra clients, adapters.
- `mycosoft_mas/voice` (**13** Python files): voice runtime support.
- `mycosoft_mas/web` currently minimal backend footprint in this repo; frontend source-of-truth is primarily in the website repo.

## 2) What is confirmed complete/recent for MYCA harness

From current repo docs and code wiring:
- Harness routes text through MINDEX-grounded path and Nemotron (`RouteType.MINDEX_GROUNDED`) with unified search context injection.
- Voice ingress transcribes then clears `raw_audio` so routing follows text semantics.
- Harness config resolves Nemotron defaults from backend selection (`get_backend_for_role(MYCA_CORE)`) plus `HARNESS_*` / `NEMOTRON_*` overrides.
- Optional harness API endpoints are documented (`/api/harness/health`, `/api/harness/packet`) when `HARNESS_API_ENABLED=1`.

## 3) Unfinished/stub gap scan (vital items first)

> Priority here is “blocks/weakens MYCA autonomous operation today” rather than cosmetic TODOs.

### P0 — highest urgency (affects live autonomy or fidelity)

1. **Harness NLM path still returns stubbed envelope/fallback behavior when full NLM path is unavailable** (`nlm_interface.py` explicitly marks stub fallback).
2. **Turbo-quant path is intentionally placeholder (zlib telemetry stand-in), not production quant transport**.
3. **MINDEX full-sync still has TODO with `db = None` placeholder (async DB not initialized in that path)**.
4. **MYCA OS gateway metrics endpoint still has TODO to fetch MINDEX metrics (`/api/mindex/metrics`)**.

### P1 — important (degrades quality/coverage or leaves fallback-only behavior)

5. **NLM training pipeline contains placeholder dataset/metrics behavior and TODO for real data source wiring (MINDEX/Qdrant/etc.)**.
6. **`integrations/clients/mindex_client.py` is explicitly documented as a “minimal stub” client**.
7. **UCP commerce adapter remains stub/no-op when live UCP endpoint is not configured**.
8. **Dashboard backend/UI has unfinished pieces (`MonitoringDashboard` stub + TODO for time filtering)**.

### P2 — structural quality gaps (not immediate outage, but should be cleaned)

9. **Multiple permissive `pass` exception handlers in MYCA OS and LLM paths can suppress actionable failures** (several files).
10. **Provider abstraction includes expected `NotImplementedError` contracts that require concrete provider support (e.g., embeddings)**.
11. **Several integrations return empty dict fallback (`{}`) on failure, reducing diagnosability if not logged upstream**.
12. **Some roadmap docs still contain open checklists around MINDEX/CREP/NLM/Jetson flows and should be reconciled against code reality before declaring full platform readiness.**

## 4) “Done now” execution checklist for vital MYCA function

### Wave A (same day)
- Implement real NLM frame/predict path in harness (`harness/nlm_interface.py`) behind current feature gate.
- Replace turbo-quant placeholder with real transport (or disable path entirely in prod to avoid false confidence).
- Complete MINDEX full-sync DB initialization path (`mindex/full_sync.py`).
- Implement/enable MYCA OS MINDEX metrics pull in gateway.

### Wave B (next 24–48h)
- Replace NLM trainer placeholders with actual data connectors and measurable training outputs.
- Upgrade stub MINDEX/UCP clients to full production clients or hard-fail with explicit capability flags.
- Add strict error telemetry where silent `pass`/`{}` fallback exists.

### Wave C (hardening)
- Run targeted integration tests for: Harness↔MINDEX, MYCA OS↔MINDEX metrics, PersonaPlex bridge, NLM predict/train, MycoBrain telemetry ingestion.
- Reconcile stale planning checklists in docs with implementation evidence to prevent drift.

## 5) Commands used for this audit

```bash
find mycosoft_mas -maxdepth 2 -type d | sort | head -n 200
python - <<'PY'
# directory-level code file counts across key subsystems
...
PY
rg -n "TODO|FIXME|TBD|NotImplementedError|pass\s*(#.*)?$|stub|placeholder" \
  mycosoft_mas/harness mycosoft_mas/mindex mycosoft_mas/nlm mycosoft_mas/avani \
  mycosoft_mas/bio mycosoft_mas/voice mycosoft_mas/integrations mycosoft_mas/web \
  mycosoft_mas/myca mycosoft_mas/myca2 mycosoft_mas/llm -S
```

## 6) Bottom line

- Your **MYCA harness core path is materially in place** (MINDEX-grounded + Nemotron + PersonaPlex wiring).
- The **remaining critical work** is mostly in placeholder/stub zones for NLM execution fidelity, quant transport, MINDEX sync initialization, and explicit production-grade adapters.
- If you want “MYCA can operate at will today,” treat the P0 list above as mandatory completion gates before broader feature expansion.

## 7) Execution handoff

- Implementation plan that operationalizes these gaps: `docs/MYCA_READINESS_EXECUTION_PLAN_APR17_2026.md`.
