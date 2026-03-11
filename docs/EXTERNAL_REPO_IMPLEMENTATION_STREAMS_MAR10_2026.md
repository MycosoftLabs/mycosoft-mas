# External Repository Implementation Streams — Phased Plan

**Date**: March 10, 2026  
**Author**: MYCA  
**Status**: Complete

## Overview

Phased implementation streams for integrating external repositories into Mycosoft. Each stream has explicit phases, dependencies, and success criteria.

**Reference**: [External Repo Classification](./EXTERNAL_REPO_CLASSIFICATION_MAR10_2026.md)

---

## Stream 1: Geo and CREP Standardization

**Repos**: Turfjs/turf, Leaflet/Leaflet  
**Category**: Adopt Now

### Phase 1: Dependency Add and Leaflet Standardization
- Add `@turf/helpers`, `@turf/bbox`, `@turf/cluster` (or full turf) to WEBSITE `package.json`.
- Standardize Leaflet usage: audit existing map components; choose Leaflet for device maps, observation maps, non-WebGL CREP dashboards.
- Keep deck.gl for heavier WebGL CREP surfaces.

### Phase 2: Turf-Based Spatial Preprocessing
- Add Turf-based spatial preprocessing for bbox clipping, clustering prep, and geometry math in WEBSITE API routes.
- Tie to CREP local-first path in `app/api/crep/fungal/route.ts`.
- Align with LOD plan in `docs/CREP_INATURALIST_MINDEX_ETL_MAR09_2026.md`.

### Success Criteria
- CREP geo math uses Turf; no ad hoc spatial math.
- Device/observation maps use Leaflet; deck.gl reserved for high-density WebGL views.

---

## Stream 2: Local Inference and Edge Intelligence

**Repos**: mudler/LocalAI, AlexsJones/llmfit  
**Category**: Prototype

### Phase 1: Model Selection Tooling (llmfit)
- Use llmfit as planning/ops layer to select deployable local models for dev PC, GPU node, Jetson variants.
- Document model choices and fit for each environment.

### Phase 2: LocalAI Prototype
- Prototype LocalAI as an OpenAI-compatible local inference endpoint behind MAS provider abstractions.
- No direct browser dependency; MAS routes requests.
- Validate against voice and runtime topology in `docs/TEST_VOICE_LOCAL_FIX_MAR10_2026.md`, `docs/CUDA_GRAPH_REENABLED_PERSONAPLEX_MAR10_2026.md`, and myca-voice-v9 plan.

### Success Criteria
- llmfit used for model selection; LocalAI prototype behind MAS provider layer without replacing Ollama/PersonaPlex.

---

## Stream 3: Governance and Finance Specialization

**Repos**: micnncim/action-label-syncer, anthropics/financial-services-plugins  
**Category**: Adopt Now (action-label-syncer) / Prototype (financial-services-plugins)

### Phase 1: Label Syncer (Adopt)
- Add `action-label-syncer` to GitHub Actions in MAS, WEBSITE, MINDEX, SDK repos.
- Create shared org label manifest.
- No runtime impact; governance only.

### Phase 2: Finance Plugin Patterns (Prototype)
- Extract ideas from financial-services-plugins for CFO/C-suite plugin structure, domain prompts, finance workflow packaging.
- Map onto Mycosoft surfaces in `docs/CFO_MCP_CONNECTOR_COMPLETE_MAR08_2026.md`.
- Keep implementation inside MAS C-suite agents and VM personas, not WEBSITE runtime.

### Success Criteria
- Labels harmonized across repos; CFO workflows enhanced with plugin-style patterns, without platform-wide Anthropic binding.

---

## Stream 4: Security and Operational Guardrails

**Repos**: sheeki03/tirith, KeygraphHQ/shannon, benchmark-action/github-action-benchmark  
**Category**: Prototype

### Phase 1: tirith Shell Protection
- Prototype tirith for internal shell protection in MYCA/Cursor operator workflows.
- Run on internal dev machine and MYCA coding VM flows.

### Phase 2: shannon Sandbox Pentest
- Run shannon only against localhost/sandbox flows.
- Measure exploit-finding value; never against production.

### Phase 3: Benchmark Suite (Conditional)
- Add `github-action-benchmark` only after defining minimal benchmark suite (MAS latency, MINDEX queries, CREP/map transforms).
- Do not add benchmarks prematurely.

### Success Criteria
- tirith tested for command safety; shannon run only in sandbox; benchmarks added only with clear suite definition.

---

## Stream 5: Repo and Design Hygiene

**Repos**: cyxzdev/Uncodixfy, action-label-syncer (covered in Stream 3)  
**Category**: Adopt Now (Uncodixfy as rules/skills)

### Phase 1: Uncodixfy as Cursor Guidance
- Convert useful ideas from Uncodixfy into internal Cursor rules/skills for website-dev and mobile-engineer.
- Do not add to WEBSITE product code; design-generation guidance only.

### Phase 2: Label Syncer (see Stream 3)
- Covered in Stream 3, Phase 1.

### Success Criteria
- Uncodixfy-derived guidance in `.cursor/rules/` or `.cursor/skills/`; labels synced across repos.

---

## Recommended Execution Order

1. **Low-risk operational wins**: action-label-syncer, Uncodixfy-derived Cursor guidance.
2. **Geo stack**: Turf + Leaflet where WEBSITE has natural seam.
3. **Local inference prototype**: llmfit + LocalAI in isolated local/GPU-node contexts.
4. **Security/ops**: tirith, shannon for internal validation.
5. **Finance specialization**: financial-services-plugins patterns for CFO/C-suite.
6. **Watchlist revisit**: Prefect, plotly.py, vinext, ctop only after platform gaps are reduced.

---

## Dependency Summary

| Stream | Depends On | Blocks |
|--------|------------|--------|
| Stream 1 (Geo) | None | CREP LOD work |
| Stream 2 (Local Inference) | Voice topology stable | - |
| Stream 3 (Governance/Finance) | None | - |
| Stream 4 (Security) | None | - |
| Stream 5 (Hygiene) | None | - |

---

## Related Documents

- [External Repo Classification](./EXTERNAL_REPO_CLASSIFICATION_MAR10_2026.md)
- [External Repo System Boundaries](./EXTERNAL_REPO_SYSTEM_BOUNDARIES_MAR10_2026.md)
- [External Repo Gap Alignment](./EXTERNAL_REPO_GAP_ALIGNMENT_MAR10_2026.md)
