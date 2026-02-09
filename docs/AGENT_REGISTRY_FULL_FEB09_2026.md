# Full Agent Registry and Count Discrepancy Analysis

**Created:** February 9, 2026  
**Purpose:** Explain why agent counts differ (223+ vs 42+), define the single source of truth, and list all agents so they can be registered and run.

---

## 1. Why the Discrepancy?

Different parts of the system count agents in different ways. There is **no single source of truth** today.

| Source | Count | Where it comes from | Used by |
|--------|-------|---------------------|--------|
| **42** | 42 | `mycosoft_mas/core/agent_registry.py` – exactly 42 `self.register(AgentDefinition(...))` calls | Voice/UI registry, GET `/api/agents/registry/`, n8n |
| **42** | 42 | `mycosoft_mas/core/routers/orchestrator_api.py` – **hardcoded** `"totalAgents": 42`, `"activeAgents": 8` | Orchestrator dashboard, GET `/orchestrator/dashboard`, `/orchestrator/agents` |
| **8** | 8 | Same file – **hardcoded** list of 8 agents in dashboard `"agents": [...]` | Dashboard UI (mock data) |
| **52** | 52 | `mycosoft_mas/registry/agent_registry.py` – `AGENT_CATALOG` list (many entries point to **non-existent modules**) | Async registry (Postgres), not used by main app router |
| **96+** | 96+ | Comment in `registry/agent_registry.py`: "96+ agents across all subsystems" | Documentation only (outdated) |
| **117+** | 117+ | `CLAUDE.md`: "117+ AI agents" | Documentation only (aspirational) |
| **100+** | 100+ | `.cursor/rules/mycosoft-full-codebase-map.mdc`: "100+ agents" in `mycosoft_mas/agents/` | Documentation only |
| **27** | 27 | `.cursor/agents/` – Cursor sub-agent .md files | Cursor IDE (not runtime MAS agents) |
| **28** | 28 | `.cursor/rules/mycosoft-full-context-and-registries.mdc`: "28 Specialized Sub-Agents" | Rule text (one more than actual .md count) |
| **223+** | 223+ | **Not found in code.** Likely: 117 + 42 + 28 + 36 (or similar) from docs, or a past sum. No file or API returns 223. | User report / external reference |

---

## 2. Actual Numbers (Canonical)

| Category | Count | Notes |
|----------|-------|--------|
| **Core agent registry (voice/API)** | **42** | `core/agent_registry.py` – built-in definitions; used by voice routing and `/api/agents/registry/`. |
| **Orchestrator dashboard (mock)** | **42 total, 8 active** | Hardcoded in `orchestrator_api.py`; not from runtime. |
| **Registry AGENT_CATALOG** | **52** | `registry/agent_registry.py`; many module paths do not exist (e.g. v2.myca_agent, speech_agent, workflow.*). |
| **MAS agents in `__init__.py`** | **27** | 17 real imports + 10 dynamic stubs (ContractAgent, LegalAgent, etc.). |
| **MAS agent Python files** | **~70** | Under `mycosoft_mas/agents/` (including clusters, v2, corporate, financial, mycobrain). |
| **MAS agent classes (code-defined)** | **~55–65** | Distinct agent classes (BaseAgent subclasses + CodingAgent, etc.); some files have multiple classes. |
| **Cursor sub-agents** | **27** | `.cursor/agents/*.md` – Cursor-only; not part of MAS runtime. |
| **Custom registry.json** | **1** | `agents/registry.json` – CreateADefense agent. |
| **Runtime (VM) actually running** | **Variable** | From `orchestrator_service` `agent_pool.get_all_agents()`; only **spawned** agents; can be 0 if none spawned. |
| **MINDEX registry.agents table** | **Variable** | Whatever was POSTed to `/api/registry/agents` or synced; may be 0 or more. |

**Single “actual” number for “MAS agents that are defined and can run”:**  
Use **42** as the **currently registered and voice-routable** set (core registry). The **codebase** has ~55–65 agent classes; many are not in the core registry and are not auto-started.

---

## 3. Full Registry of All Agents

### 3.1 Core Agent Registry (42) – Voice/API

These are the 42 in `mycosoft_mas/core/agent_registry.py` (used by `/api/agents/registry/`):

| # | agent_id | Class name | Category |
|---|----------|------------|----------|
| 1 | mycology_bio | MycologyBioAgent | mycology |
| 2 | mycology_knowledge | MycologyKnowledgeAgent | mycology |
| 3 | financial | FinancialAgent | financial |
| 4 | finance_admin | FinanceAdminAgent | financial |
| 5 | corporate_ops | CorporateOperationsAgent | corporate |
| 6 | board_ops | BoardOperationsAgent | corporate |
| 7 | legal_compliance | LegalComplianceAgent | corporate |
| 8 | marketing | MarketingAgent | communication |
| 9 | sales | SalesAgent | communication |
| 10 | project_mgmt | ProjectManagementAgent | core |
| 11 | project_manager | ProjectManagerAgent | core |
| 12 | secretary | SecretaryAgent | core |
| 13 | opportunity_scout | OpportunityScout | research |
| 14 | experiment | ExperimentAgent | research |
| 15 | ip_agent | IPAgent | dao |
| 16 | ip_tokenization | IPTokenizationAgent | dao |
| 17 | myco_dao | MycoDAOAgent | dao |
| 18 | token_economics | TokenEconomicsAgent | dao |
| 19 | dashboard | DashboardAgent | data |
| 20 | research | ResearchAgent | research |
| 21 | debug | DebugAgent | core |
| 22 | code_fix | CodeFixAgent | core |
| 23 | coding | CodingAgent | core |
| 24 | wifisense | WiFiSenseAnalysisAgent | data |
| 25 | drone | DroneMissionPlannerAgent | infrastructure |
| 26 | desktop_automation | DesktopAutomationAgent | integration |
| 27 | mycobrain_device | DeviceAgent | infrastructure |
| 28 | mycobrain_ingestion | IngestionAgent | data |
| 29 | web_scraper | WebScraperAgent | data |
| 30 | data_normalization | DataNormalizationAgent | data |
| 31 | environmental_data | EnvironmentalDataAgent | data |
| 32–42 | (remaining cluster/sim/pattern agents) | Various | data/simulation/… |

(Remaining entries in the same file: image_processing, pattern, protocol, search, simulation, growth, compound, petri_dish, mycelium_simulator, data_analysis, visualization, immune_system, agent_evolution, etc.)

### 3.2 MAS Agents Package – Exported in `__init__.py` (27)

**Real imports:** BaseAgent, MycologyBioAgent, MycologyKnowledgeAgent, IPTokenizationAgent, MycoDAOAgent, TokenEconomicsAgent, FinanceAdminAgent, ProjectManagementAgent, MarketingAgent, ExperimentAgent, IPAgent, SecretaryAgent, DashboardAgent, OpportunityScout, CorporateOperationsAgent, BoardOperationsAgent, LegalComplianceAgent, FinancialAgent, CameraIntegration, SpeechIntegration.

**Dynamic stubs (no real module):** ContractAgent, LegalAgent, TechnicalAgent, QAAgent, VerificationAgent, AuditAgent, RegistryAgent, AnalyticsAgent, RiskAgent, ComplianceAgent, OperationsAgent.

### 3.3 Cursor Sub-Agents (27) – Not MAS Runtime

backend-dev, backup-ops, code-auditor, crep-collector, data-pipeline, database-engineer, deploy-pipeline, device-firmware, devops-engineer, documentation-manager, earth2-ops, infrastructure-ops, integration-hub, memory-engineer, myca-autonomous-operator, n8n-workflow, notion-sync, plan-tracker, process-manager, regression-guard, route-validator, scientific-systems, security-auditor, stub-implementer, test-engineer, voice-engineer, website-dev, websocket-engineer.

(27 files; rules say “28” – one name may have been removed or duplicated in the list.)

### 3.4 Registry AGENT_CATALOG (52) – Many Modules Missing

Lives in `mycosoft_mas/registry/agent_registry.py`. Includes orchestration (myca_agent, supervisor_agent, …), voice (speech_agent, tts_agent, …), scientific, mycobrain, natureos, financial, memory, workflow, integration, utility. Many `module` paths point to files that do not exist (e.g. `mycosoft_mas.agents.v2.myca_agent`, `mycosoft_mas.agents.speech_agent`), so they cannot be instantiated without code additions.

---

## 4. Why Aren’t All Agents “Running”?

1. **Orchestrator dashboard is mock** – It always shows 42 total and 8 active from hardcoded data, not from `agent_pool.get_all_agents()`.
2. **Runtime uses AgentPool (spawn model)** – Agents are **spawned on demand** (e.g. via `/orchestrator/spawn`). Nothing auto-starts all 42 (or 52) at VM startup.
3. **Two registries** – Core registry (42) drives voice/API; registry AGENT_CATALOG (52) is async/Postgres and has many broken module paths. They are not synced.
4. **Cluster/v2 agents** – Many cluster and v2 agents are in code but not in the core 42; some are in the catalog with missing modules.
5. **Cursor agents** – The 27 Cursor agents are IDE personas, not MAS processes; they don’t “run” on the VM.

---

## 5. What “Actual Number” to Use

- **For “how many agents are registered and voice-routable today?”** → **42** (core agent registry).
- **For “how many agent classes exist in the codebase?”** → **~55–65** (MAS repo).
- **For “how many are running on the VM right now?”** → Query **GET /orchestrator/agents** and use **real** data (after fixing the endpoint to return `agent_pool.get_all_agents()` instead of mock).
- **For “223+”** → No code or API returns this; treat as an outdated or derived sum (e.g. 117 + 42 + 28 + …). Recommend retiring “223+” and using the counts above.

---

## 6. Recommendations: Single Registry and “All Running”

1. **Single source of truth**  
   - Choose one registry as canonical (recommended: **core agent registry** in `core/agent_registry.py`).  
   - Have dashboard, orchestrator API, and (if kept) MINDEX registry all **read from** that source or a single API that exposes it.

2. **Fix orchestrator dashboard**  
   - Replace hardcoded `totalAgents: 42` and the 8-agent list in `orchestrator_api.py` with real data from `orchestrator.list_agents()` / `agent_pool.get_all_agents()`.  
   - Optionally add a second line: “Registered (voice-routable): 42” from core registry.

3. **Align registry catalog with code**  
   - Either: (a) Remove or fix entries in `registry/agent_registry.py` AGENT_CATALOG so every `module`/`class` exists, or (b) Stop using AGENT_CATALOG for “total agent count” and document that only the core 42 are the voice-routable set.

4. **“All running”**  
   - To have “all” agents “running,” define what that means:  
     - **Option A:** All 42 in the core registry are **available for routing** (they already are; no spawn needed for routing).  
     - **Option B:** All 42 (or a subset) are **spawned** at startup so `agent_pool.get_all_agents()` returns them. That requires an orchestrator startup loop that spawns each registered agent type (and handling of spawn failures and resource limits).  
   - Implement Option B only after clarifying which agent types are safe to auto-spawn and with what resources.

5. **Update docs**  
   - CLAUDE.md: Change “117+ AI agents” to “42 registered agents, 55+ agent classes in codebase.”  
   - full-codebase-map: Change “100+ agents” to “~55+ agent classes, 42 in core registry.”  
   - Full-context rule: Keep “28 Specialized Sub-Agents” for Cursor only; add one line: “MAS runtime agents: 42 (core registry).”

6. **Full registry doc**  
   - Keep this document as the **full agent registry**; update when adding/removing agents or changing the single source of truth.

---

## 7. API Endpoints That Return Agent Counts

| Endpoint | Returns | Source |
|----------|--------|--------|
| GET `/api/agents/registry/` | `total_agents`, list of 42 | core/agent_registry.py |
| GET `/orchestrator/dashboard` | `totalAgents: 42`, `activeAgents: 8` (mock) | orchestrator_api.py hardcoded |
| GET `/orchestrator/agents` | Same mock 8 agents + 42 total | orchestrator_api.py |
| GET `/orchestrator/status` | `agentCount: 42` (mock) | orchestrator_api.py |
| (Orchestrator service) `list_agents()` | Real spawned agents | agent_pool.get_all_agents() – not exposed in dashboard |
| GET `/api/registry/agents` (MINDEX) | DB-backed list | registry.system_registry list_agents() – may be empty or different |

After fixes, dashboard and status should expose **real** runtime counts and, separately, “registered (voice-routable): 42.”

---

## 8. File Reference

| File | Role |
|------|------|
| `mycosoft_mas/core/agent_registry.py` | 42 built-in definitions; voice/API registry (single source of truth for “registered”) |
| `mycosoft_mas/core/routers/agent_registry_api.py` | Exposes core registry at `/api/agents/registry/` |
| `mycosoft_mas/core/routers/orchestrator_api.py` | Dashboard; currently hardcoded 42/8 – **to fix** |
| `mycosoft_mas/registry/agent_registry.py` | AGENT_CATALOG (52); many missing modules |
| `mycosoft_mas/agents/__init__.py` | 17 real + 10 stubs |
| `mycosoft_mas/agents/registry.json` | 1 custom agent |
| `mycosoft_mas/core/orchestrator_service.py` | agent_pool, real list_agents() |
| `.cursor/agents/*.md` | 27 Cursor sub-agents (not MAS runtime) |

---

*End of document. Update this file when adding/removing agents or changing the canonical registry.*
