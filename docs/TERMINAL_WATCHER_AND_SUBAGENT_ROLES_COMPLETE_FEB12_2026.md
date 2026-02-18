# Terminal Watcher and Subagent Roles — Implementation Complete

**Date:** February 12, 2026  
**Status:** Complete  

## Delivered

1. **terminal-watcher subagent** (`.cursor/agents/terminal-watcher.md`)
   - Reads Cursor terminals folder for active terminal output.
   - Detects errors, warnings, build failures, hot-reload failures (Next.js/React).
   - Commands: Read terminals, Check for errors, Check for warnings, Hot-reload diagnostics, Run diagnostics, Suggest fix.
   - Error patterns: build/compile, runtime, network/port, tests, hot reload, tooling (ESLint/TS/Prettier).
   - Protocol: list terminals → read output → scan → report → optionally run diagnostics.

2. **Rule: terminal-watcher and agent tasks** (`.cursor/rules/terminal-watcher-and-agent-tasks.mdc`, always apply)
   - Any agent that runs or monitors terminal commands must involve terminal-watcher to read terminals and check for errors.
   - Task types: website dev (hot reload), tests, builds, deploy scripts, lint/typecheck, long-running scripts.
   - Protocol: parent agent runs command → involves terminal-watcher → terminal-watcher reads and reports → parent fixes or reports.

3. **Subagent roles and commands doc** (`docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md`)
   - Table: every agent that uses terminal + terminal-watcher role.
   - Per-agent tables: related subagents, key commands, when to use terminal-watcher (development, operations, quality, domain, autonomous).
   - Terminal-watcher command quick reference.

4. **Registry update**
   - `terminal-watcher` added to the 32 specialized subagents in `mycosoft-full-context-and-registries.mdc` (Operations).
   - `docs/MASTER_DOCUMENT_INDEX.md` updated with Subagent Roles and Terminal Watcher entry.

## Verification

- Invoke **terminal-watcher** when any agent has started dev server, tests, build, or deploy: "Read the terminals folder and check for errors."
- During **hot-reload** website work: terminal-watcher reads the dev server terminal and reports compile/runtime errors and suggested fixes.
- Full mapping of **which agent uses which subagents and commands** is in `docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md`.

## Related

- Rule: `.cursor/rules/terminal-watcher-and-agent-tasks.mdc`
- Agent: `.cursor/agents/terminal-watcher.md`
- Reference: `docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md`
