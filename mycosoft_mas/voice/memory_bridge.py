"""
Voice-Memory Bridge
Created: February 12, 2026

Connects the voice system to the 6-layer memory system, enabling:
- Voice interactions stored in episodic memory
- Autobiographical memory updates with voice conversations
- Semantic memory queries for context during voice
- Cross-session voice memory persistence

NO MOCK DATA - real memory integration only.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger("VoiceMemoryBridge")


class VoiceMemoryBridge:
    """
    Bridge between voice system and 6-layer memory system.
    
    Responsibilities:
    - Store voice interactions in episodic memory
    - Update autobiographical memory with voice conversations
    - Query semantic memory for context during voice
    - Persist voice sessions across reconnects
    - Maintain conversation continuity
    
    Usage:
        bridge = await get_voice_memory_bridge()
        
        # Start voice session with memory context
        session_id = await bridge.start_voice_session(
            user_id="morgan",
            user_name="Morgan Rockwell"
        )
        
        # Add interaction
        await bridge.add_voice_interaction(
            session_id=session_id,
            user_message="How are the mushrooms doing?",
            assistant_response="The fruiting chamber is at 87% humidity...",
            emotion="curious"
        )
        
        # Get context for response
        context = await bridge.get_voice_context(
            user_id="morgan",
            current_message="Tell me about the last grow"
        )
        
        # End session
        await bridge.end_voice_session(session_id)
    """
    
    def __init__(self):
        self._coordinator = None
        self._autobiographical = None
        self._personaplex = None
        self._cross_session = None
        self._initialized = False
        
        # Session mapping: voice_session_id -> memory_session_id
        self._session_map: Dict[str, str] = {}
    
    async def initialize(self) -> None:
        """Initialize all memory subsystems."""
        if self._initialized:
            return
        
        try:
            # Import memory systems
            from mycosoft_mas.memory.coordinator import get_memory_coordinator
            from mycosoft_mas.memory.autobiographical import get_autobiographical_memory
            from mycosoft_mas.memory.personaplex_memory import get_personaplex_memory
            from mycosoft_mas.voice.cross_session_memory import get_cross_session_memory
            
            # Initialize coordinator (6-layer memory)
            self._coordinator = await get_memory_coordinator()
            
            # Initialize autobiographical memory
            self._autobiographical = await get_autobiographical_memory()
            
            # Initialize PersonaPlex memory
            self._personaplex = await get_personaplex_memory()
            
            # Initialize cross-session voice memory
            self._cross_session = get_cross_session_memory()
            
            self._initialized = True
            logger.info("Voice-Memory Bridge initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Voice-Memory Bridge: {e}")
            raise
    
    def _ensure_initialized(self) -> None:
        """Ensure the bridge is initialized."""
        if not self._initialized:
            raise RuntimeError("Voice-Memory Bridge not initialized. Call await bridge.initialize() first.")
    
    # =========================================================================
    # Voice Session Lifecycle
    # =========================================================================
    
    async def start_voice_session(
        self,
        user_id: str,
        user_name: str,
        speaker_profile: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new voice session with full memory integration.
        
        Args:
            user_id: User identifier
            user_name: User's display name
            speaker_profile: Optional speaker profile ID
            context: Initial session context
            
        Returns:
            Voice session ID (string)
        """
        self._ensure_initialized()
        
        # Start PersonaPlex voice session
        voice_session = await self._personaplex.start_session(
            user_id=user_id,
            speaker_profile=speaker_profile,
            context=context or {}
        )
        
        # Start memory coordinator conversation
        memory_session_id = await self._coordinator.start_conversation(user_id)
        
        # Map voice session to memory session
        self._session_map[str(voice_session.id)] = memory_session_id
        
        # Start cross-session voice memory conversation
        voice_context = self._cross_session.start_conversation(user_id)
        
        # Load user profile and preferences
        user_profile = await self._coordinator.get_user_profile(user_id)
        voice_prefs = self._cross_session.load_user_preferences(user_id)
        
        # Load previous conversation context
        previous_context = await self._autobiographical.get_context_for_response(
            user_id=user_id,
            current_message="",  # Initial context
            context_window=5
        )
        
        # Add context to voice session
        voice_session.context.update({
            "memory_session_id": memory_session_id,
            "user_profile": {
                "preferences": user_profile.preferences,
                "interaction_summary": user_profile.interaction_summary,
            },
            "voice_preferences": {
                "voice_speed": voice_prefs.voice_speed,
                "voice_pitch": voice_prefs.voice_pitch,
                "preferred_voice": voice_prefs.preferred_voice,
                "response_verbosity": voice_prefs.response_verbosity,
            },
            "previous_conversations": previous_context.get("recent_history", [])[:3],
            "relationship": previous_context.get("relationship", {}),
        })
        
        # Record session start in episodic memory
        await self._coordinator.record_episode(
            agent_id="voice_system",
            event_type="interaction",
            description=f"Voice session started with {user_name}",
            participants=[user_id],
            context={
                "session_id": str(voice_session.id),
                "speaker_profile": speaker_profile,
            },
            importance=0.6
        )
        
        logger.info(f"Started voice session {voice_session.id} for {user_name} with full memory context")
        return str(voice_session.id)
    
    async def add_voice_interaction(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        emotion: Optional[str] = None,
        duration_ms: Optional[int] = None,
        audio_hash: Optional[str] = None
    ) -> bool:
        """
        Add a voice interaction to all memory systems.
        
        This stores the interaction in:
        - PersonaPlex voice memory (turn tracking)
        - Coordinator conversation memory (6-layer)
        - Cross-session voice memory (user-specific)
        - Autobiographical memory (life story)
        - Episodic memory (events)
        
        Args:
            session_id: Voice session ID
            user_message: What the user said
            assistant_response: MYCA's response
            emotion: Detected emotion (optional)
            duration_ms: Turn duration in milliseconds
            audio_hash: Hash of audio recording
            
        Returns:
            True if successfully stored in all systems
        """
        self._ensure_initialized()
        
        try:
            # Get voice session
            voice_session = self._personaplex._active_sessions.get(UUID(session_id))
            if not voice_session:
                logger.warning(f"Voice session {session_id} not found")
                return False
            
            user_id = voice_session.user_id or "unknown"
            memory_session_id = self._session_map.get(session_id)
            
            # 1. Add to PersonaPlex voice memory
            await self._personaplex.add_turn(
                session_id=UUID(session_id),
                role="user",
                content=user_message,
                audio_hash=audio_hash,
                duration_ms=duration_ms,
                emotion=emotion
            )
            
            await self._personaplex.add_turn(
                session_id=UUID(session_id),
                role="assistant",
                content=assistant_response,
                duration_ms=duration_ms,
                emotion=emotion
            )
            
            # 2. Add to coordinator conversation memory
            if memory_session_id:
                await self._coordinator.add_conversation_turn(
                    session_id=memory_session_id,
                    role="user",
                    content=user_message,
                    metadata={"source": "voice", "emotion": emotion}
                )
                
                await self._coordinator.add_conversation_turn(
                    session_id=memory_session_id,
                    role="assistant",
                    content=assistant_response,
                    metadata={"source": "voice", "duration_ms": duration_ms}
                )
            
            # 3. Add to cross-session voice memory
            voice_context = self._cross_session.get_conversation(
                voice_session.context.get("conversation_id", "")
            )
            if voice_context:
                voice_context.add_intent(user_message)
                voice_context.add_response(assistant_response)
            
            # 4. Store in autobiographical memory
            emotional_state = {
                emotion or "neutral": 0.7,
                "engagement": 0.8
            }
            
            interaction_id = await self._autobiographical.store_interaction(
                user_id=user_id,
                user_name=voice_session.context.get("user_name", user_id),
                message=user_message,
                response=assistant_response,
                emotional_state=emotional_state,
                reflection=None,  # Will be added later if significant
                importance=0.5,
                tags=["voice", emotion or "neutral"],
                milestone=False
            )
            
            # 5. Record in episodic memory (for significant turns only)
            if len(user_message) > 20:  # Only store substantial interactions
                await self._coordinator.record_episode(
                    agent_id="voice_system",
                    event_type="interaction",
                    description=f"Voice interaction: {user_message[:100]}",
                    participants=[user_id],
                    context={
                        "session_id": session_id,
                        "response": assistant_response[:100],
                        "emotion": emotion,
                        "interaction_id": interaction_id,
                    },
                    outcome="completed",
                    importance=0.5
                )
            
            logger.debug(f"Stored voice interaction in all memory systems")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add voice interaction: {e}")
            return False
    
    async def end_voice_session(
        self,
        session_id: str,
        summary_override: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        End a voice session and finalize memory storage.
        
        Args:
            session_id: Voice session ID
            summary_override: Optional manual summary
            
        Returns:
            Session summary with statistics
        """
        self._ensure_initialized()
        
        try:
            # End PersonaPlex session (generates summary and topics)
            voice_session = await self._personaplex.end_session(UUID(session_id))
            if not voice_session:
                logger.warning(f"Voice session {session_id} not found")
                return None
            
            user_id = voice_session.user_id or "unknown"
            memory_session_id = self._session_map.pop(session_id, None)
            
            # Use override or generated summary
            summary = summary_override or voice_session.summary or "Voice session completed"
            
            # Store session summary in autobiographical memory
            if voice_session.turn_count > 0:
                await self._autobiographical.store_interaction(
                    user_id=user_id,
                    user_name=voice_session.context.get("user_name", user_id),
                    message=f"Voice session summary: {summary}",
                    response=f"Session had {voice_session.turn_count} turns covering topics: {', '.join(voice_session.topics)}",
                    emotional_state={"satisfaction": 0.7},
                    reflection=summary,
                    importance=0.7,
                    tags=["voice_session", "summary"] + voice_session.topics,
                    milestone=voice_session.turn_count > 10  # Long sessions are milestones
                )
            
            # Store session summary in semantic memory
            await self._coordinator.agent_remember(
                agent_id="voice_system",
                content={
                    "type": "session_summary",
                    "session_id": session_id,
                    "user_id": user_id,
                    "summary": summary,
                    "topics": voice_session.topics,
                    "turn_count": voice_session.turn_count,
                    "duration_seconds": voice_session.duration.total_seconds() if voice_session.duration else 0,
                },
                layer="semantic",
                importance=0.7,
                tags=["voice_session", "summary"] + voice_session.topics
            )
            
            # Record session end episode
            await self._coordinator.record_episode(
                agent_id="voice_system",
                event_type="interaction",
                description=f"Voice session ended: {summary}",
                participants=[user_id],
                context={
                    "session_id": session_id,
                    "turn_count": voice_session.turn_count,
                    "topics": voice_session.topics,
                },
                outcome="completed",
                importance=0.7
            )
            
            # Cleanup memory coordinator session
            if memory_session_id:
                await self._coordinator.cleanup_session(memory_session_id)
            
            logger.info(f"Ended voice session {session_id} ({voice_session.turn_count} turns)")
            
            return {
                "session_id": session_id,
                "summary": summary,
                "topics": voice_session.topics,
                "turn_count": voice_session.turn_count,
                "duration_seconds": voice_session.duration.total_seconds() if voice_session.duration else 0,
                "emotional_arc": voice_session.emotional_arc,
            }
            
        except Exception as e:
            logger.error(f"Failed to end voice session: {e}")
            return None
    
    # =========================================================================
    # Memory Context Retrieval
    # =========================================================================
    
    async def get_voice_context(
        self,
        user_id: str,
        current_message: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive memory context for voice response generation.
        
        This queries:
        - Recent conversation history (short-term)
        - Previous voice sessions (cross-session)
        - Autobiographical memory (life story with user)
        - Semantic memory (relevant facts and knowledge)
        - User preferences and profile
        
        Args:
            user_id: User identifier
            current_message: Current user message
            session_id: Optional current session ID
            
        Returns:
            Comprehensive context dictionary for response generation
        """
        self._ensure_initialized()
        
        context = {
            "user_id": user_id,
            "current_message": current_message,
        }
        
        try:
            # 1. Get recent conversation history
            if session_id:
                memory_session_id = self._session_map.get(session_id)
                if memory_session_id:
                    recent_history = await self._coordinator.get_conversation_context(
                        session_id=memory_session_id,
                        turns=10
                    )
                    context["recent_history"] = recent_history
            
            # 2. Get cross-session voice context
            voice_context = await self._personaplex.get_cross_session_context(user_id)
            context["voice_sessions"] = voice_context
            
            # 3. Get autobiographical context
            autobio_context = await self._autobiographical.get_context_for_response(
                user_id=user_id,
                current_message=current_message,
                context_window=10
            )
            context["autobiographical"] = autobio_context
            
            # 4. Get relevant semantic knowledge
            semantic_results = await self._coordinator.agent_recall(
                agent_id="voice_system",
                query=current_message,
                layer="semantic",
                limit=5
            )
            context["semantic_knowledge"] = semantic_results
            
            # 5. Get user profile and preferences
            user_profile = await self._coordinator.get_user_profile(user_id)
            context["user_profile"] = {
                "preferences": user_profile.preferences,
                "learned_facts": user_profile.learned_facts[:10],
                "interaction_summary": user_profile.interaction_summary,
            }
            
            # 6. Get relevant episodes
            recent_episodes = await self._coordinator.get_recent_episodes(
                agent_id="voice_system",
                limit=5
            )
            context["recent_episodes"] = recent_episodes
            
            logger.debug(f"Retrieved voice context for {user_id}: {len(context)} sections")
            return context
            
        except Exception as e:
            logger.error(f"Failed to get voice context: {e}")
            return context
    
    async def search_voice_memory(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search across all voice memory for relevant past interactions.
        
        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum results
            
        Returns:
            List of relevant past voice interactions
        """
        self._ensure_initialized()
        
        results = []
        
        try:
            # Search autobiographical memory
            autobio_results = await self._autobiographical.search_memories(
                query=query,
                user_id=user_id,
                limit=limit
            )
            
            for interaction in autobio_results:
                results.append({
                    "timestamp": interaction.timestamp.isoformat(),
                    "message": interaction.message,
                    "response": interaction.response,
                    "source": "autobiographical",
                    "importance": interaction.importance,
                    "tags": interaction.tags,
                })
            
            # Search semantic memory
            semantic_results = await self._coordinator.agent_recall(
                agent_id="voice_system",
                query=query,
                layer="semantic",
                limit=limit
            )
            
            for result in semantic_results:
                if result.get("content", {}).get("type") == "session_summary":
                    results.append({
                        "timestamp": result.get("created_at"),
                        "summary": result.get("content", {}).get("summary"),
                        "topics": result.get("content", {}).get("topics", []),
                        "source": "semantic",
                        "importance": result.get("importance", 0.5),
                    })
            
            # Sort by importance and recency
            results.sort(key=lambda x: x.get("importance", 0.5), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search voice memory: {e}")
            return []
    
    # =========================================================================
    # User Learning and Preferences
    # =========================================================================
    
    async def learn_from_voice(
        self,
        user_id: str,
        fact: str,
        importance: float = 0.7,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Learn a new fact about a user from voice interaction.
        
        Args:
            user_id: User identifier
            fact: Fact to learn
            importance: Importance score
            tags: Optional tags
            
        Returns:
            True if successfully learned
        """
        self._ensure_initialized()
        
        try:
            # Store in user context
            fact_data = {
                "fact": fact,
                "source": "voice",
                "learned_at": datetime.now(timezone.utc).isoformat(),
                "importance": importance,
            }
            
            await self._coordinator.learn_user_fact(user_id, fact_data)
            
            # Store in semantic memory
            await self._coordinator.agent_remember(
                agent_id="voice_system",
                content={
                    "type": "learned_fact",
                    "user_id": user_id,
                    "fact": fact,
                },
                layer="semantic",
                importance=importance,
                tags=(tags or []) + [f"user:{user_id}", "learned_fact"]
            )
            
            logger.info(f"Learned from voice: {fact[:50]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to learn from voice: {e}")
            return False
    
    async def update_voice_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: Any
    ) -> bool:
        """
        Update a user's voice preference.
        
        Args:
            user_id: User identifier
            preference_key: Preference key (e.g., "voice_speed", "response_verbosity")
            preference_value: New preference value
            
        Returns:
            True if successfully updated
        """
        self._ensure_initialized()
        
        try:
            # Update in cross-session memory
            prefs = self._cross_session.load_user_preferences(user_id)
            
            if hasattr(prefs, preference_key):
                setattr(prefs, preference_key, preference_value)
            else:
                prefs.custom[preference_key] = preference_value
            
            self._cross_session.save_user_preferences(prefs)
            
            # Also store in coordinator
            await self._coordinator.update_user_preference(
                user_id=user_id,
                key=f"voice_{preference_key}",
                value=preference_value
            )
            
            logger.info(f"Updated voice preference for {user_id}: {preference_key}={preference_value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update voice preference: {e}")
            return False
    
    # =========================================================================
    # Statistics and Health
    # =========================================================================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get voice-memory bridge statistics."""
        self._ensure_initialized()
        
        try:
            coordinator_stats = await self._coordinator.get_stats()
            autobio_stats = await self._autobiographical.get_statistics()
            personaplex_stats = await self._personaplex.get_stats()
            
            return {
                "bridge": {
                    "initialized": self._initialized,
                    "active_voice_sessions": len(self._session_map),
                },
                "coordinator": coordinator_stats,
                "autobiographical": autobio_stats,
                "personaplex": personaplex_stats,
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    async def shutdown(self) -> None:
        """Shutdown the voice-memory bridge."""
        if self._coordinator:
            await self._coordinator.shutdown()
        
        if self._autobiographical:
            await self._autobiographical.close()
        
        self._initialized = False
        logger.info("Voice-Memory Bridge shutdown complete")


# Singleton instance
_bridge: Optional[VoiceMemoryBridge] = None
_bridge_lock = asyncio.Lock()


async def get_voice_memory_bridge() -> VoiceMemoryBridge:
    """
    Get or create the singleton VoiceMemoryBridge instance.
    
    Returns:
        Initialized VoiceMemoryBridge
    """
    global _bridge
    
    if _bridge is None:
        async with _bridge_lock:
            if _bridge is None:
                _bridge = VoiceMemoryBridge()
                await _bridge.initialize()
    
    return _bridge


__all__ = [
    "VoiceMemoryBridge",
    "get_voice_memory_bridge",
]
