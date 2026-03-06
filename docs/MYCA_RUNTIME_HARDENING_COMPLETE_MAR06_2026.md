# MYCA Runtime Hardening Complete

**Date**: March 6, 2026
**Author**: GPT-5.4 / MYCA
**Status**: Complete
**Related Plan**: `.cursor/plans/myca_full_omnichannel_b338cfc1.plan.md`

## Overview

Phase 1 of the MYCA full omnichannel execution plan is complete. The VM 191 runtime control plane is now materially safer, the credential/env contract is more consistent, and the deployment path provisions the new gateway security/runtime flags instead of assuming an open control surface.

## Completed Changes

### 1. Gateway Control Plane Hardening

Updated `mycosoft_mas/myca/os/gateway.py`:

- Added credential-aware request authorization for protected routes.
- Supported `X-MYCA-API-Key`, `X-API-Key`, and `Authorization: Bearer`.
- Added trusted-remote fallback only for explicitly local/trusted IPs.
- Removed implicit Morgan impersonation from `/message`; `is_morgan` now defaults to `false`.
- Gated `/shell` behind `MYCA_ENABLE_SHELL_API=true`.
- Gated `/skills/install` behind `MYCA_ENABLE_SKILL_INSTALL=true`.
- Protected `/status`, `/tasks`, `/logs`, `/sessions`, `/skills`, `/ws`, standup/investor endpoints, and onboarding endpoints.

### 2. Environment Contract Normalization

Updated `mycosoft_mas/myca/os/comms_hub.py` and `mycosoft_mas/myca/os/channels_health.py`:

- Added fallback resolution across old and new env names for Discord, Slack, Signal, WhatsApp, Asana, and workspace URLs.
- Aligned runtime channel expectations with validation logic so health checks and runtime code stop disagreeing about token names.

### 3. Staff Identity Foundation

Created `mycosoft_mas/myca/os/staff_registry.py`:

- Loads canonical staff definitions from `config/org_roles.yaml`.
- Expands `${ENV_VAR}` placeholders used in channel mappings.
- Resolves canonical `person_id` from platform ID, email, or known display name.

Updated:

- `mycosoft_mas/agents/workspace_agent.py`
- `mycosoft_mas/core/routers/workspace_api.py`
- `mycosoft_mas/security/platform_access.py`

These now rely on the org roles registry instead of stale hardcoded staff assumptions, and the workspace API now exposes `/api/workspace/inbox` for the comms polling contract.

### 4. Deployment Path Hardening

Updated `scripts/deploy_myca_191_v2.py`:

- Ensures `MYCA_GATEWAY_PORT=8100`.
- Ensures `MYCA_ENABLE_SHELL_API=false`.
- Ensures `MYCA_ENABLE_SKILL_INSTALL=false`.
- Ensures `MYCA_TRUSTED_IPS` is present.
- Ensures `MYCA_GATEWAY_API_KEY` is generated on the target VM if absent.
- Ensures `NATUREOS_API_URL` and `PRESENCE_API_URL` are provisioned.
- Removed the previous hardcoded WhatsApp auth secret from the deploy path.

## Additional Runtime Promotion Started

While completing the hardening phase, the following broader runtime upgrades were also started:

- Added `mycosoft_mas/myca/os/natureos_bridge.py`
- Integrated NatureOS into `mycosoft_mas/myca/os/core.py`
- Expanded `mycosoft_mas/myca/os/llm_brain.py` live context assembly to include NatureOS and unified search context
- Promoted non-Morgan dialogue routing in `mycosoft_mas/myca/os/executive.py` and `mycosoft_mas/myca/os/core.py`
- Added first-class task handlers in `mycosoft_mas/myca/os/tool_orchestrator.py` for `github`, `asana`, `natureos`, and `search`

These changes support later phases but do not replace the dedicated follow-on runtime integration work.

## Verification

### Runtime Import Check

Verified edited runtime modules import successfully:

- `gateway.py`
- `comms_hub.py`
- `channels_health.py`
- `natureos_bridge.py`
- `core.py`
- `executive.py`
- `tool_orchestrator.py`
- `staff_registry.py`
- `workspace_api.py`
- `workspace_agent.py`
- `platform_access.py`
- `github_client.py`

### Targeted Regression Suite

Ran:

```bash
poetry run pytest tests/consciousness/test_world_model.py tests/integrations/test_natureos_client.py tests/core/test_voice_tools_natureos.py tests/test_memory_integration.py tests/test_intent_classifier.py
```

Result after fixing a pre-existing memory package export issue:

- `100 passed`
- `2 skipped`

### Test Fix Applied During Verification

Fixed an existing import mismatch in `mycosoft_mas/memory/__init__.py`:

- Removed `ProceduralSkill` export because `mycosoft_mas/memory/procedural_memory.py` does not define that symbol.

This was required to get the memory integration tests green.

## Files Changed

- `mycosoft_mas/myca/os/gateway.py`
- `mycosoft_mas/myca/os/comms_hub.py`
- `mycosoft_mas/myca/os/channels_health.py`
- `mycosoft_mas/myca/os/natureos_bridge.py`
- `mycosoft_mas/myca/os/core.py`
- `mycosoft_mas/myca/os/llm_brain.py`
- `mycosoft_mas/myca/os/executive.py`
- `mycosoft_mas/myca/os/tool_orchestrator.py`
- `mycosoft_mas/myca/os/staff_registry.py`
- `mycosoft_mas/agents/workspace_agent.py`
- `mycosoft_mas/core/routers/workspace_api.py`
- `mycosoft_mas/security/platform_access.py`
- `mycosoft_mas/integrations/github_client.py`
- `mycosoft_mas/memory/__init__.py`
- `scripts/deploy_myca_191_v2.py`

## Next Phase

Continue Phase 2: promote the already-built system surfaces into one canonical runtime path across:

- MINDEX
- NatureOS
- worldview/state
- NLM/presence/search
- MycoBrain, CREP, and Earth2
- shared text/voice reasoning context

## Related Documents

- [MYCA Platform Status and Gaps](./MYCA_PLATFORM_STATUS_AND_GAPS_MAR05_2026.md)
- [MYCA Living Employee Full Integration Phase 0](./MYCA_LIVING_EMPLOYEE_FULL_INTEGRATION_PHASE0_COMPLETE_MAR02_2026.md)
- [Request Flow Architecture](./REQUEST_FLOW_ARCHITECTURE_MAR05_2026.md)
