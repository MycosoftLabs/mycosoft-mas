# MYCA Support Upgrade Audit — March 7, 2026

**Status:** Complete  
**Related Plan:** `.cursor/plans/myca_support_audit_844444cd.plan.md`  
**Goal:** Identify which Mycosoft surfaces should be upgraded so the improved MYCA runtime can interact with Morgan more effectively, surface context faster, and operate more naturally across the platform.

---

## Executive Summary

The audit reviewed Website, MINDEX, NatureOS, MycoBrain, external AI/cowork, and automation surfaces. The platform has strong foundations—MYCA chat/voice, search-MYCA integration, grounding, and A2A agent surfaces exist—but several upgrades would materially improve MYCA-to-Morgan interaction, context continuity, and system visibility.

**Highest-value upgrades:**

- **Morgan oversight panel** — Dedicated control/visibility surface for Morgan (no equivalent today)
- **Staff/task context API** — MINDEX lacks staff/project/task context MYCA needs for delegation
- **MycoBrain→MYCA telemetry path** — FCI telemetry goes to Mycorrhizae; MYCA does not consume it
- **NatureOS→MYCA hooks** — Shell, workflows, analytics not exposed to MYCA for machine-readable summaries
- **Cowork/MYCA handoff** — Claude Cowork and Cursor run separately; Morgan must context-switch

---

## 1. Website and Frontend Surfaces

### What Currently Exists (MYCA Can Already Use)

| Surface | Location | Purpose |
|---------|----------|---------|
| **MYCA Chat Widget** | `components/myca/MYCAChatWidget.tsx` | Text chat with memory, grounding, confirmation |
| **MYCA Context** | `contexts/myca-context.tsx` | Session, conversation, consciousness, grounding state |
| **UnifiedMYCAFAB** | `components/myca/UnifiedMYCAFAB.tsx` | Floating action for chat/voice on MYCA-enabled routes |
| **Fluid Search + MYCA** | `components/search/fluid/`, `MYCAChatPanel.tsx` | Search context passed to MYCA; MYCA-driven search actions refresh results |
| **Mobile Search Chat** | `components/search/mobile/MobileSearchChat.tsx` | ChatGPT-like MYCA on phone; `contextText` passed |
| **AIWidget** | `components/search/fluid/widgets/AIWidget.tsx` | Follow-ups include search context (species, compounds, etc.) |
| **Dashboard** | `app/dashboard/page.tsx` | MRR, memory health, links; `isSuperAdmin` (Morgan) shows extra content |
| **Grounding page** | `app/dashboard/grounding/page.tsx` | Grounding state visibility |
| **MYCA routes** | `/myca/*`, `/search`, `/test-voice`, `/natureos`, `/dashboard`, `/defense`, `/apps`, `/scientific`, `/admin` | MYCA-enabled via `MYCA_PREFIXES` in AppShellProviders |
| **Voice** | `app/myca/voice-duplex/`, `test-voice` | Voice endpoints; Morgan identity in orchestrator prompt |
| **myca-api, myca-nlq, myca-mas** | `lib/services/`, `lib/integrations/` | MAS API, NLQ, intention routing |

### Gaps (What Should Be Upgraded)

| Gap | Type | Impact |
|-----|------|--------|
| **No Morgan oversight panel** | UX | Morgan has no single control/visibility surface for MYCA state, tasks, staff delegation, or autonomous work |
| **Dashboard is generic** | UX | MRR, memory health exist; no MYCA-specific widgets (pending confirmations, active tasks, staff digest, worldview summary) |
| **No cross-page context continuity** | Backend | MYCA context is session-scoped; navigating between /search, /dashboard, /natureos does not carry "what Morgan was just doing" |
| **CREP/defense not MYCA-facing** | Integration | CREP, OEI, FUSARIUM pages exist but no explicit MYCA context or "ask MYCA about this" hooks |
| **Device pages** | Integration | Device manager shows MycoBrain; MYCA cannot easily "what devices are online?" without dedicated API surface |
| **Admin surfaces** | UX | `/admin` in MYCA_PREFIXES but no MYCA-aware admin control panel |

### Upgrade Recommendations (Website)

- **Quick win:** Add MYCA state widget to dashboard (consciousness, grounding, pending confirmations) — `app/dashboard/page.tsx`, reuse `useMYCA()`
- **Medium:** Morgan oversight panel — new route `/myca/oversight` or `/dashboard/morgan` with tasks, confirmations, staff context, worldview summary
- **Medium:** Pass page context to MYCA (e.g. "Morgan is on CREP dashboard") via `context` in `sendMessage`
- **Large:** Full Morgan control plane — supervise, steer, trust controls; visibility into autonomous work queue

---

## 2. MINDEX and Knowledge/Data Surfaces

### What Currently Exists

| Surface | Location | Purpose |
|---------|----------|---------|
| **Unified search** | `mindex_api/routers/unified_search.py` | Cross-table search (species, compounds, genetics, research) |
| **A2A agent** | `mindex_api/routers/a2a_agent.py` | Read-only agent for MAS; search and stats intents |
| **Grounding** | `mindex_api/routers/grounding.py` | Spatial points, episodes, experience packets, thought objects for MYCA |
| **Knowledge router** | `mindex_api/main.py` | Categories, knowledge graph for MYCA world model |
| **Research router** | `mindex_api/routers/research.py` | OpenAlex papers |
| **Beta router** | `mindex_api/routers/beta.py` | Beta signups (MYCA Loop Closure) |

### Gaps

| Gap | Type | Impact |
|-----|------|--------|
| **No staff/task/project context API** | Backend | MYCA cannot query "what is Morgan working on?" or "RJ's tasks" — no staff-scoped MINDEX surface |
| **EP visibility** | Backend | Experience packets stored in grounding; no high-level "recent EP summary for MYCA" endpoint |
| **Knowledge graph not MYCA-optimized** | Backend | KG exists for world model; unclear if MYCA gets structured "worldview digest" vs raw queries |
| **Memory write path** | Integration | MAS memory (6 layers) vs MINDEX — write path for MYCA-learned facts could be clearer |

### Upgrade Recommendations (MINDEX)

- **Quick win:** Document A2A agent usage for MYCA; ensure MAS uses it for search/stats delegation
- **Medium:** Staff/task context API — e.g. `GET /api/mindex/staff-context?user=morgan` returning active projects, recent tasks (requires Asana/GitHub integration or separate store)
- **Medium:** EP summary endpoint for MYCA — e.g. `GET /api/mindex/grounding/ep-summary?session_id=X&limit=10`
- **Large:** MYCA worldview digest — periodic snapshot of KG + memory relevant to current user and time window

---

## 3. NatureOS Apps and Tooling

### What Currently Exists

| Surface | Location | Purpose |
|---------|----------|---------|
| **Core API** | `NatureOS/src/core-api/Program.cs` | C# .NET API, SignalR hub, CORS for Mycosoft origins |
| **Website NatureOS routes** | `app/natureos/*` | Workflows, storage, api, sdk, lab-tools, devices, ai-studio |
| **MYCA on NatureOS** | AppShellProviders | MYCA FAB on `/natureos` routes |
| **Devices** | `natureos/devices/*` | Registry, map, fleet, alerts, telemetry |

### Gaps

| Gap | Type | Impact |
|-----|------|--------|
| **No machine-readable summaries** | Integration | Shell, workflows, analytics are human-focused; MYCA cannot "summarize NatureOS state" |
| **No direct MYCA hooks** | Integration | No webhook or API for "MYCA: run this workflow" or "MYCA: device X status" |
| **SignalR not MYCA-facing** | Integration | NatureOSHub pushes to clients; MYCA is not a subscriber |
| **Lab tools** | Integration | Lab tools, exports, monitoring not exposed to MYCA for reasoning |

### Upgrade Recommendations (NatureOS)

- **Quick win:** Add MYCA-friendly REST summary endpoint — e.g. `GET /api/natureos/summary` returning device count, workflow status, last telemetry
- **Medium:** Webhook for MYCA→NatureOS actions — e.g. trigger workflow, request device command
- **Large:** NatureOS→MYCA bridge — push relevant events (device alert, workflow complete) to MYCA context

---

## 4. MycoBrain Firmware and Device Surfaces

### What Currently Exists

| Surface | Location | Purpose |
|---------|----------|---------|
| **MycoBrain service** | `services/mycobrain/mycobrain_service_standalone.py` | Serial comms, heartbeats to MAS Device Registry |
| **FCI telemetry** | `mycobrain/firmware/MycoBrain_FCI/` | 10 Hz telemetry, device.id, fci_telemetry_t struct |
| **Mycorrhizae channels** | `device.{id}.telemetry`, `device.{id}.commands` | FCI publishes to Mycorrhizae protocol |
| **Website device manager** | `app/devices/*` | Mushroom-1, SporeBase, etc.; fetches from MAS `/api/devices/network` |

### Gaps

| Gap | Type | Impact |
|-----|------|--------|
| **FCI telemetry → MYCA path missing** | Integration | Telemetry goes to Mycorrhizae; MYCA does not consume it for "lab state" or "device health" |
| **Device status richness** | Firmware | Status is basic; MYCA would benefit from "experiment in progress," "sensor anomaly" |
| **Presence/environment for MYCA** | Integration | MycoBrain presence (who is in lab) not surfaced to MYCA |
| **Protocol gap** | Firmware | MDP v1; no explicit "MYCA request" channel |

### Upgrade Recommendations (MycoBrain)

- **Quick win:** Document MycoBrain→MAS heartbeat flow; ensure MYCA can query device registry for "what devices are online"
- **Medium:** Mycorrhizae→MYCA bridge — subscribe to `device.*.telemetry` or aggregate channel; inject recent telemetry into MYCA context when relevant
- **Medium:** Enrich device status in MAS registry — e.g. `experiment_active`, `last_telemetry_at`
- **Large:** MYCA-situational awareness — MYCA can "see" lab state, device health, presence without Morgan asking

---

## 5. External AI and Cowork Surfaces

### What Currently Exists

| Surface | Location | Purpose |
|---------|----------|---------|
| **Claude Cowork (PlotCore)** | CoworkVMService | COO, Secretary, HR automations; hourly/daily tasks |
| **Cowork Watchdog** | `scripts/install-cowork-vm-watchdog.ps1` | Keeps Cowork VM running |
| **Cursor** | Dev environment | Coding, agents, Cursor rules/skills |
| **MAS orchestrator** | VM 188 | MYCA orchestration, agent delegation |
| **MYCA VM 191** | VM 191 | MYCA workspace, n8n, OpenWork |

### Gaps

| Gap | Type | Impact |
|-----|------|--------|
| **Cowork and MYCA are separate** | Integration | Morgan uses Claude Cowork for tasks; MYCA runs on MAS. No handoff. |
| **Cursor↔MYCA** | Integration | Cursor agents are separate from MYCA; Morgan context-switches |
| **Duplicate functionality** | UX | Cowork does COO/Secretary; MYCA has SecretaryAgent. Risk of duplication. |
| **"Where does Morgan get work done?"** | UX | Cowork for some tasks, MYCA for others, Cursor for code — no single front door |

### Upgrade Recommendations (External AI/Cowork)

- **Quick win:** Document Cowork vs MYCA scope — when to use each; avoid duplicate automations
- **Medium:** MYCA→Cowork handoff — e.g. MYCA delegates "schedule meeting" to Cowork workflow via webhook
- **Medium:** Cursor→MYCA context — e.g. "Morgan is in Cursor working on X" passed to MYCA when relevant
- **Large:** Unified front door — Morgan interacts primarily with MYCA; MYCA orchestrates Cowork, Cursor, and other tools behind the scenes

---

## 6. Automation and Workflow Layer

### What Currently Exists

| Surface | Location | Purpose |
|---------|----------|---------|
| **n8n MAS** | VM 188:5678 | 66 MAS workflows |
| **n8n MYCA** | VM 191, `workflows/n8n/` | 12 MYCA personal workflows |
| **Workflow sync** | `N8N_WORKFLOW_SYNC_AND_REGISTRY_FEB18_2026` | Repo↔local↔cloud sync |
| **GET /api/workflows/registry** | MAS | Workflow registry for MYCA |
| **POST /api/workflows/sync-both** | MAS | Sync both n8n instances |
| **GitHub, Asana, Discord, Signal** | Integrations | Platform connectors |

### Gaps

| Gap | Type | Impact |
|-----|------|--------|
| **MYCA→Morgan workflow visibility** | UX | Morgan cannot easily see "what workflows ran for me today" in MYCA UI |
| **Webhook flows** | Integration | Webhooks exist; MYCA-triggered workflows (e.g. "run deploy when Morgan approves") need clarity |
| **Missing automations** | Backend | Gaps in "Morgan asked MYCA to X → workflow executes" — some paths incomplete |
| **n8n MAS vs MYCA** | Architecture | Two n8n instances; MAS workflows vs MYCA workflows — Morgan may not know which to use |

### Upgrade Recommendations (Automation)

- **Quick win:** Add "recent workflow runs" to Morgan oversight panel (when built) — query n8n API or MAS workflow history
- **Medium:** MYCA→n8n trigger — standard way for MYCA to trigger a workflow (e.g. "deploy when Morgan says go")
- **Medium:** Morgan approval workflow — MYCA queues action → Morgan approves in MYCA UI → workflow executes
- **Large:** Unified workflow visibility — single view of "what ran for Morgan" across MAS and MYCA n8n

---

## Prioritized Upgrade Plan

### Quick Wins (1–2 days each)

| # | Upgrade | Repo(s) | Files | Impact |
|---|---------|---------|-------|--------|
| 1 | MYCA state widget on dashboard | WEBSITE | `app/dashboard/page.tsx` | Morgan sees consciousness, grounding, pending confirmations |
| 2 | Document A2A agent for MYCA | MINDEX, MAS | `mindex_api/routers/a2a_agent.py`, MAS MindexAgent | Clear delegation path |
| 3 | Document Cowork vs MYCA scope | MAS | New doc in `docs/` | Reduces duplication and confusion |
| 4 | Document MycoBrain→MAS flow | MAS, mycobrain | `services/mycobrain/`, device registry | MYCA can query devices |
| 5 | Pass page context to MYCA | WEBSITE | `AppShellProviders`, `myca-context` | "Morgan is on CREP" improves replies |

### Medium Upgrades (3–7 days each)

| # | Upgrade | Repo(s) | Files | Impact |
|---|---------|---------|-------|--------|
| 6 | Morgan oversight panel | WEBSITE | New `app/myca/oversight/` or `app/dashboard/morgan/` | Single control/visibility surface |
| 7 | Staff/task context API | MINDEX or MAS | New router | MYCA knows "what is Morgan working on?" |
| 8 | EP summary endpoint | MINDEX | `routers/grounding.py` | MYCA gets recent experience packet summary |
| 9 | NatureOS summary endpoint | NatureOS | `src/core-api/` | MYCA can "summarize NatureOS state" |
| 10 | Mycorrhizae→MYCA telemetry bridge | MAS | New bridge module | MYCA sees lab telemetry when relevant |
| 11 | MYCA→n8n trigger pattern | MAS, n8n | Workflows, MAS API | Standard "MYCA triggers workflow" path |
| 12 | Morgan approval UX in MYCA | WEBSITE | `MYCAChatWidget`, confirmation flow | Smoother approve/reject for autonomous actions |

### Large Architectural Follow-Ons (2+ weeks each)

| # | Upgrade | Repo(s) | Dependencies | Impact |
|---|---------|---------|--------------|--------|
| 13 | Full Morgan control plane | WEBSITE, MAS | Oversight panel, workflow visibility, approval UX | Supervise, steer, trust MYCA |
| 14 | MYCA worldview digest | MINDEX, MAS | KG, memory, EP | MYCA maintains rich context for Morgan |
| 15 | Unified front door (MYCA orchestrates Cowork/Cursor) | MAS, integrations | Cowork webhooks, Cursor context | Morgan stays in MYCA; MYCA delegates |
| 16 | NatureOS→MYCA event bridge | NatureOS, MAS | SignalR or webhook | Device alerts, workflow done → MYCA context |
| 17 | MycoBrain situational awareness | mycobrain, MAS, Mycorrhizae | Telemetry bridge, device status | MYCA "sees" lab state |
| 18 | Unified workflow visibility | MAS, n8n | Both n8n instances | "What ran for Morgan" in one view |

---

## Cross-Repo Dependencies

| Upgrade | Depends On |
|---------|------------|
| Morgan oversight panel | MYCA context, MAS task/delegation APIs |
| Staff/task context API | Asana/GitHub integration or separate task store |
| Mycorrhizae→MYCA bridge | Mycorrhizae subscribe API, MAS context injection |
| NatureOS summary | NatureOS API, device/workflow aggregation |
| MYCA worldview digest | MINDEX KG, grounding EP, MAS memory layers |

---

## Priority Lens (Ranking)

Findings are ranked by impact on:

1. **MYCA–Morgan interaction quality** — Oversight panel, context continuity, approval UX
2. **Context and continuity** — Page context, staff/task API, worldview digest
3. **System visibility** — MYCA sees devices, workflows, lab state
4. **Morgan supervise/steer/trust** — Control plane, approval workflows
5. **Reduced context switching** — Unified front door, Cowork/MYCA handoff

---

## Verification Checklist

After implementing upgrades:

- [ ] Morgan can see MYCA state (consciousness, grounding, confirmations) from dashboard
- [ ] MYCA receives page context ("Morgan is on CREP") when chatting
- [ ] MYCA can query device registry for "devices online"
- [ ] Morgan oversight panel exists and shows tasks, confirmations, workflow runs
- [ ] Staff/task context available to MYCA (when API exists)
- [ ] NatureOS summary endpoint returns machine-readable state
- [ ] MycoBrain telemetry flows to MYCA when relevant (bridge)
- [ ] Cowork vs MYCA scope documented
- [ ] MYCA→n8n trigger pattern documented and used

---

## Related Docs

- `docs/MYCA_PLATFORM_STATUS_AND_GAPS_MAR05_2026.md` — Current status
- `docs/SEARCH_MYCA_INTEGRATION_FEB23_2026.md` — Search–MYCA integration
- `docs/COWORK_VM_CONTINUITY_MAR04_2026.md` — Cowork watchdog
- `docs/N8N_WORKFLOW_SYNC_AND_REGISTRY_FEB18_2026.md` — n8n sync
- `docs/MYCA_FULL_OMNICHANNEL_EXECUTION_COMPLETE_MAR06_2026.md` — Recent MYCA runtime
