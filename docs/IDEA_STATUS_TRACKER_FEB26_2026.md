# Idea Status Tracker FEB26_2026

## Purpose
Living, system-wide status tracker for all ideas in
`docs/MYCA_Master_Ideas_Concepts_Resources.md` (834 entries). This tracker
applies status overrides and cross-references to all entries in that source
catalog.

## Source Catalog (All 834 ideas)
Full categorized list (verbatim) lives here:
- `docs/MYCA_Master_Ideas_Concepts_Resources.md`

## Default Status Rules
- All ideas are **Not Started** unless listed in Status Overrides.
- If an idea maps to an existing system, set status to **Implemented** or **Partial**
  and include concrete code references.

## Cross-Repo Codebase Reference Map
- MAS: `mycosoft_mas/agents/`, `mycosoft_mas/core/routers/`, `mycosoft_mas/bio/`,
  `mycosoft_mas/memory/`, `mycosoft_mas/voice/`, `mycosoft_mas/simulation/`
- MINDEX: `mindex_api/routers/`, `mindex_etl/jobs/`, `migrations/`
- NLM: `nlm/api/`, `nlm/biology/`, `nlm/chemistry/`, `nlm/physics/`
- Mycorrhizae: `mycorrhizae/`, `api/`, `mycorrhizae/fci/`, `mycorrhizae/hpl/`
- Website: `app/`, `components/`, `lib/`, `app/api/`

## Status Overrides (Implemented / Partial)

### MYCA / MAS / AI System
- **Implemented**: Multi-agent orchestration (`mycosoft_mas/core/orchestrator.py`)
- **Implemented**: Grounded cognition (`mycosoft_mas/memory/`, `mindex_api/routers/grounding.py`)
- **Implemented**: Voice system code complete (`mycosoft_mas/voice/`) - GPU hardware blocked
- **Implemented**: FCI signal processing (`mycosoft_mas/bio/fci.py`, `mindex` FCI schema)
- **Implemented**: A2A protocol (`mycosoft_mas/integrations/a2a_client.py`)
- **Partial**: Real-time telemetry dashboard (Website UI exists, needs live data integration)

### Applications & Products
- **Implemented**: Petri Dish Simulator (`mycosoft_mas/simulation/`, Website UI)
- **Implemented**: NatureOS Dashboard (Website `app/natureos/`)
- **Implemented**: Device Portal (Website `app/devices/`)
- **Partial**: Compounds data (MINDEX implemented, no simulator UI)

### Science & Biology
- **Implemented**: MINDEX taxonomy (`mindex_api/routers/taxon.py`)
- **Implemented**: Chemical compounds (`mindex_api/routers/compounds.py`)
- **Implemented**: Genetic sequences (`mindex_api/routers/genetics.py`)
- **Implemented**: DNA storage system (`mycosoft_mas/bio/dna_storage.py`)
- **Partial**: M-Wave analyzer (Mycorrhizae `mycorrhizae/mwave/`, pipeline missing)

### Hardware & Lab
- **Implemented**: MycoBrain firmware (repo `mycobrain/`)
- **Implemented**: MDP v1 protocol (Mycorrhizae `mycorrhizae/protocols/mdp_v1.py`)
- **Partial**: FCI hardware integration (Mycorrhizae `mycorrhizae/fci/` exists, device drivers missing)

## Update Policy
When the source catalog changes, update Status Overrides and re-run the
cross-reference pass to reflect new or implemented ideas.
