# Cursor Suite Audit — Rules, Agents, Indexing, Interaction

**Date:** February 12, 2026  
**Purpose:** Single reference for the Cursor rules, sub-agents, doc indexes, and how they interact. Use this to verify consistency and re-audit after adding rules/agents/docs.

---

## 1. Current Counts (source of truth)

| Item | Count | Location |
|------|--------|----------|
| **Rules** | 25 | `.cursor/rules/*.mdc` |
| **Sub-agents** | 32 | `.cursor/agents/*.md` |
| **Skills** | 17+ (MAS) + 6 (website) + 5 (Cursor-level) | `.cursor/skills/`, `WEBSITE/website/.cursor/skills/`, `~/.cursor/skills-cursor/` |

**Note:** `docs/WORK_TODOS_GAPS_AND_MISSING_AGENTS_RULES_FEB10_2026.md` mentions "29 agents, 18 rules"; that snapshot is from Feb 10. **Current counts above are authoritative** (this audit and `.cursor/rules/mycosoft-full-context-and-registries.mdc`). Rule count is 25 per glob of `.cursor/rules/*.mdc`.

---

## 2. All Rules (25)

| Rule | Purpose |
|------|---------|
| `agent-creation-patterns.mdc` | How to create MAS agents (BaseAgent, registration) |
| `agent-must-execute-operations.mdc` | Agents run commands themselves; never ask user to run terminal |
| `api-endpoint-patterns.mdc` | FastAPI router/endpoint patterns for MAS |
| `autostart-services.mdc` | Notion watcher, backup; healthcheck script; when to add autostart |
| `cursor-docs-indexing.mdc` | Vital vs full docs; CURSOR_DOCS_INDEX first; docs_manifest for discovery |
| `cursor-system-registration.mdc` | Sync rules/agents/skills via `scripts/sync_cursor_system.py` after changes |
| `dev-deploy-pipeline.mdc` | Dev on 3010, deploy to sandbox, NAS mount, Cloudflare purge |
| `dev-machine-performance.mdc` | Why machine is slow (GPU services); use dev:next-only; cleanup script |
| `dev-server-3010.mdc` | Dev server on port 3010 only; ensure-dev-server.ps1; no duplicate servers |
| `docker-management.mdc` | Docker resource management, container lifecycle, MAS coordination |
| `fci-vision-alignment.mdc` | FCI/HPL/Mycorrhizae vision alignment |
| `gap-agent-background.mdc` | Gap awareness in every chat; gap_report_index/latest; when to invoke gap-agent |
| `memory-system-patterns.mdc` | Memory system patterns for MAS |
| `mycobrain-always-on.mdc` | MycoBrain device/service always-on expectations |
| `mycodao-agent.mdc` | TypeScript/Next.js/React/Shadcn standards; port 3010; deployment checklist |
| `mycosoft-full-codebase-map.mdc` | Multi-root workspace; repo inventory (9 repos) |
| `mycosoft-full-context-and-registries.mdc` | Full context first; 32 sub-agents; indexes/registries table; read before plan/code |
| `no-git-lfs.mdc` | Git LFS policy (e.g. PersonaPlex incident, concurrenttransfers) |
| `python-coding-standards.mdc` | Python style for MAS |
| `python-process-registry.mdc` | Port map, GPU services, autostart, one-shot scripts, kill commands |
| `read-recent-docs-before-planning.mdc` | Read CURSOR_DOCS_INDEX → MASTER_DOCUMENT_INDEX; last 7 days; registries; gap reports |
| `testing-standards.mdc` | Testing expectations for MAS |
| `vm-layout-and-dev-remote-services.mdc` | VM layout (187/188/189); dev using remote MAS/MINDEX; deploy flows |
| `vm-credentials.mdc` | VM SSH/sudo from `.credentials.local`; never ask user for password |
| `website-component-patterns.mdc` | Website component standards |

---

## 3. All Sub-Agents (32)

| Agent | Use For |
|-------|---------|
| `backend-dev` | Python/FastAPI, MAS agents, API endpoints, integrations |
| `website-dev` | Next.js, React, Tailwind, API routes |
| `dev-server-guardian` | Dev server on 3010 only; no duplicate npm; dev:next-only |
| `database-engineer` | PostgreSQL, Redis, Qdrant, migrations, pgvector |
| `memory-engineer` | 6-layer memory, MINDEX backend, context injection |
| `device-firmware` | MycoBrain ESP32, sensors, MDP, serial |
| `websocket-engineer` | WebSocket, SSE, SignalR, real-time |
| `deploy-pipeline` | Commit, push, Docker build, VM restart, Cloudflare purge |
| `devops-engineer` | CI/CD, GitHub Actions, Docker, env management |
| `docker-ops` | Docker containers, images, daemon; VM Docker troubleshoot |
| `infrastructure-ops` | VM management, Docker, SSH, NAS, Proxmox |
| `process-manager` | GPU cleanup, port conflicts, zombie processes, autostart |
| `backup-ops` | Cursor chat backup, Proxmox snapshots, DB backups |
| `code-auditor` | TODOs, FIXMEs, stubs, dead code |
| `gap-agent` | Cross-repo gaps, missing connections, bridge gaps; plans |
| `plan-tracker` | 650+ plans, roadmaps, stale/abandoned work |
| `route-validator` | Missing pages, broken links, 501 routes |
| `stub-implementer` | Replace placeholders with real implementations |
| `regression-guard` | Pre-deploy validation, health checks, build verification |
| `test-engineer` | Unit/integration/API tests |
| `security-auditor` | Secrets, RBAC, vulnerability scanning |
| `scientific-systems` | Lab, experiments, FCI, MycoBrain compute, DNA storage |
| `voice-engineer` | PersonaPlex, Moshi, intent, GPU voice |
| `earth2-ops` | Earth2 simulation, prediction, weather models |
| `crep-collector` | Aviation, maritime, satellite, weather data |
| `data-pipeline` | MINDEX ETL, scrapers, GBIF, blob, NAS |
| `n8n-workflow` | n8n workflow automation, webhooks, triggers |
| `n8n-ops` | n8n on MAS VM, workflows, health, credentials |
| `integration-hub` | External API clients, API keys, rate limits |
| `notion-sync` | Notion doc sync, watcher, categorization |
| `documentation-manager` | Dated docs, registry updates, MASTER_DOCUMENT_INDEX |
| `myca-autonomous-operator` | Auto-fix, auto-deploy, auto-maintain |

---

## 4. Index Flow and “Read First” Order

1. **First (vital/current):** `.cursor/CURSOR_DOCS_INDEX.md` — Curated vital and current docs; new replaces old.  
   See `.cursor/rules/cursor-docs-indexing.mdc` and `read-recent-docs-before-planning.mdc`.

2. **Second (full TOC):** `docs/MASTER_DOCUMENT_INDEX.md` — Full table of contents for all docs.

3. **Full discovery (all docs):** `.cursor/docs_manifest.json` — All .md paths/titles/repos.  
   Regenerate: `python scripts/build_docs_manifest.py`.

4. **Gap intake:**  
   - `.cursor/gap_report_index.json` — Missing work in *indexed* files (MASTER_DOCUMENT_INDEX).  
   - `.cursor/gap_report_latest.json` — Repo-wide gaps (TODOs, stubs, 501, bridge gaps).  
   Regenerate index: `python scripts/gap_scan_cursor_index.py`.  
   Full scan: `python scripts/gap_scan_cursor_background.py`.  
   See `.cursor/rules/gap-agent-background.mdc`.

5. **Registries (before plan/code):**  
   - `docs/SYSTEM_REGISTRY_FEB04_2026.md`  
   - `docs/API_CATALOG_FEB04_2026.md`  
   - `docs/system_map.md`  
   - `docs/MEMORY_DOCUMENTATION_INDEX_FEB05_2026.md` (when relevant)

---

## 5. Interaction Checklist

- **Rules ↔ Agents:** Agents reference rules (e.g. `dev-server-guardian` → `dev-server-3010.mdc`; `documentation-manager` → CURSOR_DOCS_INDEX, docs_manifest; `gap-agent` → gap_report files). All rule filenames above exist in `.cursor/rules/`.
- **Rules ↔ Docs:** `read-recent-docs-before-planning.mdc` and `cursor-docs-indexing.mdc` point to CURSOR_DOCS_INDEX, MASTER_DOCUMENT_INDEX, docs_manifest. `mycosoft-full-context-and-registries.mdc` includes Cursor docs index in the indexes table.
- **Docs ↔ Indexes:** Entries in CURSOR_DOCS_INDEX and MASTER_DOCUMENT_INDEX should point to existing files. ALWAYS_ON_SERVICES_FEB12_2026 is in both; CURSOR_DOCS_INDEX is the canonical “vital” list.
- **Scripts:**  
  - `scripts/build_docs_manifest.py` → `.cursor/docs_manifest.json`  
  - `scripts/gap_scan_cursor_index.py` → `.cursor/gap_report_index.json`  
  - `scripts/gap_scan_cursor_background.py` → `.cursor/gap_report_latest.json`  
  - `scripts/sync_cursor_system.py` → register rules/agents/skills (see `cursor-system-registration.mdc`)

---

## 6. MCPs, Extensions, and Sub-Agent Usage

- **MCPs:** Cursor uses `.mcp.json` in repo root (github, mindex-db). User may have Supabase, Context7, Cloudflare, cursor-ide-browser. See **`docs/CURSOR_MCP_AND_EXTENSIONS_FEB12_2026.md`** for which MCP to use when and which sub-agents should use them.
- **Sub-agents:** Use all 32; @-invoke or follow the right agent for the task (dev vs ops vs quality vs domain). Full list in Section 3 above.
- **Extensions:** No workspace `.vscode/extensions.json` yet; optional to add recommendations. Backup-ops backs up `mcp.json`.

---

## 7. Re-audit After Changes

- **New rule:** Add to this audit (Section 2), run `scripts/sync_cursor_system.py`, and ensure any agent that should follow it references it. Re-count rules with a glob of `.cursor/rules/*.mdc` and update Section 1.
- **New agent:** Add to this audit (Section 3) and to the table in `mycosoft-full-context-and-registries.mdc` (update “32” to new count), run sync script.
- **New vital doc:** Add to `.cursor/CURSOR_DOCS_INDEX.md` (and optionally MASTER_DOCUMENT_INDEX), then run `python scripts/build_docs_manifest.py`.
- **New MCP or extension:** Document in `docs/CURSOR_MCP_AND_EXTENSIONS_FEB12_2026.md` and which sub-agents should use it.
- **Count drift:** If rule or agent count changes, update Section 1 and the full-context rule so they stay in sync.
