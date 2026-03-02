# Mycosoft MAS - Definitive Agent Census

**Date:** March 2, 2026
**Audited by:** Claude Code Agent
**Status:** CANONICAL - This is the single source of truth for agent counts

---

## Executive Summary

After a complete codebase audit, the conflicting agent numbers (40, 117, 273+) have been resolved. The real numbers are:

| Metric | Count | Notes |
|--------|-------|-------|
| **Total unique agent classes** | **160** | All Python classes inheriting BaseAgent/BaseAgentV2 |
| **Fully implemented** | **87** | Have real `process_task`/`execute_task`/`run_cycle` logic |
| **Stubs/skeleton** | **73** | Minimal implementation, need buildout |
| **Legacy runtime stubs** | **11** | Generated at runtime in `__init__.py`, no real code |
| **Core Registry (voice-routable)** | **46** | In `mycosoft_mas/core/agent_registry.py` |
| **Catalog Registry** | **55** | In `mycosoft_mas/registry/agent_registry.py` |
| **Combined registry (unique)** | **100** | Only 1 overlap between the two registries |
| **Unregistered agents** | **~60** | Exist in code but in neither registry |

### Where the Conflicting Numbers Came From

| Claimed | Source | Reality |
|---------|--------|---------|
| **40** | Early status docs | ~46 agents in the core voice-routable registry |
| **117+** | CLAUDE.md | Aspirational. Real combined registry = 100 |
| **215+** | AGENT_REGISTRY.md | Counted duplicates, sub-agents, Pydantic models |
| **273+** | Various docs | Summed overlapping sources + stubs + non-agents |

**THE REAL NUMBER IS 160 UNIQUE AGENT CLASSES, OF WHICH 87 ARE FULLY IMPLEMENTED.**

---

## The Two Registry Problem

There are TWO separate registries that do NOT overlap (except `gap_agent`):

### Registry 1: Core Voice-Routable Registry (46 agents)
**File:** `mycosoft_mas/core/agent_registry.py`
**Used by:** MYCA voice commands, 24/7 agent runner, orchestrator routing
**These are the agents that actually RUN in the 24/7 cycle.**

### Registry 2: Catalog Registry (55 agents)
**File:** `mycosoft_mas/registry/agent_registry.py`
**Used by:** System discovery, database persistence, status tracking
**These are the agents in the AGENT_CATALOG for the async registry service.**

### The Problem
- Only **1 agent** (`gap_agent`) exists in both
- **60+ agents** in the codebase are in NEITHER registry
- The v2 corporate agents (CEO, CFO, CTO, etc.) are in neither
- The v2 Earth2 agents are in neither
- The v2 scientific/lab agents are in neither

---

## Complete Agent Inventory by Department

### Core/Orchestration (9 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | ManagerAgent | IMPL | Core | agents/manager_agent.py |
| 2 | MYCAAgent | IMPL | - | agents/v2/myca_agent.py |
| 3 | SupervisorAgent | IMPL | - | agents/v2/supervisor_agent.py |
| 4 | CoordinatorAgent | IMPL | - | agents/v2/coordinator_agent.py |
| 5 | PlannerAgent | IMPL | - | agents/v2/planner_agent.py |
| 6 | ExecutorAgent | IMPL | - | agents/v2/executor_agent.py |
| 7 | RegistryAgent | IMPL | - | agents/v2/registry_agent.py |
| 8 | DashboardAgent | STUB | Core | agents/dashboard_agent.py |
| 9 | GapAgent | IMPL | Both | agents/gap_agent.py |

### Corporate Suite (12 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | CEOAgent | IMPL | - | agents/v2/corporate_agents.py |
| 2 | CFOAgent | IMPL | - | agents/v2/corporate_agents.py |
| 3 | CTOAgent | IMPL | - | agents/v2/corporate_agents.py |
| 4 | COOAgent | IMPL | - | agents/v2/corporate_agents.py |
| 5 | LegalAgent | IMPL | - | agents/v2/corporate_agents.py |
| 6 | HRAgent | IMPL | - | agents/v2/corporate_agents.py |
| 7 | MarketingAgent (v2) | IMPL | - | agents/v2/corporate_agents.py |
| 8 | SalesAgent (v2) | IMPL | - | agents/v2/corporate_agents.py |
| 9 | ProcurementAgent | IMPL | - | agents/v2/corporate_agents.py |
| 10 | CorporateOperationsAgent | STUB | Core | agents/corporate/ |
| 11 | BoardOperationsAgent | STUB | Core | agents/corporate/ |
| 12 | LegalComplianceAgent | STUB | Core | agents/corporate/ |

### Financial (8 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | FinancialAgent | STUB | Core | agents/financial/ |
| 2 | RelayFinancialAgent | STUB | Core | agents/financial/ |
| 3 | FinanceAdminAgent | STUB | Core | agents/finance_admin_agent.py |
| 4 | FinancialOperationsAgent | STUB | - | agents/financial/ |
| 5 | TokenEconomicsAgent | STUB | Core | agents/token_economics_agent.py |
| 6 | TradingAgent | IMPL | Catalog | agents/trading_agent.py |
| 7 | MarketAnalysisAgent | IMPL | Catalog | agents/market_analysis_agent.py |
| 8 | PortfolioAgent | IMPL | Catalog | agents/portfolio_agent.py |

### Scientific & Research (11 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | LabAgent | IMPL | - | agents/v2/scientific_agents.py |
| 2 | ScientistAgent | IMPL | - | agents/v2/scientific_agents.py |
| 3 | SimulationAgent | IMPL | - | agents/v2/scientific_agents.py |
| 4 | HypothesisAgent | IMPL | - | agents/v2/scientific_agents.py |
| 5 | ProteinDesignAgent | IMPL | - | agents/v2/scientific_agents.py |
| 6 | MetabolicPathwayAgent | IMPL | - | agents/v2/scientific_agents.py |
| 7 | MyceliumComputeAgent | IMPL | - | agents/v2/scientific_agents.py |
| 8 | ResearchAgent | IMPL | Core | agents/research_agent.py |
| 9 | ExperimentAgent | STUB | Core | agents/experiment_agent.py |
| 10 | BioreactorAgent | IMPL | - | agents/v2/lab_agents.py |
| 11 | IncubatorAgent | IMPL | - | agents/v2/lab_agents.py |

### Lab Equipment (4 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | MicroscopyAgent | IMPL | - | agents/v2/lab_agents.py |
| 2 | PipettorAgent | IMPL | - | agents/v2/lab_agents.py |
| 3 | BioreactorAgent | IMPL | - | agents/v2/lab_agents.py |
| 4 | IncubatorAgent | IMPL | - | agents/v2/lab_agents.py |

### Simulation (10 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | AlphaFoldAgent | IMPL | - | agents/v2/simulation_agents.py |
| 2 | BoltzGenAgent | IMPL | - | agents/v2/simulation_agents.py |
| 3 | COBRAAgent | IMPL | - | agents/v2/simulation_agents.py |
| 4 | MyceliumSimulatorAgent | IMPL | Core | agents/v2/simulation_agents.py |
| 5 | PhysicsSimulatorAgent | IMPL | - | agents/v2/simulation_agents.py |
| 6 | PhysicsNeMoAgent | IMPL | - | agents/v2/physicsnemo_agent.py |
| 7 | GrowthSimulatorAgent | STUB | Core | agents/clusters/simulation/ |
| 8 | CompoundSimulatorAgent | STUB | Core | agents/clusters/simulation/ |
| 9 | PetriDishSimulatorAgent | STUB | Core | agents/clusters/simulation/ |
| 10 | NatureOSSimulationAgent | IMPL | - | agents/natureos_simulation_agent.py |

### Earth2/Climate (5 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | Earth2OrchestratorAgent | IMPL | - | agents/v2/earth2_agents.py |
| 2 | WeatherForecastAgent | IMPL | - | agents/v2/earth2_agents.py |
| 3 | NowcastAgent | IMPL | - | agents/v2/earth2_agents.py |
| 4 | ClimateSimulationAgent | IMPL | - | agents/v2/earth2_agents.py |
| 5 | SporeDispersalAgent | IMPL | - | agents/v2/earth2_agents.py |

### Device/MycoBrain (14 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | MycoBrainCoordinatorAgent | STUB | - | agents/v2/device_agents.py |
| 2 | MycoBrainDeviceAgent | STUB | Core | agents/mycobrain/device_agent.py |
| 3 | MycoBrainIngestionAgent | STUB | Core | agents/mycobrain/ingestion_agent.py |
| 4 | MycoBrainTelemetryForwarderAgent | STUB | - | agents/mycobrain/ |
| 5 | BME688SensorAgent | STUB | - | agents/v2/device_agents.py |
| 6 | BME690SensorAgent | STUB | - | agents/v2/device_agents.py |
| 7 | LoRaGatewayAgent | STUB | - | agents/v2/device_agents.py |
| 8 | FirmwareAgent | STUB | - | agents/v2/device_agents.py |
| 9 | MycoDroneAgent | STUB | - | agents/v2/device_agents.py |
| 10 | SpectrometerAgent | STUB | - | agents/v2/device_agents.py |
| 11 | CameraAgent | IMPL | Catalog | agents/mycobrain/camera_agent.py |
| 12 | SensorAgent | IMPL | Catalog | agents/mycobrain/sensor_agent.py |
| 13 | NFCAgent | IMPL | Catalog | agents/mycobrain/nfc_agent.py |
| 14 | GrowControllerAgent | IMPL | Catalog | agents/mycobrain/ |

### Infrastructure (8 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | ProxmoxAgent | STUB | - | agents/v2/infrastructure_agents.py |
| 2 | DockerAgent | STUB | - | agents/v2/infrastructure_agents.py |
| 3 | NetworkAgent | STUB | - | agents/v2/infrastructure_agents.py |
| 4 | StorageAgent | STUB | - | agents/v2/infrastructure_agents.py |
| 5 | MonitoringAgent | STUB | - | agents/v2/infrastructure_agents.py |
| 6 | DeploymentAgent | STUB | - | agents/v2/infrastructure_agents.py |
| 7 | CloudflareAgent | STUB | - | agents/v2/infrastructure_agents.py |
| 8 | SecurityAgent | STUB | - | agents/v2/infrastructure_agents.py |

### Integration (16 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | N8NAgent | STUB | - | agents/v2/integration_agents.py |
| 2 | ElevenLabsAgent | STUB | - | agents/v2/integration_agents.py |
| 3 | ZapierAgent | STUB | - | agents/v2/integration_agents.py |
| 4 | IFTTTAgent | STUB | - | agents/v2/integration_agents.py |
| 5 | OpenAIAgent | STUB | - | agents/v2/integration_agents.py |
| 6 | AnthropicAgent | STUB | - | agents/v2/integration_agents.py |
| 7 | GeminiAgent | STUB | - | agents/v2/integration_agents.py |
| 8 | GrokAgent | STUB | - | agents/v2/integration_agents.py |
| 9 | SupabaseAgent | STUB | - | agents/v2/integration_agents.py |
| 10 | NotionAgent | STUB | - | agents/v2/integration_agents.py |
| 11 | WebsiteAgent | STUB | - | agents/v2/integration_agents.py |
| 12 | APIGatewayAgent | IMPL | Catalog | agents/integration/ |
| 13 | WebhookAgent | IMPL | Catalog | agents/integration/ |
| 14 | MCPBridgeAgent | IMPL | Catalog | agents/integration/ |
| 15 | DatabaseAgent | IMPL | Catalog | agents/integration/ |
| 16 | CameraIntegration | STUB | - | agents/integrations/ |

### Security (5 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | GuardianAgent (v1) | IMPL | Core | agents/guardian_agent.py |
| 2 | GuardianAgentV2 | IMPL | - | agents/v2/security_agents.py |
| 3 | SecurityMonitorAgentV2 | IMPL | - | agents/v2/security_agents.py |
| 4 | ThreatResponseAgentV2 | IMPL | - | agents/v2/security_agents.py |
| 5 | CREPSecurityAgent | IMPL | - | agents/crep_security_agent.py |

### Voice/Dialog (6 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | SpeechAgent | IMPL | Catalog | agents/speech_agent.py |
| 2 | TTSAgent | IMPL | Catalog | agents/tts_agent.py |
| 3 | STTAgent | IMPL | Catalog | agents/stt_agent.py |
| 4 | VoiceBridgeAgent | IMPL | Catalog | agents/voice_bridge_agent.py |
| 5 | DialogAgent | IMPL | Catalog | agents/dialog_agent.py |
| 6 | IntentAgent | IMPL | Catalog | agents/intent_agent.py |

### Memory (5 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | MemoryManagerAgent | IMPL | Catalog | agents/memory/ |
| 2 | GraphMemoryAgent | IMPL | Catalog | agents/memory/ |
| 3 | VectorMemoryAgent | IMPL | Catalog | agents/memory/ |
| 4 | SessionMemoryAgent | IMPL | Catalog | agents/memory/ |
| 5 | LongTermMemoryAgent | IMPL | Catalog | agents/memory/ |

### Workflow (5 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | N8NWorkflowAgent | IMPL | Catalog | agents/workflow/ |
| 2 | TriggerAgent | IMPL | Catalog | agents/workflow/ |
| 3 | SchedulerAgent | IMPL | Catalog | agents/workflow/ |
| 4 | NotificationAgent | IMPL | Catalog | agents/workflow/ |
| 5 | WorkflowGeneratorAgent | STUB | - | agents/workflow_generator_agent.py |

### Data/Cluster Agents (14 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | DataAnalysisAgent | STUB | Core | agents/clusters/analytics_insights/ |
| 2 | WebScraperAgent | STUB | Core | agents/clusters/data_collection/ |
| 3 | DataNormalizationAgent | STUB | Core | agents/clusters/data_collection/ |
| 4 | EnvironmentalDataAgent | STUB | Core | agents/clusters/data_collection/ |
| 5 | ImageProcessingAgent | STUB | Core | agents/clusters/data_collection/ |
| 6 | SearchAgent | STUB | Core | agents/clusters/search_discovery/ |
| 7 | DNAAnalysisAgent | STUB | Core | agents/clusters/knowledge_management/ |
| 8 | SpeciesDatabaseAgent | STUB | Core | agents/clusters/knowledge_management/ |
| 9 | MyceliumPatternAgent | STUB | Core | agents/clusters/pattern_recognition/ |
| 10 | EnvironmentalPatternAgent | STUB | Core | agents/clusters/pattern_recognition/ |
| 11 | MycorrhizaeProtocolAgent | STUB | Core | agents/clusters/protocol_management/ |
| 12 | DataFlowCoordinatorAgent | STUB | Core | agents/clusters/protocol_management/ |
| 13 | DeviceCoordinatorAgent | STUB | Core | agents/clusters/device_management/ |
| 14 | VisualizationAgent | STUB | Core | agents/clusters/user_interface/ |

### V2 Data Agents (5 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | MindexAgent | STUB | - | agents/v2/data_agents.py |
| 2 | NLMAgent | STUB | - | agents/v2/data_agents.py |
| 3 | ETLAgent | STUB | - | agents/v2/data_agents.py |
| 4 | SearchAgent (v2) | STUB | - | agents/v2/data_agents.py |
| 5 | RouteMonitorAgent | STUB | - | agents/v2/data_agents.py |

### NatureOS (5 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | DeviceRegistryAgent | IMPL | Catalog | agents/natureos/ |
| 2 | EnvironmentAgent | IMPL | Catalog | agents/natureos/ |
| 3 | DataPipelineAgent | IMPL | Catalog | agents/natureos/ |
| 4 | EdgeComputeAgent | IMPL | Catalog | agents/natureos/ |
| 5 | NatureOSSimulationAgent | IMPL | - | agents/natureos_simulation_agent.py |

### Utility (7 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | HealthCheckAgent | IMPL | Catalog | agents/utility/ |
| 2 | BackupAgent | IMPL | Catalog | agents/utility/ |
| 3 | CleanupAgent | IMPL | Catalog | agents/utility/ |
| 4 | LogAgent | IMPL | Catalog | agents/utility/ |
| 5 | DesktopAutomationAgent | STUB | Core | agents/desktop_automation_agent.py |
| 6 | GroundingAgent | IMPL | Catalog | agents/v2/grounding_agent.py |
| 7 | ReflectionAgent | IMPL | Catalog | agents/v2/reflection_agent.py |

### DAO/IP (3 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | MycoDAOAgent | IMPL | Core | agents/myco_dao_agent.py |
| 2 | IPTokenizationAgent | STUB | Core | agents/ip_tokenization_agent.py |
| 3 | IPAgent | STUB | Core | agents/ip_agent.py |

### Mycology (2 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | MycologyBioAgent | STUB | Core | agents/mycology_bio_agent.py |
| 2 | MycologyKnowledgeAgent | STUB | Core | agents/mycology_knowledge_agent.py |

### Business (5 agents)
| # | Agent | Status | Registry | File |
|---|-------|--------|----------|------|
| 1 | MarketingAgent (v1) | IMPL | Core | agents/marketing_agent.py |
| 2 | SalesAgent (v1) | IMPL | Core | agents/sales_agent.py |
| 3 | SecretaryAgent | IMPL | Core | agents/secretary_agent.py |
| 4 | ProjectManagerAgent | STUB | Core | agents/project_manager_agent.py |
| 5 | OpportunityScout | STUB | Core | agents/opportunity_scout.py |

### Legacy Runtime Stubs (11 agents)
These are generated at startup in `__init__.py` for backward compatibility:
ContractAgent, LegalAgent, TechnicalAgent, QAAgent, VerificationAgent,
AuditAgent, RegistryAgent, AnalyticsAgent, RiskAgent, ComplianceAgent, OperationsAgent

---

## Critical Issues to Fix

### 1. Unify the Two Registries
The core registry (`core/agent_registry.py`, 46 agents) and catalog registry (`registry/agent_registry.py`, 55 agents) have only 1 overlap. They need to be merged into a single source of truth.

### 2. Register the ~60 Unregistered Agents
Many v2 agents (corporate suite, earth2, scientific, infrastructure, integration) are not in either registry. They exist in code but the orchestrator doesn't know about them.

### 3. Implement 73 Stub Agents
73 agent classes exist as skeletons. The financial, infrastructure, integration, and device agent stubs particularly need implementation for a functioning enterprise.

### 4. Fix CLAUDE.md Agent Count
Update from "117+" to the real number: "160 agent classes (87 implemented, 73 stubs)".

### 5. Retire Conflicting Documentation
- `docs/AGENT_REGISTRY.md` (claims 215+) - outdated
- Any doc claiming 273+ agents - never was real

---

## How to Verify (Run Anytime)

```bash
python scripts/verify_agents.py          # Full report
python scripts/verify_agents.py --json   # Machine-readable
python scripts/verify_agents.py --category corporate  # Filter
```

---

## Live Runtime Status

The 24/7 agent runner (`core/agent_runner.py`) loads agents from the **Core Registry only** (46 agents) via `runner_agent_loader.py`. These run in cycles every 5 minutes. Agents that fail to import run in "fallback mode" (idle but present).

The Catalog Registry agents are available via the async registry service but are NOT automatically loaded into the runner.

**To make ALL agents run live, they need to be:**
1. Registered in the core registry
2. Have their module_path pointing to a real, importable class
3. Implement either `process_task()`, `execute_task()`, or `run_cycle()`
