# External Repository Classification — Adopt, Prototype, Watchlist, Do Not Integrate

**Date**: March 10, 2026  
**Author**: MYCA  
**Status**: Complete

## Overview

Classification of 18 external GitHub repositories against Mycosoft architecture. Each repo is assigned to **Adopt Now**, **Prototype**, **Watchlist**, or **Do Not Integrate**, with rationale and insertion points.

**Reference**: [External Repo System Boundaries](./EXTERNAL_REPO_SYSTEM_BOUNDARIES_MAR10_2026.md)

---

## Adopt Now (4)

### Turfjs/turf

| Field | Value |
|-------|-------|
| **Rationale** | Direct fit for CREP geospatial preprocessing, bbox math, clustering prep, local-first map logic. No overlap with existing stacks. |
| **Insertion Points** | WEBSITE `app/api/crep/*`, CREP data adapters, MINDEX-backed geo UIs. |
| **Where** | `app/api/crep/fungal/route.ts` and related CREP adapters; any geo preprocessing in WEBSITE API routes. |

---

### Leaflet/Leaflet

| Field | Value |
|-------|-------|
| **Rationale** | Already effectively in the website stack. Standardize as lightweight 2D map layer; avoid ad hoc map choices. |
| **Insertion Points** | WEBSITE device maps, observation maps, non-WebGL CREP dashboards. |
| **Where** | Device manager maps, CREP observation views; keep deck.gl for heavier WebGL CREP surfaces. |

---

### micnncim/action-label-syncer

| Field | Value |
|-------|-------|
| **Rationale** | Immediate repo-governance win across MAS, WEBSITE, MINDEX, SDK, and other repos. Low risk, high organizational value. |
| **Insertion Points** | GitHub Actions; shared org label manifests. |
| **Where** | `.github/workflows/` in each repo; org-level label config. |

---

### cyxzdev/Uncodixfy

| Field | Value |
|-------|-------|
| **Rationale** | Useful as Cursor/design-generation rule asset, not as runtime code. Strengthens website-dev and mobile-engineer workflows. |
| **Insertion Points** | Internal Cursor rules/skills for website-dev and mobile-engineer. |
| **Where** | `.cursor/rules/`, `.cursor/skills/`; do not add to WEBSITE runtime. |

---

## Prototype (6)

### mudler/LocalAI

| Field | Value |
|-------|-------|
| **Rationale** | Strongest fit for local-first inference, GPU node, Jetson, fallback serving. Aligns with MYCA local/edge inference needs. |
| **Condition** | Controlled prototype only; overlaps with Ollama and current voice/inference paths. |
| **Insertion Points** | GPU node, Jetson/Mushroom devices, MAS provider abstraction, local inference fallback. |
| **Where** | MAS LLM provider layer; validate against `docs/TEST_VOICE_LOCAL_FIX_MAR10_2026.md` and v9 roadmap. |

---

### AlexsJones/llmfit

| Field | Value |
|-------|-------|
| **Rationale** | Helps choose right local models for dev machine, GPU node, Jetson instead of guessing. |
| **Insertion Points** | Ops tooling, deployment planning, model routing heuristics. |
| **Where** | Scripts, deployment docs; not runtime. |

---

### anthropics/financial-services-plugins

| Field | Value |
|-------|-------|
| **Rationale** | Useful for CFO/C-suite specialization patterns, not platform-wide adoption. |
| **Insertion Points** | CFO MCP workflows, MYCA finance/corporate assistants, C-suite VM patterns. |
| **Where** | `mycosoft_mas/finance/`, C-Suite API; see `docs/CFO_MCP_CONNECTOR_COMPLETE_MAR08_2026.md`. |

---

### KeygraphHQ/shannon

| Field | Value |
|-------|-------|
| **Rationale** | Valuable as sandbox/staging pentest layer for WEBSITE, MAS, MINDEX. |
| **Condition** | Security validation only; localhost/sandbox only. |
| **Insertion Points** | Security validation before deploy. |
| **Where** | Local dev and sandbox flows; never production. |

---

### benchmark-action/github-action-benchmark

| Field | Value |
|-------|-------|
| **Rationale** | Useful once stable benchmarks exist for MAS latency, MINDEX queries, CREP/map transforms. |
| **Insertion Points** | GitHub Actions in mycosoft-mas, website, mindex. |
| **Where** | `.github/workflows/`; add only after defining minimal benchmark suite. |

---

### sheeki03/tirith

| Field | Value |
|-------|-------|
| **Rationale** | Directly relevant to AI-agent terminal safety in Cursor/MCP-heavy environment. |
| **Insertion Points** | Internal dev machine, MYCA coding VM workflows, command safety hardening. |
| **Where** | Operator/CTO workflows; Cursor integration for command validation. |

---

## Watchlist (4)

### PrefectHQ/prefect

| Field | Value |
|-------|-------|
| **Rationale** | Technically strong but overlaps with MAS + n8n orchestration. |
| **Condition** | Worthwhile only if MINDEX ETL grows beyond current scheduling and retry needs. |
| **Revisit When** | ETL scheduling becomes a documented gap. |

---

### plotly/plotly.py

| Field | Value |
|-------|-------|
| **Rationale** | Good for Python-generated scientific reports and notebooks; weak fit for main Next.js runtime. |
| **Revisit When** | Scientific report generation becomes a documented need; prefer WEBSITE-first viz. |

---

### cloudflare/vinext

| Field | Value |
|-------|-------|
| **Rationale** | Strategically interesting for Workers-first website hosting; too experimental for current runtime. |
| **Revisit When** | Migrating WEBSITE to Workers; requires explicit plan. |

---

### bcicen/ctop

| Field | Value |
|-------|-------|
| **Rationale** | Useful operator tool; not a subsystem. |
| **Revisit When** | Ops tooling audit; low priority. |

---

## Do Not Integrate (4)

### ultrafunkamsterdam/nodriver

| Field | Value |
|-------|-------|
| **Reason** | Anti-bot browser automation is poor fit for Mycosoft compliance, stability, and trust posture. |

---

### VeNoMouS/cloudscraper

| Field | Value |
|-------|-------|
| **Reason** | Cloudflare-bypass tooling conflicts with Mycosoft's own Cloudflare posture; adds legal/reputational risk. |

---

### theajack/disable-devtool

| Field | Value |
|-------|-------|
| **Reason** | Security theater; hostile to debugging/accessibility; not meaningful platform security. |

---

### ghostty-org/ghostty

| Field | Value |
|-------|-------|
| **Reason** | Developer terminal choice only; no meaningful integration path into MYCA/platform; weak Windows fit. |

---

## Summary Table

| Category | Count | Repos |
|----------|-------|-------|
| Adopt Now | 4 | Turf, Leaflet, action-label-syncer, Uncodixfy |
| Prototype | 6 | LocalAI, llmfit, financial-services-plugins, shannon, github-action-benchmark, tirith |
| Watchlist | 4 | Prefect, plotly.py, vinext, ctop |
| Do Not Integrate | 4 | nodriver, cloudscraper, disable-devtool, ghostty |

---

## Related Documents

- [External Repo System Boundaries](./EXTERNAL_REPO_SYSTEM_BOUNDARIES_MAR10_2026.md)
- [External Repo Implementation Streams](./EXTERNAL_REPO_IMPLEMENTATION_STREAMS_MAR10_2026.md)
- [External Repo Gap Alignment](./EXTERNAL_REPO_GAP_ALIGNMENT_MAR10_2026.md)
