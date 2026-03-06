# MYCA Staff Identity and Memory Complete

**Date**: March 6, 2026
**Author**: GPT-5.4 / MYCA
**Status**: Complete
**Related Plan**: `.cursor/plans/myca_full_omnichannel_b338cfc1.plan.md`

## Overview

Phase 3 of the MYCA full omnichannel execution plan is complete. MYCA now has a canonical staff registry path, sender-to-person resolution, and person-scoped conversational memory injection in the live reply pipeline instead of relying on stale hardcoded people data or Morgan-only memory behavior.

## Completed Work

### 1. Canonical Staff Registry

Created:

- `mycosoft_mas/myca/os/staff_registry.py`

This module now:

- loads the canonical staff roster from `config/org_roles.yaml`
- expands `${ENV_VAR}` placeholders used for channel IDs
- exposes a shared `load_staff_directory()` function
- resolves canonical `person_id` values from platform IDs, email, or known names

This becomes the common base for workspace operations, sender authorization, and runtime message handling.

### 2. Workspace Layer Now Uses The Canonical Registry

Updated:

- `mycosoft_mas/agents/workspace_agent.py`
- `mycosoft_mas/core/routers/workspace_api.py`

Key changes:

- `WorkspaceAgent` now uses the canonical staff directory instead of stale inline role definitions.
- Added `resolve_staff_member()` helper to workspace routing.
- Added `/api/workspace/inbox` so the workspace API matches the comms-hub polling contract.
- Upgraded workspace dispatch paths to use real Slack, Discord, Signal, WhatsApp, Asana, and email clients where possible instead of pure placeholders.

### 3. Sender Authorization Uses The Same Staff Source

Updated:

- `mycosoft_mas/security/platform_access.py`

Key changes:

- leadership/team resolution now derives from the canonical staff registry instead of a separate divergent static map
- Discord/phone/platform identity resolution can now flow through the same shared staff/channel registry

### 4. MYCA OS Message Loop Resolves Canonical People

Updated:

- `mycosoft_mas/myca/os/core.py`

Key changes:

- inbound messages now resolve a canonical `person_id`
- Morgan detection is no longer based only on caller flags
- person-scoped `session:last_topic:{person_id}` memory is written for non-Morgan conversations

### 5. Person-Scoped Memory And Role Context In Replies

Updated:

- `mycosoft_mas/myca/os/llm_brain.py`
- `mycosoft_mas/myca/os/executive.py`

Key changes:

- the live context builder now pulls person-scoped session memory when a canonical `person_id` is available
- known staff role/scopes are injected into the LLM context for reply generation
- non-Morgan staff messages now route through the real `llm_brain.respond()` path instead of only falling back to canned keyword-only responses

This does not yet finish the full omnichannel bus, but it materially improves the continuity and quality of staff-facing dialogue.

## Verification

### Import Verification

Verified clean imports for:

- `mycosoft_mas.myca.os.llm_brain`
- `mycosoft_mas.agents.workspace_agent`

### Regression Baseline

The targeted regression baseline remained green after these changes:

```bash
poetry run pytest tests/consciousness/test_world_model.py tests/integrations/test_natureos_client.py tests/core/test_voice_tools_natureos.py tests/test_memory_integration.py tests/test_intent_classifier.py
```

Result:

- `100 passed`
- `2 skipped`

## Files Changed For Phase 3

- `mycosoft_mas/myca/os/staff_registry.py`
- `mycosoft_mas/agents/workspace_agent.py`
- `mycosoft_mas/core/routers/workspace_api.py`
- `mycosoft_mas/security/platform_access.py`
- `mycosoft_mas/myca/os/core.py`
- `mycosoft_mas/myca/os/executive.py`
- `mycosoft_mas/myca/os/llm_brain.py`

## Remaining Gap After Phase 3

The staff identity/memory layer is now much stronger, but Phase 4 is still required so the omnichannel bus itself becomes fully coherent across:

- Discord
- Signal
- WhatsApp
- Slack
- Asana
- GitHub
- email

especially for shared threads, inbox aggregation, and platform-native participation.

## Related Documents

- [MYCA Runtime Hardening Complete](./MYCA_RUNTIME_HARDENING_COMPLETE_MAR06_2026.md)
- [MYCA Full-System Runtime Promotion Complete](./MYCA_FULL_SYSTEM_RUNTIME_PROMOTION_COMPLETE_MAR06_2026.md)
- [Organizational Structure Update Complete](./ORGANIZATIONAL_STRUCTURE_UPDATE_COMPLETE_MAR05_2026.md)
