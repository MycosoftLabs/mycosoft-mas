# MYCA Omnichannel Dialogue Bus Complete

**Date**: March 6, 2026
**Author**: GPT-5.4 / MYCA
**Status**: Complete
**Related Plan**: `.cursor/plans/myca_full_omnichannel_b338cfc1.plan.md`

## Overview

Phase 4 of the MYCA full omnichannel execution plan is complete. The bus is still not the final end-state for every platform nuance, but the runtime now has materially better parity between declared connector architecture and the actual MYCA OS communication loop.

## Completed Work

### 1. WhatsApp Polling Added To The Live Comms Hub

Updated:

- `mycosoft_mas/myca/os/comms_hub.py`

Key changes:

- added `_poll_whatsapp()`
- included WhatsApp in `poll_all_channels()`
- normalized inbound WhatsApp messages into the same shape used by the MYCA OS message loop

This closes one of the bigger gaps between outbound WhatsApp support and actual inbound dialogue support.

### 2. Workspace Inbox Contract Fixed

Updated:

- `mycosoft_mas/core/routers/workspace_api.py`

Key changes:

- added `/api/workspace/inbox` as an alias for aggregated polling
- widened default workspace message polling to include:
  - Slack
  - Discord
  - Signal
  - WhatsApp
  - email
  - Asana

This now matches the assumptions already present in the MYCA OS comms layer.

### 3. Omnichannel Status Now Uses The Same Env Contract As Runtime

Updated:

- `mycosoft_mas/core/routers/omnichannel_api.py`

Key changes:

- added `_env_any()` fallback helper
- aligned Slack, Discord, and Asana connector status logic with the same fallback env names used in runtime code
- reduced status drift between “configured in code” and “configured at runtime”

### 4. Workspace Agent And Runtime Now Share A More Coherent Messaging Base

Previously:

- the comms runtime expected `/api/workspace/inbox`
- the workspace API did not provide it
- channel defaults were narrower than the intended omnichannel architecture

Now:

- the workspace route contract exists
- the comms hub can poll more of the declared channel surface
- the system is closer to one coherent bus instead of separate per-platform islands

## Verification

### Import Verification

Verified clean imports for:

- `mycosoft_mas.myca.os.comms_hub`
- `mycosoft_mas.core.routers.omnichannel_api`
- `mycosoft_mas.core.routers.workspace_api`

### Regression Baseline

The previously established targeted regression suite remained green after these changes:

```bash
poetry run pytest tests/consciousness/test_world_model.py tests/integrations/test_natureos_client.py tests/core/test_voice_tools_natureos.py tests/test_memory_integration.py tests/test_intent_classifier.py
```

Result:

- `100 passed`
- `2 skipped`

## Files Changed For Phase 4

- `mycosoft_mas/myca/os/comms_hub.py`
- `mycosoft_mas/core/routers/omnichannel_api.py`
- `mycosoft_mas/core/routers/workspace_api.py`

## Remaining Gap After Phase 4

Phase 5 is still required so that omnichannel dialogue turns into actual system-level execution:

- task routes must be first-class for GitHub, Asana, NatureOS, search, and device/worldview work
- MYCA must orchestrate specialist MAS agents directly instead of relying on generic fallback behavior
- voice and text tool invocation must converge around the same operational paths

## Related Documents

- [MYCA Runtime Hardening Complete](./MYCA_RUNTIME_HARDENING_COMPLETE_MAR06_2026.md)
- [MYCA Full-System Runtime Promotion Complete](./MYCA_FULL_SYSTEM_RUNTIME_PROMOTION_COMPLETE_MAR06_2026.md)
- [MYCA Staff Identity and Memory Complete](./MYCA_STAFF_IDENTITY_AND_MEMORY_COMPLETE_MAR06_2026.md)
