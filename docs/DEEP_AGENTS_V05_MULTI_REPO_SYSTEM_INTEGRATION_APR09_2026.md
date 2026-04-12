# Deep Agents v0.5 Multi-Repo System Integration (Apr 9, 2026)

## Date
Apr 9, 2026

## Status
In progress (multi-repo expansion pass 2 complete)

## Scope
Extend Deep Agents v0.5 from MAS foundation into cross-repo event orchestration so search, device, NatureOS, and MYCA surfaces can publish domain events into MAS Deep Agent workflows.

## Delivered In This Pass

### MAS (`mycosoft-mas`)
- Added cross-system ingestion endpoint: `POST /api/deep-agents/domain-event` in `mycosoft_mas/core/routers/agent_protocol_api.py`.
- Endpoint routes external domain events through `submit_domain_task(...)` with Deep Agent feature-flag checks.

### WEBSITE (`WEBSITE/website`)
- Added shared publisher helper:
  - `lib/mas/deep-agent-events.ts`
- Wired domain-event dispatch into:
  - `app/api/search/unified-v2/route.ts` (`search` domain)
  - `app/api/natureos/status/route.ts` (`natureos` domain)
  - `app/api/devices/network/route.ts` (`device` domain)
  - `app/api/myca/activity/route.ts` (`myca` domain)
  - `app/api/security/agents/route.ts` (`security` domain)
  - `app/api/security/redteam/route.ts` (`security` domain)
  - `app/api/myca/query/route.ts` (`myca` domain)
- Removed mock-only fallback activity payloads from:
  - `app/api/natureos/activity/route.ts`
  - Route now returns real upstream events or explicit "No data available" error-state payload.

### MINDEX (`MINDEX/mindex`)
- Added shared publisher helper:
  - `mindex_api/utils/deep_agent_events.py`
- Wired domain-event dispatch into:
  - `mindex_api/routers/unified_search.py` (`search` domain for unified/earth/nearby searches)
  - `mindex_api/routers/mycobrain.py` (`device` domain for register/telemetry/command queue flows)
  - `mindex_api/routers/research.py` (`search` domain for research search + paper details)
  - `mindex_api/routers/observations.py` (`search` domain for list + bulk ingest)
  - `mindex_api/routers/etl.py` (`search` domain for ETL sync + status)
- Removed mock ETL status metrics from `mindex_api/routers/etl.py`; endpoint now returns explicit real-data-only status shape when live metrics are unavailable.

### NatureOS (`NATUREOS/NatureOS`)
- Added publisher service:
  - `src/core-api/Services/DeepAgentEventService.cs`
- Registered service in DI:
  - `src/core-api/Program.cs`
- Wired dispatch into:
  - `src/core-api/Controllers/MycoBrainController.cs` (telemetry, command send, register)
  - `src/core-api/Controllers/MasDevicesController.cs` (register + MycoBrain command compatibility endpoint)
  - `src/core-api/Controllers/MonitoringController.cs` (metrics, alerts, health, device-health)
  - `src/core-api/Controllers/WorkflowController.cs` (list/get/save/execute/history)
  - `src/core-api/Controllers/SecurityController.cs` (`/api/security/me`)

## Feature-Flag Behavior
- Domain-event publishing remains best-effort and non-blocking.
- Dispatch can be disabled with:
  - `MYCA_DEEP_AGENTS_DOMAIN_HOOKS_ENABLED=false`
- MAS ingress endpoint returns `{ accepted: false }` when Deep Agents are disabled.

## Why This Matters
- Converts major cross-system operational paths into async Deep Agent signal sources.
- Preserves existing API behavior while enabling centralized autonomous follow-up in MAS.
- Establishes a consistent event contract for additional repos/endpoints to adopt.

## Remaining Work For Full Completion
- Add equivalent hooks to remaining high-value website domains (additional CREP pipelines, workflow surfaces, and SOC drill-down routes).
- Extend MINDEX hooks beyond current search/research/observations/etl/mycobrain coverage into remaining ingestion and analytics routers.
- Add deployment rollout and VM validation for MAS + WEBSITE + MINDEX + NatureOS with runtime evidence.
- Resolve Deep Agents dependency strategy for production packaging (`langchain` version conflict isolation or upgrade path).
