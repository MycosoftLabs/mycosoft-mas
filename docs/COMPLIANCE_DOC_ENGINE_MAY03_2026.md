# Compliance document engine — NIST 800-171 (May 03, 2026)

**Date:** May 3, 2026  
**Status:** Complete  

## Pipeline

1. **Control state** — `mycosoft_mas/compliance/control_state.py` aggregates device inventory, incidents, red team findings, and related signals into a JSON snapshot (framework: NIST 800-171; see `docs/TACO_NIST_800_171_MAPPING_APR08_2026.md`).  
2. **Research** — `perplexity_client` (when API key present).  
3. **Authoring** — `anthropic_client` drafts SSP / POA&M markdown sections.  
4. **Review** — `openai_client` scores consistency / readability and suggests diffs.  
5. **Persist** — `soc_ops.compliance_docs` + `compliance_controls` via `soc` repository.

## MAS API

- Listing and regeneration routes under `/api/compliance/*` (see `myca_main.py` router includes).  
- Requires Postgres (`MINDEX_DATABASE_URL` / `DATABASE_URL`).

## Website

- **`/security/compliance`** — tab **SSP / POA&M (MAS)** polls `/api/security?action=mas-compliance-bundle`; **Regenerate** posts `mas_compliance_regenerate` then refetches (admin-only).

## Operational notes

- Regeneration incurs external LLM cost; rate-limit via Guardian or cron on MAS if abuse is a concern.  
- Store **model id / version** metadata on each doc row for audit (see repository fields).
