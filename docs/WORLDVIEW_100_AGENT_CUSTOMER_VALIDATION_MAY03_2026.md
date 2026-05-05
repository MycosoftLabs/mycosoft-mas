# Worldview — 100 Agent Customer Validation — MAY03_2026

**Date:** May 03, 2026  
**Status:** In progress (harness + scripts landed; payments live path stub; waves to execute under caps)

## Purpose

Validate production **mycosoft.com** Worldview v1 under realistic load using **100 internal** subaccounts (Mycosoft Inc. sole payer), 20 archetypes × 5 agents, mixed frameworks (70 local-style / 30 cloud API), with treasury caps and kill switch.

## Implementation map

| Area | Location |
|------|----------|
| Preflight checklist | `docs/AGENT100_PREFLIGHT_MAY03_2026.md` |
| Harness | `mycosoft_mas/agent100/` |
| SQL | `migrations/agent100_tables.sql` |
| CLI | `scripts/agent100/*.py` |
| Matrix | `mycosoft_mas/agent100/configs/agents_matrix.yaml` |

## Operating sequence

1. Apply SQL in Supabase (if persisting calls/charges).
2. Set env: `AGENT100_WORLDBASE_URL`, per-agent `AGENT100_KEY_*`, caps, optional `NEXT_PUBLIC_SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.
3. Clear `data/agent100/STATE.json` → `{"halted": false}` or remove file.
4. `python scripts/agent100/spawn.py --wave1 --mode health` → expand to wave2/wave3.
5. `python scripts/agent100/report.py` for aggregates.
6. Kill: `python scripts/agent100/kill_all.py`.

## Whitepaper

Synthesis of per-archetype metrics, dataset/mode matrix, and agent feedback belongs in the final whitepaper section after wave3 completes; this document tracks scope and file map until then.
