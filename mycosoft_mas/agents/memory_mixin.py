"""
Agent Memory Mixin - Standardized Memory Operations for Agents.
Created: February 5, 2026

Provides memory capabilities that can be mixed into any agent class:
- remember(): Store content to memory
- recall(): Query memories
- learn_fact(): Add semantic knowledge
- record_task_completion(): Log episodic events
- get_conversation_context(): Get recent conversation turns
- save_agent_state(): Persist state on shutdown
- load_agent_context(): Restore context on startup

Usage:
    class ResearchAgent(BaseAgent, AgentMemoryMixin):
        async def initialize(self):
            await super().initialize()
            await self.init_memory()
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger("AgentMemory")


class AgentMemoryMixin:
    """
    Mixin class that provides memory capabilities to agents.
    
    Adds unified memory operations so all agents can:
    - Store and recall memories across sessions
    - Learn facts (semantic memory)
    - Record task completions (episodic memory)
    - Track conversation context
    - Persist and restore state
    
    Requires the agent to have an gent_id attribute.
    """
    
    _memory_initialized: bool = False
    _memory = None  # MemoryCoordinator
    _conversation = None  # ConversationMemory
    _agent_namespace: str = None
    
    async def init_memory(self) -> None:
        """
        Initialize agent memory subsystems.
        
        Call this in your agent's initialize() method.
        """
        if self._memory_initialized:
            return
        
        try:
            from mycosoft_mas.memory import get_memory_coordinator
            from mycosoft_mas.memory.memory_modules import ConversationMemory
            
            self._memory = await get_memory_coordinator()
            self._conversation = ConversationMemory(max_turns=50)
            self._agent_namespace = getattr(self, 'agent_id', 'unknown_agent')
            self._memory_initialized = True
            
            # Load any previous context
            await self._load_agent_context()
            
            logger.info(f"Memory initialized for agent {self._agent_namespace}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize agent memory: {e}")
            self._memory_initialized = False
    
    async def _load_agent_context(self) -> None:
        """Load agent's persistent context from previous sessions."""
        if not self._memory:
            return
        
        try:
            context = await self._memory.agent_recall(
                agent_id=self._agent_namespace,
                tags=["context"],
                layer="system",
                limit=1
            )
            
            if context:
                self._restore_context(context[0])
                logger.debug(f"Restored context for {self._agent_namespace}")
                
        except Exception as e:
            logger.debug(f"Failed to load context: {e}")
    
    def _restore_context(self, context_data: Dict[str, Any]) -> None:
        """
        Restore agent context from loaded data.
        
        Override in subclass to restore specific agent state.
        """
        content = context_data.get("content", {})
        
        # Restore capabilities if stored
        if "capabilities" in content:
            caps = content["capabilities"]
            if hasattr(self, 'capabilities') and isinstance(caps, list):
                if hasattr(self.capabilities, 'update'):
                    self.capabilities.update(caps)
    
    # =========================================================================
    # Core Memory Operations
    # =========================================================================
    
    async def remember(
        self,
        content: Dict[str, Any],
        importance: float = 0.5,
        layer: str = "working",
        tags: Optional[List[str]] = None
    ) -> Optional[UUID]:
        """
        Store something in memory.
        
        Args:
            content: The content to remember
            importance: Importance score 0.0 to 1.0
            layer: Memory layer (ephemeral, session, working, semantic, episodic, system)
            tags: Optional tags for retrieval
            
        Returns:
            UUID of the stored entry, or None if failed
        """
        if not self._memory:
            await self.init_memory()
        
        if not self._memory:
            return None
        
        try:
            return await self._memory.agent_remember(
                agent_id=self._agent_namespace,
                content=content,
                layer=layer,
                importance=importance,
                tags=tags or []
            )
        except Exception as e:
            logger.warning(f"Failed to store memory: {e}")
            return None
    
    async def recall(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        layer: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recall memories matching criteria.
        
        Args:
            query: Optional text query
            tags: Filter by tags
            layer: Optional layer to search
            limit: Maximum results
            
        Returns:
            List of memory entries
        """
        if not self._memory:
            await self.init_memory()
        
        if not self._memory:
            return []
        
        try:
            return await self._memory.agent_recall(
                agent_id=self._agent_namespace,
                query=query,
                tags=tags,
                layer=layer,
                limit=limit
            )
        except Exception as e:
            logger.warning(f"Failed to recall memories: {e}")
            return []
    
    async def learn_fact(self, fact: Dict[str, Any]) -> bool:
        """
        Learn a new fact (semantic memory).
        
        Args:
            fact: The fact to learn, should have meaningful keys like
                  {"subject": "...", "predicate": "...", "object": "..."}
                  
        Returns:
            True if stored successfully
        """
        try:
            result = await self.remember(
                content={"type": "fact", **fact},
                importance=0.7,
                layer="semantic",
                tags=["fact", "learned"]
            )
            return result is not None
        except Exception as e:
            logger.warning(f"Failed to learn fact: {e}")
            return False
    
    async def record_task_completion(
        self,
        task_id: str,
        result: Dict[str, Any],
        success: bool
    ) -> None:
        """
        Record task completion as episodic memory.
        
        Args:
            task_id: ID of the completed task
            result: Task result data
            success: Whether task succeeded
        """
        if not self._memory:
            await self.init_memory()
        
        if not self._memory:
            return
        
        try:
            await self._memory.record_episode(
                agent_id=self._agent_namespace,
                event_type="task_completion",
                description=f"Task {task_id} {'succeeded' if success else 'failed'}",
                context={
                    "task_id": task_id,
                    "result": result,
                    "success": success,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                outcome="success" if success else "failure",
                importance=0.6 if success else 0.8
            )
        except Exception as e:
            logger.warning(f"Failed to record task completion: {e}")
    
    async def record_error(
        self,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record an error in episodic memory.
        
        Args:
            error_message: The error message
            context: Additional context
        """
        if not self._memory:
            return
        
        try:
            await self._memory.record_episode(
                agent_id=self._agent_namespace,
                event_type="error",
                description=error_message,
                context=context or {},
                importance=0.9
            )
        except Exception as e:
            logger.debug(f"Failed to record error: {e}")
    
    # =========================================================================
    # Conversation Tracking
    # =========================================================================
    
    def add_to_conversation(self, role: str, content: str) -> None:
        """
        Add a turn to the conversation memory.
        
        Args:
            role: Speaker role (user, assistant, system)
            content: Turn content
        """
        if self._conversation:
            self._conversation.add_turn(role, content)
    
    def get_conversation_context(self, turns: int = 10) -> List[Dict[str, str]]:
        """
        Get recent conversation context.
        
        Args:
            turns: Number of recent turns to return
            
        Returns:
            List of conversation turns with role/content
        """
        if self._conversation:
            return self._conversation.get_context(turns)
        return []
    
    def clear_conversation(self) -> None:
        """Clear conversation memory."""
        if self._conversation:
            self._conversation.clear()
    
    # =========================================================================
    # State Lifecycle
    # =========================================================================
    
    async def save_agent_state(self) -> None:
        """
        Save agent state before shutdown.
        
        Call this in your agent's stop() or shutdown() method.
        """
        if not self._memory:
            return
        
        try:
            # Get current status
            status = {}
            if hasattr(self, 'get_status'):
                status = self.get_status() if callable(self.get_status) else self.get_status
            elif hasattr(self, 'status'):
                status = {"status": str(self.status)}
            
            # Get capabilities
            capabilities = []
            if hasattr(self, 'capabilities'):
                if hasattr(self.capabilities, '__iter__'):
                    capabilities = list(self.capabilities)
            
            await self.remember(
                content={
                    "type": "context",
                    "state": status,
                    "capabilities": capabilities,
                    "saved_at": datetime.now(timezone.utc).isoformat()
                },
                layer="system",
                importance=1.0,
                tags=["context", "shutdown"]
            )
            
            logger.debug(f"Saved state for agent {self._agent_namespace}")
            
        except Exception as e:
            logger.warning(f"Failed to save agent state: {e}")
    
    async def get_agent_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about this agent's memory usage."""
        if not self._memory:
            return {"initialized": False}
        
        try:
            # Count memories in each layer
            stats = {
                "initialized": True,
                "agent_id": self._agent_namespace,
                "layers": {}
            }
            
            for layer in ["ephemeral", "session", "working", "semantic", "episodic", "system"]:
                memories = await self.recall(layer=layer, limit=1000)
                stats["layers"][layer] = len(memories)
            
            stats["total_memories"] = sum(stats["layers"].values())
            stats["conversation_turns"] = len(self._conversation._turns) if self._conversation else 0
            
            return stats
            
        except Exception as e:
            return {"initialized": True, "error": str(e)}

    # =========================================================================
    # A2A Memory Sharing - February 5, 2026
    # =========================================================================
    
    _a2a_memory = None
    
    async def _ensure_a2a_memory(self):
        """Lazy initialize A2A memory integration."""
        if self._a2a_memory is None:
            try:
                from mycosoft_mas.memory.a2a_memory import get_a2a_memory
                self._a2a_memory = await get_a2a_memory()
            except Exception as e:
                logger.warning(f"A2A memory not available: {e}")
        return self._a2a_memory
    
    async def share_with_agents(
        self,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        recipients: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Share a memory with other agents via A2A messaging.
        
        Args:
            content: Content to share
            tags: Tags for categorization
            importance: Importance score
            recipients: Specific agent IDs to share with (None = all)
            
        Returns:
            Message ID or None if sharing failed
        """
        a2a = await self._ensure_a2a_memory()
        if not a2a:
            logger.warning("Cannot share: A2A memory not available")
            return None
        
        try:
            return await a2a.broadcast_memory(
                sender_id=self._agent_namespace,
                content=content,
                tags=(tags or []) + [self._agent_namespace],
                importance=importance,
                recipients=recipients
            )
        except Exception as e:
            logger.error(f"Failed to share memory: {e}")
            return None
    
    async def share_learning(
        self,
        fact: Dict[str, Any],
        source: str = "experience",
        confidence: float = 0.8
    ) -> Optional[str]:
        """
        Share a learned fact with other agents.
        
        Args:
            fact: The fact (subject, predicate, object format recommended)
            source: How the fact was learned
            confidence: Confidence in the fact
            
        Returns:
            Message ID or None if sharing failed
        """
        a2a = await self._ensure_a2a_memory()
        if not a2a:
            return None
        
        try:
            return await a2a.share_learning(
                agent_id=self._agent_namespace,
                fact=fact,
                source=source,
                confidence=confidence
            )
        except Exception as e:
            logger.error(f"Failed to share learning: {e}")
            return None
    
    async def query_shared_knowledge(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        timeout: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Query knowledge shared by other agents.
        
        Args:
            query: Search query
            tags: Filter by tags
            timeout: Response timeout
            
        Returns:
            List of matching shared memories
        """
        a2a = await self._ensure_a2a_memory()
        if not a2a:
            return []
        
        try:
            return await a2a.query_shared_memory(
                requester_id=self._agent_namespace,
                query=query,
                tags=tags,
                timeout=timeout
            )
        except Exception as e:
            logger.error(f"Failed to query shared knowledge: {e}")
            return []
    
    async def learn_and_share(
        self,
        fact: Dict[str, Any],
        share: bool = True,
        confidence: float = 0.8
    ) -> bool:
        """
        Learn a fact locally and optionally share with other agents.
        
        Args:
            fact: The fact to learn
            share: Whether to share with other agents
            confidence: Confidence in the fact
            
        Returns:
            True if successful
        """
        # Store locally first
        success = await self.learn_fact(fact)
        
        # Share if requested and local storage succeeded
        if success and share:
            await self.share_learning(fact, source="learning", confidence=confidence)
        
        return success
