#!/usr/bin/env python3
"""
Create MAS v2 Orchestrator Upgrade Files

This script creates the upgraded MYCA Orchestrator with:
- Agent spawning and lifecycle management
- Task distribution and routing
- Health monitoring and heartbeats
- Gap detection system
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


def create_orchestrator_service():
    """Create the upgraded orchestrator service"""
    content = '''"""
MAS v2 Orchestrator Service

The central MYCA orchestrator that manages all agents, tasks, and communications.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import runtime components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mycosoft_mas.runtime import (
        AgentPool,
        AgentConfig,
        AgentState,
        AgentStatus,
        AgentCategory,
        AgentMessage,
        MessageType,
        MessageBroker,
        TaskPriority,
        AgentTask,
    )
except ImportError:
    # Fallback for standalone execution
    from runtime import (
        AgentPool,
        AgentConfig,
        AgentState,
        AgentStatus,
        AgentCategory,
        AgentMessage,
        MessageType,
        MessageBroker,
        TaskPriority,
        AgentTask,
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MYCA_Orchestrator")


# Pydantic models for API
class AgentSpawnRequest(BaseModel):
    agent_id: str
    agent_type: str
    category: str = "core"
    display_name: Optional[str] = None
    description: str = ""
    cpu_limit: float = 1.0
    memory_limit: int = 512
    auto_start: bool = True


class TaskSubmitRequest(BaseModel):
    agent_id: str
    task_type: str
    payload: Dict[str, Any] = {}
    priority: int = 5
    timeout: int = 300


class MessageSendRequest(BaseModel):
    from_agent: str
    to_agent: str
    message_type: str = "request"
    payload: Dict[str, Any] = {}
    priority: int = 5


class OrchestratorService:
    """
    MYCA Orchestrator Service
    
    Central intelligence that:
    - Manages agent lifecycle (spawn, stop, restart)
    - Distributes tasks to agents
    - Monitors agent health
    - Handles agent-to-agent communication
    - Detects gaps and auto-creates agents
    """
    
    def __init__(self):
        self.agent_pool = AgentPool()
        self.message_broker: Optional[MessageBroker] = None
        self.task_queues: Dict[str, asyncio.Queue] = {}
        self.pending_tasks: Dict[str, AgentTask] = {}
        self.agent_heartbeats: Dict[str, datetime] = {}
        self._started = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the orchestrator service"""
        logger.info("Starting MYCA Orchestrator...")
        
        # Initialize agent pool
        await self.agent_pool.initialize()
        
        # Connect to message broker
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.message_broker = MessageBroker(redis_url)
        await self.message_broker.connect()
        
        # Subscribe to heartbeats
        await self.message_broker.subscribe(
            "orchestrator:heartbeats",
            self._handle_heartbeat
        )
        
        # Start monitoring
        self._monitor_task = asyncio.create_task(self._health_monitor())
        
        self._started = True
        logger.info("MYCA Orchestrator started")
    
    async def stop(self):
        """Stop the orchestrator service"""
        logger.info("Stopping MYCA Orchestrator...")
        
        if self._monitor_task:
            self._monitor_task.cancel()
        
        if self.message_broker:
            await self.message_broker.close()
        
        self._started = False
        logger.info("MYCA Orchestrator stopped")
    
    async def spawn_agent(self, config: AgentConfig) -> AgentState:
        """Spawn a new agent container"""
        logger.info(f"Spawning agent: {config.agent_id}")
        
        state = await self.agent_pool.spawn_agent(config)
        
        # Create task queue for agent
        self.task_queues[config.agent_id] = asyncio.Queue()
        
        # Log event
        if self.message_broker:
            event = AgentMessage(
                from_agent="orchestrator",
                to_agent="broadcast",
                message_type=MessageType.EVENT,
                payload={
                    "event": "agent_spawned",
                    "agent_id": config.agent_id,
                    "agent_type": config.agent_type,
                }
            )
            await self.message_broker.publish("mas:events", event.to_json())
        
        return state
    
    async def stop_agent(self, agent_id: str, force: bool = False) -> bool:
        """Stop an agent container"""
        logger.info(f"Stopping agent: {agent_id}")
        
        result = await self.agent_pool.stop_agent(agent_id, force)
        
        # Clean up task queue
        self.task_queues.pop(agent_id, None)
        
        # Log event
        if result and self.message_broker:
            event = AgentMessage(
                from_agent="orchestrator",
                to_agent="broadcast",
                message_type=MessageType.EVENT,
                payload={
                    "event": "agent_stopped",
                    "agent_id": agent_id,
                }
            )
            await self.message_broker.publish("mas:events", event.to_json())
        
        return result
    
    async def restart_agent(self, agent_id: str) -> AgentState:
        """Restart an agent container"""
        logger.info(f"Restarting agent: {agent_id}")
        return await self.agent_pool.restart_agent(agent_id)
    
    async def get_agent(self, agent_id: str) -> Optional[AgentState]:
        """Get agent state"""
        return await self.agent_pool.get_agent_state(agent_id)
    
    async def list_agents(self) -> List[AgentState]:
        """List all agents"""
        return await self.agent_pool.get_all_agents()
    
    async def submit_task(self, task: AgentTask) -> str:
        """Submit a task to an agent"""
        agent_id = task.agent_id
        
        # Check agent exists and is active
        state = await self.agent_pool.get_agent_state(agent_id)
        if not state:
            raise ValueError(f"Agent {agent_id} not found")
        if state.status not in [AgentStatus.ACTIVE, AgentStatus.IDLE]:
            raise ValueError(f"Agent {agent_id} is not available (status: {state.status.value})")
        
        # Store task
        self.pending_tasks[task.id] = task
        
        # Send to agent via message broker
        if self.message_broker:
            message = AgentMessage(
                from_agent="orchestrator",
                to_agent=agent_id,
                message_type=MessageType.REQUEST,
                payload={
                    "task_id": task.id,
                    "task_type": task.task_type,
                    **task.payload,
                },
                priority=task.priority,
            )
            await self.message_broker.publish(f"agent:{agent_id}", message.to_json())
        
        logger.info(f"Task {task.id} submitted to agent {agent_id}")
        return task.id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task"""
        task = self.pending_tasks.get(task_id)
        if task:
            return task.to_dict()
        return None
    
    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """Send a message between agents"""
        message = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
            priority=priority,
        )
        
        if self.message_broker:
            if to_agent == "broadcast":
                await self.message_broker.publish("mas:broadcast", message.to_json())
            else:
                await self.message_broker.publish(f"agent:{to_agent}", message.to_json())
        
        return message.id
    
    async def _handle_heartbeat(self, message_data: str):
        """Handle heartbeat from agent"""
        try:
            message = AgentMessage.from_json(message_data)
            agent_id = message.from_agent
            self.agent_heartbeats[agent_id] = datetime.utcnow()
            
            # Update agent state if provided
            payload = message.payload
            if payload:
                state = await self.agent_pool.get_agent_state(agent_id)
                if state:
                    state.tasks_completed = payload.get("tasks_completed", state.tasks_completed)
                    state.tasks_failed = payload.get("tasks_failed", state.tasks_failed)
                    state.last_heartbeat = datetime.utcnow()
                    
        except Exception as e:
            logger.error(f"Error handling heartbeat: {e}")
    
    async def _health_monitor(self):
        """Monitor agent health continuously"""
        check_interval = int(os.environ.get("HEALTH_CHECK_INTERVAL", "30"))
        heartbeat_timeout = int(os.environ.get("HEARTBEAT_TIMEOUT", "60"))
        
        while True:
            try:
                await asyncio.sleep(check_interval)
                
                # Check for dead agents
                now = datetime.utcnow()
                agents = await self.agent_pool.get_all_agents()
                
                for agent in agents:
                    last_heartbeat = self.agent_heartbeats.get(agent.agent_id)
                    
                    if last_heartbeat:
                        age = (now - last_heartbeat).total_seconds()
                        if age > heartbeat_timeout:
                            logger.warning(f"Agent {agent.agent_id} missed heartbeat (last: {age:.0f}s ago)")
                            agent.status = AgentStatus.ERROR
                            agent.error_message = "Heartbeat timeout"
                
                # Update container health
                await self.agent_pool.update_agent_health()
                
                # Log pool stats
                stats = await self.agent_pool.get_pool_stats()
                logger.debug(f"Pool stats: {stats}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    async def detect_gaps(self) -> List[Dict[str, Any]]:
        """Detect missing agents that should exist"""
        gaps = []
        
        # Required agent categories and minimum counts
        required = {
            AgentCategory.CORE: 3,
            AgentCategory.INFRASTRUCTURE: 5,
            AgentCategory.SECURITY: 2,
            AgentCategory.DATA: 3,
        }
        
        for category, min_count in required.items():
            agents = await self.agent_pool.get_agents_by_category(category)
            active = [a for a in agents if a.status in [AgentStatus.ACTIVE, AgentStatus.BUSY]]
            
            if len(active) < min_count:
                gaps.append({
                    "category": category.value,
                    "required": min_count,
                    "active": len(active),
                    "missing": min_count - len(active),
                })
        
        return gaps
    
    async def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        agents = await self.agent_pool.get_all_agents()
        stats = await self.agent_pool.get_pool_stats()
        
        return {
            "status": "running" if self._started else "stopped",
            "started": self._started,
            "total_agents": len(agents),
            "pool_stats": stats,
            "pending_tasks": len(self.pending_tasks),
            "message_broker_connected": self.message_broker is not None,
        }


# Create FastAPI app
app = FastAPI(
    title="MYCA Orchestrator",
    description="Multi-Agent System Orchestrator - Central Intelligence",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Orchestrator instance
orchestrator = OrchestratorService()


@app.on_event("startup")
async def startup():
    await orchestrator.start()


@app.on_event("shutdown")
async def shutdown():
    await orchestrator.stop()


# API Routes

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "myca-orchestrator"}


@app.get("/status")
async def status():
    """Get orchestrator status"""
    return await orchestrator.get_orchestrator_status()


@app.get("/agents")
async def list_agents():
    """List all agents"""
    agents = await orchestrator.list_agents()
    return {"agents": [a.to_dict() for a in agents]}


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details"""
    agent = await orchestrator.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.to_dict()


@app.post("/agents/spawn")
async def spawn_agent(request: AgentSpawnRequest):
    """Spawn a new agent"""
    try:
        category = AgentCategory(request.category)
    except ValueError:
        category = AgentCategory.CUSTOM
    
    config = AgentConfig(
        agent_id=request.agent_id,
        agent_type=request.agent_type,
        category=category,
        display_name=request.display_name or request.agent_id,
        description=request.description,
        cpu_limit=request.cpu_limit,
        memory_limit=request.memory_limit,
        auto_start=request.auto_start,
    )
    
    try:
        state = await orchestrator.spawn_agent(config)
        return state.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str, force: bool = False):
    """Stop an agent"""
    result = await orchestrator.stop_agent(agent_id, force)
    if not result:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "stopped", "agent_id": agent_id}


@app.post("/agents/{agent_id}/restart")
async def restart_agent(agent_id: str):
    """Restart an agent"""
    try:
        state = await orchestrator.restart_agent(agent_id)
        return state.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/agents/register")
async def register_agent(data: Dict[str, Any]):
    """Register an agent (called by agents on startup)"""
    agent_id = data.get("agent_id")
    logger.info(f"Agent registered: {agent_id}")
    return {"status": "registered", "agent_id": agent_id}


@app.post("/agents/{agent_id}/deregister")
async def deregister_agent(agent_id: str):
    """Deregister an agent (called by agents on shutdown)"""
    logger.info(f"Agent deregistered: {agent_id}")
    return {"status": "deregistered", "agent_id": agent_id}


@app.post("/tasks")
async def submit_task(request: TaskSubmitRequest):
    """Submit a task to an agent"""
    task = AgentTask(
        agent_id=request.agent_id,
        task_type=request.task_type,
        payload=request.payload,
        priority=TaskPriority(request.priority),
        timeout=request.timeout,
    )
    
    try:
        task_id = await orchestrator.submit_task(task)
        return {"task_id": task_id, "status": "submitted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task status"""
    task = await orchestrator.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/messages")
async def send_message(request: MessageSendRequest):
    """Send a message between agents"""
    try:
        message_type = MessageType(request.message_type)
    except ValueError:
        message_type = MessageType.REQUEST
    
    message_id = await orchestrator.send_message(
        request.from_agent,
        request.to_agent,
        message_type,
        request.payload,
        TaskPriority(request.priority),
    )
    
    return {"message_id": message_id, "status": "sent"}


@app.get("/gaps")
async def detect_gaps():
    """Detect missing agents"""
    gaps = await orchestrator.detect_gaps()
    return {"gaps": gaps}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
'''
    core_dir = BASE_DIR / "mycosoft_mas" / "core"
    (core_dir / "orchestrator_service.py").write_text(content)
    print("Created mycosoft_mas/core/orchestrator_service.py")


def create_gap_detector():
    """Create gap detector for automatic agent creation"""
    content = '''"""
MAS v2 Gap Detector

Detects missing agents and triggers automatic creation.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from mycosoft_mas.runtime import (
    AgentConfig,
    AgentCategory,
    AgentStatus,
)


logger = logging.getLogger("GapDetector")


@dataclass
class AgentGap:
    """Represents a detected gap in agent coverage"""
    gap_id: str
    gap_type: str  # category, route, integration, device
    category: Optional[AgentCategory]
    description: str
    severity: str  # critical, high, medium, low
    suggested_agent: Dict[str, Any]
    auto_create: bool
    detected_at: datetime


class GapDetector:
    """
    Detects gaps in agent coverage and suggests/creates agents.
    
    Gap Types:
    - Category: Missing agents in required categories
    - Route: API routes without monitoring agents
    - Integration: External services without agents
    - Device: MycoBrain devices without agents
    """
    
    # Required agents by category
    REQUIRED_AGENTS = {
        AgentCategory.CORE: [
            {"agent_id": "myca-core", "agent_type": "orchestrator", "description": "Central orchestrator"},
            {"agent_id": "task-router", "agent_type": "router", "description": "Task routing"},
            {"agent_id": "event-processor", "agent_type": "processor", "description": "Event processing"},
        ],
        AgentCategory.CORPORATE: [
            {"agent_id": "ceo-agent", "agent_type": "executive", "description": "Strategic decisions"},
            {"agent_id": "cfo-agent", "agent_type": "financial", "description": "Financial oversight"},
            {"agent_id": "cto-agent", "agent_type": "technical", "description": "Technology decisions"},
        ],
        AgentCategory.INFRASTRUCTURE: [
            {"agent_id": "proxmox-agent", "agent_type": "vm-manager", "description": "VM management"},
            {"agent_id": "docker-agent", "agent_type": "container-manager", "description": "Container orchestration"},
            {"agent_id": "network-agent", "agent_type": "network-manager", "description": "Network management"},
            {"agent_id": "storage-agent", "agent_type": "storage-manager", "description": "Storage management"},
            {"agent_id": "monitoring-agent", "agent_type": "monitor", "description": "System monitoring"},
        ],
        AgentCategory.SECURITY: [
            {"agent_id": "soc-agent", "agent_type": "security", "description": "Security operations"},
            {"agent_id": "audit-agent", "agent_type": "audit", "description": "Audit logging"},
        ],
        AgentCategory.DEVICE: [
            {"agent_id": "mycobrain-coordinator", "agent_type": "device-coordinator", "description": "MycoBrain fleet management"},
        ],
        AgentCategory.INTEGRATION: [
            {"agent_id": "n8n-agent", "agent_type": "workflow", "description": "n8n workflow integration"},
            {"agent_id": "zapier-agent", "agent_type": "integration", "description": "Zapier integration"},
            {"agent_id": "elevenlabs-agent", "agent_type": "voice", "description": "Voice synthesis"},
        ],
        AgentCategory.DATA: [
            {"agent_id": "mindex-agent", "agent_type": "database", "description": "MINDEX database operations"},
            {"agent_id": "etl-agent", "agent_type": "etl", "description": "Data ETL processing"},
            {"agent_id": "search-agent", "agent_type": "search", "description": "Search operations"},
        ],
    }
    
    # Routes that should have monitoring agents
    CRITICAL_ROUTES = [
        "/api/auth",
        "/api/mindex",
        "/api/mycobrain",
        "/api/natureos",
        "/api/ai",
        "/api/search",
    ]
    
    def __init__(self, agent_pool, orchestrator=None):
        self.agent_pool = agent_pool
        self.orchestrator = orchestrator
        self.detected_gaps: List[AgentGap] = []
    
    async def scan_for_gaps(self) -> List[AgentGap]:
        """Scan for all types of gaps"""
        self.detected_gaps = []
        
        await self._scan_category_gaps()
        await self._scan_route_gaps()
        await self._scan_integration_gaps()
        
        logger.info(f"Detected {len(self.detected_gaps)} gaps")
        return self.detected_gaps
    
    async def _scan_category_gaps(self):
        """Scan for missing agents by category"""
        for category, required_agents in self.REQUIRED_AGENTS.items():
            existing = await self.agent_pool.get_agents_by_category(category)
            existing_ids = {a.agent_id for a in existing if a.status in [AgentStatus.ACTIVE, AgentStatus.BUSY]}
            
            for agent_spec in required_agents:
                if agent_spec["agent_id"] not in existing_ids:
                    gap = AgentGap(
                        gap_id=f"category-{agent_spec['agent_id']}",
                        gap_type="category",
                        category=category,
                        description=f"Missing {agent_spec['description']} agent",
                        severity="high" if category in [AgentCategory.CORE, AgentCategory.SECURITY] else "medium",
                        suggested_agent={
                            "agent_id": agent_spec["agent_id"],
                            "agent_type": agent_spec["agent_type"],
                            "category": category.value,
                            "display_name": agent_spec["description"],
                            "description": agent_spec["description"],
                        },
                        auto_create=category in [AgentCategory.CORE, AgentCategory.INFRASTRUCTURE],
                        detected_at=datetime.utcnow(),
                    )
                    self.detected_gaps.append(gap)
    
    async def _scan_route_gaps(self):
        """Scan for API routes without monitoring"""
        # This would check which routes have active agents
        for route in self.CRITICAL_ROUTES:
            agent_id = f"route-{route.replace('/', '-').strip('-')}"
            state = await self.agent_pool.get_agent_state(agent_id)
            
            if not state or state.status not in [AgentStatus.ACTIVE, AgentStatus.BUSY]:
                gap = AgentGap(
                    gap_id=f"route-{agent_id}",
                    gap_type="route",
                    category=AgentCategory.DATA,
                    description=f"No monitoring agent for route {route}",
                    severity="medium",
                    suggested_agent={
                        "agent_id": agent_id,
                        "agent_type": "route-monitor",
                        "category": "data",
                        "display_name": f"Route Monitor: {route}",
                        "description": f"Monitors API route {route}",
                    },
                    auto_create=True,
                    detected_at=datetime.utcnow(),
                )
                self.detected_gaps.append(gap)
    
    async def _scan_integration_gaps(self):
        """Scan for integrations without agents"""
        integrations = [
            {"id": "n8n", "agent_type": "workflow", "critical": True},
            {"id": "zapier", "agent_type": "integration", "critical": False},
            {"id": "elevenlabs", "agent_type": "voice", "critical": True},
            {"id": "openai", "agent_type": "ai-provider", "critical": True},
            {"id": "anthropic", "agent_type": "ai-provider", "critical": True},
        ]
        
        for integration in integrations:
            agent_id = f"{integration['id']}-agent"
            state = await self.agent_pool.get_agent_state(agent_id)
            
            if not state or state.status not in [AgentStatus.ACTIVE, AgentStatus.BUSY]:
                gap = AgentGap(
                    gap_id=f"integration-{agent_id}",
                    gap_type="integration",
                    category=AgentCategory.INTEGRATION,
                    description=f"No agent for {integration['id']} integration",
                    severity="high" if integration["critical"] else "low",
                    suggested_agent={
                        "agent_id": agent_id,
                        "agent_type": integration["agent_type"],
                        "category": "integration",
                        "display_name": f"{integration['id'].capitalize()} Integration Agent",
                        "description": f"Manages {integration['id']} integration",
                    },
                    auto_create=integration["critical"],
                    detected_at=datetime.utcnow(),
                )
                self.detected_gaps.append(gap)
    
    async def auto_fill_gaps(self) -> List[str]:
        """Automatically create agents to fill gaps marked for auto-creation"""
        created = []
        
        for gap in self.detected_gaps:
            if not gap.auto_create:
                continue
            
            try:
                config = AgentConfig(
                    agent_id=gap.suggested_agent["agent_id"],
                    agent_type=gap.suggested_agent["agent_type"],
                    category=AgentCategory(gap.suggested_agent["category"]),
                    display_name=gap.suggested_agent["display_name"],
                    description=gap.suggested_agent["description"],
                )
                
                if self.orchestrator:
                    await self.orchestrator.spawn_agent(config)
                    created.append(config.agent_id)
                    logger.info(f"Auto-created agent: {config.agent_id}")
                    
            except Exception as e:
                logger.error(f"Failed to auto-create agent {gap.suggested_agent['agent_id']}: {e}")
        
        return created
    
    def get_gap_report(self) -> Dict[str, Any]:
        """Generate a gap report"""
        by_type = {}
        by_severity = {}
        
        for gap in self.detected_gaps:
            by_type[gap.gap_type] = by_type.get(gap.gap_type, 0) + 1
            by_severity[gap.severity] = by_severity.get(gap.severity, 0) + 1
        
        return {
            "total_gaps": len(self.detected_gaps),
            "by_type": by_type,
            "by_severity": by_severity,
            "auto_fillable": len([g for g in self.detected_gaps if g.auto_create]),
            "gaps": [
                {
                    "gap_id": g.gap_id,
                    "type": g.gap_type,
                    "severity": g.severity,
                    "description": g.description,
                    "auto_create": g.auto_create,
                }
                for g in self.detected_gaps
            ]
        }
'''
    runtime_dir = BASE_DIR / "mycosoft_mas" / "runtime"
    (runtime_dir / "gap_detector.py").write_text(content)
    print("Created mycosoft_mas/runtime/gap_detector.py")


def create_agent_factory():
    """Create agent factory for creating agents from templates"""
    content = '''"""
MAS v2 Agent Factory

Creates new agents from templates with validation and approval workflow.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import (
    AgentConfig,
    AgentCategory,
    AgentState,
    AgentMessage,
    MessageType,
)


logger = logging.getLogger("AgentFactory")


class AgentTemplate:
    """Template for creating new agents"""
    
    def __init__(
        self,
        template_id: str,
        agent_type: str,
        category: AgentCategory,
        display_name: str,
        description: str = "",
        cpu_limit: float = 1.0,
        memory_limit: int = 512,
        capabilities: List[str] = None,
        settings: Dict[str, Any] = None,
    ):
        self.template_id = template_id
        self.agent_type = agent_type
        self.category = category
        self.display_name = display_name
        self.description = description
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.capabilities = capabilities or []
        self.settings = settings or {}


class AgentFactory:
    """
    Factory for creating new agents.
    
    Provides:
    - Template-based agent creation
    - Validation before creation
    - Approval workflow for certain agent types
    - Event logging
    """
    
    # Pre-defined templates
    TEMPLATES = {
        "infrastructure": AgentTemplate(
            template_id="infrastructure",
            agent_type="infrastructure",
            category=AgentCategory.INFRASTRUCTURE,
            display_name="Infrastructure Agent",
            description="Manages infrastructure components",
            cpu_limit=1.0,
            memory_limit=512,
            capabilities=["vm-management", "container-management"],
        ),
        "data": AgentTemplate(
            template_id="data",
            agent_type="data",
            category=AgentCategory.DATA,
            display_name="Data Agent",
            description="Handles data operations",
            cpu_limit=2.0,
            memory_limit=1024,
            capabilities=["etl", "query", "transform"],
        ),
        "security": AgentTemplate(
            template_id="security",
            agent_type="security",
            category=AgentCategory.SECURITY,
            display_name="Security Agent",
            description="Monitors security",
            cpu_limit=1.0,
            memory_limit=512,
            capabilities=["threat-detection", "audit"],
        ),
        "device": AgentTemplate(
            template_id="device",
            agent_type="device",
            category=AgentCategory.DEVICE,
            display_name="Device Agent",
            description="Manages IoT device",
            cpu_limit=0.5,
            memory_limit=256,
            capabilities=["telemetry", "control"],
        ),
        "integration": AgentTemplate(
            template_id="integration",
            agent_type="integration",
            category=AgentCategory.INTEGRATION,
            display_name="Integration Agent",
            description="Handles external integration",
            cpu_limit=1.0,
            memory_limit=512,
            capabilities=["api-calls", "webhooks"],
        ),
        "route-monitor": AgentTemplate(
            template_id="route-monitor",
            agent_type="route-monitor",
            category=AgentCategory.DATA,
            display_name="Route Monitor Agent",
            description="Monitors API route",
            cpu_limit=0.5,
            memory_limit=256,
            capabilities=["monitoring", "alerting"],
        ),
    }
    
    # Agent types that require explicit approval
    APPROVAL_REQUIRED = [
        AgentCategory.CORPORATE,
        AgentCategory.FINANCIAL,
    ]
    
    def __init__(self, orchestrator=None, message_broker=None):
        self.orchestrator = orchestrator
        self.message_broker = message_broker
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        self.creation_log: List[Dict[str, Any]] = []
    
    def get_template(self, template_id: str) -> Optional[AgentTemplate]:
        """Get a template by ID"""
        return self.TEMPLATES.get(template_id)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List available templates"""
        return [
            {
                "template_id": t.template_id,
                "agent_type": t.agent_type,
                "category": t.category.value,
                "display_name": t.display_name,
                "description": t.description,
            }
            for t in self.TEMPLATES.values()
        ]
    
    async def create_agent(
        self,
        template: AgentTemplate,
        agent_id: Optional[str] = None,
        reason: str = "manual",
        auto_approved: bool = False,
        custom_settings: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentState]:
        """
        Create a new agent from template.
        
        Args:
            template: Agent template to use
            agent_id: Custom agent ID (auto-generated if not provided)
            reason: Reason for creation
            auto_approved: Skip approval workflow
            custom_settings: Override template settings
            
        Returns:
            AgentState if created, None if pending approval
        """
        agent_id = agent_id or f"{template.agent_type}-{str(uuid4())[:8]}"
        
        # Check if approval required
        if template.category in self.APPROVAL_REQUIRED and not auto_approved:
            approval_id = str(uuid4())
            self.pending_approvals[approval_id] = {
                "approval_id": approval_id,
                "template": template,
                "agent_id": agent_id,
                "reason": reason,
                "custom_settings": custom_settings,
                "requested_at": datetime.utcnow().isoformat(),
            }
            
            # Notify for approval
            await self._notify_approval_required(approval_id)
            
            logger.info(f"Agent creation pending approval: {agent_id} (approval: {approval_id})")
            return None
        
        # Create config
        config = AgentConfig(
            agent_id=agent_id,
            agent_type=template.agent_type,
            category=template.category,
            display_name=template.display_name,
            description=template.description,
            cpu_limit=template.cpu_limit,
            memory_limit=template.memory_limit,
            capabilities=template.capabilities,
            settings={**template.settings, **(custom_settings or {})},
        )
        
        # Spawn agent
        if self.orchestrator:
            state = await self.orchestrator.spawn_agent(config)
            
            # Log creation
            self._log_creation(agent_id, template, reason, "created")
            
            return state
        
        return None
    
    async def approve_creation(self, approval_id: str) -> Optional[AgentState]:
        """Approve a pending agent creation"""
        pending = self.pending_approvals.pop(approval_id, None)
        if not pending:
            logger.warning(f"Approval {approval_id} not found")
            return None
        
        return await self.create_agent(
            template=pending["template"],
            agent_id=pending["agent_id"],
            reason=pending["reason"],
            auto_approved=True,
            custom_settings=pending["custom_settings"],
        )
    
    async def reject_creation(self, approval_id: str, reason: str = "rejected"):
        """Reject a pending agent creation"""
        pending = self.pending_approvals.pop(approval_id, None)
        if pending:
            self._log_creation(pending["agent_id"], pending["template"], reason, "rejected")
            logger.info(f"Agent creation rejected: {pending['agent_id']}")
    
    def list_pending_approvals(self) -> List[Dict[str, Any]]:
        """List pending approval requests"""
        return [
            {
                "approval_id": p["approval_id"],
                "agent_id": p["agent_id"],
                "agent_type": p["template"].agent_type,
                "category": p["template"].category.value,
                "reason": p["reason"],
                "requested_at": p["requested_at"],
            }
            for p in self.pending_approvals.values()
        ]
    
    async def _notify_approval_required(self, approval_id: str):
        """Notify that approval is required"""
        if self.message_broker:
            pending = self.pending_approvals.get(approval_id)
            if pending:
                message = AgentMessage(
                    from_agent="agent-factory",
                    to_agent="orchestrator",
                    message_type=MessageType.EVENT,
                    payload={
                        "event": "approval_required",
                        "approval_id": approval_id,
                        "agent_id": pending["agent_id"],
                        "agent_type": pending["template"].agent_type,
                    },
                )
                await self.message_broker.publish("mas:events", message.to_json())
    
    def _log_creation(self, agent_id: str, template: AgentTemplate, reason: str, status: str):
        """Log agent creation event"""
        self.creation_log.append({
            "agent_id": agent_id,
            "agent_type": template.agent_type,
            "category": template.category.value,
            "reason": reason,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def get_creation_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent creation log entries"""
        return self.creation_log[-limit:]
'''
    runtime_dir = BASE_DIR / "mycosoft_mas" / "runtime"
    (runtime_dir / "agent_factory.py").write_text(content)
    print("Created mycosoft_mas/runtime/agent_factory.py")


def create_docker_compose_agents():
    """Create docker-compose file for agent deployment"""
    content = '''# MAS v2 Agent Deployment
# Docker Compose configuration for deploying MAS agents

version: '3.8'

services:
  # MYCA Orchestrator
  myca-orchestrator:
    build:
      context: ..
      dockerfile: docker/Dockerfile.orchestrator
    container_name: myca-orchestrator
    ports:
      - "8001:8001"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MINDEX_URL=http://mindex:8000
      - LOG_LEVEL=INFO
      - HEALTH_CHECK_INTERVAL=30
      - HEARTBEAT_TIMEOUT=60
    networks:
      - mas-network
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Redis for messaging
  redis:
    image: redis:7-alpine
    container_name: mas-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - mas-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  # Core Agents
  myca-core:
    build:
      context: ..
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_ID: myca-core
        AGENT_TYPE: orchestrator
        AGENT_CATEGORY: core
    container_name: mas-agent-myca-core
    environment:
      - AGENT_ID=myca-core
      - AGENT_TYPE=orchestrator
      - AGENT_CATEGORY=core
      - REDIS_URL=redis://redis:6379/0
      - ORCHESTRATOR_URL=http://myca-orchestrator:8001
    networks:
      - mas-network
    depends_on:
      - myca-orchestrator
      - redis
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    restart: unless-stopped

  # Infrastructure Agents
  proxmox-agent:
    build:
      context: ..
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_ID: proxmox-agent
        AGENT_TYPE: vm-manager
        AGENT_CATEGORY: infrastructure
    container_name: mas-agent-proxmox
    environment:
      - AGENT_ID=proxmox-agent
      - AGENT_TYPE=vm-manager
      - AGENT_CATEGORY=infrastructure
      - REDIS_URL=redis://redis:6379/0
      - ORCHESTRATOR_URL=http://myca-orchestrator:8001
      - PROXMOX_HOST=${PROXMOX_HOST:-192.168.0.100}
      - PROXMOX_TOKEN=${PROXMOX_TOKEN}
    networks:
      - mas-network
    depends_on:
      - myca-orchestrator
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    restart: unless-stopped

  docker-agent:
    build:
      context: ..
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_ID: docker-agent
        AGENT_TYPE: container-manager
        AGENT_CATEGORY: infrastructure
    container_name: mas-agent-docker
    environment:
      - AGENT_ID=docker-agent
      - AGENT_TYPE=container-manager
      - AGENT_CATEGORY=infrastructure
      - REDIS_URL=redis://redis:6379/0
      - ORCHESTRATOR_URL=http://myca-orchestrator:8001
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - mas-network
    depends_on:
      - myca-orchestrator
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    restart: unless-stopped

  # Security Agents
  soc-agent:
    build:
      context: ..
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_ID: soc-agent
        AGENT_TYPE: security
        AGENT_CATEGORY: security
    container_name: mas-agent-soc
    environment:
      - AGENT_ID=soc-agent
      - AGENT_TYPE=security
      - AGENT_CATEGORY=security
      - REDIS_URL=redis://redis:6379/0
      - ORCHESTRATOR_URL=http://myca-orchestrator:8001
      - UNIFI_HOST=${UNIFI_HOST:-192.168.1.1}
      - UNIFI_USERNAME=${UNIFI_USERNAME}
      - UNIFI_PASSWORD=${UNIFI_PASSWORD}
    networks:
      - mas-network
    depends_on:
      - myca-orchestrator
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    restart: unless-stopped

  # Integration Agents
  n8n-agent:
    build:
      context: ..
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_ID: n8n-agent
        AGENT_TYPE: workflow
        AGENT_CATEGORY: integration
    container_name: mas-agent-n8n
    environment:
      - AGENT_ID=n8n-agent
      - AGENT_TYPE=workflow
      - AGENT_CATEGORY=integration
      - REDIS_URL=redis://redis:6379/0
      - ORCHESTRATOR_URL=http://myca-orchestrator:8001
      - N8N_HOST=${N8N_HOST:-http://n8n:5678}
    networks:
      - mas-network
    depends_on:
      - myca-orchestrator
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    restart: unless-stopped

  elevenlabs-agent:
    build:
      context: ..
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_ID: elevenlabs-agent
        AGENT_TYPE: voice
        AGENT_CATEGORY: integration
    container_name: mas-agent-elevenlabs
    environment:
      - AGENT_ID=elevenlabs-agent
      - AGENT_TYPE=voice
      - AGENT_CATEGORY=integration
      - REDIS_URL=redis://redis:6379/0
      - ORCHESTRATOR_URL=http://myca-orchestrator:8001
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
    networks:
      - mas-network
    depends_on:
      - myca-orchestrator
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    restart: unless-stopped

  # Data Agents
  mindex-agent:
    build:
      context: ..
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_ID: mindex-agent
        AGENT_TYPE: database
        AGENT_CATEGORY: data
    container_name: mas-agent-mindex
    environment:
      - AGENT_ID=mindex-agent
      - AGENT_TYPE=database
      - AGENT_CATEGORY=data
      - REDIS_URL=redis://redis:6379/0
      - ORCHESTRATOR_URL=http://myca-orchestrator:8001
      - MINDEX_URL=http://mindex:8000
    networks:
      - mas-network
    depends_on:
      - myca-orchestrator
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1024M
    restart: unless-stopped

  # Device Agents
  mycobrain-coordinator:
    build:
      context: ..
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_ID: mycobrain-coordinator
        AGENT_TYPE: device-coordinator
        AGENT_CATEGORY: device
    container_name: mas-agent-mycobrain
    environment:
      - AGENT_ID=mycobrain-coordinator
      - AGENT_TYPE=device-coordinator
      - AGENT_CATEGORY=device
      - REDIS_URL=redis://redis:6379/0
      - ORCHESTRATOR_URL=http://myca-orchestrator:8001
    networks:
      - mas-network
    depends_on:
      - myca-orchestrator
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
    restart: unless-stopped

networks:
  mas-network:
    driver: bridge
    name: mas-network

volumes:
  redis-data:
'''
    docker_dir = BASE_DIR / "docker"
    docker_dir.mkdir(exist_ok=True)
    (docker_dir / "docker-compose.agents.yml").write_text(content)
    print("Created docker/docker-compose.agents.yml")


def main():
    """Create all orchestrator upgrade files"""
    print("Creating MAS v2 Orchestrator Upgrade Files...")
    print(f"Base directory: {BASE_DIR}")
    print()
    
    create_orchestrator_service()
    create_gap_detector()
    create_agent_factory()
    create_docker_compose_agents()
    
    print()
    print("All orchestrator upgrade files created successfully!")


if __name__ == "__main__":
    main()
