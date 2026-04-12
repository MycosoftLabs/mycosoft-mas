# Deep Agents v0.5 Cross-System Hooks (Apr 9, 2026)

**Date:** Apr 9, 2026  
**Status:** In Progress (Cross-system integration pass completed)  
**Related:** `docs/DEEP_AGENTS_V05_INTEGRATION_PLAN.md`, `docs/DEEP_AGENTS_V05_FOUNDATION_IMPLEMENTATION_APR09_2026.md`

## Scope Delivered in This Pass

Expanded Deep Agents integration from a foundation-only layer into active cross-domain hooks for:

- NatureOS platform organization and federation flows
- Search orchestration entrypoint
- Security audit event ingestion
- Device registry and command operations
- MYCA voice orchestrator turns

## Implementation Details

### New Deep Agent Domain Hook Module

- Added `mycosoft_mas/deep_agents/domain_hooks.py`
 - `submit_domain_task(...)` submits context-rich domain tasks to Deep Agent orchestrator
 - `schedule_domain_task(...)` performs non-blocking async fan-out using `asyncio.create_task`
 - Domain-to-agent defaults cover `search`, `security`, `device`, `natureos`, and `myca`
 - Runtime-safe behavior: if Deep Agents are disabled by feature flags, hooks no-op
 - Feature gate: `MYCA_DEEP_AGENTS_DOMAIN_HOOKS_ENABLED` (default `true`)

### Hooked Systems

- `mycosoft_mas/core/routers/search_orchestrator_api.py`
 - Emits a Deep Agent follow-up task after unified search execution

- `mycosoft_mas/core/routers/security_audit_api.py`
 - Emits a Deep Agent security-review task when audit entries are logged

- `mycosoft_mas/core/routers/device_registry_api.py`
 - Emits a Deep Agent task on first device registration
 - Emits a Deep Agent task on successful device command execution

- `mycosoft_mas/core/routers/platform_api.py`
 - Emits NatureOS domain tasks for:
   - organization creation
   - member invitations
   - federation peer connections

- `mycosoft_mas/core/routers/voice_orchestrator_api.py`
 - Emits MYCA domain task for each processed voice/chat turn with intent/action metadata

- `mycosoft_mas/deep_agents/__init__.py`
 - Re-exported `schedule_domain_task` for centralized import surface

## Why This Matters

This pass extends Deep Agents from passive availability into active, event-driven orchestration paths that touch:

- NatureOS governance workflows
- search intelligence
- security operations
- device operations
- MYCA cognitive loop

This directly aligns with the integration plan requirement to support all major MYCA system surfaces rather than a single subsystem.

## Verification

Executed:

- `poetry run python -m compileall` on all changed modules
- linter diagnostics on all changed files (`ReadLints`) with no new errors

## Remaining Work

- Replace synchronous dispatch internals with fully async Deep Agent task-first flow where applicable
- Complete container/runtime dependency strategy for `deepagents`/`langchain` version isolation or migration
- Extend hooks into remaining MAS/NLM/MINDEX/WEBSITE pathways (including more NatureOS and search pipeline internals)
- Deploy and validate on VM topology with feature flags enabled
