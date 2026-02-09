# MYCA Memory Integration Plan - February 5, 2026

## Current State Analysis

### Memory Systems Available

| System | Location | Purpose | Status |
|--------|----------|---------|--------|
| **UnifiedMemoryService** | `memory/service.py` | Original memory with scopes | Exists, not integrated |
| **MYCAMemory (6-Layer)** | `memory/myca_memory.py` | New 6-layer architecture | Exists, not integrated |
| **ConversationMemory** | `memory/memory_modules.py` | Conversation tracking | Exists, standalone |
| **EpisodicMemory** | `memory/memory_modules.py` | Event-based storage | Exists, standalone |
| **CrossSessionMemory** | `memory/memory_modules.py` | User profiles | Exists, standalone |
| **PersonaPlexMemory** | `memory/personaplex_memory.py` | Voice sessions | Exists, standalone |
| **N8NMemory** | `memory/n8n_memory.py` | Workflow patterns | Exists, standalone |
| **Mem0Adapter** | `memory/mem0_adapter.py` | Fact extraction | Exists, standalone |
| **MCPMemoryServer** | `memory/mcp_memory_server.py` | Claude MCP integration | Exists, standalone |

### Gap Analysis

| Component | Memory Integration | Status |
|-----------|-------------------|--------|
| **Orchestrator** (`core/orchestrator.py`) | None | ❌ No memory |
| **BaseAgent** (`agents/base_agent.py`) | None | ❌ No memory |
| **MYCA Main** (`core/myca_main.py`) | Memory API router | ⚠️ Partial |
| **PersonaPlex Bridge** | PersonaPlexMemory | ⚠️ Separate |
| **n8n Client** | N8NMemory | ⚠️ Separate |

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MYCA ORCHESTRATOR                           │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    MemoryCoordinator                        │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │    │
│  │  │ MYCA     │ │ Unified  │ │ Cross    │ │ Conversation  │  │    │
│  │  │ Memory   │ │ Memory   │ │ Session  │ │ Memory        │  │    │
│  │  │ (6-Layer)│ │ Service  │ │ Memory   │ │               │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                     AGENT POOL                                 │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │ │
│  │  │Research │ │BizDev   │ │Finance  │ │Marketing│ │...96+   │ │ │
│  │  │Agent    │ │Agent    │ │Agent    │ │Agent    │ │Agents   │ │ │
│  │  │         │ │         │ │         │ │         │ │         │ │ │
│  │  │ Memory  │ │ Memory  │ │ Memory  │ │ Memory  │ │ Memory  │ │ │
│  │  │ Mixin   │ │ Mixin   │ │ Mixin   │ │ Mixin   │ │ Mixin   │ │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        STORAGE BACKENDS                             │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐    │
│  │  Redis    │  │PostgreSQL │  │  Qdrant   │  │  In-Memory    │    │
│  │ (Session) │  │ (MINDEX)  │  │ (Vector)  │  │ (Ephemeral)   │    │
│  └───────────┘  └───────────┘  └───────────┘  └───────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Create Memory Coordinator (Day 1)

### 1.1 Create `mycosoft_mas/memory/coordinator.py`

```python
"""
Memory Coordinator - Central memory orchestration for MYCA.
Provides unified access to all memory systems.
"""

class MemoryCoordinator:
    """
    Central coordinator for all MYCA memory operations.
    
    Responsibilities:
    - Route memory operations to appropriate backend
    - Maintain consistency across memory systems
    - Handle memory lifecycle (store, retrieve, decay, archive)
    - Provide agent-specific memory namespacing
    """
    
    def __init__(self):
        self._myca_memory: MYCAMemory = None
        self._conversation_memory: Dict[str, ConversationMemory] = {}
        self._cross_session: CrossSessionMemory = None
        self._episodic: EpisodicMemory = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all memory subsystems."""
        self._myca_memory = await get_myca_memory()
        self._cross_session = CrossSessionMemory()
        await self._cross_session.initialize()
        self._episodic = EpisodicMemory()
        self._initialized = True
    
    # Agent Memory Operations
    async def agent_remember(self, agent_id: str, content: Dict, layer: str = "working") -> UUID
    async def agent_recall(self, agent_id: str, query: str, limit: int = 10) -> List[Dict]
    async def agent_get_context(self, agent_id: str) -> Dict[str, Any]
    
    # Conversation Memory
    async def add_conversation_turn(self, session_id: str, role: str, content: str) -> None
    async def get_conversation_context(self, session_id: str, turns: int = 10) -> List[Dict]
    
    # Episode Recording
    async def record_episode(self, agent_id: str, event_type: str, description: str, **kwargs) -> UUID
    
    # Cross-Session
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]
    async def update_user_preference(self, user_id: str, key: str, value: Any) -> None
```

### 1.2 Create Singleton Access

```python
# In mycosoft_mas/memory/__init__.py
from .coordinator import MemoryCoordinator, get_memory_coordinator

_coordinator: Optional[MemoryCoordinator] = None

async def get_memory_coordinator() -> MemoryCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = MemoryCoordinator()
        await _coordinator.initialize()
    return _coordinator
```

---

## Phase 2: Integrate with Orchestrator (Day 1-2)

### 2.1 Update `mycosoft_mas/core/orchestrator.py`

```python
from mycosoft_mas.memory import get_memory_coordinator, MemoryLayer

class Orchestrator:
    def __init__(self):
        # ... existing code ...
        self._memory: MemoryCoordinator = None
    
    async def start(self) -> None:
        if self._running:
            return
        
        self._running = True
        
        # Initialize memory coordinator
        self._memory = await get_memory_coordinator()
        
        # Store orchestrator start in system memory
        await self._memory.agent_remember(
            agent_id="orchestrator",
            content={
                "event": "orchestrator_started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services": list(self._services.keys())
            },
            layer="system"
        )
        
        self.register_default_services()
        self._health_task = asyncio.create_task(self._health_polling_loop())
        
        logger.info("Orchestrator started with memory integration")
    
    async def _record_health_event(self, service_id: str, state: str, error: str = None):
        """Record health events in episodic memory."""
        await self._memory.record_episode(
            agent_id="orchestrator",
            event_type="health_check",
            description=f"Service {service_id} state: {state}",
            context={"service_id": service_id, "state": state, "error": error}
        )
    
    async def _save_recovery_state(self, service_id: str) -> None:
        """Save state for recovery using memory system."""
        recovery_data = {
            "service_id": service_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "status": self._status[service_id].__dict__
        }
        await self._memory.agent_remember(
            agent_id="orchestrator",
            content=recovery_data,
            layer="system"
        )
```

### 2.2 Add Memory Event Handlers

```python
# In orchestrator.py - Add memory-based recovery

async def _attempt_recovery(self, service_id: str) -> None:
    """Attempt recovery with memory-based state restoration."""
    # Query previous successful configurations
    history = await self._memory.agent_recall(
        agent_id="orchestrator",
        query=f"service:{service_id} state:healthy",
        limit=5
    )
    
    if history:
        # Use last known good configuration
        last_good = history[0]
        logger.info(f"Restoring from memory: {last_good}")
    
    # ... existing recovery logic ...
```

---

## Phase 3: Create Agent Memory Mixin (Day 2)

### 3.1 Create `mycosoft_mas/agents/memory_mixin.py`

```python
"""
Memory Mixin for Agents.
Provides standardized memory operations for all agents.
"""

from mycosoft_mas.memory import get_memory_coordinator, MemoryLayer

class AgentMemoryMixin:
    """
    Mixin class that provides memory capabilities to agents.
    
    Usage:
        class ResearchAgent(BaseAgent, AgentMemoryMixin):
            async def initialize(self):
                await super().initialize()
                await self.init_memory()
    """
    
    _memory_initialized: bool = False
    _memory: MemoryCoordinator = None
    _conversation: ConversationMemory = None
    
    async def init_memory(self) -> None:
        """Initialize agent memory subsystems."""
        if self._memory_initialized:
            return
        
        self._memory = await get_memory_coordinator()
        self._conversation = ConversationMemory(max_turns=50)
        self._memory_initialized = True
        
        # Load any cross-session context
        await self._load_agent_context()
    
    async def _load_agent_context(self) -> None:
        """Load agent's persistent context from previous sessions."""
        context = await self._memory.agent_recall(
            agent_id=self.agent_id,
            query="type:context",
            limit=1
        )
        if context:
            self._restore_context(context[0])
    
    # Core Memory Operations
    async def remember(
        self,
        content: Dict[str, Any],
        importance: float = 0.5,
        layer: str = "working",
        tags: List[str] = None
    ) -> UUID:
        """Store something in memory."""
        return await self._memory.agent_remember(
            agent_id=self.agent_id,
            content=content,
            layer=layer,
            importance=importance,
            tags=tags or []
        )
    
    async def recall(
        self,
        query: str = None,
        tags: List[str] = None,
        layer: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Recall memories matching criteria."""
        return await self._memory.agent_recall(
            agent_id=self.agent_id,
            query=query,
            tags=tags,
            layer=layer,
            limit=limit
        )
    
    async def learn_fact(self, fact: Dict[str, Any]) -> bool:
        """Learn a new fact (semantic memory)."""
        return await self.remember(
            content={"type": "fact", **fact},
            importance=0.7,
            layer="semantic"
        )
    
    async def record_task_completion(
        self,
        task_id: str,
        result: Dict[str, Any],
        success: bool
    ) -> None:
        """Record task completion as episodic memory."""
        await self._memory.record_episode(
            agent_id=self.agent_id,
            event_type="task_completion",
            description=f"Task {task_id} {'succeeded' if success else 'failed'}",
            context={"task_id": task_id, "result": result, "success": success}
        )
    
    # Conversation Tracking
    def add_to_conversation(self, role: str, content: str) -> None:
        """Add a turn to the conversation memory."""
        self._conversation.add_turn(role, content)
    
    def get_conversation_context(self, turns: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation context."""
        return self._conversation.get_context(turns)
    
    # Lifecycle
    async def save_agent_state(self) -> None:
        """Save agent state before shutdown."""
        await self.remember(
            content={
                "type": "context",
                "state": self.get_status(),
                "capabilities": list(self.capabilities),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            layer="system",
            importance=1.0
        )
```

### 3.2 Update `BaseAgent` to Use Mixin

```python
# In mycosoft_mas/agents/base_agent.py

from mycosoft_mas.agents.memory_mixin import AgentMemoryMixin

class BaseAgent(AgentMonitorable, AgentSecurable, AgentMemoryMixin):
    """Base agent class with memory integration."""
    
    async def initialize(self) -> None:
        """Initialize the agent and its components."""
        try:
            # ... existing initialization ...
            
            # Initialize memory
            await self.init_memory()
            
            # Load previous learnings
            learnings = await self.recall(tags=["learning"], limit=10)
            if learnings:
                self.logger.info(f"Restored {len(learnings)} learnings from memory")
            
            self.status = AgentStatus.ACTIVE
            self.logger.info(f"Agent {self.agent_id} initialized with memory")
        except Exception as e:
            # ...
```

---

## Phase 4: Integrate Voice/Workflow Memory (Day 2-3)

### 4.1 PersonaPlex Integration

```python
# In mycosoft_mas/voice/personaplex_bridge.py

from mycosoft_mas.memory.personaplex_memory import PersonaPlexMemory

class PersonaPlexBridge:
    def __init__(self):
        self._memory = PersonaPlexMemory()
    
    async def start_session(self, user_id: str) -> str:
        session_id = await self._memory.start_session(user_id)
        return session_id
    
    async def process_turn(self, session_id: str, user_input: str, response: str):
        await self._memory.add_turn(session_id, "user", user_input)
        await self._memory.add_turn(session_id, "assistant", response)
    
    async def end_session(self, session_id: str):
        summary = await self._memory.summarize_session(session_id)
        await self._memory.persist_session(session_id)
        return summary
```

### 4.2 N8N Workflow Integration

```python
# In mycosoft_mas/integrations/n8n_client.py

from mycosoft_mas.memory.n8n_memory import N8NMemory

class N8NClient:
    def __init__(self):
        self._memory = N8NMemory()
    
    async def execute_workflow(self, workflow_id: str, data: Dict) -> Dict:
        start = datetime.now()
        try:
            result = await self._execute(workflow_id, data)
            
            # Record successful execution
            await self._memory.record_execution(
                workflow_id=workflow_id,
                status="success",
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
                input_data=data,
                output_data=result
            )
            
            return result
        except Exception as e:
            await self._memory.record_execution(
                workflow_id=workflow_id,
                status="failed",
                error=str(e)
            )
            raise
```

---

## Phase 5: Memory API Enhancements (Day 3)

### 5.1 Update Memory API Router

```python
# In mycosoft_mas/core/routers/memory_api.py

from mycosoft_mas.memory import get_memory_coordinator

router = APIRouter(prefix="/api/v1/memory")

@router.post("/remember")
async def remember(request: RememberRequest):
    """Store a memory."""
    memory = await get_memory_coordinator()
    entry_id = await memory.agent_remember(
        agent_id=request.agent_id or "api",
        content=request.content,
        layer=request.layer,
        importance=request.importance,
        tags=request.tags
    )
    return {"id": str(entry_id), "status": "stored"}

@router.post("/recall")
async def recall(request: RecallRequest):
    """Recall memories."""
    memory = await get_memory_coordinator()
    results = await memory.agent_recall(
        agent_id=request.agent_id or "api",
        query=request.query,
        tags=request.tags,
        layer=request.layer,
        limit=request.limit
    )
    return {"memories": results, "count": len(results)}

@router.get("/stats")
async def get_stats():
    """Get memory system statistics."""
    memory = await get_memory_coordinator()
    myca = await get_myca_memory()
    return await myca.get_stats()

@router.get("/agent/{agent_id}/context")
async def get_agent_context(agent_id: str):
    """Get an agent's current memory context."""
    memory = await get_memory_coordinator()
    return await memory.agent_get_context(agent_id)
```

---

## Phase 6: Testing & Validation (Day 3-4)

### 6.1 Create Memory Integration Tests

```python
# tests/test_memory_integration.py

import pytest
from mycosoft_mas.memory import get_memory_coordinator
from mycosoft_mas.agents.base_agent import BaseAgent

class TestMemoryIntegration:
    
    @pytest.mark.asyncio
    async def test_agent_memory_lifecycle(self):
        """Test agent can store and recall memories."""
        memory = await get_memory_coordinator()
        
        # Store
        entry_id = await memory.agent_remember(
            agent_id="test_agent",
            content={"task": "research", "topic": "mushrooms"},
            layer="working"
        )
        assert entry_id is not None
        
        # Recall
        results = await memory.agent_recall(
            agent_id="test_agent",
            query="mushrooms"
        )
        assert len(results) > 0
        assert "mushrooms" in str(results[0])
    
    @pytest.mark.asyncio
    async def test_cross_session_memory(self):
        """Test memories persist across sessions."""
        memory = await get_memory_coordinator()
        
        # Save user preference
        await memory.update_user_preference("user123", "language", "en")
        
        # New session - should remember
        profile = await memory.get_user_profile("user123")
        assert profile["preferences"]["language"] == "en"
    
    @pytest.mark.asyncio
    async def test_orchestrator_memory(self):
        """Test orchestrator uses memory for recovery."""
        from mycosoft_mas.core.orchestrator import get_orchestrator
        
        orch = get_orchestrator()
        await orch.start()
        
        # Check memory was initialized
        assert orch._memory is not None
        
        # Check startup was recorded
        memory = await get_memory_coordinator()
        events = await memory.agent_recall(
            agent_id="orchestrator",
            query="orchestrator_started"
        )
        assert len(events) > 0
```

---

## Implementation Timeline

| Phase | Task | Duration | Dependencies |
|-------|------|----------|--------------|
| **1** | Create MemoryCoordinator | 4 hours | None |
| **2** | Integrate with Orchestrator | 4 hours | Phase 1 |
| **3** | Create AgentMemoryMixin | 4 hours | Phase 1 |
| **4** | Voice/Workflow Integration | 4 hours | Phase 1 |
| **5** | Memory API Enhancements | 2 hours | Phase 1 |
| **6** | Testing & Validation | 4 hours | Phases 1-5 |

**Total Estimated Time: 22 hours (3 days)**

---

## Memory Usage Patterns by Agent Type

| Agent Category | Primary Memory Layers | Key Operations |
|---------------|----------------------|----------------|
| **Research Agents** | Semantic, Episodic | Learn facts, recall knowledge |
| **BizDev Agents** | Working, Episodic | Track opportunities, record outcomes |
| **Finance Agents** | System, Semantic | Store configs, learn patterns |
| **Marketing Agents** | Working, Session | Campaign context, user preferences |
| **Scientific Agents** | Semantic, Episodic | Experiment data, observations |
| **Orchestrator** | System, Episodic | Recovery state, health history |

---

## Memory Layer Guidelines

### When to Use Each Layer

| Layer | Use For | TTL | Example |
|-------|---------|-----|---------|
| **Ephemeral** | Scratch calculations | 30 min | Temp variables during task |
| **Session** | Current conversation | 24 hours | Chat context with user |
| **Working** | Active task state | 7 days | Project being worked on |
| **Semantic** | Learned knowledge | Permanent | "Morgan is the founder" |
| **Episodic** | Significant events | Permanent | "Successfully deployed v2.0" |
| **System** | Configuration | Permanent | Agent settings, preferences |

---

## Success Metrics

After implementation, verify:

1. **Orchestrator** records all health events in episodic memory
2. **Agents** can recall learnings from previous sessions
3. **Voice sessions** persist conversation summaries
4. **Workflow executions** are tracked in n8n memory
5. **Memory API** returns stats for all layers
6. **Recovery** uses memory to restore last known good state

---

## Files to Create/Modify

### New Files
- [ ] `mycosoft_mas/memory/coordinator.py` - Memory Coordinator
- [ ] `mycosoft_mas/agents/memory_mixin.py` - Agent Memory Mixin
- [ ] `tests/test_memory_integration.py` - Integration tests

### Files to Modify
- [ ] `mycosoft_mas/memory/__init__.py` - Add coordinator exports
- [ ] `mycosoft_mas/core/orchestrator.py` - Add memory integration
- [ ] `mycosoft_mas/agents/base_agent.py` - Use memory mixin
- [ ] `mycosoft_mas/core/routers/memory_api.py` - Enhanced API
- [ ] `mycosoft_mas/voice/personaplex_bridge.py` - Voice memory
- [ ] `mycosoft_mas/integrations/n8n_client.py` - Workflow memory

---

## Next Steps

1. **Start Phase 1**: Create `coordinator.py` with unified memory access
2. **Test coordinator**: Verify all memory backends work together
3. **Integrate orchestrator**: Add memory to service health tracking
4. **Create mixin**: Build reusable agent memory mixin
5. **Update base agent**: Apply mixin to all agents
6. **Run integration tests**: Validate end-to-end memory flow

---

## Related Documents

- **[MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md](./MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md)** - Brain-memory integration
- **[MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md](./MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md)** - UI component migration
- **[MEMORY_SYSTEM_COMPLETE_FEB05_2026.md](./MEMORY_SYSTEM_COMPLETE_FEB05_2026.md)** - Complete system reference
- **[MEMORY_AWARENESS_PROTOCOL_FEB05_2026.md](./MEMORY_AWARENESS_PROTOCOL_FEB05_2026.md)** - Awareness system

---

*Document created: February 5, 2026*
*Status: Ready for Implementation*
