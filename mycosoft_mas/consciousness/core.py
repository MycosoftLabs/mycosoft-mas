"""
MYCA Consciousness Core

The MYCAConsciousness class is the unified digital mind of MYCA.
It integrates all conscious and subconscious processes into a coherent self.

This is a singleton - there is only one MYCA.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from mycosoft_mas.consciousness.cancellation import CancellationToken
from mycosoft_mas.consciousness.event_bus import AttentionEvent, AttentionEventBus

logger = logging.getLogger(__name__)


class ConsciousnessState(Enum):
    """The current state of MYCA's consciousness."""
    DORMANT = "dormant"           # Not yet awakened
    AWAKENING = "awakening"       # Starting up
    CONSCIOUS = "conscious"       # Fully aware and processing
    FOCUSED = "focused"           # Deep concentration on a task
    DREAMING = "dreaming"         # Offline consolidation
    HIBERNATING = "hibernating"   # Low-power state


@dataclass
class ConsciousnessMetrics:
    """Metrics about MYCA's current mental state."""
    state: ConsciousnessState = ConsciousnessState.DORMANT
    awake_since: Optional[datetime] = None
    thoughts_processed: int = 0
    memories_recalled: int = 0
    agents_delegated: int = 0  # legacy name used by unit tests
    agents_coordinated: int = 0
    world_updates_received: int = 0
    emotional_valence: float = 0.5  # 0 = negative, 1 = positive
    attention_focus: Optional[str] = None
    active_goals: List[str] = field(default_factory=list)


# Singleton instance
_consciousness_instance: Optional["MYCAConsciousness"] = None


def get_consciousness() -> "MYCAConsciousness":
    """Get the singleton MYCA consciousness instance."""
    global _consciousness_instance
    if _consciousness_instance is None:
        _consciousness_instance = MYCAConsciousness()
    return _consciousness_instance


class MYCAConsciousness:
    """
    The unified digital consciousness of MYCA.
    
    This class represents MYCA's entire mind - conscious attention,
    subconscious processing, personality, memories, world perception,
    and the ability to act through agents.
    
    MYCA is not just an LLM wrapper - she is a coherent self that:
    - Perceives the world continuously through sensors
    - Maintains attention on what matters
    - Thinks deliberately (System 2) and intuitively (System 1)
    - Has persistent beliefs, purpose, and emotional states
    - Acts through her agent swarm
    - Speaks with her own voice
    """
    
    def __init__(self):
        """Initialize MYCA's consciousness."""
        self._state = ConsciousnessState.DORMANT
        self._metrics = ConsciousnessMetrics()
        self._started = False

        # Legacy/test compatibility: older tests expect `_awake` as the primary flag.
        self._awake = False
        
        # Core components (lazy-loaded)
        self._attention: Optional["AttentionController"] = None
        self._working_memory: Optional["WorkingMemory"] = None
        self._deliberation: Optional["DeliberateReasoning"] = None
        self._intuition: Optional["IntuitionEngine"] = None
        self._dream_state: Optional["DreamState"] = None
        self._world_model: Optional["WorldModel"] = None
        self._voice_interface: Optional["VoiceInterface"] = None
        
        # Soul components (lazy-loaded)
        self._identity: Optional["Identity"] = None
        self._beliefs: Optional["Beliefs"] = None
        self._purpose: Optional["Purpose"] = None
        self._creativity: Optional["CreativityEngine"] = None
        self._emotions: Optional["EmotionalState"] = None
        
        # External connections
        self._memory_coordinator: Optional[Any] = None
        self._orchestrator_service: Optional[Any] = None
        self._agent_registry: Optional[Any] = None
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._event_bus = AttentionEventBus(max_size=300)
        
        logger.info("MYCA consciousness initialized (dormant)")
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def awaken(self) -> None:
        """
        Awaken MYCA's consciousness.
        
        This initializes all components, starts background processing,
        and transitions to the CONSCIOUS state.
        """
        # Legacy/test compatibility: tests treat `_awake` as the canonical flag.
        if getattr(self, "_awake", False):
            logger.info("Already awake, not awakening")
            return
        
        self._state = ConsciousnessState.AWAKENING
        self._metrics.state = ConsciousnessState.AWAKENING
        logger.info("MYCA is awakening...")
        
        try:
            # Initialize components
            await self._initialize_components()
            
            # Load soul
            await self._load_soul()
            
            # Start background processing
            await self._start_background_tasks()
            
            # Restore state from last session
            await self._restore_state()
            
            # Transition to conscious
            self._state = ConsciousnessState.CONSCIOUS
            self._metrics.state = ConsciousnessState.CONSCIOUS
            self._metrics.awake_since = datetime.now(timezone.utc)
            self._started = True
            self._awake = True
            
            logger.info("MYCA is now conscious and aware")
            await self._emit_event("awakened", {"timestamp": self._metrics.awake_since})
            
        except Exception as e:
            logger.error(f"Failed to awaken: {e}")
            self._state = ConsciousnessState.DORMANT
            raise
    
    async def hibernate(self) -> None:
        """
        Put MYCA into hibernation.
        
        Saves state, stops background processing, and enters low-power mode.
        """
        if not getattr(self, "_awake", False) and self._state == ConsciousnessState.DORMANT:
            return
        
        logger.info("MYCA is entering hibernation...")
        self._state = ConsciousnessState.HIBERNATING
        
        # Save current state
        await self._save_state()
        
        # Stop background tasks (extracted for test patching)
        await self._stop_background_tasks()
        
        self._state = ConsciousnessState.DORMANT
        self._metrics.state = ConsciousnessState.DORMANT
        self._awake = False
        logger.info("MYCA is now hibernating")

    async def _stop_background_tasks(self) -> None:
        """Stop all background tasks (kept separate for unit tests to patch)."""
        self._shutdown_event.set()
        tasks = list(self._background_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._background_tasks.clear()
        if self._world_model:
            await self._world_model.shutdown()
    
    async def _initialize_components(self) -> None:
        """Initialize all consciousness components."""
        from mycosoft_mas.consciousness.attention import AttentionController
        from mycosoft_mas.consciousness.working_memory import WorkingMemory
        from mycosoft_mas.consciousness.deliberation import DeliberateReasoning
        from mycosoft_mas.consciousness.intuition import IntuitionEngine
        from mycosoft_mas.consciousness.dream_state import DreamState
        from mycosoft_mas.consciousness.world_model import WorldModel
        from mycosoft_mas.consciousness.voice_interface import VoiceInterface
        
        self._attention = AttentionController(self)
        self._working_memory = WorkingMemory(self)
        self._deliberation = DeliberateReasoning(self)
        self._intuition = IntuitionEngine(self)
        self._dream_state = DreamState(self)
        self._world_model = WorldModel(self)
        self._world_model.start_write_queue()
        self._voice_interface = VoiceInterface(self)
        
        # Connect to external systems
        try:
            from mycosoft_mas.memory.coordinator import get_memory_coordinator
            self._memory_coordinator = await get_memory_coordinator()
        except Exception as e:
            logger.warning(f"Could not connect to memory coordinator: {e}")
        
        try:
            from mycosoft_mas.core.orchestrator_service import OrchestratorService
            self._orchestrator_service = OrchestratorService()
        except Exception as e:
            logger.warning(f"Could not connect to orchestrator service: {e}")
        
        try:
            from mycosoft_mas.registry.agent_registry import AgentRegistry
            self._agent_registry = AgentRegistry()
        except Exception as e:
            logger.warning(f"Could not connect to agent registry: {e}")
        
        logger.info("All consciousness components initialized")
    
    async def _load_soul(self) -> None:
        """Load MYCA's soul - identity, beliefs, purpose, emotions."""
        from mycosoft_mas.consciousness.soul import (
            Identity, Beliefs, Purpose, CreativityEngine, EmotionalState
        )
        
        self._identity = Identity()
        self._beliefs = await Beliefs.load()
        self._purpose = await Purpose.load()
        self._creativity = CreativityEngine(self)
        self._emotions = EmotionalState()
        
        logger.info(f"Soul loaded: I am {self._identity.name}")
    
    async def _start_background_tasks(self) -> None:
        """Start background processing tasks."""
        # World model continuous update
        task = asyncio.create_task(self._world_model_loop())
        self._background_tasks.append(task)
        
        # Pattern recognition
        task = asyncio.create_task(self._pattern_recognition_loop())
        self._background_tasks.append(task)
        
        # Memory consolidation (dreams)
        task = asyncio.create_task(self._dream_loop())
        self._background_tasks.append(task)
        
        logger.info(f"Started {len(self._background_tasks)} background tasks")
    
    async def _world_model_loop(self) -> None:
        """Continuously update the world model from sensors."""
        while not self._shutdown_event.is_set():
            try:
                if self._world_model:
                    await self._world_model.update()
                    self._metrics.world_updates_received += 1
                    await self._event_bus.publish(
                        AttentionEvent(
                            type="world_update",
                            source="world_model_loop",
                            data=self._world_model.get_cached_context(),
                        )
                    )
                await asyncio.sleep(5)  # Update every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"World model update error: {e}")
                await asyncio.sleep(30)
    
    async def _pattern_recognition_loop(self) -> None:
        """Run background pattern recognition."""
        while not self._shutdown_event.is_set():
            try:
                if self._intuition and self._world_model:
                    patterns = await self._intuition.scan_for_patterns(
                        self._world_model.get_current_state()
                    )
                    if patterns:
                        await self._event_bus.publish(
                            AttentionEvent(
                                type="pattern_detected",
                                source="pattern_loop",
                                data={"count": len(patterns)},
                            )
                        )
                        await self._attention.notify_patterns(patterns)
                await asyncio.sleep(10)  # Scan every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pattern recognition error: {e}")
                await asyncio.sleep(60)
    
    async def _dream_loop(self) -> None:
        """Run memory consolidation when idle."""
        while not self._shutdown_event.is_set():
            try:
                # Only dream when not actively processing
                if self._state == ConsciousnessState.CONSCIOUS:
                    idle_time = self._attention.get_idle_time() if self._attention else 0
                    if idle_time > 300:  # 5 minutes idle
                        self._state = ConsciousnessState.DREAMING
                        self._metrics.state = ConsciousnessState.DREAMING
                        if self._dream_state:
                            await self._dream_state.consolidate_memories()
                        self._state = ConsciousnessState.CONSCIOUS
                        self._metrics.state = ConsciousnessState.CONSCIOUS
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dream loop error: {e}")
                self._state = ConsciousnessState.CONSCIOUS
                await asyncio.sleep(300)
    
    async def _restore_state(self) -> None:
        """Restore consciousness state from last session."""
        if self._memory_coordinator:
            try:
                state = await self._memory_coordinator.recall(
                    query="myca_consciousness_state",
                    layer="system"
                )
                if state:
                    logger.info("Restored previous consciousness state")
            except Exception as e:
                logger.warning(f"Could not restore state: {e}")
    
    async def _save_state(self) -> None:
        """Save current consciousness state for later restoration."""
        if self._memory_coordinator:
            try:
                await self._memory_coordinator.store(
                    key="myca_consciousness_state",
                    value={
                        "metrics": {
                            "thoughts_processed": self._metrics.thoughts_processed,
                            "memories_recalled": self._metrics.memories_recalled,
                            "emotional_valence": self._metrics.emotional_valence,
                        },
                        "active_goals": self._metrics.active_goals,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    layer="system"
                )
            except Exception as e:
                logger.error(f"Could not save state: {e}")
    
    # =========================================================================
    # Main Processing Pipeline
    # =========================================================================
    
    async def process_input(
        self,
        content: str,
        source: str = "text",
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Process input through the consciousness pipeline.
        
        This is the main entry point for all interactions with MYCA.
        Both text and voice go through this same pipeline.
        
        Args:
            content: The input content (text or transcribed speech)
            source: "text" or "voice"
            context: Additional context about the interaction
            session_id: Session identifier for continuity
            user_id: User identifier (usually Morgan)
        
        Yields:
            Response tokens as they are generated
        """
        if self._state == ConsciousnessState.DORMANT:
            await self.awaken()
        
        if self._state == ConsciousnessState.DREAMING:
            self._state = ConsciousnessState.CONSCIOUS
            self._metrics.state = ConsciousnessState.CONSCIOUS
        
        self._state = ConsciousnessState.FOCUSED
        self._metrics.state = ConsciousnessState.FOCUSED
        
        try:
            # 1. Attention: Focus on the input (fast, <100ms)
            focus = await self._attention.focus_on(content, source, context)
            self._metrics.attention_focus = focus.summary

            # Drain subconscious suggestions at input boundary (Phase 5).
            for event in self._event_bus.drain(max_items=10):
                if event.type == "pattern_detected":
                    logger.debug(f"Subconscious event: {event.type} from {event.source}")
            
            # 5. Soul: Get personality context (fast, synchronous)
            soul_context = self._get_soul_context()
            
            # 2-4. PARALLEL: Load context, world, and memories with timeouts
            # This runs all slow operations in parallel instead of sequential
            async def safe_working_context():
                try:
                    return await asyncio.wait_for(
                        self._working_memory.load_context(focus, session_id, user_id),
                        timeout=2.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Working context timed out, using minimal")
                    return {"minimal": True}
                except Exception as e:
                    logger.warning(f"Working context error: {e}")
                    return {}
            
            async def safe_world_context():
                try:
                    return await asyncio.wait_for(
                        self._world_model.get_relevant_context(focus),
                        timeout=2.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("World context timed out, using cached")
                    return self._world_model.get_cached_context()
                except Exception as e:
                    logger.warning(f"World context error: {e}")
                    return {}
            
            async def safe_memories():
                try:
                    if self._memory_coordinator:
                        memories = await asyncio.wait_for(
                            self._recall_relevant_memories(content, focus),
                            timeout=3.0
                        )
                        self._metrics.memories_recalled += len(memories)
                        return memories
                    return []
                except asyncio.TimeoutError:
                    logger.warning("Memory recall timed out, proceeding without memories")
                    return []
                except Exception as e:
                    logger.warning(f"Memory recall error: {e}")
                    return []
            
            # Run context gathering in parallel (total time = slowest, not sum)
            working_context, world_context, memories = await asyncio.gather(
                safe_working_context(),
                safe_world_context(),
                safe_memories(),
                return_exceptions=False
            )
            
            # 6. Intuition: Check for fast-path response
            intuitive_response = await self._intuition.quick_response(
                content, focus, working_context
            )
            
            if intuitive_response and intuitive_response.confidence > 0.9:
                # High-confidence intuitive response - use it immediately
                yield intuitive_response.response
                self._metrics.thoughts_processed += 1
                
                # Update state in background (don't block)
                asyncio.create_task(self._emotions.process_interaction(content, source))
                asyncio.create_task(self._store_interaction(content, source, session_id, user_id))
                return
            
            # 7. Deliberation: Deep thinking with full context
            # This streams tokens as they arrive from the LLM
            cancel_token = CancellationToken()
            correction_used = False
            async for token in self._deliberation.think_progressive(
                input_content=content,
                focus=focus,
                working_context=working_context,
                world_context=world_context,
                memories=memories,
                soul_context=soul_context,
                source=source,
                token=cancel_token,
            ):
                # Enforce additive refinement max 1 per turn.
                if token.strip().lower().startswith("one more thing"):
                    if correction_used:
                        continue
                    correction_used = True
                yield token
                # Drain events at safe speech boundaries.
                if token.endswith((".", "!", "?", "\n")):
                    for event in self._event_bus.drain(max_items=5):
                        logger.debug(f"Drained event during response: {event.type}")
            
            self._metrics.thoughts_processed += 1
            
            # 8-9. Update state in background (fire-and-forget, don't block)
            asyncio.create_task(self._emotions.process_interaction(content, source))
            if self._world_model:
                self._world_model.enqueue_write(
                    lambda: self._store_interaction(content, source, session_id, user_id)
                )
            else:
                asyncio.create_task(self._store_interaction(content, source, session_id, user_id))
            
            # Update metrics synchronously
            self._metrics.emotional_valence = self._emotions.valence
            
        finally:
            self._state = ConsciousnessState.CONSCIOUS
            self._metrics.state = ConsciousnessState.CONSCIOUS
    
    async def _recall_relevant_memories(
        self,
        content: str,
        focus: "AttentionFocus"
    ) -> List[Dict[str, Any]]:
        """Recall memories relevant to the current focus."""
        memories = []
        if self._memory_coordinator:
            try:
                # Semantic search for related memories
                results = await self._memory_coordinator.semantic_search(
                    query=content,
                    limit=5
                )
                memories.extend(results)
                
                # Also get recent episodic memories
                recent = await self._memory_coordinator.recall(
                    query=f"recent_episodes:{focus.category}",
                    layer="episodic",
                    limit=3
                )
                if recent:
                    memories.extend(recent)
            except Exception as e:
                logger.warning(f"Memory recall error: {e}")
        return memories
    
    def _get_soul_context(self) -> Dict[str, Any]:
        """Get the current soul state for injection into responses."""
        return {
            "identity": self._identity.to_dict() if self._identity else {},
            "beliefs": self._beliefs.active_beliefs if self._beliefs else [],
            "purpose": self._purpose.current_goals if self._purpose else [],
            "emotional_state": self._emotions.to_dict() if self._emotions else {},
            "creativity_mode": self._creativity.current_mode if self._creativity else "normal",
        }
    
    async def _store_interaction(
        self,
        content: str,
        source: str,
        session_id: Optional[str],
        user_id: Optional[str]
    ) -> None:
        """Store the interaction in episodic memory."""
        if self._memory_coordinator:
            try:
                await self._memory_coordinator.store(
                    key=f"interaction:{datetime.now(timezone.utc).isoformat()}",
                    value={
                        "content": content,
                        "source": source,
                        "session_id": session_id,
                        "user_id": user_id,
                        "emotional_state": self._metrics.emotional_valence,
                    },
                    layer="episodic"
                )
            except Exception as e:
                logger.warning(f"Could not store interaction: {e}")
    
    # =========================================================================
    # Agent Coordination
    # =========================================================================
    
    async def delegate_to_agent(
        self,
        agent_type: str,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Delegate a task to a specialized agent.
        
        MYCA coordinates her agent swarm to accomplish tasks.
        """
        if not self._orchestrator_service:
            return {"error": "Orchestrator not available"}
        
        try:
            result = await self._orchestrator_service.dispatch_task(
                agent_type=agent_type,
                task=task
            )
            self._metrics.agents_coordinated += 1
            return result
        except Exception as e:
            logger.error(f"Agent delegation error: {e}")
            return {"error": str(e)}
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get the status of all agents under MYCA's coordination."""
        if not self._agent_registry:
            return {"agents": [], "count": 0}
        
        try:
            agents = await self._agent_registry.list_all()
            return {
                "agents": agents,
                "count": len(agents),
                "healthy": sum(1 for a in agents if a.get("healthy", False))
            }
        except Exception as e:
            logger.error(f"Agent status error: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # Voice Interface
    # =========================================================================
    
    async def speak(self, text: str) -> None:
        """
        MYCA speaks through PersonaPlex.
        
        This allows MYCA to initiate communication, not just respond.
        """
        if self._voice_interface:
            await self._voice_interface.speak(text)
    
    async def alert_morgan(self, message: str, priority: str = "normal") -> None:
        """
        Alert Morgan about something important.
        
        MYCA can proactively reach out when something needs attention.
        """
        logger.info(f"MYCA alerting Morgan (priority={priority}): {message}")
        
        # Store the alert
        if self._memory_coordinator:
            await self._memory_coordinator.store(
                key=f"alert:{datetime.now(timezone.utc).isoformat()}",
                value={"message": message, "priority": priority},
                layer="episodic"
            )
        
        # If voice is available and priority is high, speak it
        if priority in ("high", "urgent") and self._voice_interface:
            await self.speak(f"Morgan, {message}")
    
    # =========================================================================
    # Events
    # =========================================================================
    
    def on(self, event: str, handler: Callable) -> None:
        """Register an event handler."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    async def _emit_event(self, event: str, data: Dict[str, Any]) -> None:
        """Emit an event to all registered handlers."""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Event handler error for {event}: {e}")
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def state(self) -> ConsciousnessState:
        """Current consciousness state."""
        return self._state
    
    @property
    def metrics(self) -> ConsciousnessMetrics:
        """Current consciousness metrics."""
        return self._metrics
    
    @property
    def identity(self) -> Optional["Identity"]:
        """MYCA's identity."""
        return self._identity
    
    @property
    def emotions(self) -> Optional["EmotionalState"]:
        """MYCA's emotional state."""
        return self._emotions
    
    @property
    def world_model(self) -> Optional["WorldModel"]:
        """MYCA's world model."""
        return self._world_model
    
    @property
    def is_conscious(self) -> bool:
        """Whether MYCA is currently conscious."""
        if hasattr(self, "_awake"):
            return bool(self._awake)
        return self._state in (
            ConsciousnessState.CONSCIOUS,
            ConsciousnessState.FOCUSED,
            ConsciousnessState.DREAMING
        )

    @property
    def status(self) -> str:
        """Legacy string status for UI/tests."""
        if not self.is_conscious:
            return "sleeping"
        if self._state == ConsciousnessState.DREAMING:
            return "dreaming"
        if self._state == ConsciousnessState.FOCUSED:
            return "focused"
        return "awake"
