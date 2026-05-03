# Compound Analyser — Chemputer Agent MVP Complete (May 03, 2026)

**Date:** May 03, 2026  
**Status:** MVP complete  
**Related plan shell:** `docs/COMPOUND_ANALYSER_CHEMPUTER_AGENT_PLAN_MAY01_2026.md`

## What shipped

| Component | Detail |
|-----------|--------|
| **MAS agent** | `ChemputerAgent` (`mycosoft_mas/agents/lab/chemputer_agent.py`) — resolves compounds via **MINDEX only** (`GET …/compounds/{id}`); rejects raw SMILES without MINDEX resolution in MVP. |
| **MAS API** | `POST /api/natureos/lab/chemputer/plan` — body `{ compound_id, smiles? }`; **404** when compound missing (`compound_not_found` in message); **502** for other failures. |
| **Website BFF** | `app/api/natureos/lab/chemputer/plan/route.ts` proxies MAS. |
| **UI** | `/natureos/compound-analyser` embeds `CompoundSimEmbed` → same UX as `app/apps/compound-sim/page.tsx`: “Chemputer plan” for **MINDEX UUIDs**; blocks stub `cs-*` IDs; shows `experiment_plan` / structured errors only. |

## Registry

- `docs/SYSTEM_REGISTRY_FEB04_2026.md` — NatureOS Lab MVP agents table.
- `docs/API_CATALOG_FEB04_2026.md` — MAS + website proxy rows.

## Deferred

- RDKit-backed retrosynthesis service contract.
- SMILES → MINDEX resolution path.
- Persistent experiment log table beyond agent JSON response.
