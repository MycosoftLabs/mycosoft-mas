# Work, To-Dos, Gaps, and Missing Agents/Rules — Run-Through

**Date:** February 10, 2026  
**Purpose:** Single run-through of current work streams, to-dos, gaps, Cursor vs project alignment, and recommended missing sub-agents/rules for both Cursor and the project.

---

## 1. Current Work Streams and To-Dos

### Active / Recently Completed

| Stream | Status | Reference |
|--------|--------|-----------|
| MYCA True Consciousness | **Deployed** (Feb 11) | `docs/MYCA_CONSCIOUSNESS_DEPLOYMENT_FEB11_2026.md`, `MYCA_CONSCIOUSNESS_ARCHITECTURE_FEB10_2026.md` |
| Gap Agent (MAS + Cursor) | **Done** | `docs/GAP_AGENT_FEB10_2026.md`, `.cursor/agents/gap-agent.md`, `.cursor/rules/gap-agent-background.mdc` |
| Phase 1 Agent Runtime | **Done** | `docs/PHASE1_COMPLETION_LOG_FEB10_2026.md` |
| FCI Implementation | **Complete** (spec + schema + API) | `docs/FCI_IMPLEMENTATION_COMPLETE_FEB10_2026.md`, Mycorrhizae protocol spec |
| Fungi Compute App | **Complete** (STFT, spike train, causality, species DB) | `docs/FUNGI_COMPUTE_APP_FEB09_2026.md` |
| Fungi Electrical Signaling Science | **Doc complete** | `docs/FUNGI_ELECTRICAL_SIGNALING_SCIENCE_FEB10_2026.md` |
| Device Manager / Gateway | **Doc + API** | `docs/DEVICE_MANAGER_AND_GATEWAY_ARCHITECTURE_FEB10_2026.md` |
| Mycorrhizae on MAS VM | **Deployed** (188:8002) | `docs/MYCORRHIZAE_AND_MAS_DEPLOYMENT_COMPLETE_FEB10_2026.md` |
| GitHub push (HTTP 500) | **Fixed** (LFS `concurrenttransfers = 1`) | `docs/GITHUB_PUSH_500_ROOT_CAUSE_FEB10_2026.md` |

### Incomplete Plans (from plan-tracker)

| Plan | Status | Effort |
|------|--------|--------|
| MYCA Memory Integration | Not started | 22 hours |
| Voice System | ~40% done | Weeks |
| Scientific Dashboard Backend | UI only, no backend | Weeks |
| MyceliumSeg Phases 1,3,4 | Partial | Days |
| MAS Topology Real Data | Pending | Weeks |
| NLM Foundation Model | Not started | 12 weeks |
| NatureOS SDK | Not started | 10 weeks |
| Hybrid Firmware | Planning | Weeks |
| Scaling Plan 90 Days | Not started | 90 days |
| CREP Phase 5 Collectors | Partial | Days |
| Future Roadmap Phases 2–6 | Not started | Months |
| WebSocket Infrastructure | Not started | Weeks |

### Vision vs Implementation (from gap analysis)

| Component | Vision | Current | Gap |
|-----------|--------|---------|-----|
| FCI | Two-way fungal communication, bio-computation | Data structures + routing | **CRITICAL** |
| HPL | Full language, patterns, devices | Basic DSL, 8 keywords | **HIGH** |
| MINDEX | DeSci, AI/ML, carbon credits | PostgreSQL + API | **HIGH** |
| Mycorrhizae | Bridge to insights | HTTP pub/sub router | **MEDIUM** |
| GFST | Validated theory | No validation | **HIGH** |

---

## 2. Gaps Summary

### From Gap Agent / `gap_report_latest.json`

- **TODOs/FIXMEs/XXX/BUG markers:** Hundreds across MAS repo (many in docs and minified JS; code TODOs are the actionable set).
- **501 / stub routes:** Tracked by code-auditor and route-validator (7 broken API routes per full-context rule).
- **Bridge/integration gaps:** Gap agent suggests plans when two projects need a third connection; use `GET /agents/gap/scan` or `.cursor/gap_report_latest.json`.

### Known System Gaps (full-context rule)

| Category | Count | Priority |
|----------|-------|----------|
| TODOs/FIXMEs in code | 80+ | Medium–High |
| Placeholder/stub implementations | 50+ | Medium–High |
| Missing website pages | 15 | High |
| Broken API routes (501) | 7 | High |
| Incomplete plans/roadmaps | 17 | Track |
| Security flaw (base64 encryption) | 1 | Critical |
| Voice system completion | 40% | High |
| WebSocket infrastructure | Not built | Medium |

---

## 3. Cursor vs Project Alignment

**Current counts (source of truth):** See `docs/CURSOR_SUITE_AUDIT_FEB12_2026.md` — **32 sub-agents**, **25 rules**. MCPs and extensions: see `docs/CURSOR_MCP_AND_EXTENSIONS_FEB12_2026.md`.

### Cursor Agents (32 total in `.cursor/agents/` — see CURSOR_SUITE_AUDIT for full list)

**Development:** backend-dev, website-dev, dev-server-guardian, database-engineer, memory-engineer, device-firmware, websocket-engineer  
**Operations:** deploy-pipeline, devops-engineer, docker-ops, infrastructure-ops, process-manager, backup-ops  
**Quality/Audit:** code-auditor, gap-agent, plan-tracker, route-validator, stub-implementer, regression-guard, test-engineer, security-auditor  
**Domain:** scientific-systems, voice-engineer, earth2-ops, crep-collector, data-pipeline, n8n-workflow, n8n-ops, integration-hub, notion-sync, documentation-manager  
**Autonomous:** myca-autonomous-operator  

**Update applied:** Full list and counts in `docs/CURSOR_SUITE_AUDIT_FEB12_2026.md` (32 agents, 25 rules).

### Cursor Rules (25 in `.cursor/rules/`)

Full list in CURSOR_SUITE_AUDIT. Includes: agent-creation-patterns, agent-must-execute-operations, api-endpoint-patterns, autostart-services, cursor-docs-indexing, cursor-system-registration, dev-deploy-pipeline, dev-machine-performance, dev-server-3010, docker-management, fci-vision-alignment, gap-agent-background, memory-system-patterns, mycobrain-always-on, mycodao-agent, mycosoft-full-codebase-map, mycosoft-full-context-and-registries, no-git-lfs, python-coding-standards, python-process-registry, read-recent-docs-before-planning, testing-standards, vm-layout-and-dev-remote-services, vm-credentials, website-component-patterns.

### MAS Core Agent Registry (runtime agents, `mycosoft_mas/core/agent_registry.py`)

35+ agent_ids including: mycology_bio, mycology_knowledge, financial, finance_admin, corporate_ops, board_ops, legal_compliance, marketing, sales, project_manager, myco_dao, ip_tokenization, ip_agent, dashboard, opportunity_scout, research, experiment, token_economics, secretary, **gap_agent**, desktop_automation, mycobrain_device, mycobrain_ingestion, web_scraper, data_normalization, environmental_data, image_processing, growth_simulator, mycelium_simulator, compound_simulator, petri_dish_simulator, species_database, dna_analysis, mycelium_pattern, environmental_pattern, mycorrhizae_protocol.

**Note:** Cursor agents are *development/ops/audit* roles (who to @ in Cursor). MAS agents are *runtime* (orchestrator, voice, devices, gap scanner). They serve different purposes; alignment is “Gap” exists in both.

---

## 4. Missing Sub-Agents or Rules

### Cursor (additions recommended)

| Item | Type | Rationale |
|------|------|-----------|
| **gap-agent** | Agent | **DONE** — Already added to the “32 Specialized Sub-Agents” table in `mycosoft-full-context-and-registries.mdc`. |
| **fci-vision rule** | Rule | When touching FCI, HPL, or Mycorrhizae protocol code: read `docs/VISION_VS_IMPLEMENTATION_GAP_ANALYSIS_FEB10_2026.md` and `docs/FUNGI_ELECTRICAL_SIGNALING_SCIENCE_FEB10_2026.md`; align with vision where feasible. |
| **consciousness rule** (optional) | Rule | When touching MYCA consciousness modules (unified_router, Conscious/Subconscious/Soul layers): read `docs/MYCA_CONSCIOUSNESS_ARCHITECTURE_FEB10_2026.md` and deployment docs. |
| **fungi-compute agent** (optional) | Agent | Dedicated agent for Fungi Compute App (NatureOS app, oscilloscope, STFT, species DB). Could stay under **scientific-systems**; add only if that agent becomes overloaded. |

### Project (MAS / docs)

| Item | Type | Rationale |
|------|------|-----------|
| **Gap Agent** | MAS agent + API | **DONE** — `gap_agent.py`, `gap_api.py`, core + registry registration. |
| **Vision-gap tracker** | Doc or MAS task type | Vision vs implementation gap is documented; no separate “agent” required. Gap agent’s suggested_plans can reference vision-gap doc. Consider adding a short “vision alignment” section to MASTER_DOCUMENT_INDEX or a single `VISION_ALIGNMENT_FEB10_2026.md` that links FCI/HPL/MINDEX/GFST docs. |
| **Registry sync** | Process | When adding a new Cursor agent or MAS runtime agent, update: (1) `.cursor/rules/mycosoft-full-context-and-registries.mdc` if it’s a Cursor sub-agent, (2) `docs/SYSTEM_REGISTRY_FEB04_2026.md` and agent_registry for MAS agents. |

---

## 5. Recommended Next Steps

1. **Add FCI/vision rule** — Create `.cursor/rules/fci-vision-alignment.mdc`: when working on FCI, HPL, or Mycorrhizae protocol, read vision gap analysis and fungal signaling science; avoid building in ignorance of the stated vision.
2. **Optional consciousness rule** — If many edits touch consciousness code, add a short rule pointing to MYCA consciousness architecture and deployment docs.
3. **Keep gap-agent in the loop** — Use `@gap-agent` or the background rule when planning across repos or when the user asks “what’s missing?” or “find gaps.” Ensure `scripts/gap_scan_cursor_background.py` runs periodically if you want fresh `.cursor/gap_report_latest.json`.
4. **Registries** — After adding any new Cursor agent, add it to the “32 Specialized Sub-Agents” table in mycosoft-full-context-and-registries.mdc and to docs/CURSOR_SUITE_AUDIT_FEB12_2026.md (bump count). After adding any new MAS agent, register in `agent_registry.py` and SYSTEM_REGISTRY / API_CATALOG as per existing process.

---

## 6. Quick Reference

| What | Where |
|------|--------|
| Current work / to-dos | This doc §1; plan-tracker agent; MASTER_DOCUMENT_INDEX |
| Code/docs gaps | gap_report_latest.json; GET /agents/gap/scan; code-auditor, gap-agent |
| Vision vs implementation | VISION_VS_IMPLEMENTATION_GAP_ANALYSIS_FEB10_2026.md |
| Cursor sub-agents list | .cursor/agents/ (32); mycosoft-full-context-and-registries.mdc; CURSOR_SUITE_AUDIT_FEB12_2026.md |
| Cursor rules | .cursor/rules/ (25); CURSOR_SUITE_AUDIT_FEB12_2026.md |
| MCPs & extensions | docs/CURSOR_MCP_AND_EXTENSIONS_FEB12_2026.md |
| MAS runtime agents | mycosoft_mas/core/agent_registry.py; registry/agent_registry.py |
