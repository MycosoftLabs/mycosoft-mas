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
from uuid import UUID

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
    _agent_namespace: Optional[str] = None

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
            max_turns = getattr(self, "memory_max_turns", getattr(self, "max_turns", 50))
            self._conversation = ConversationMemory(max_turns=max_turns)
            self._agent_namespace = getattr(self, "agent_id", "unknown_agent")
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
                agent_id=self._agent_namespace, tags=["context"], layer="system", limit=1
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
            if hasattr(self, "capabilities") and isinstance(caps, list):
                if hasattr(self.capabilities, "update"):
                    self.capabilities.update(caps)

    # =========================================================================
    # Core Memory Operations
    # =========================================================================

    async def remember(
        self,
        content: Dict[str, Any],
        importance: float = 0.5,
        layer: str = "working",
        tags: Optional[List[str]] = None,
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
                tags=tags or [],
            )
        except Exception as e:
            logger.warning(f"Failed to store memory: {e}")
            return None

    async def recall(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        layer: Optional[str] = None,
        limit: int = 10,
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
                agent_id=self._agent_namespace, query=query, tags=tags, layer=layer, limit=limit
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
                tags=["fact", "learned"],
            )
            return result is not None
        except Exception as e:
            logger.warning(f"Failed to learn fact: {e}")
            return False

    async def record_task_completion(
        self, task_id: str, result: Dict[str, Any], success: bool
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                outcome="success" if success else "failure",
                importance=0.6 if success else 0.8,
            )
        except Exception as e:
            logger.warning(f"Failed to record task completion: {e}")

    async def record_error(
        self, error_message: str, context: Optional[Dict[str, Any]] = None
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
                importance=0.9,
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
            if hasattr(self, "get_status"):
                status = self.get_status() if callable(self.get_status) else self.get_status
            elif hasattr(self, "status"):
                status = {"status": str(self.status)}

            # Get capabilities
            capabilities = []
            if hasattr(self, "capabilities"):
                if hasattr(self.capabilities, "__iter__"):
                    capabilities = list(self.capabilities)

            await self.remember(
                content={
                    "type": "context",
                    "state": status,
                    "capabilities": capabilities,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                },
                layer="system",
                importance=1.0,
                tags=["context", "shutdown"],
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
            stats = {"initialized": True, "agent_id": self._agent_namespace, "layers": {}}

            for layer in ["ephemeral", "session", "working", "semantic", "episodic", "system"]:
                if hasattr(self._memory, "count_memories"):
                    stats["layers"][layer] = await self._memory.count_memories(
                        agent_id=self._agent_namespace, layer=layer
                    )
                else:
                    memories = await self.recall(layer=layer, limit=1000)
                    stats["layers"][layer] = len(memories)

            stats["total_memories"] = sum(stats["layers"].values())
            stats["conversation_turns"] = (
                len(self._conversation._turns) if self._conversation else 0
            )

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
        recipients: Optional[List[str]] = None,
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
                recipients=recipients,
            )
        except Exception as e:
            logger.error(f"Failed to share memory: {e}")
            return None

    async def share_learning(
        self, fact: Dict[str, Any], source: str = "experience", confidence: float = 0.8
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
                agent_id=self._agent_namespace, fact=fact, source=source, confidence=confidence
            )
        except Exception as e:
            logger.error(f"Failed to share learning: {e}")
            return None

    async def query_shared_knowledge(
        self, query: str, tags: Optional[List[str]] = None, timeout: float = 5.0
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
                requester_id=self._agent_namespace, query=query, tags=tags, timeout=timeout
            )
        except Exception as e:
            logger.error(f"Failed to query shared knowledge: {e}")
            return []

    async def learn_and_share(
        self, fact: Dict[str, Any], share: bool = True, confidence: float = 0.8
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

    # =========================================================================
    # Palace Memory Operations (April 7, 2026)
    # Spatial memory + AAAK diary + contradiction detection + tunnels
    # =========================================================================

    async def palace_remember(
        self,
        content: str,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        hall: Optional[str] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> Optional[UUID]:
        """
        File content into the memory palace with spatial metadata.

        Auto-classifies wing/room/hall if not provided.
        """
        if not self._memory:
            await self.init_memory()
        if not self._memory:
            return None

        try:
            return await self._memory.palace_ingest(
                content=content,
                wing=wing,
                room=room,
                hall=hall,
                importance=importance,
                tags=tags,
                agent_id=self._agent_namespace or "unknown",
            )
        except Exception as e:
            logger.warning(f"Palace remember failed: {e}")
            return None

    async def palace_recall(
        self,
        query: Optional[str] = None,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        hall: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Wing/room-scoped retrieval from the memory palace."""
        if not self._memory:
            await self.init_memory()
        if not self._memory:
            return []

        try:
            return await self._memory.palace_search(
                query=query, wing=wing, room=room, hall=hall, limit=limit
            )
        except Exception as e:
            logger.warning(f"Palace recall failed: {e}")
            return []

    async def palace_search(self, query: str, limit: int = 10) -> str:
        """L3 deep semantic search across all palace memory."""
        if not self._memory:
            await self.init_memory()
        if not self._memory:
            return ""

        try:
            return await self._memory.palace_deep_search(query=query, limit=limit)
        except Exception as e:
            logger.warning(f"Palace search failed: {e}")
            return ""

    async def wake_up(self, wing: Optional[str] = None) -> str:
        """
        Load L0+L1 context (~170 tokens) for agent initialization.

        Call at agent start to get compact identity + critical facts context.
        """
        if not self._memory:
            await self.init_memory()
        if not self._memory:
            return ""

        try:
            return await self._memory.palace_wake_up(wing=wing)
        except Exception as e:
            logger.warning(f"Wake-up failed: {e}")
            return ""

    async def get_tunnels(self, wing: str) -> List[Dict[str, Any]]:
        """Discover cross-domain connections (tunnels) from a wing."""
        if not self._memory:
            await self.init_memory()
        if not self._memory:
            return []

        try:
            await self._memory._ensure_palace()
            if self._memory._palace_navigator:
                tunnels = await self._memory._palace_navigator.find_tunnels(wing)
                return [
                    {
                        "room": t.room_name,
                        "wing_a": t.wing_a,
                        "wing_b": t.wing_b,
                        "strength": t.strength,
                    }
                    for t in tunnels
                ]
        except Exception as e:
            logger.warning(f"Get tunnels failed: {e}")
        return []

    async def diary_write(self, summary: str, wing: Optional[str] = None) -> bool:
        """
        Write an AAAK diary entry for this agent.
        Persists across sessions for domain expertise continuity.
        """
        if not self._memory:
            await self.init_memory()
        if not self._memory:
            return False

        try:
            await self._memory._ensure_palace()
            from mycosoft_mas.memory.palace.aaak_dialect import AAKEncoder
            from mycosoft_mas.memory.palace.db_pool import get_shared_pool

            encoder = AAKEncoder()
            aaak = encoder.compress(
                content=summary,
                wing=wing or "agents",
                room=self._agent_namespace or "unknown",
                agent_id=self._agent_namespace or "unknown",
            )

            pool = await get_shared_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO mindex.agent_diaries (agent_id, entry_aaak, entry_raw, wing, room)
                    VALUES ($1, $2, $3::jsonb, $4, $5)
                    """,
                    self._agent_namespace or "unknown",
                    aaak,
                    __import__("json").dumps({"summary": summary}),
                    wing or "agents",
                    self._agent_namespace or "unknown",
                )
            return True
        except Exception as e:
            logger.warning(f"Diary write failed: {e}")
            return False

    async def diary_read(self, n: int = 5) -> List[Dict[str, str]]:
        """Read the last N diary entries for this agent."""
        try:
            from mycosoft_mas.memory.palace.db_pool import get_shared_pool

            pool = await get_shared_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT entry_aaak, entry_raw, wing, room, created_at
                    FROM mindex.agent_diaries
                    WHERE agent_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    self._agent_namespace or "unknown",
                    n,
                )
                return [
                    {
                        "aaak": row["entry_aaak"],
                        "raw": row["entry_raw"],
                        "wing": row["wing"],
                        "room": row["room"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"Diary read failed: {e}")
            return []

    async def check_fact(
        self, subject: str, predicate: str, obj: str
    ) -> Dict[str, Any]:
        """Check for contradictions before filing a fact."""
        try:
            from mycosoft_mas.memory.palace.contradiction_detector import (
                ContradictionDetector,
            )

            detector = ContradictionDetector()
            await detector.initialize()
            return await detector.check_and_report(subject, predicate, obj)
        except Exception as e:
            logger.warning(f"Fact check failed: {e}")
            return {"safe": True, "contradictions": [], "recommendation": "Check unavailable."}

    async def get_timeline(self, entity: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chronological timeline of facts about an entity."""
        try:
            from mycosoft_mas.memory.persistent_graph import get_knowledge_graph

            graph = get_knowledge_graph()
            await graph.initialize()
            return await graph.get_timeline(entity, limit=limit)
        except Exception as e:
            logger.warning(f"Timeline query failed: {e}")
            return []
