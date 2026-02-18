# Cursor Team Audit — Subagents, Commands, Rules

**Date:** February 12, 2026  
**Status:** Complete  
**Purpose:** Single source of truth so every subagent, command, and rule is coded, workable, and active as a senior software team. Gaps fixed; problems removed or updated.

---

## 1. All 34 Subagents (Canonical List)

All live in `.cursor/agents/*.md`. Use the right agent for the task; involve **terminal-watcher** when any agent runs terminal commands.

### Development (8)

| Agent | Role | Key commands |
|-------|------|---------------|
| backend-dev | Python/FastAPI, MAS agents, APIs, integrations | pytest, poetry run, lint, start API |
| website-dev | Next.js, React, Tailwind, API routes | npm run dev:next-only, build, lint |
| mobile-engineer | Mobile responsiveness for all pages/apps | Audit breakpoints, touch targets, nav |
| dev-server-guardian | Dev server on 3010 only, no duplicate servers | start-dev.ps1, ensure-dev-server.ps1 (WEBSITE/website/scripts) |
| database-engineer | PostgreSQL, Redis, Qdrant, migrations | Migrations, SQL, docker |
| memory-engineer | 6-layer memory, MINDEX, context injection | Memory scripts, MINDEX APIs |
| device-firmware | MycoBrain ESP32, MDP, serial | Serial, MycoBrain service |
| websocket-engineer | WebSocket, SSE, SignalR | Run WS server, tests |

### Operations (9)

| Agent | Role | Key commands |
|-------|------|---------------|
| deploy-pipeline | Commit, push, Docker, VM restart, Cloudflare purge | git push, SSH to VMs, docker build/run, purge |
| devops-engineer | CI/CD, GitHub Actions, env | CI scripts, env config |
| docker-ops | Docker Desktop, containers, vmmem | docker ps/build/stop, prune |
| infrastructure-ops | VM, Docker, SSH, NAS, Proxmox | SSH, VM commands |
| process-manager | GPU cleanup, port conflicts, zombie processes, autostart | dev-machine-cleanup.ps1, autostart-healthcheck.ps1, netstat |
| terminal-watcher | Read terminals for errors, diagnostics, hot-reload | List/read terminals folder, check errors, run diagnostics |
| gpu-node-ops | GPU node gpu01 (192.168.0.190), PersonaPlex/Earth2 | ssh gpu01, nvidia-smi, docker on gpu01 |
| backup-ops | Cursor backup, Proxmox snapshots, DB backups | Backup scripts, schtasks |

### Quality/Audit (9)

| Agent | Role | Key commands |
|-------|------|---------------|
| bug-fixer | Diagnose and fix bugs from errors/stack traces | Reproduce, diagnose, patch, run tests |
| code-auditor | TODOs, FIXMEs, stubs, dead code | grep, rg, lint |
| gap-agent | Cross-repo gaps, missing connections, bridge gaps | gap_scan_cursor_background.py, gap_scan_cursor_index.py, read gap_report_*.json |
| plan-tracker | 650+ plans, roadmaps, stale work | List plans, PLAN_PROGRESS_*.md |
| route-validator | Missing pages, broken links, 501 routes | Check links, API routes |
| stub-implementer | Replace placeholders with real code | Implement stubs, update tests |
| regression-guard | Pre-deploy validation, health checks | Build, health endpoints |
| test-engineer | Unit/integration/API tests | pytest, npm test |
| security-auditor | Secrets, RBAC, vulnerabilities | Scan, audit |

### Domain (10)

| Agent | Role | Key commands |
|-------|------|---------------|
| scientific-systems | Lab, experiments, FCI, MycoBrain compute | Lab scripts, FCI APIs |
| voice-engineer | PersonaPlex, Moshi, intent, GPU voice | Start/stop voice services |
| earth2-ops | Earth2 simulation, weather models | Earth2 API, scripts |
| crep-collector | Aviation, maritime, satellite, weather | Collector scripts |
| data-pipeline | MINDEX ETL, scrapers, GBIF | ETL jobs, scrapers |
| n8n-workflow | n8n automation, webhooks | Workflow triggers |
| n8n-ops | n8n on MAS VM (188), health, credentials | SSH 188, n8n health |
| integration-hub | External API clients, keys, rate limits | API clients |
| notion-sync | Notion doc sync, watcher | notion_docs_sync.py, watcher |
| documentation-manager | Dated docs, registries, MASTER_DOCUMENT_INDEX | build_docs_manifest.py, update indexes |

### Autonomous (1)

| Agent | Role | Key commands |
|-------|------|---------------|
| myca-autonomous-operator | Auto-fix, auto-deploy, auto-maintain | All of the above as needed; use terminal-watcher for any terminal output |

---

## 2. All 32 Rules (Canonical List)

All live in `.cursor/rules/*.mdc`. `alwaysApply: true` = applies to every chat.

| Rule | Purpose | alwaysApply |
|------|---------|-------------|
| mycosoft-full-context-and-registries | Full context and registries before plan/code; 34 subagents; plan/task completion docs | true |
| agent-must-execute-operations | Never ask user to run commands; use run_terminal_cmd; load .credentials.local | true |
| **agent-must-invoke-subagents-and-docs** | **Canonical: at task start load docs + @-invoke or follow sub-agents; why they aren’t auto-invoked** | true |
| agent-must-invoke-subagents | Task-type table and checklist; same obligation (see agent-must-invoke-subagents-and-docs) | true |
| terminal-watcher-and-agent-tasks | When any agent runs terminal, involve terminal-watcher to read terminals for errors | true |
| plan-and-task-completion-docs | At plan completion create completion doc; at task completion update docs/indexes | true |
| python-process-registry | Ports, processes, GPU, autostart, VM services; read before starting anything | true |
| vm-layout-and-dev-remote-services | VM IPs (187/188/189), dev on 3010, MAS/MINDEX URLs | true |
| dev-server-3010 | Website dev on 3010 only; dev:next-only; start externally when possible | (globs) |
| run-servers-externally | Long-running servers (dev server, Moshi, Bridge) run in external terminal, not Cursor | true |
| dev-deploy-pipeline | Dev → sandbox pipeline; rebuild, purge Cloudflare | (globs) |
| dev-machine-performance | Why machine is slow; KillStaleGPU; npm run dev:next-only | (globs) |
| cursor-docs-indexing | CURSOR_DOCS_INDEX, docs_manifest.json, build_docs_manifest.py | true |
| read-recent-docs-before-planning | Read last 72 hrs docs before new work | (user rule) |
| cursor-system-registration | All agents in Cursor; sync from repos | (globs) |
| autostart-services | Notion watcher, backup; healthcheck script | true |
| docker-management | Docker resource, containers, vmmem; docker-ops | (globs) |
| mycobrain-always-on | MycoBrain service 24/7; device-firmware | (globs) |
| mobile-first-standards | Mobile-first; mobile-engineer | (globs) |
| gap-agent-background | Gap scan, gap_report_*.json; gap-agent | (globs) |
| deprecated-unifi-dashboard | Unifi dashboard deprecated; do not use | (globs) |
| vm-credentials | Credentials in .credentials.local | (globs) |
| agent-creation-patterns | BaseAgent, registration | (globs) |
| fci-vision-alignment | FCI alignment | (globs) |
| no-git-lfs | Do not use Git LFS | (globs) |
| website-component-patterns | Components, Tailwind, Shadcn | (globs) |
| mycosoft-full-codebase-map | 9 repos, key paths | true |
| python-coding-standards | Python style, type hints | (globs) |
| api-endpoint-patterns | FastAPI, routers | (globs) |
| memory-system-patterns | Memory layers, MINDEX | (globs) |
| testing-standards | pytest, coverage | (globs) |
| mycodao-agent | TypeScript, Next.js, port 3010, deployment | (globs) |

---

## 3. All 19 Skills (MAS .cursor/skills)

| Skill | Use when |
|-------|----------|
| create-api-endpoint | New FastAPI router/endpoints |
| create-api-route | New Next.js API route |
| create-mas-agent | New MAS agent (BaseAgent) |
| create-integration-client | New external service client |
| create-nextjs-page | New Next.js page |
| create-react-component | New React component (Shadcn/Tailwind) |
| database-migration | PostgreSQL schema changes |
| deploy-mas-service | Deploy/restart MAS on 188 |
| deploy-mindex | Deploy/restart MINDEX on 189 |
| deploy-website-sandbox | Deploy website to 187, purge Cloudflare |
| docker-troubleshoot | Container/daemon issues |
| run-system-tests | System health, VMs, APIs |
| security-audit | Secrets, RBAC, vulnerabilities |
| setup-env-vars | Website .env.local, API URLs |
| start-dev-website | Start dev server on 3010 |
| update-registries | After adding agents/APIs/docs |
| vm-health-check | Check 187/188/189 health |
| mobile-audit | Mobile responsiveness audit |
| gpu-node-deploy | Deploy to gpu01 |

---

## 4. Scripts and Commands Verification

| Referenced script/command | Location | Status |
|---------------------------|----------|--------|
| gap_scan_cursor_background.py | MAS/scripts/ | Exists |
| gap_scan_cursor_index.py | MAS/scripts/ | Exists |
| start-dev.ps1 | WEBSITE/website/scripts/ | Exists |
| ensure-dev-server.ps1 | WEBSITE/website/scripts/ | Exists |
| dev-machine-cleanup.ps1 | MAS/scripts/ | Exists |
| autostart-healthcheck.ps1 | MAS/scripts/ | Exists |
| build_docs_manifest.py | MAS/scripts/ | Exists |
| notion_docs_watcher.py | MAS/scripts/ | Exists |
| notion_docs_sync.py | MAS/scripts/ | Exists |

All dev-server-guardian and gap-agent commands point to existing scripts. Website scripts are run from **WEBSITE/website** repo root (path: `.\scripts\...`).

---

## 5. Gaps Fixed in This Audit

1. **Registry:** bug-fixer and gpu-node-ops were in `.cursor/agents/` but not in the full-context subagent list. **Fixed:** Added both; count updated 32 → 34.
2. **bug-fixer:** Missing "MANDATORY: Execute all operations yourself." **Fixed:** Added; aligns with other execution agents.
3. **gpu-node-ops:** Missing YAML frontmatter (name, description) and execute-mandatory. **Fixed:** Added frontmatter and execute-mandatory.
4. **SUBAGENT_ROLES_AND_COMMANDS:** bug-fixer and gpu-node-ops were missing from the roles/commands doc. **Fixed:** Added to Quality and Operations tables with terminal-watcher usage.

---

## 6. Problems Removed or Updated

1. **Inconsistent agent count:** Registry said "32" but listed 33 after terminal-watcher. **Updated:** "34 Specialized Sub-Agents" with bug-fixer and gpu-node-ops included.
2. **No single audit doc:** There was no one place listing every agent, rule, and skill with verification. **Added:** This document.
3. **execute-mandatory:** bug-fixer and gpu-node-ops did not state they must execute operations themselves. **Fixed:** Both now state MANDATORY execute and reference agent-must-execute-operations.mdc.

---

## 7. How to Use This Doc

- **At every chat when work is requested:** (1) Load CURSOR_DOCS_INDEX and task-relevant docs. (2) Pick the right subagent(s) from §1 and **@-invoke them or follow their agent file**. (3) If you run terminal commands, involve terminal-watcher. See `.cursor/rules/agent-must-invoke-subagents-and-docs.mdc`. Sub-agents are not auto-invoked — you must do this.
- **Before starting a task:** Pick the right subagent(s) from §1; if the task involves terminal (dev server, tests, build, deploy), involve terminal-watcher.
- **Rules:** §2 lists all rules; full-context and terminal-watcher and plan-and-task-completion-docs are always-on.
- **Skills:** §3 lists when to use each skill (read the SKILL.md for steps).
- **Commands/scripts:** §4 confirms referenced scripts exist and where they live.
- **Ongoing:** When adding a new agent or rule, add it here and to the full-context registry (if agent). When removing or deprecating, update this doc and the registry.

---

## 8. Related Docs

- `.cursor/rules/mycosoft-full-context-and-registries.mdc` — Full context and 34 subagents
- `docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md` — Per-agent subagents and terminal-watcher
- `.cursor/rules/terminal-watcher-and-agent-tasks.mdc` — Terminal monitoring requirement
- `.cursor/rules/plan-and-task-completion-docs.mdc` — Completion docs requirement
- `docs/MASTER_DOCUMENT_INDEX.md` — Document index
