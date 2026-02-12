# Cursor MCPs, Extensions, and Sub-Agent Usage

**Date:** February 12, 2026  
**Purpose:** Ensure all sub-agents, MCPs (Model Context Protocol servers), and extensions are used properly. Single reference for “when to use which tool.”

---

## 1. MCPs — What Cursor Uses

### Repo config (`.mcp.json` in MAS repo root)

| Server | Type | Purpose | Env / config |
|--------|------|---------|--------------|
| **github** | http | GitHub API (PRs, issues, repos, search) | `GITHUB_PAT` in env |
| **mindex-db** | stdio | MINDEX DB access via @bytebase/dbhub | `MINDEX_DATABASE_URL` in env |

Ensure `GITHUB_PAT` and `MINDEX_DATABASE_URL` are set (e.g. in Cursor settings or `.env`) so these MCPs work.

### Cursor-provided / user-configured MCPs (when available)

If your Cursor has these MCPs enabled, use them as below:

| MCP | Use for | Sub-agents that should use it |
|-----|---------|-------------------------------|
| **GitHub** | PRs, issues, branches, search, file contents, review | deploy-pipeline, devops-engineer, integration-hub, documentation-manager, myca-autonomous-operator |
| **Supabase** | Docs, DB tables, migrations, auth, logs, types, Edge Functions | database-engineer, memory-engineer, backend-dev, website-dev (when using Supabase) |
| **Context7** | Up-to-date library docs (resolve-library-id, query-docs) | backend-dev, website-dev, integration-hub — use before guessing API usage |
| **Cloudflare** | KV, Workers, R2, D1, Queues, AI, routes, cron, zones | infrastructure-ops, deploy-pipeline (when deploying to Cloudflare) |
| **cursor-ide-browser** | Navigate, snapshot, click, type, fill, test UI in browser | website-dev, test-engineer, regression-guard — for UI verification |
| **mindex-db** | Direct MINDEX DB queries (when configured) | database-engineer, data-pipeline, memory-engineer |

---

## 2. Using Sub-Agents Properly

- **@-invoke the right agent** for the task (see `docs/CURSOR_SUITE_AUDIT_FEB12_2026.md` for the full list of 32 agents).
- **Development:** backend-dev (Python/MAS/APIs), website-dev (Next.js/React), database-engineer (Postgres/Redis/Qdrant), memory-engineer (memory/MINDEX), device-firmware (MycoBrain), websocket-engineer (real-time).
- **Operations:** deploy-pipeline (deploy, Cloudflare purge), devops-engineer (CI/CD), docker-ops (Docker lifecycle), infrastructure-ops (VMs, NAS), process-manager (GPU/ports/autostart), backup-ops (backups).
- **Quality:** code-auditor, gap-agent, plan-tracker, route-validator, stub-implementer, regression-guard, test-engineer, security-auditor — use for audits, gaps, tests, security.
- **Domain:** scientific-systems, voice-engineer, earth2-ops, crep-collector, data-pipeline, n8n-workflow, n8n-ops, integration-hub, notion-sync, documentation-manager.
- **Autonomous:** myca-autonomous-operator — for auto-fix, auto-deploy, cross-system maintenance.

When a task spans multiple areas (e.g. deploy + DB + website), use or reference multiple agents rather than one generic pass.

---

## 3. MCP Usage by Task Type

| Task | Prefer MCP(s) | Prefer sub-agent(s) |
|------|----------------|---------------------|
| GitHub PR/issue/search | GitHub | deploy-pipeline, documentation-manager |
| Supabase schema/auth/Edge Functions | Supabase | database-engineer, backend-dev, website-dev |
| Library/framework docs | Context7 | backend-dev, website-dev, integration-hub |
| Cloudflare Workers/KV/D1 | Cloudflare | infrastructure-ops, deploy-pipeline |
| Browser UI test / click-through | cursor-ide-browser | website-dev, test-engineer, regression-guard |
| MINDEX schema/query (if mindex-db enabled) | mindex-db | database-engineer, data-pipeline, memory-engineer |

---

## 4. MAS Runtime MCP Config (separate from Cursor)

The MAS codebase has `mycosoft_mas/config/mcp_servers.yaml` for **MAS runtime** MCP clients (primary, secondary, tool_integration, cursor_mcp, chatgpt, elevenlabs, space_weather, environmental, earth_science, financial, automation, defense). That config is for the orchestrator/integrations on the MAS VM, **not** for Cursor IDE. Cursor uses `.mcp.json` (and any user-added MCPs). Do not confuse the two.

---

## 5. Extensions

- **Workspace:** The MAS repo does not currently have `.vscode/extensions.json`. To recommend extensions for the workspace, add that file with `recommendations` (e.g. Python, Pylance, ESLint, Prettier, Docker).
- **Cursor built-in:** Cursor provides terminal, search, codebase indexing, and MCP tooling. Prefer using MCPs and sub-agents over asking the user to install extra extensions unless a specific need is documented.
- **Backup-ops** includes `mcp.json` in backup scope (see `.cursor/agents/backup-ops.md`); keep MCP config in version control or backed up as appropriate.

---

## 6. Checklist for “Using Everything Properly”

1. **Before coding:** Read indexes (CURSOR_DOCS_INDEX, MASTER_DOCUMENT_INDEX) and relevant registries; check gap reports if planning.
2. **Sub-agents:** For the current task, pick the right agent(s) from the 32 and @-invoke or follow their guidance.
3. **MCPs:** For GitHub → use GitHub MCP; for Supabase → use Supabase MCP; for library docs → use Context7; for Cloudflare → use Cloudflare MCP; for UI testing → use cursor-ide-browser; for MINDEX DB (if configured) → use mindex-db.
4. **Registries:** After adding agents/endpoints/docs, update CURSOR_SUITE_AUDIT, full-context rule, SYSTEM_REGISTRY, API_CATALOG, and run `scripts/sync_cursor_system.py` for rules/agents/skills.
5. **Manifest:** After adding many new docs, run `python scripts/build_docs_manifest.py` to refresh `.cursor/docs_manifest.json`.
