# Nemotron Rollback Runbook — MAR31 2026

Date: 2026-03-31  
Status: Active

## Rollback Triggers

Trigger rollback for a category if any condition holds for two consecutive windows:

- p95 latency exceeds configured gate
- fallback rate exceeds configured gate
- structured correctness drops below configured gate
- user-facing contract breaks (AVANI/website schema mismatch)

Gates are defined in `config/llm_migration_rollout.yaml`.

## Soft Rollback (Category-only)

Use when only one category is degraded.

```powershell
setx MYCA_BACKEND_MODE_<CATEGORY> llama
```

Examples:

```powershell
setx MYCA_BACKEND_MODE_CORPORATE llama
setx MYCA_BACKEND_MODE_NLM llama
```

Then restart MAS orchestrator service and rerun smoke matrix.

## Global Rollback (All categories)

Use when degradation is systemic.

```powershell
setx MYCA_BACKEND_MODE llama
```

Restart MAS service and validate:

```powershell
poetry run python scripts/llm/run_nemotron_smoke_matrix.py
```

Expected: providers resolve to `ollama` and fallback pressure drops.

## Post-Rollback Checklist

1. Confirm mode variables effective in runtime environment.
2. Confirm telemetry now shows expected provider.
3. Validate AVANI route contracts (`/api/myca`, `/api/myca/consciousness/chat`).
4. Keep rollout wave in pending state until root cause is resolved.

## Forward-Recovery

After issue resolution:

1. Re-enable category in hybrid mode.
2. Run smoke matrix and route parity checks.
3. Promote category back to Nemotron only after passing quality gates.

