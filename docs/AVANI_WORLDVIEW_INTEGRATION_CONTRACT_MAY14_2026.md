# AVANI Worldview Integration Contract - 2026-05-14

## Purpose
AVANI governs the transformation from internal MAS WorldState to customer-facing MINDEX Worldview responses.

Canonical flow:

`Sensors / NLM / Earth Sim / MINDEX / devices / human-economic context -> MAS WorldState -> AVANI grounding, governance, audit -> MINDEX Worldview API -> MYCA, agent customers, human customers`

## Ownership
- MAS `/api/myca/world/*` is the internal canonical live WorldState surface.
- AVANI is the governance and audit authority for WorldState release and action gating.
- MINDEX `/api/worldview/*` is the paid/read-only customer distribution API.
- Specialist commands remain separate from worldstate/worldview and must be AVANI-gated before execution.

## Runtime Interfaces
- `GET /api/avani/worldstate` returns a compact AVANI governance snapshot of MAS WorldState.
- `GET /api/avani/context` returns current AVANI season, governed worldstate, and runtime governance posture.
- `POST /api/avani/preflight` is the shared action-capable preflight for MYCA, agents, workflows, model promotion, Earth Sim commands, red-team operations, and system configuration.
- `POST /api/avani/device/preflight` reviews hardware/device commands with telemetry trust, operator identity, ecological impact, reversibility, rollback plan, season, and audit metadata.
- `POST /api/avani/grounding-check` evaluates whether a claim/action is grounded by supplied evidence.
- `POST /api/avani/worldview/review` reviews a filtered MINDEX Worldview response before customer release.
- `GET /api/avani/operator/status` returns scoped operator status: season, operational posture, storage mode, audit verification, recent denials, device preflights, and Worldview reviews.

## Worldview Metadata
Worldview response `data` remains backward-compatible. AVANI governance is attached under `meta.avani` with:
- `avani_verdict`
- `audit_trail_id`
- `worldstate_snapshot_id`
- `freshness`
- `degraded`
- `confidence`
- `provenance`
- `sensitivity`
- `ecological_risk`
- `governance_notes`

## Production Configuration
- `AVANI_OPTIONAL`: set only to `true`, `1`, or `yes` when MAS may boot without AVANI. Default behavior is critical/fail-loud.
- `AVANI_AUDIT_LEDGER_DIR`: local JSONL fallback directory when MINDEX/Postgres is unavailable.
- `MINDEX_API_URL`: MINDEX API base URL.
- `MINDEX_API_KEY`: API key used by MAS/AVANI for MINDEX-backed storage or calls.
- `MINDEX_INTERNAL_TOKEN`: internal MINDEX service token where internal routes require it.
- `AVANI_API_URL`: MINDEX-side base URL for MAS or standalone AVANI, used by Worldview governance review.
- `AVANI_API_KEY`: scoped key used by MINDEX to call `POST /api/avani/worldview/review`; must include `avani:evaluate`.

## Required AVANI Scopes
- `avani:evaluate`: proposal, message, grounding, ecological, and worldview review.
- `avani:update`: season updates.
- `avani:root`: Frost/Winter recovery and root authority behavior.
- `avani:audit:read`: audit reads, stats, verification, context/worldstate snapshots.

## Failure Policy
- Low-risk read-only Worldview responses may return with explicit degraded AVANI metadata if AVANI is unreachable.
- Internal, telemetry, device, command, or high-risk domains fail closed or return an AVANI-governed denial.
- Tool execution, device control, model promotion, Earth Sim commands, system config, and irreversible workflows fail closed when AVANI is unavailable.
- Hardware commands require trusted telemetry, operator identity, bounded ecological impact, reversibility context, and a rollback plan for high-impact or low-reversibility actions.

## Current Enforcement Hooks
- MYCA tool pipeline gates `execute_workflow`, `generate_workflow`, and outbound omnichannel sends through local AVANI preflight before execution.
- TAC-O voice deployment commands run AVANI device review before any sensor deployment command is sent.
- Red-team medium/high/critical simulations run AVANI preflight before Guardian authority approval.
- MINDEX Worldview routes call AVANI review after auth/filtering and before customer response; existing `data` payloads remain unchanged while governance appears under `meta.avani`.

## Verification
- MAS: `PYTHONPATH=.; pytest tests/test_avani`
- MINDEX: targeted Worldview tests must prove `meta.avani` is present and `data` payload compatibility is preserved.
