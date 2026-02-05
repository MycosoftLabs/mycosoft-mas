"""
Agent Registry Service.
Created: February 5, 2026

Comprehensive registry for all AI agents in the Mycosoft Multi-Agent System.
Provides discovery, registration, status tracking, and capability management
for 96+ agents across all subsystems.

Agent Categories:
- Core Orchestration (MYCA, Coordinator, Supervisor)
- Voice Processing (Speech, TTS, STT, Dialog)
- Scientific Research (Lab, Simulation, Protocol)
- MycoBrain Device Control (Telemetry, Firmware)
- NatureOS Platform (Device, Environment)
- Financial (Trading, Analysis)
- Memory Management (Graph, Vector, Session)
- n8n Workflow Integration
"""

import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger("AgentRegistry")


class AgentCategory(str, Enum):
    """Categories of agents in the system."""
    ORCHESTRATION = "orchestration"
    VOICE = "voice"
    SCIENTIFIC = "scientific"
    MYCOBRAIN = "mycobrain"
    NATUREOS = "natureos"
    FINANCIAL = "financial"
    MEMORY = "memory"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"
    UTILITY = "utility"


class AgentStatus(str, Enum):
    """Possible agent states."""
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    INITIALIZING = "initializing"


@dataclass
class AgentCapability:
    """A capability that an agent can perform."""
    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    requires_auth: bool = False
    rate_limited: bool = False


@dataclass
class RegisteredAgent:
    """A registered agent in the system."""
    id: UUID
    name: str
    category: AgentCategory
    description: str
    module_path: str
    class_name: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.OFFLINE
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: Optional[datetime] = None


class AgentRegistry:
    """
    Central registry for all Mycosoft AI agents.
    
    Provides:
    - Agent registration and discovery
    - Capability querying
    - Status monitoring
    - Dependency management
    - Category-based filtering
    """
    
    # Pre-defined agent catalog
    AGENT_CATALOG = [
        # ===== Orchestration Agents =====
        {"name": "myca_agent", "category": "orchestration", "module": "mycosoft_mas.agents.v2.myca_agent", "class": "MYCAAgent", "description": "MYCA Core Orchestrator - Central AI coordinator"},
        {"name": "supervisor_agent", "category": "orchestration", "module": "mycosoft_mas.agents.v2.supervisor_agent", "class": "SupervisorAgent", "description": "Multi-agent workflow supervisor"},
        {"name": "coordinator_agent", "category": "orchestration", "module": "mycosoft_mas.agents.v2.coordinator_agent", "class": "CoordinatorAgent", "description": "Task coordination and routing"},
        {"name": "registry_agent", "category": "orchestration", "module": "mycosoft_mas.agents.v2.registry_agent", "class": "RegistryAgent", "description": "System registry management"},
        {"name": "planner_agent", "category": "orchestration", "module": "mycosoft_mas.agents.v2.planner_agent", "class": "PlannerAgent", "description": "Task planning and decomposition"},
        {"name": "executor_agent", "category": "orchestration", "module": "mycosoft_mas.agents.v2.executor_agent", "class": "ExecutorAgent", "description": "Task execution management"},
        
        # ===== Voice Processing Agents =====
        {"name": "speech_agent", "category": "voice", "module": "mycosoft_mas.agents.speech_agent", "class": "SpeechAgent", "description": "Speech processing and recognition"},
        {"name": "tts_agent", "category": "voice", "module": "mycosoft_mas.agents.tts_agent", "class": "TTSAgent", "description": "Text-to-speech synthesis"},
        {"name": "stt_agent", "category": "voice", "module": "mycosoft_mas.agents.stt_agent", "class": "STTAgent", "description": "Speech-to-text transcription"},
        {"name": "voice_bridge_agent", "category": "voice", "module": "mycosoft_mas.agents.voice_bridge_agent", "class": "VoiceBridgeAgent", "description": "PersonaPlex voice bridge"},
        {"name": "dialog_agent", "category": "voice", "module": "mycosoft_mas.agents.dialog_agent", "class": "DialogAgent", "description": "Conversational dialog management"},
        {"name": "intent_agent", "category": "voice", "module": "mycosoft_mas.agents.intent_agent", "class": "IntentAgent", "description": "Intent classification and extraction"},
        
        # ===== Scientific Research Agents =====
        {"name": "lab_manager_agent", "category": "scientific", "module": "mycosoft_mas.agents.v2.lab_agents", "class": "LabManagerAgent", "description": "Laboratory experiment coordination"},
        {"name": "experiment_agent", "category": "scientific", "module": "mycosoft_mas.agents.v2.scientific_agents", "class": "ExperimentAgent", "description": "Experiment design and execution"},
        {"name": "analysis_agent", "category": "scientific", "module": "mycosoft_mas.agents.v2.scientific_agents", "class": "AnalysisAgent", "description": "Data analysis and reporting"},
        {"name": "simulation_agent", "category": "scientific", "module": "mycosoft_mas.agents.v2.simulation_agents", "class": "SimulationAgent", "description": "Scientific simulation runner"},
        {"name": "protocol_agent", "category": "scientific", "module": "mycosoft_mas.agents.v2.scientific_agents", "class": "ProtocolAgent", "description": "Protocol management and execution"},
        {"name": "mycology_agent", "category": "scientific", "module": "mycosoft_mas.agents.v2.scientific_agents", "class": "MycologyAgent", "description": "Mycology research specialist"},
        {"name": "earth2_agent", "category": "scientific", "module": "mycosoft_mas.agents.v2.earth2_agents", "class": "Earth2Agent", "description": "Earth2 climate simulation"},
        
        # ===== MycoBrain Device Agents =====
        {"name": "telemetry_forwarder_agent", "category": "mycobrain", "module": "mycosoft_mas.agents.mycobrain.telemetry_forwarder_agent", "class": "TelemetryForwarderAgent", "description": "Device telemetry forwarding"},
        {"name": "firmware_update_agent", "category": "mycobrain", "module": "mycosoft_mas.agents.mycobrain.firmware_update_agent", "class": "FirmwareUpdateAgent", "description": "Device firmware management"},
        {"name": "nfc_agent", "category": "mycobrain", "module": "mycosoft_mas.agents.mycobrain.nfc_agent", "class": "NFCAgent", "description": "NFC tag reading and writing"},
        {"name": "sensor_agent", "category": "mycobrain", "module": "mycosoft_mas.agents.mycobrain.sensor_agent", "class": "SensorAgent", "description": "Sensor data processing"},
        {"name": "camera_agent", "category": "mycobrain", "module": "mycosoft_mas.agents.mycobrain.camera_agent", "class": "CameraAgent", "description": "Camera vision processing"},
        {"name": "grow_controller_agent", "category": "mycobrain", "module": "mycosoft_mas.agents.mycobrain.grow_controller_agent", "class": "GrowControllerAgent", "description": "Growth environment control"},
        
        # ===== NatureOS Platform Agents =====
        {"name": "device_registry_agent", "category": "natureos", "module": "mycosoft_mas.agents.natureos.device_registry_agent", "class": "DeviceRegistryAgent", "description": "Device registration and discovery"},
        {"name": "environment_agent", "category": "natureos", "module": "mycosoft_mas.agents.natureos.environment_agent", "class": "EnvironmentAgent", "description": "Environmental monitoring"},
        {"name": "data_pipeline_agent", "category": "natureos", "module": "mycosoft_mas.agents.natureos.data_pipeline_agent", "class": "DataPipelineAgent", "description": "Data pipeline orchestration"},
        {"name": "edge_compute_agent", "category": "natureos", "module": "mycosoft_mas.agents.natureos.edge_compute_agent", "class": "EdgeComputeAgent", "description": "Edge computing coordination"},
        
        # ===== Financial Agents =====
        {"name": "trading_agent", "category": "financial", "module": "mycosoft_mas.agents.trading_agent", "class": "TradingAgent", "description": "Crypto trading operations"},
        {"name": "market_analysis_agent", "category": "financial", "module": "mycosoft_mas.agents.market_analysis_agent", "class": "MarketAnalysisAgent", "description": "Market data analysis"},
        {"name": "portfolio_agent", "category": "financial", "module": "mycosoft_mas.agents.portfolio_agent", "class": "PortfolioAgent", "description": "Portfolio management"},
        {"name": "opportunity_scout_agent", "category": "financial", "module": "mycosoft_mas.agents.opportunity_scout_agent", "class": "OpportunityScoutAgent", "description": "Investment opportunity detection"},
        
        # ===== Memory Agents =====
        {"name": "memory_manager_agent", "category": "memory", "module": "mycosoft_mas.agents.memory.memory_manager_agent", "class": "MemoryManagerAgent", "description": "Central memory coordination"},
        {"name": "graph_memory_agent", "category": "memory", "module": "mycosoft_mas.agents.memory.graph_memory_agent", "class": "GraphMemoryAgent", "description": "Knowledge graph operations"},
        {"name": "vector_memory_agent", "category": "memory", "module": "mycosoft_mas.agents.memory.vector_memory_agent", "class": "VectorMemoryAgent", "description": "Vector embedding storage"},
        {"name": "session_memory_agent", "category": "memory", "module": "mycosoft_mas.agents.memory.session_memory_agent", "class": "SessionMemoryAgent", "description": "Session state management"},
        {"name": "long_term_memory_agent", "category": "memory", "module": "mycosoft_mas.agents.memory.long_term_memory_agent", "class": "LongTermMemoryAgent", "description": "Long-term memory persistence"},
        
        # ===== Workflow Agents =====
        {"name": "n8n_workflow_agent", "category": "workflow", "module": "mycosoft_mas.agents.workflow.n8n_workflow_agent", "class": "N8NWorkflowAgent", "description": "n8n workflow execution"},
        {"name": "trigger_agent", "category": "workflow", "module": "mycosoft_mas.agents.workflow.trigger_agent", "class": "TriggerAgent", "description": "Event trigger management"},
        {"name": "scheduler_agent", "category": "workflow", "module": "mycosoft_mas.agents.workflow.scheduler_agent", "class": "SchedulerAgent", "description": "Task scheduling"},
        {"name": "notification_agent", "category": "workflow", "module": "mycosoft_mas.agents.workflow.notification_agent", "class": "NotificationAgent", "description": "Notification dispatch"},
        
        # ===== Integration Agents =====
        {"name": "api_gateway_agent", "category": "integration", "module": "mycosoft_mas.agents.integration.api_gateway_agent", "class": "APIGatewayAgent", "description": "API gateway coordination"},
        {"name": "webhook_agent", "category": "integration", "module": "mycosoft_mas.agents.integration.webhook_agent", "class": "WebhookAgent", "description": "Webhook management"},
        {"name": "mcp_bridge_agent", "category": "integration", "module": "mycosoft_mas.agents.integration.mcp_bridge_agent", "class": "MCPBridgeAgent", "description": "MCP protocol bridge"},
        {"name": "database_agent", "category": "integration", "module": "mycosoft_mas.agents.integration.database_agent", "class": "DatabaseAgent", "description": "Database operations"},
        
        # ===== Utility Agents =====
        {"name": "health_check_agent", "category": "utility", "module": "mycosoft_mas.agents.utility.health_check_agent", "class": "HealthCheckAgent", "description": "System health monitoring"},
        {"name": "log_agent", "category": "utility", "module": "mycosoft_mas.agents.utility.log_agent", "class": "LogAgent", "description": "Log aggregation and analysis"},
        {"name": "backup_agent", "category": "utility", "module": "mycosoft_mas.agents.utility.backup_agent", "class": "BackupAgent", "description": "Data backup operations"},
        {"name": "cleanup_agent", "category": "utility", "module": "mycosoft_mas.agents.utility.cleanup_agent", "class": "CleanupAgent", "description": "Resource cleanup"},
    ]
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize agent registry."""
        self._database_url = database_url or os.getenv(
            "MINDEX_DATABASE_URL",
            "postgresql://mycosoft:REDACTED_VM_SSH_PASSWORD@192.168.0.189:5432/mindex"
        )
        self._agents: Dict[str, RegisteredAgent] = {}
        self._initialized = False
        self._pool = None
    
    async def initialize(self) -> None:
        """Initialize the registry and load agents."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=5
            )
            logger.info("Agent registry connected to database")
        except Exception as e:
            logger.warning(f"Database connection failed, using in-memory registry: {e}")
        
        # Register catalog agents
        await self._register_catalog_agents()
        self._initialized = True
        logger.info(f"Agent registry initialized with {len(self._agents)} agents")
    
    async def _register_catalog_agents(self) -> None:
        """Register all agents from the catalog."""
        for agent_def in self.AGENT_CATALOG:
            agent = RegisteredAgent(
                id=uuid4(),
                name=agent_def["name"],
                category=AgentCategory(agent_def["category"]),
                description=agent_def["description"],
                module_path=agent_def["module"],
                class_name=agent_def["class"],
                status=AgentStatus.OFFLINE
            )
            self._agents[agent.name] = agent
            
            # Persist to database if available
            if self._pool:
                await self._persist_agent(agent)
    
    async def _persist_agent(self, agent: RegisteredAgent) -> None:
        """Persist agent to database."""
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO registry.agents (name, type, description, status, metadata)
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    ON CONFLICT (name) DO UPDATE SET
                        type = EXCLUDED.type,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status,
                        metadata = EXCLUDED.metadata
                """, agent.name, agent.category.value, agent.description,
                    agent.status.value, f'{{"module": "{agent.module_path}", "class": "{agent.class_name}"}}')
        except Exception as e:
            logger.warning(f"Failed to persist agent {agent.name}: {e}")
    
    def get_agent(self, name: str) -> Optional[RegisteredAgent]:
        """Get an agent by name."""
        return self._agents.get(name)
    
    def get_agents_by_category(self, category: AgentCategory) -> List[RegisteredAgent]:
        """Get all agents in a category."""
        return [a for a in self._agents.values() if a.category == category]
    
    def get_active_agents(self) -> List[RegisteredAgent]:
        """Get all active agents."""
        return [a for a in self._agents.values() if a.status == AgentStatus.ACTIVE]
    
    def get_all_agents(self) -> List[RegisteredAgent]:
        """Get all registered agents."""
        return list(self._agents.values())
    
    async def update_status(self, name: str, status: AgentStatus) -> bool:
        """Update an agent's status."""
        if name not in self._agents:
            return False
        
        self._agents[name].status = status
        self._agents[name].last_heartbeat = datetime.now(timezone.utc)
        
        if self._pool:
            await self._persist_agent(self._agents[name])
        
        return True
    
    def get_agent_count_by_category(self) -> Dict[str, int]:
        """Get agent counts per category."""
        counts = {}
        for cat in AgentCategory:
            counts[cat.value] = len([a for a in self._agents.values() if a.category == cat])
        return counts
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_agents": len(self._agents),
            "by_category": self.get_agent_count_by_category(),
            "by_status": {
                s.value: len([a for a in self._agents.values() if a.status == s])
                for s in AgentStatus
            },
            "initialized": self._initialized,
            "database_connected": self._pool is not None
        }


# Singleton instance
_agent_registry: Optional[AgentRegistry] = None


async def get_agent_registry() -> AgentRegistry:
    """Get or create the singleton agent registry instance."""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
        await _agent_registry.initialize()
    return _agent_registry
