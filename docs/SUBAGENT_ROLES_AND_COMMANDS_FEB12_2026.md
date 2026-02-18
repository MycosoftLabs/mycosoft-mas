# Subagent Roles and Commands by Agent

**Date:** February 12, 2026  
**Status:** Complete  
**Purpose:** For every agent working on a task: related subagents, their roles, commands, and when to use terminal-watcher for errors, diagnostics, and debugging (especially hot-reload).

---

## Session/task start: MUST invoke or follow sub-agents (every chat)

**Rule:** When the user asks you to **do work** (code, fix, deploy, plan, debug, test), you MUST:

1. **Load docs:** Read `.cursor/CURSOR_DOCS_INDEX.md` and any docs relevant to the task (e.g. voice → `VOICE_TEST_QUICK_START_FEB18_2026.md`, `MYCA_VOICE_TEST_SYSTEMS_ONLINE_FEB18_2026.md`). For plans, read last 7 days per `read-recent-docs-before-planning.mdc`.
2. **Identify sub-agents:** Use the tables below (and `docs/CURSOR_TEAM_AUDIT_FEB12_2026.md`) to pick which sub-agents own this work.
3. **Invoke or follow:** Either **@-mention** those sub-agents (e.g. @voice-engineer, @website-dev, @documentation-manager) or read their `.cursor/agents/<name>.md` and apply their "When Invoked" and commands yourself.
4. **Terminal:** If you run dev server, tests, build, or deploy, involve **terminal-watcher** (read terminals folder, check for errors).

See `.cursor/rules/agent-must-invoke-subagents-and-docs.mdc` and `.cursor/rules/mycosoft-full-context-and-registries.mdc` (step 0). **Sub-agents are not auto-invoked** — the current agent must do this every chat when work is requested.

---

## Terminal watcher (all terminal-using agents)

**Rule:** When any agent runs or monitors terminal commands (dev server, tests, build, deploy), involve **terminal-watcher** to read the terminals folder, detect errors, run diagnostics, and suggest fixes. See `.cursor/rules/terminal-watcher-and-agent-tasks.mdc`.

| Agent | Uses terminal? | Terminal-watcher role |
|-------|----------------|------------------------|
| backend-dev | Yes (tests, run server, lint) | Read terminal after tests/build; report errors. |
| website-dev | Yes (dev server, hot reload, build) | **Primary:** Read dev server terminal for compile/runtime errors; hot-reload diagnostics. |
| dev-server-guardian | Yes (start/fix dev server) | Read terminal after start; confirm no compile errors on 3010. |
| test-engineer | Yes (pytest, npm test) | Read test terminal for FAILED, exit code; run diagnostics. |
| deploy-pipeline | Yes (git, SSH, docker, purge) | Read deploy terminal for SSH/Docker/script errors. |
| myca-autonomous-operator | Yes (all of the above) | Use terminal-watcher for any command that produces terminal output. |
| regression-guard | Yes (build, health checks) | Read build/check terminal for failures. |
| process-manager | Yes (cleanup, port check) | Optional: confirm no new errors in terminals after kill/restart. |
| docker-ops | Yes (docker commands) | Read terminal for Docker errors. |
| devops-engineer | Yes (CI, scripts) | Read terminal for pipeline/script errors. |
| Other agents | If they run terminal commands | Involve terminal-watcher to check output for errors. |

---

## By agent: related subagents and commands

### Development agents

| Agent | Related subagents | Key commands (agent) | When to use terminal-watcher |
|-------|-------------------|------------------------|------------------------------|
| **backend-dev** | terminal-watcher, test-engineer, database-engineer, process-manager | Run tests, lint, start API server | After tests, after build; when tests fail or server won’t start. |
| **website-dev** | terminal-watcher, dev-server-guardian, mobile-engineer, test-engineer | `npm run dev:next-only`, build, lint | **Always** during hot-reload; read dev server terminal for compile/runtime errors. |
| **mobile-engineer** | terminal-watcher (if running dev/build), website-dev | Audit pages, check breakpoints | When dev server or build is run. |
| **dev-server-guardian** | terminal-watcher, process-manager | start-dev.ps1, ensure-dev-server.ps1, check 3010 | After starting server; confirm no errors in server terminal. |
| **database-engineer** | terminal-watcher, deploy-mindex skill | Migrations, SQL, docker | After migration or DB commands. |
| **memory-engineer** | terminal-watcher (if scripts run) | Memory scripts, MINDEX | When running scripts that output to terminal. |
| **device-firmware** | terminal-watcher, process-manager | Serial, MycoBrain service | When running service or serial tools. |
| **mycobrain-ops** | device-firmware, website-dev, terminal-watcher, process-manager | MycoBrain service, discover, firmware, UI | Full MycoBrain stack: services, firmware, UI, discovery, run/modify/upgrade. |
| **websocket-engineer** | terminal-watcher, backend-dev | Run WS server, tests | After starting server or running tests. |

### Operations agents

| Agent | Related subagents | Key commands (agent) | When to use terminal-watcher |
|-------|-------------------|------------------------|------------------------------|
| **deploy-pipeline** | terminal-watcher, regression-guard, docker-ops | git push, SSH, docker build/run, purge | After each deploy step; read deploy terminal for errors. |
| **devops-engineer** | terminal-watcher, docker-ops | CI scripts, GitHub Actions, env | When running CI or env scripts. |
| **docker-ops** | terminal-watcher, process-manager | docker ps/build/stop, prune | After Docker commands; check for Docker errors. |
| **infrastructure-ops** | terminal-watcher, process-manager | SSH, VM, NAS | After SSH or infra commands. |
| **process-manager** | terminal-watcher (optional) | dev-machine-cleanup.ps1, netstat, kill | After cleanup; optionally confirm terminals show no new errors. |
| **gpu-node-ops** | terminal-watcher (if deploy/run) | ssh gpu01, nvidia-smi, docker on gpu01 | When running GPU workloads or containers on gpu01. |
| **backup-ops** | terminal-watcher (if scripts run) | Backup scripts, scheduled tasks | When running backup scripts. |

### Quality / audit agents

| Agent | Related subagents | Key commands (agent) | When to use terminal-watcher |
|-------|-------------------|------------------------|------------------------------|
| **code-auditor** | stub-implementer, terminal-watcher (if lint run) | grep, lint, find TODOs | When running lint or other CLI tools. |
| **gap-agent** | plan-tracker, terminal-watcher (if scripts run) | Cross-repo search, suggest plans | When running any terminal commands. |
| **plan-tracker** | documentation-manager, terminal-watcher (if scripts run) | List plans, generate progress report | When running scripts. |
| **route-validator** | website-dev, terminal-watcher (if build run) | Check links, API routes | When running build or serve. |
| **stub-implementer** | terminal-watcher, test-engineer | Replace stubs, run tests | After code changes; read test/build terminal. |
| **regression-guard** | terminal-watcher, deploy-pipeline | Build, health checks, pre-deploy | **Always** read terminal during build and health checks. |
| **test-engineer** | terminal-watcher, backend-dev, website-dev | pytest, npm test, coverage | **Always** read test terminal for failures and stack traces. |
| **security-auditor** | terminal-watcher (if scan run) | Secret scan, RBAC check | When running scans that output to terminal. |
| **bug-fixer** | terminal-watcher, test-engineer | Reproduce, diagnose, patch, run tests | When reproducing or running tests; read terminal for stack traces. |

### Domain agents

| Agent | Related subagents | Key commands (agent) | When to use terminal-watcher |
|-------|-------------------|------------------------|------------------------------|
| **scientific-systems** | terminal-watcher (if run scripts) | Lab/experiment scripts | When running scripts. |
| **myca-voice** | voice-engineer, terminal-watcher, process-manager | MYCA voice docs, bridge flow, consciousness | When fixing MYCA persona/brain in voice; read voice docs first. |
| **voice-engineer** | terminal-watcher, process-manager | PersonaPlex, bridge, GPU | When starting/stopping voice services. |
| **earth2-ops** | terminal-watcher, process-manager | Earth2 API, GPU | When running Earth2 server. |
| **crep-collector** | terminal-watcher (if collectors run) | Collector scripts | When running collectors. |
| **data-pipeline** | terminal-watcher, database-engineer | ETL, GBIF, scrapers | When running ETL or pipeline commands. |
| **n8n-workflow** | terminal-watcher (if CLI used) | n8n CLI, webhooks | When using n8n CLI. |
| **n8n-ops** | terminal-watcher (if SSH/commands) | SSH to 188, n8n health | When running SSH or n8n commands. |
| **integration-hub** | terminal-watcher (if tests run) | API client tests | When running integration tests. |
| **mycobrain-ops** | device-firmware, website-dev, terminal-watcher | MycoBrain service, discover, firmware, UI | Full MycoBrain stack: run, modify, upgrade, ensure working. |
| **notion-sync** | terminal-watcher (if sync run) | notion_docs_sync, watcher | When running sync scripts. |
| **documentation-manager** | terminal-watcher (if manifest run) | build_docs_manifest.py | When running manifest or doc scripts. |

### Autonomous

| Agent | Related subagents | Key commands (agent) | When to use terminal-watcher |
|-------|-------------------|------------------------|------------------------------|
| **myca-autonomous-operator** | terminal-watcher, deploy-pipeline, process-manager, regression-guard | All terminal commands | **Always** when running any terminal command: deploy, test, build, dev server, scripts. |

---

## Terminal-watcher commands (quick reference)

| Command | Action |
|---------|--------|
| **Read terminals** | List terminals folder → read relevant `*.txt` → get full output. |
| **Check for errors** | Search output for Error, failed, Exception, Traceback, EADDRINUSE, compilation failed, exit ≠ 0. |
| **Check for warnings** | Search for Warning, warn, deprecated, React/Next hydration warnings. |
| **Hot-reload diagnostics** | For Next.js: "Failed to compile", "Module not found"; report file:line; suggest fix or `npm run build`. |
| **Run diagnostics** | Run lint, typecheck, or re-run failing command; summarize result. |
| **Suggest fix** | From stack trace: file, line, cause; suggest code/config change or port kill. |

Full command table and error patterns: `.cursor/agents/terminal-watcher.md`.

---

## Summary

- **Every agent** that runs or relies on terminal output should **involve terminal-watcher** to read terminals, detect errors, run diagnostics, and suggest fixes.
- **Hot-reload (website):** website-dev and dev-server-guardian use terminal-watcher to read the dev server terminal and report Next.js/React compile and runtime errors.
- **Subagent roles and commands** for each agent are listed above; terminal-watcher is the standard subagent for terminal monitoring and debugging across all of them.
