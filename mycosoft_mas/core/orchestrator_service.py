"""
MAS v2 Orchestrator Service

The central MYCA orchestrator that manages all agents, tasks, and communications.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
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

try:
    from mycosoft_mas.integrations.n8n_client import N8NClient
except ImportError:
    from integrations.n8n_client import N8NClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MYCA_Orchestrator")

N8N_VOICE_WEBHOOK = os.getenv("N8N_VOICE_WEBHOOK", "myca/command")

def resolve_n8n_webhook_url() -> Optional[str]:
    base = os.getenv("N8N_WEBHOOK_URL") or os.getenv("N8N_URL")
    if not base:
        return None
    base = base.rstrip("/")
    if not base.endswith("/webhook"):
        base = f"{base}/webhook"
    return base

def extract_response_text(payload: object) -> Optional[str]:
    if isinstance(payload, dict):
        for key in ("response_text", "response", "text", "message", "answer"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, dict):
            for key in ("response_text", "response", "text", "message", "answer"):
                value = first.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return None

_n8n_client: Optional[N8NClient] = None

def get_n8n_client() -> N8NClient:
    global _n8n_client
    if _n8n_client is None:
        webhook_url = resolve_n8n_webhook_url()
        _n8n_client = N8NClient(config={"webhook_url": webhook_url} if webhook_url else {})
    return _n8n_client


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



# ==================== CONNECTION MANAGEMENT ====================

class ConnectionCreateRequest(BaseModel):
    source: str
    target: str
    type: str = "message"
    bidirectional: bool = True
    priority: int = 5


class ConnectionDeleteRequest(BaseModel):
    source: str
    target: str


# In-memory connection store (will be persisted to Redis/DB)
agent_connections: Dict[str, List[Dict[str, Any]]] = {}


@app.get("/connections")
async def list_connections():
    """List all agent connections"""
    all_connections = []
    for agent_id, conns in agent_connections.items():
        for conn in conns:
            all_connections.append({
                "source": agent_id,
                **conn
            })
    return {"connections": all_connections, "total": len(all_connections)}


@app.get("/connections/{agent_id}")
async def get_agent_connections(agent_id: str):
    """Get connections for a specific agent"""
    conns = agent_connections.get(agent_id, [])
    return {"agent_id": agent_id, "connections": conns}


@app.post("/connections/create")
async def create_connection(request: ConnectionCreateRequest):
    """Create a connection between two agents"""
    source = request.source
    target = request.target
    
    # Initialize if needed
    if source not in agent_connections:
        agent_connections[source] = []
    
    # Check if connection exists
    existing = next((c for c in agent_connections[source] if c["target"] == target), None)
    if existing:
        return {"status": "exists", "connection": existing}
    
    # Create connection
    connection = {
        "target": target,
        "type": request.type,
        "bidirectional": request.bidirectional,
        "priority": request.priority,
        "created_at": datetime.utcnow().isoformat(),
        "status": "active"
    }
    agent_connections[source].append(connection)
    
    # If bidirectional, create reverse connection
    if request.bidirectional:
        if target not in agent_connections:
            agent_connections[target] = []
        reverse_exists = next((c for c in agent_connections[target] if c["target"] == source), None)
        if not reverse_exists:
            agent_connections[target].append({
                "target": source,
                "type": request.type,
                "bidirectional": True,
                "priority": request.priority,
                "created_at": datetime.utcnow().isoformat(),
                "status": "active"
            })
    
    logger.info(f"Connection created: {source} -> {target} (type: {request.type})")
    return {"status": "created", "connection": {"source": source, **connection}}


@app.post("/connections/delete")
async def delete_connection(request: ConnectionDeleteRequest):
    """Delete a connection between agents"""
    source = request.source
    target = request.target
    
    if source not in agent_connections:
        raise HTTPException(status_code=404, detail="Source agent has no connections")
    
    # Find and remove connection
    original_len = len(agent_connections[source])
    agent_connections[source] = [c for c in agent_connections[source] if c["target"] != target]
    
    if len(agent_connections[source]) == original_len:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Also remove reverse if exists
    if target in agent_connections:
        agent_connections[target] = [c for c in agent_connections[target] if c["target"] != source]
    
    logger.info(f"Connection deleted: {source} -> {target}")
    return {"status": "deleted", "source": source, "target": target}


# ============================================================================
# Voice/Chat Endpoints - MYCA AI Interface
# ============================================================================

class VoiceChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    source: Optional[str] = None
    want_audio: bool = False


@app.post("/voice/orchestrator/chat")
async def voice_orchestrator_chat(request: VoiceChatRequest):
    """
    Main MYCA voice/chat interface.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    conversation_id = request.conversation_id or str(uuid4())
    webhook_url = resolve_n8n_webhook_url()
    if not webhook_url:
        raise HTTPException(status_code=503, detail="N8N webhook URL not configured")

    payload = {
        "message": request.message,
        "conversation_id": conversation_id,
        "session_id": request.session_id,
        "source": request.source or "mas-voice",
        "want_audio": request.want_audio,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        client = get_n8n_client()
        result = await client.trigger_workflow(N8N_VOICE_WEBHOOK, payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"N8N workflow failed: {exc}") from exc

    response_text = extract_response_text(result)
    if not response_text:
        raise HTTPException(status_code=502, detail="N8N workflow returned no response_text")

    return {
        "response_text": response_text,
        "response": response_text,
        "agent": "n8n-workflow",
        "conversation_id": conversation_id,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


