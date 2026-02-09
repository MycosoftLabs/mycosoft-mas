"""
Memory Coordinator - Central Memory Hub for MYCA.
Created: February 5, 2026

Provides unified access to all memory systems:
- MYCAMemory (6-Layer): Ephemeral, Session, Working, Semantic, Episodic, System
- ConversationMemory: Turn-based conversation tracking
- EpisodicMemory: Event-based storage
- CrossSessionMemory: User profiles and cross-session context
- PersonaPlexMemory: Voice session persistence
- N8NMemory: Workflow execution history

This coordinator ensures all components (Orchestrator, Agents, Voice, Frontend)
use memory consistently and data flows between systems properly.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger("MemoryCoordinator")


@dataclass
class UserProfile:
    """Aggregated user profile from all sessions."""
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    learned_facts: List[Dict[str, Any]] = field(default_factory=list)
    interaction_summary: Dict[str, Any] = field(default_factory=dict)
    last_seen: Optional[datetime] = None


class MemoryCoordinator:
    """
    Central coordinator for all MYCA memory operations.
    
    Responsibilities:
    - Route memory operations to appropriate backend
    - Maintain consistency across memory systems  
    - Handle memory lifecycle (store, retrieve, decay, archive)
    - Provide agent-specific memory namespacing
    - Coordinate cross-session context
    
    Usage:
        coordinator = await get_memory_coordinator()
        
        # Agent memory
        entry_id = await coordinator.agent_remember(
            agent_id="research_agent",
            content={"task": "analyze mushrooms"},
            layer="working"
        )
        
        # Conversation
        await coordinator.add_conversation_turn(session_id, "user", "Hello")
        context = await coordinator.get_conversation_context(session_id)
    """
    
    def __init__(self):
        self._myca_memory = None  # MYCAMemory 6-layer
        self._conversation_memories: Dict[str, Any] = {}  # ConversationMemory by session
        self._cross_session = None  # CrossSessionMemory
        self._episodic = None  # EpisodicMemory
        self._personaplex_memory = None  # Voice session memory
        self._n8n_memory = None  # Workflow memory
        self._initialized = False
        self._agent_namespaces: Set[str] = set()
    
    async def initialize(self) -> None:
        """Initialize all memory subsystems."""
        if self._initialized:
            return
        
        try:
            # Import memory modules
            from mycosoft_mas.memory.myca_memory import get_myca_memory, MYCAMemory, MemoryLayer
            from mycosoft_mas.memory.memory_modules import (
                ConversationMemory,
                EpisodicMemory, 
                EventType,
                CrossSessionMemory
            )
            
            # Initialize 6-layer memory
            self._myca_memory = await get_myca_memory()
            
            # Initialize cross-session memory
            self._cross_session = CrossSessionMemory()
            await self._cross_session.initialize()
            
            # Initialize episodic memory
            self._episodic = EpisodicMemory()
            
            # Store module references for internal use
            self._MemoryLayer = MemoryLayer
            self._ConversationMemory = ConversationMemory
            self._EventType = EventType
            
            self._initialized = True
            logger.info("MemoryCoordinator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MemoryCoordinator: {e}")
            raise
    
    def _ensure_initialized(self) -> None:
        """Ensure the coordinator is initialized."""
        if not self._initialized:
            raise RuntimeError("MemoryCoordinator not initialized. Call await coordinator.initialize() first.")
    
    # =========================================================================
    # Agent Memory Operations
    # =========================================================================
    
    async def agent_remember(
        self,
        agent_id: str,
        content: Dict[str, Any],
        layer: str = "working",
        importance: float = 0.5,
        tags: Optional[List[str]] = None
    ) -> UUID:
        """
        Store a memory for a specific agent.
        
        Args:
            agent_id: Unique identifier for the agent
            content: The content to store
            layer: Memory layer (ephemeral, session, working, semantic, episodic, system)
            importance: Importance score 0.0 to 1.0
            tags: Optional tags for retrieval
            
        Returns:
            UUID of the stored memory entry
        """
        self._ensure_initialized()
        
        # Namespace the content with agent_id
        namespaced_content = {
            "agent_id": agent_id,
            "data": content,
            "stored_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Map string layer to enum
        memory_layer = self._MemoryLayer(layer.lower())
        
        # Store in 6-layer memory
        entry_id = await self._myca_memory.remember(
            content=namespaced_content,
            layer=memory_layer,
            importance=importance,
            tags=(tags or []) + [f"agent:{agent_id}"]
        )
        
        self._agent_namespaces.add(agent_id)
        logger.debug(f"Agent {agent_id} stored memory {entry_id} in {layer}")
        
        return entry_id
    
    async def agent_recall(
        self,
        agent_id: str,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        layer: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recall memories for a specific agent.
        
        Args:
            agent_id: Agent to recall memories for
            query: Optional text query (for semantic search)
            tags: Filter by tags
            layer: Optional layer to search
            limit: Maximum results
            
        Returns:
            List of memory entries
        """
        self._ensure_initialized()
        
        from mycosoft_mas.memory.myca_memory import MemoryQuery
        
        # Build query
        q = MemoryQuery(
            text=query,
            layer=self._MemoryLayer(layer.lower()) if layer else None,
            tags=(tags or []) + [f"agent:{agent_id}"],
            limit=limit
        )
        
        entries = await self._myca_memory.recall(query=q)
        
        # Extract data from namespaced content
        results = []
        for entry in entries:
            result = {
                "id": str(entry.id),
                "content": entry.content.get("data", entry.content),
                "layer": entry.layer.value,
                "importance": entry.importance,
                "created_at": entry.created_at.isoformat(),
                "tags": entry.tags
            }
            results.append(result)
        
        return results
    
    async def agent_get_context(self, agent_id: str) -> Dict[str, Any]:
        """
        Get full context for an agent including recent memories and profile.
        
        Args:
            agent_id: Agent to get context for
            
        Returns:
            Dictionary containing memories from all relevant layers
        """
        self._ensure_initialized()
        
        context = {
            "agent_id": agent_id,
            "working_memory": await self.agent_recall(agent_id, layer="working", limit=5),
            "recent_episodes": await self.agent_recall(agent_id, layer="episodic", limit=3),
            "semantic_knowledge": await self.agent_recall(agent_id, layer="semantic", limit=5),
            "system_config": await self.agent_recall(agent_id, layer="system", limit=3),
        }
        
        return context
    
    # =========================================================================
    # Conversation Memory Operations
    # =========================================================================
    
    def _get_conversation_memory(self, session_id: str):
        """Get or create conversation memory for a session."""
        if session_id not in self._conversation_memories:
            self._conversation_memories[session_id] = self._ConversationMemory(max_turns=100)
        return self._conversation_memories[session_id]
    
    async def add_conversation_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a turn to conversation memory.
        
        Args:
            session_id: Session identifier
            role: Speaker role (user, assistant, system)
            content: Turn content
            metadata: Optional metadata
        """
        self._ensure_initialized()
        
        conv = self._get_conversation_memory(session_id)
        conv.add_turn(role, content, metadata)
        
        logger.debug(f"Added {role} turn to session {session_id[:8]}...")
    
    async def get_conversation_context(
        self,
        session_id: str,
        turns: int = 10
    ) -> List[Dict[str, str]]:
        """
        Get recent conversation context.
        
        Args:
            session_id: Session identifier
            turns: Number of recent turns to return
            
        Returns:
            List of conversation turns
        """
        self._ensure_initialized()
        
        conv = self._get_conversation_memory(session_id)
        return conv.get_context(turns)
    
    async def get_full_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """Get full context with summaries for long conversations."""
        self._ensure_initialized()
        
        conv = self._get_conversation_memory(session_id)
        return conv.get_full_context_with_summaries()
    
    async def summarize_conversation(self, session_id: str) -> str:
        """Generate summary of a conversation session."""
        self._ensure_initialized()
        
        conv = self._get_conversation_memory(session_id)
        context = conv.get_full_context_with_summaries()
        
        # Build simple extractive summary
        summaries = context.get("summaries", [])
        if summaries:
            return " | ".join(s.get("summary", "") for s in summaries[-3:])
        
        # Fallback to recent turns
        recent = context.get("recent_turns", [])
        if recent:
            return " ".join(t.get("content", "")[:50] for t in recent[-5:])
        
        return "No conversation history"
    
    # =========================================================================
    # Episode Recording
    # =========================================================================
    
    async def record_episode(
        self,
        agent_id: str,
        event_type: str,
        description: str,
        participants: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        outcome: Optional[str] = None,
        importance: float = 0.5
    ) -> UUID:
        """
        Record a significant event/episode.
        
        Args:
            agent_id: Agent recording the episode
            event_type: Type of event (interaction, task_completion, error, learning, decision, observation)
            description: Description of the event
            participants: Other participants involved
            context: Additional context
            outcome: Outcome of the event
            importance: Importance score
            
        Returns:
            UUID of the recorded episode
        """
        self._ensure_initialized()
        
        # Map string to EventType enum
        event_type_enum = self._EventType(event_type.lower())
        
        episode = self._episodic.record_episode(
            event_type=event_type_enum,
            description=description,
            participants=[agent_id] + (participants or []),
            context=context or {},
            outcome=outcome,
            importance=importance
        )
        
        # Also store in persistent episodic layer
        await self.agent_remember(
            agent_id=agent_id,
            content={
                "type": "episode",
                "event_type": event_type,
                "description": description,
                "participants": [agent_id] + (participants or []),
                "context": context or {},
                "outcome": outcome
            },
            layer="episodic",
            importance=importance,
            tags=["episode", event_type]
        )
        
        logger.debug(f"Recorded episode for {agent_id}: {event_type}")
        return episode.id
    
    async def get_recent_episodes(
        self,
        agent_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent episodes, optionally filtered."""
        self._ensure_initialized()
        
        if agent_id:
            # Query from persistent storage
            return await self.agent_recall(
                agent_id=agent_id,
                tags=["episode"] + ([event_type] if event_type else []),
                layer="episodic",
                limit=limit
            )
        else:
            # Query from in-memory episodic
            episodes = self._episodic.recall_by_type(
                self._EventType(event_type) if event_type else None,
                limit=limit
            )
            return [e.to_dict() for e in episodes]
    
    # =========================================================================
    # Cross-Session / User Profile
    # =========================================================================
    
    async def get_user_profile(self, user_id: str) -> UserProfile:
        """
        Get aggregated user profile from all sessions.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserProfile with preferences, facts, and interaction summary
        """
        self._ensure_initialized()
        
        profile_data = await self._cross_session.get_user_profile(user_id)
        
        return UserProfile(
            user_id=user_id,
            preferences=profile_data.get("preferences", {}),
            learned_facts=profile_data.get("learned_facts", []),
            interaction_summary=profile_data.get("interaction_summary", {}),
            last_seen=datetime.now(timezone.utc)
        )
    
    async def update_user_preference(
        self,
        user_id: str,
        key: str,
        value: Any
    ) -> None:
        """Update a user preference."""
        self._ensure_initialized()
        
        prefs = await self._cross_session.load_user_context(user_id, "preferences") or {}
        prefs[key] = value
        prefs["_updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await self._cross_session.save_user_context(user_id, "preferences", prefs)
        logger.debug(f"Updated preference {key} for user {user_id}")
    
    async def learn_user_fact(self, user_id: str, fact: Dict[str, Any]) -> bool:
        """Learn a new fact about a user."""
        self._ensure_initialized()
        return await self._cross_session.update_learned_fact(user_id, fact)
    
    # =========================================================================
    # System Memory Operations
    # =========================================================================
    
    async def store_system_config(
        self,
        namespace: str,
        key: str,
        config: Dict[str, Any]
    ) -> UUID:
        """
        Store system configuration in permanent memory.
        
        Args:
            namespace: Configuration namespace (e.g., "orchestrator", "agent_defaults")
            key: Configuration key
            config: Configuration data
            
        Returns:
            UUID of stored entry
        """
        self._ensure_initialized()
        
        return await self.agent_remember(
            agent_id=f"system:{namespace}",
            content={
                "type": "config",
                "key": key,
                "config": config
            },
            layer="system",
            importance=1.0,
            tags=["config", namespace, key]
        )
    
    async def load_system_config(
        self,
        namespace: str,
        key: str
    ) -> Optional[Dict[str, Any]]:
        """Load system configuration."""
        self._ensure_initialized()
        
        results = await self.agent_recall(
            agent_id=f"system:{namespace}",
            tags=["config", key],
            layer="system",
            limit=1
        )
        
        if results:
            return results[0].get("content", {}).get("config")
        return None
    
    # =========================================================================
    # Memory Statistics & Cleanup
    # =========================================================================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        self._ensure_initialized()
        
        myca_stats = await self._myca_memory.get_stats()
        
        return {
            "coordinator": {
                "initialized": self._initialized,
                "active_conversations": len(self._conversation_memories),
                "agent_namespaces": list(self._agent_namespaces),
            },
            "myca_memory": myca_stats,
            "episodic_count": len(self._episodic._episodes) if self._episodic else 0
        }
    
    async def cleanup_session(self, session_id: str) -> None:
        """Clean up a session's conversation memory."""
        if session_id in self._conversation_memories:
            # Optionally summarize before cleanup
            summary = await self.summarize_conversation(session_id)
            
            # Store summary in episodic memory
            await self.record_episode(
                agent_id="system",
                event_type="interaction",
                description=f"Session ended: {summary[:200]}",
                context={"session_id": session_id},
                importance=0.6
            )
            
            # Remove from active conversations
            del self._conversation_memories[session_id]
            logger.info(f"Cleaned up session {session_id[:8]}...")
    
    async def shutdown(self) -> None:
        """Shutdown the memory coordinator."""
        if self._myca_memory:
            await self._myca_memory.shutdown()
        
        # Cleanup all active conversations
        for session_id in list(self._conversation_memories.keys()):
            await self.cleanup_session(session_id)
        
        self._initialized = False
        logger.info("MemoryCoordinator shutdown complete")


    # =========================================================================
    # PersonaPlex Voice Memory Operations
    # =========================================================================
    
    async def _ensure_personaplex_memory(self):
        """Lazy initialize PersonaPlex memory."""
        if self._personaplex_memory is None:
            try:
                from mycosoft_mas.memory.personaplex_memory import get_personaplex_memory
                self._personaplex_memory = await get_personaplex_memory()
            except Exception as e:
                logger.warning(f"PersonaPlex memory not available: {e}")
        return self._personaplex_memory
    
    async def start_voice_session(
        self,
        user_id: Optional[str] = None,
        speaker_profile: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Start a new voice session with memory persistence.
        
        Args:
            user_id: Optional user identifier
            speaker_profile: Optional speaker profile
            context: Initial context
            
        Returns:
            Session ID string or None if unavailable
        """
        memory = await self._ensure_personaplex_memory()
        if not memory:
            return None
        
        session = await memory.start_session(user_id, speaker_profile, context)
        return str(session.id)
    
    async def add_voice_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        emotion: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> bool:
        """Add a turn to a voice session."""
        from uuid import UUID
        memory = await self._ensure_personaplex_memory()
        if not memory:
            return False
        
        turn = await memory.add_turn(
            session_id=UUID(session_id),
            role=role,
            content=content,
            emotion=emotion,
            duration_ms=duration_ms
        )
        return turn is not None
    
    async def end_voice_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        End a voice session and get the summary.
        
        Returns:
            Session summary and metadata
        """
        from uuid import UUID
        memory = await self._ensure_personaplex_memory()
        if not memory:
            return None
        
        session = await memory.end_session(UUID(session_id))
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "summary": session.summary,
            "topics": session.topics,
            "turn_count": session.turn_count,
            "duration_seconds": session.duration.total_seconds() if session.duration else 0
        }
    
    async def get_voice_context(self, user_id: str) -> Dict[str, Any]:
        """Get cross-session voice context for a user."""
        memory = await self._ensure_personaplex_memory()
        if not memory:
            return {"sessions_count": 0}
        
        return await memory.get_cross_session_context(user_id)
    
    # =========================================================================
    # N8N Workflow Memory Operations  
    # =========================================================================
    
    async def _ensure_n8n_memory(self):
        """Lazy initialize N8N memory."""
        if self._n8n_memory is None:
            try:
                from mycosoft_mas.memory.n8n_memory import get_n8n_memory
                self._n8n_memory = await get_n8n_memory()
            except Exception as e:
                logger.warning(f"N8N memory not available: {e}")
        return self._n8n_memory
    
    async def record_workflow_start(
        self,
        workflow_id: str,
        workflow_name: str,
        category: str = "custom",
        trigger: str = "manual",
        input_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Record the start of a workflow execution.
        
        Returns:
            Execution ID string or None if unavailable
        """
        memory = await self._ensure_n8n_memory()
        if not memory:
            return None
        
        from mycosoft_mas.memory.n8n_memory import WorkflowCategory
        execution = await memory.record_execution(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            category=WorkflowCategory(category),
            trigger=trigger,
            input_data=input_data or {}
        )
        return str(execution.id)
    
    async def record_workflow_complete(
        self,
        execution_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        nodes_executed: int = 0
    ) -> bool:
        """Record workflow completion."""
        from uuid import UUID
        memory = await self._ensure_n8n_memory()
        if not memory:
            return False
        
        from mycosoft_mas.memory.n8n_memory import ExecutionStatus
        result = await memory.complete_execution(
            execution_id=UUID(execution_id),
            status=ExecutionStatus(status),
            output_data=output_data,
            error_message=error_message,
            nodes_executed=nodes_executed
        )
        return result is not None
    
    async def get_workflow_patterns(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get learned patterns for a workflow."""
        memory = await self._ensure_n8n_memory()
        if not memory:
            return []
        
        patterns = await memory.get_patterns(workflow_id)
        return [
            {
                "type": p.pattern_type,
                "description": p.description,
                "frequency": p.frequency,
                "recommendations": p.recommendations,
                "confidence": p.confidence
            }
            for p in patterns
        ]
    
    async def get_workflow_performance(self, workflow_id: str) -> Dict[str, Any]:
        """Get performance report for a workflow."""
        memory = await self._ensure_n8n_memory()
        if not memory:
            return {}
        
        return await memory.get_performance_report(workflow_id)
    
    async def get_workflow_health(self) -> Dict[str, Any]:
        """Get overall workflow system health."""
        memory = await self._ensure_n8n_memory()
        if not memory:
            return {"database_connected": False}
        
        return await memory.get_workflow_health()


# Singleton instance
_coordinator: Optional[MemoryCoordinator] = None
_coordinator_lock = asyncio.Lock()


async def get_memory_coordinator() -> MemoryCoordinator:
    """
    Get or create the singleton MemoryCoordinator instance.
    
    Returns:
        Initialized MemoryCoordinator
    """
    global _coordinator
    
    if _coordinator is None:
        async with _coordinator_lock:
            if _coordinator is None:
                _coordinator = MemoryCoordinator()
                await _coordinator.initialize()
    
    return _coordinator