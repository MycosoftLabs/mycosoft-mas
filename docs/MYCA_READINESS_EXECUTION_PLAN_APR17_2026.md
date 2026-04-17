# MYCA Readiness Execution Plan (Make It Real) — Apr 17, 2026

**Purpose:** turn the Apr 17 audit into an executable engineering plan with concrete code changes, acceptance tests, and rollout gates.

**Scope:** MAS repo (`mycosoft_mas`) with direct dependencies on MINDEX, PersonaPlex GPU nodes, NLM, AVANI, MycoBrain, and website-facing APIs.

---

## 1) Success criteria (hard gates)

We consider this complete only when all are true:

1. Harness NLM path runs real model-backed inference in production mode (no stub fallback for normal operation).
2. Turbo-quant path is either real transport or fully disabled in prod (no placeholder pretending to be production).
3. MINDEX full-sync path initializes DB client/pool and performs an end-to-end sync without `db = None` placeholders.
4. MYCA OS gateway surfaces real MINDEX metrics (or a strict error state with actionable diagnostics).
5. NLM trainer uses real connectors (MINDEX/Qdrant or configured equivalents) and emits non-placeholder datasets/metrics.
6. Stub-only integration clients used by production flows are replaced or hard-failed behind capability flags.
7. Regression + integration tests pass for harness, NLM, MINDEX bridge, and MYCA gateway metrics surfaces.

---

## 2) Workstreams and exact files

## WS-A — Harness/NLM productionization (P0)

### A1. Replace harness NLM stub-first behavior
**Files:**
- `mycosoft_mas/harness/nlm_interface.py`
- `mycosoft_mas/harness/engine.py`
- `mycosoft_mas/harness/config.py`

**Implementation:**
- Add explicit runtime modes: `stub|local|remote` (env-driven).
- In `local` mode, load NLM runtime adapter and execute real frame + predict.
- In `remote` mode, call configured NLM endpoint with typed request/response contract.
- Keep `stub` allowed only for tests/dev; in prod, fail fast if model unavailable.

**Acceptance:**
- `HarnessResult.structured` includes real model metadata (`model_id`, `inference_ms`, `confidence`) not `frame_stub`.
- Unit tests validate each mode and error behavior.

### A2. Turbo-quant placeholder removal
**Files:**
- `mycosoft_mas/harness/turbo_quant.py`
- `mycosoft_mas/harness/nemotron_client.py`

**Implementation:**
- Add `HARNESS_TURBO_QUANT_MODE=disabled|measure_only|transport`.
- `transport` must call real quant endpoint/protocol.
- In production profile, block `measure_only` unless explicitly approved via env flag.

**Acceptance:**
- No ambiguous placeholder wording in runtime path.
- Telemetry labels distinguish measured bytes vs transported bytes.

---

## WS-B — MINDEX reliability and gateway observability (P0)

### B1. MINDEX full-sync DB initialization
**File:**
- `mycosoft_mas/mindex/full_sync.py`

**Implementation:**
- Replace `db = None` placeholder with real async DB/pool bootstrap.
- Add health precheck + retries with bounded backoff.
- Add structured failure errors (connection/auth/schema).

**Acceptance:**
- Sync command returns non-zero on hard failure with clear reason.
- Integration test runs with test DB and verifies at least one sync cycle.

### B2. MYCA gateway MINDEX metrics implementation
**File:**
- `mycosoft_mas/myca/os/gateway.py`

**Implementation:**
- Implement TODO for `/api/mindex/metrics` pull.
- Add timeout, auth header handling, cache TTL, and degraded mode response.
- Expose provenance field: `metrics_source=live|cached|unavailable`.

**Acceptance:**
- Gateway endpoint returns populated metrics when MINDEX is up.
- Returns explicit degraded payload (not silent pass) when MINDEX is down.

---

## WS-C — NLM trainer and integration clients (P1)

### C1. Remove placeholder dataset/metrics in trainer
**Files:**
- `mycosoft_mas/nlm/training/trainer.py`
- `mycosoft_mas/nlm/trainer.py`

**Implementation:**
- Implement dataset provider abstraction with real sources.
- Replace placeholder IDs/records with source-derived records.
- Compute real training/eval metrics with consistent schema.

**Acceptance:**
- Trainer output contains source lineage + non-placeholder sample IDs.
- Calibration artifacts reflect real run metadata.

### C2. Upgrade stub clients on production path
**Files (minimum):**
- `mycosoft_mas/integrations/clients/mindex_client.py`
- `mycosoft_mas/integrations/ucp_commerce_adapter.py`

**Implementation:**
- Replace minimal stub client with full request/response client (typed errors).
- Keep stubs only behind explicit `*_ALLOW_STUB=true` dev flags.
- Fail closed for prod routes if critical client not configured.

**Acceptance:**
- Health endpoints expose capability status (`enabled`, `configured`, `stub_mode`).
- Production profile rejects stub-mode calls for critical flows.

---

## WS-D — Error handling hardening (P1/P2)

**Files (representative):**
- `mycosoft_mas/myca/os/*.py`
- `mycosoft_mas/llm/*.py`
- `mycosoft_mas/integrations/*.py`

**Implementation:**
- Replace silent `pass` blocks on critical paths with structured logs + typed fallback.
- Replace bare `{}` fallbacks where they hide operational errors.
- Add correlation IDs across harness → gateway → MINDEX/NLM calls.

**Acceptance:**
- No silent swallow on core request path exceptions.
- Errors observable in logs and metrics dashboards.

---

## 3) Test plan (must pass)

## Unit + component
- `poetry run pytest tests/test_harness_smoke.py -v`
- `poetry run pytest tests/test_memory_integration.py -v`
- `poetry run pytest tests/test_static_system_integration.py -v`
- Add new tests:
  - `tests/test_harness_nlm_modes.py`
  - `tests/test_mindex_full_sync_db_init.py`
  - `tests/test_myca_gateway_mindex_metrics.py`

## Integration (LAN/staging)
- Harness packet flow with MINDEX grounding on/off.
- NLM local and remote inference modes.
- Gateway metrics when MINDEX healthy/unhealthy.
- MycoBrain telemetry -> MINDEX ingest -> MYCA readback loop.

## Runtime smoke
- `GET /api/harness/health`
- `POST /api/harness/packet`
- Gateway metrics endpoint (with MINDEX source state)
- MINDEX sync job status endpoint/log check

---

## 4) Rollout sequence

1. **Phase 0:** Feature flags added, default-safe behavior preserved.
2. **Phase 1:** Deploy WS-A + WS-B to staging (no prod traffic).
3. **Phase 2:** Run full test matrix + soak for 24h.
4. **Phase 3:** Deploy WS-C + WS-D to staging; repeat soak.
5. **Phase 4:** Canary production (10% traffic) with rollback guardrails.
6. **Phase 5:** Full production cutover + post-cutover verification.

---

## 5) Rollback rules

Immediate rollback if any of the following occurs:
- Harness error rate > 3% for 10 min.
- MINDEX sync failure sustained > 15 min.
- Gateway metrics endpoint returns malformed payloads.
- NLM inference latency exceeds SLA and queue depth breaches threshold.

Rollback actions:
- Disable new modes via env flags (`HARNESS_NLM_MODE=stub`, `HARNESS_TURBO_QUANT_MODE=disabled`).
- Revert deployment image to previous stable tag.
- Keep diagnostics snapshots for incident review.

---

## 6) Owner-ready execution checklist

### P0 (Do now)
- [ ] WS-A A1 complete + tests
- [ ] WS-A A2 complete + tests
- [ ] WS-B B1 complete + tests
- [ ] WS-B B2 complete + tests

### P1 (Next)
- [ ] WS-C C1 complete + tests
- [ ] WS-C C2 complete + tests
- [ ] WS-D core-path hardening complete

### Exit criteria
- [ ] All gates in Section 1 satisfied
- [ ] Staging soak completed with no P0/P1 incidents
- [ ] Production canary + full rollout completed

