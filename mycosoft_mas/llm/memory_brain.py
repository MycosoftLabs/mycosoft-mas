"""
MYCA Memory-Integrated Brain - February 5, 2026
Updated: February 5, 2026 - Added Earth2, GPU, and Map context injection

Integrates the MYCA Brain (Frontier LLM Router) with the unified memory system.
This provides PersonaPlex with memory-aware responses:

- Recalls relevant memories before generating responses
- Injects user profile and preferences into context
- Stores conversation turns automatically
- Records significant events in episodic memory
- Learns facts from conversations

This is the cognitive layer between PersonaPlex voice and MYCA's intelligence.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("MYCAMemoryBrain")


@dataclass
class MemoryAwareContext:
    """Extended context with memory information."""
    session_id: str
    conversation_id: str
    user_id: str = "morgan"
    turn_count: int = 0
    history: List[Dict[str, str]] = field(default_factory=list)
    active_tools: List[str] = field(default_factory=list)
    current_role: str = "orchestrator"
    
    # Memory-specific context
    recalled_memories: List[Dict[str, Any]] = field(default_factory=list)
    user_profile: Optional[Dict[str, Any]] = None
    recent_episodes: List[Dict[str, Any]] = field(default_factory=list)
    shared_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    voice_context: Optional[Dict[str, Any]] = None
    
    # Search session context (Feb 5, 2026)
    search_context: Optional[Dict[str, Any]] = None
    
    # Earth2 Weather AI context (Feb 5, 2026)
    earth2_context: Optional[Dict[str, Any]] = None
    
    # GPU state context (Feb 5, 2026)
    gpu_context: Optional[Dict[str, Any]] = None
    
    # Map/Geographic context (Feb 5, 2026)
    map_context: Optional[Dict[str, Any]] = None


class MYCAMemoryBrain:
    """
    Memory-aware MYCA Brain that integrates LLM responses with memory.
    
    Capabilities:
    - Pre-response memory recall (semantic search)
    - User profile loading and preference application
    - Automatic conversation persistence
    - Episodic event recording
    - Cross-session context building
    - Voice session awareness
    """
    
    def __init__(self):
        self._frontier_router = None
        self._memory_coordinator = None
        self._personaplex_memory = None
        self._search_memory = None
        self._earth2_memory = None
        self._gpu_memory = None
        self._initialized = False
        
        # Memory injection settings
        self.max_recalled_memories = 5
        self.max_recent_episodes = 3
        self.memory_relevance_threshold = 0.5
    
    async def initialize(self) -> None:
        """Initialize the memory-aware brain."""
        if self._initialized:
            return
        
        try:
            # Import frontier router
            from mycosoft_mas.llm.frontier_router import get_frontier_router
            self._frontier_router = get_frontier_router()
            
            # Import memory coordinator
            from mycosoft_mas.memory import get_memory_coordinator
            self._memory_coordinator = await get_memory_coordinator()
            
            # Import search memory (Feb 5, 2026)
            try:
                from mycosoft_mas.memory.search_memory import get_search_memory
                self._search_memory = await get_search_memory()
                logger.debug("Search memory integration enabled")
            except Exception as se:
                logger.debug(f"Search memory not available: {se}")
                self._search_memory = None
            
            # Import Earth2 memory (Feb 5, 2026)
            try:
                from mycosoft_mas.memory.earth2_memory import get_earth2_memory
                self._earth2_memory = await get_earth2_memory()
                logger.debug("Earth2 memory integration enabled")
            except Exception as e2e:
                logger.debug(f"Earth2 memory not available: {e2e}")
                self._earth2_memory = None
            
            # Import GPU memory (Feb 5, 2026)
            try:
                from mycosoft_mas.memory.gpu_memory import get_gpu_memory
                self._gpu_memory = await get_gpu_memory()
                logger.debug("GPU memory integration enabled")
            except Exception as gpue:
                logger.debug(f"GPU memory not available: {gpue}")
                self._gpu_memory = None
            
            self._initialized = True
            logger.info("MYCA Memory Brain initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Memory Brain: {e}")
            raise
    
    async def _load_memory_context(
        self,
        user_message: str,
        context: MemoryAwareContext
    ) -> MemoryAwareContext:
        """Load relevant memories into the context."""
        if not self._memory_coordinator:
            return context
        
        try:
            # 1. Load user profile
            if context.user_id:
                profile = await self._memory_coordinator.get_user_profile(context.user_id)
                context.user_profile = {
                    "user_id": profile.user_id,
                    "preferences": profile.preferences,
                    "last_interaction": profile.last_seen.isoformat() if profile.last_seen else None
                }
            
            # 2. Recall relevant semantic memories
            memories = await self._memory_coordinator.agent_recall(
                agent_id="myca_brain",
                query=user_message,
                layer="semantic",
                limit=self.max_recalled_memories
            )
            context.recalled_memories = memories
            
            # 3. Get recent episodes
            episodes = await self._memory_coordinator.get_recent_episodes(
                agent_id="myca_brain",
                limit=self.max_recent_episodes
            )
            context.recent_episodes = episodes
            
            # 4. Get voice session context if available
            if context.conversation_id:
                voice_ctx = await self._memory_coordinator.get_voice_context(context.user_id)
                context.voice_context = voice_ctx
            
            # 5. Load active search session context (Feb 5, 2026)
            if self._search_memory and context.user_id:
                search_session_id = self._search_memory._user_sessions.get(context.user_id)
                if search_session_id:
                    search_ctx = await self._search_memory.get_session_context(search_session_id)
                    if "error" not in search_ctx:
                        context.search_context = search_ctx
                        logger.debug(f"Loaded search context with {len(search_ctx.get('queries', []))} queries")
            
            # 6. Load Earth2 weather context (Feb 5, 2026)
            if self._earth2_memory and context.user_id:
                try:
                    earth2_ctx = await self._earth2_memory.get_context_for_voice(context.user_id)
                    if earth2_ctx:
                        context.earth2_context = earth2_ctx
                        logger.debug(f"Loaded Earth2 context with {len(earth2_ctx.get('recent_forecasts', []))} forecasts")
                except Exception as e2e:
                    logger.debug(f"Error loading Earth2 context: {e2e}")
            
            # 7. Load GPU state context (Feb 5, 2026)
            if self._gpu_memory:
                try:
                    gpu_ctx = await self._gpu_memory.get_context_for_llm()
                    if gpu_ctx:
                        context.gpu_context = gpu_ctx
                        logger.debug(f"Loaded GPU context: {gpu_ctx.get('utilization_percent', 0)}% VRAM")
                except Exception as gpue:
                    logger.debug(f"Error loading GPU context: {gpue}")
            
            logger.debug(f"Loaded memory context: {len(memories)} memories, {len(episodes)} episodes")
            
        except Exception as e:
            logger.warning(f"Error loading memory context: {e}")
        
        return context
    
    def _build_memory_enhanced_prompt(self, context: MemoryAwareContext) -> str:
        """Build additional prompt content from memory."""
        sections = []
        
        # User profile section
        if context.user_profile and context.user_profile.get("preferences"):
            prefs = context.user_profile["preferences"]
            sections.append("=== USER PREFERENCES ===")
            for key, value in list(prefs.items())[:5]:
                if not key.startswith("_"):
                    sections.append(f"- {key}: {value}")
        
        # Recalled memories section
        if context.recalled_memories:
            sections.append("")
            sections.append("=== RELEVANT MEMORIES ===")
            for mem in context.recalled_memories[:self.max_recalled_memories]:
                content = mem.get("content", {})
                if isinstance(content, dict):
                    summary = content.get("summary", content.get("data", str(content)[:100]))
                else:
                    summary = str(content)[:100]
                sections.append(f"- {summary}")
        
        # Recent episodes section
        if context.recent_episodes:
            sections.append("")
            sections.append("=== RECENT EVENTS ===")
            for ep in context.recent_episodes[:self.max_recent_episodes]:
                content = ep.get("content", {})
                desc = content.get("description", str(content)[:100])
                sections.append(f"- {desc}")
        
        # Voice session context
        if context.voice_context and context.voice_context.get("sessions_count", 0) > 0:
            sections.append("")
            sections.append("=== VOICE HISTORY ===")
            sections.append(f"Previous sessions: {context.voice_context.get('sessions_count', 0)}")
            if context.voice_context.get("last_session_summary"):
                sections.append(f"Last session: {context.voice_context['last_session_summary'][:100]}")
            if context.voice_context.get("frequent_topics"):
                topics = [t[0] for t in context.voice_context["frequent_topics"][:5]]
                sections.append(f"Common topics: {', '.join(topics)}")
        
        # Search session context (Feb 5, 2026)
        if context.search_context:
            sc = context.search_context
            sections.append("")
            sections.append("=== ACTIVE SEARCH SESSION ===")
            if sc.get("queries"):
                sections.append(f"Recent searches: {', '.join(sc['queries'][-3:])}")
            if sc.get("current_species"):
                sections.append(f"Currently viewing: {sc['current_species']}")
            if sc.get("focused_species"):
                sections.append(f"Species explored: {', '.join(sc['focused_species'][-5:])}")
            if sc.get("explored_topics"):
                sections.append(f"Topics explored: {', '.join(sc['explored_topics'])}")
            if sc.get("recent_ai"):
                sections.append("Recent AI exchanges:")
                for ai in sc["recent_ai"][-2:]:
                    role = ai.get("role", "?")
                    content = ai.get("content", "")[:80]
                    sections.append(f"  {role}: {content}...")
        
        # Earth2 Weather AI context (Feb 5, 2026)
        if context.earth2_context:
            e2 = context.earth2_context
            sections.append("")
            sections.append("=== WEATHER AI CONTEXT ===")
            if e2.get("favorite_locations"):
                locs = [loc.get("name", "Unknown") for loc in e2["favorite_locations"][:3] if loc.get("name")]
                if locs:
                    sections.append(f"Favorite locations: {', '.join(locs)}")
            if e2.get("preferred_models"):
                sections.append(f"Preferred models: {', '.join(e2['preferred_models'][:3])}")
            if e2.get("recent_forecasts"):
                sections.append(f"Recent forecasts: {len(e2['recent_forecasts'])}")
                for fc in e2["recent_forecasts"][:2]:
                    sections.append(f"  - {fc.get('location', 'Unknown')} ({fc.get('model', 'fcn')}, {fc.get('lead_time', 24)}h)")
            if e2.get("variables_of_interest"):
                sections.append(f"Weather interests: {', '.join(e2['variables_of_interest'][:5])}")
        
        # GPU State context (Feb 5, 2026)
        if context.gpu_context:
            gpu = context.gpu_context
            sections.append("")
            sections.append("=== GPU STATE ===")
            sections.append(f"VRAM: {gpu.get('vram_used_mb', 0)}MB / {gpu.get('vram_total_mb', 0)}MB ({gpu.get('utilization_percent', 0)}%)")
            if gpu.get("loaded_models"):
                sections.append(f"Loaded models: {', '.join(gpu['loaded_models'][:5])}")
            if gpu.get("model_count", 0) > 0:
                sections.append(f"Active models: {gpu['model_count']}")
        
        # Map/Geographic context (Feb 5, 2026)
        if context.map_context:
            mc = context.map_context
            sections.append("")
            sections.append("=== MAP CONTEXT ===")
            if mc.get("current_location"):
                loc = mc["current_location"]
                sections.append(f"Current view: {loc.get('lat', 0):.2f}, {loc.get('lng', 0):.2f}")
            if mc.get("zoom_level"):
                sections.append(f"Zoom level: {mc['zoom_level']}")
            if mc.get("visible_layers"):
                sections.append(f"Active layers: {', '.join(mc['visible_layers'][:5])}")
            if mc.get("selected_region"):
                sections.append(f"Selected region: {mc['selected_region']}")
        
        return "\n".join(sections) if sections else ""
    
    async def stream_response(
        self,
        message: str,
        session_id: str,
        conversation_id: str,
        user_id: str = "morgan",
        history: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Dict]] = None,
        provider: str = "auto"
    ) -> AsyncGenerator[str, None]:
        """
        Stream a memory-aware response.
        
        Args:
            message: User message
            session_id: Voice/chat session ID
            conversation_id: Conversation thread ID
            user_id: User identifier
            history: Optional conversation history
            tools: Available tools
            provider: LLM provider ("auto", "gemini", "claude", "openai")
            
        Yields:
            Response tokens
        """
        if not self._initialized:
            await self.initialize()
        
        # Create context
        context = MemoryAwareContext(
            session_id=session_id,
            conversation_id=conversation_id,
            user_id=user_id,
            history=history or [],
            turn_count=len(history) if history else 0
        )
        
        # Load memory context
        context = await self._load_memory_context(message, context)
        
        # Build memory-enhanced context for frontier router
        from mycosoft_mas.llm.frontier_router import ConversationContext
        frontier_context = ConversationContext(
            session_id=session_id,
            conversation_id=conversation_id,
            user_id=user_id,
            turn_count=context.turn_count,
            history=context.history,
            active_tools=context.active_tools,
            current_role=context.current_role
        )
        
        # Store user message in memory
        await self._store_turn(context, "user", message)
        
        # Collect full response for memory storage
        full_response = []
        
        try:
            # Get memory enhancement
            memory_prompt = self._build_memory_enhanced_prompt(context)
            
            # Inject memory context into the message if we have relevant memories
            enhanced_message = message
            if memory_prompt:
                # Add memory context as system context (not visible to user)
                frontier_context.history.insert(0, {
                    "role": "system",
                    "content": f"[MEMORY CONTEXT]\n{memory_prompt}"
                })
            
            # Stream response from frontier LLM
            async for token in self._frontier_router.stream_response(
                message=message,
                context=frontier_context,
                tools=tools,
                provider=provider
            ):
                full_response.append(token)
                yield token
            
            # Store assistant response
            response_text = "".join(full_response)
            await self._store_turn(context, "assistant", response_text)
            
            # Extract and store any learned facts
            await self._extract_and_store_facts(context, message, response_text)
            
        except Exception as e:
            logger.error(f"Error in memory-aware response: {e}")
            error_msg = "I apologize, I encountered an issue. Please try again."
            await self._store_turn(context, "assistant", error_msg)
            yield error_msg
    
    async def get_response(
        self,
        message: str,
        session_id: str,
        conversation_id: str,
        user_id: str = "morgan",
        history: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Dict]] = None,
        provider: str = "auto"
    ) -> str:
        """
        Get a complete memory-aware response (non-streaming).
        
        Returns:
            Complete response text
        """
        tokens = []
        async for token in self.stream_response(
            message=message,
            session_id=session_id,
            conversation_id=conversation_id,
            user_id=user_id,
            history=history,
            tools=tools,
            provider=provider
        ):
            tokens.append(token)
        return "".join(tokens)
    
    async def _store_turn(
        self,
        context: MemoryAwareContext,
        role: str,
        content: str
    ) -> None:
        """Store a conversation turn in memory."""
        if not self._memory_coordinator:
            return
        
        try:
            # Store in conversation memory
            await self._memory_coordinator.add_conversation_turn(
                session_id=context.session_id,
                role=role,
                content=content,
                metadata={
                    "conversation_id": context.conversation_id,
                    "user_id": context.user_id,
                    "turn": context.turn_count
                }
            )
            
            # Store in persistent memory with session layer
            await self._memory_coordinator.agent_remember(
                agent_id="myca_brain",
                content={
                    "type": "conversation_turn",
                    "role": role,
                    "content": content[:500],  # Truncate for storage
                    "session_id": context.session_id,
                    "conversation_id": context.conversation_id
                },
                layer="session",
                importance=0.6,
                tags=["conversation", role, context.conversation_id]
            )
            
        except Exception as e:
            logger.warning(f"Error storing turn: {e}")
    
    async def _extract_and_store_facts(
        self,
        context: MemoryAwareContext,
        user_message: str,
        response: str
    ) -> None:
        """Extract facts from conversation and store in semantic memory."""
        if not self._memory_coordinator:
            return
        
        # Simple fact extraction patterns
        fact_patterns = [
            ("my name is", "user_name"),
            ("i prefer", "preference"),
            ("i like", "preference"),
            ("i work at", "workplace"),
            ("i am a", "role"),
            ("my favorite", "preference"),
        ]
        
        try:
            user_lower = user_message.lower()
            for pattern, fact_type in fact_patterns:
                if pattern in user_lower:
                    # Extract the fact
                    idx = user_lower.find(pattern)
                    fact_content = user_message[idx:idx+100].strip()
                    
                    # Store as learned fact
                    await self._memory_coordinator.learn_user_fact(
                        user_id=context.user_id,
                        fact={
                            "type": fact_type,
                            "content": fact_content,
                            "learned_from": "conversation",
                            "session_id": context.session_id
                        }
                    )
                    
                    logger.debug(f"Learned fact: {fact_type} - {fact_content[:50]}")
                    break
                    
        except Exception as e:
            logger.warning(f"Error extracting facts: {e}")
    
    async def record_significant_event(
        self,
        event_type: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.7
    ) -> None:
        """Record a significant event in episodic memory."""
        if not self._memory_coordinator:
            return
        
        try:
            await self._memory_coordinator.record_episode(
                agent_id="myca_brain",
                event_type=event_type,
                description=description,
                context=context,
                importance=importance
            )
        except Exception as e:
            logger.warning(f"Error recording event: {e}")
    
    async def recall_context(
        self,
        query: str,
        user_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Recall relevant context for a query.
        
        Returns:
            Dictionary with memories, episodes, and user profile
        """
        if not self._memory_coordinator:
            return {"memories": [], "episodes": [], "profile": None}
        
        try:
            memories = await self._memory_coordinator.agent_recall(
                agent_id="myca_brain",
                query=query,
                limit=limit
            )
            
            episodes = await self._memory_coordinator.get_recent_episodes(
                agent_id="myca_brain",
                limit=5
            )
            
            profile = await self._memory_coordinator.get_user_profile(user_id)
            
            return {
                "memories": memories,
                "episodes": episodes,
                "profile": {
                    "user_id": profile.user_id,
                    "preferences": profile.preferences
                } if profile else None
            }
            
        except Exception as e:
            logger.error(f"Error recalling context: {e}")
            return {"memories": [], "episodes": [], "profile": None}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get brain statistics."""
        stats = {
            "initialized": self._initialized,
            "frontier_router": self._frontier_router is not None,
            "memory_coordinator": self._memory_coordinator is not None,
        }
        
        if self._frontier_router:
            stats["provider_health"] = self._frontier_router.provider_health
        
        if self._memory_coordinator:
            try:
                mem_stats = await self._memory_coordinator.get_stats()
                stats["memory"] = mem_stats
            except:
                pass
        
        return stats


# Singleton instance
_memory_brain: Optional[MYCAMemoryBrain] = None
_brain_lock = asyncio.Lock()


async def get_memory_brain() -> MYCAMemoryBrain:
    """Get or create the memory-aware brain singleton."""
    global _memory_brain
    
    if _memory_brain is None:
        async with _brain_lock:
            if _memory_brain is None:
                _memory_brain = MYCAMemoryBrain()
                await _memory_brain.initialize()
    
    return _memory_brain
