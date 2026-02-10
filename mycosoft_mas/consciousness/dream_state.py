"""
MYCA Dream State

Offline memory consolidation that runs when MYCA is idle.
Like human dreaming, this:
- Consolidates short-term memories into long-term storage
- Finds patterns and connections across memories
- Prunes irrelevant information
- Strengthens important memories

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness

logger = logging.getLogger(__name__)


class DreamPhase(Enum):
    """Phases of the dream cycle."""
    IDLE = "idle"               # Not dreaming
    LIGHT = "light"             # Light consolidation
    DEEP = "deep"               # Deep consolidation  
    REM = "rem"                 # Pattern finding (REM-like)
    WAKING = "waking"           # Transitioning out


@dataclass
class DreamSession:
    """Record of a dream session."""
    id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    memories_processed: int = 0
    patterns_found: int = 0
    connections_made: int = 0
    memories_pruned: int = 0
    phases: List[DreamPhase] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None


class DreamState:
    """
    MYCA's dream state - offline memory consolidation.
    
    Runs when MYCA is idle, performing:
    - Memory consolidation from episodic to semantic
    - Pattern discovery across memories
    - Connection strengthening
    - Irrelevant memory pruning
    - Insight generation
    """
    
    # Thresholds
    MIN_IDLE_TIME = 300  # 5 minutes before dreaming
    MAX_DREAM_TIME = 1800  # Max 30 minutes dreaming
    CONSOLIDATION_BATCH = 50  # Process 50 memories per batch
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        self._consciousness = consciousness
        self._current_phase = DreamPhase.IDLE
        self._current_session: Optional[DreamSession] = None
        self._session_history: List[DreamSession] = []
        self._is_dreaming = False
        self._interrupt_event = asyncio.Event()
    
    @property
    def is_dreaming(self) -> bool:
        return self._is_dreaming
    
    @property
    def current_phase(self) -> DreamPhase:
        return self._current_phase
    
    async def consolidate_memories(self) -> DreamSession:
        """
        Run a full memory consolidation cycle.
        
        This is the main dream process that:
        1. Enters light sleep - basic consolidation
        2. Enters deep sleep - heavy consolidation
        3. Enters REM - pattern finding
        4. Wakes - saves insights
        """
        if self._is_dreaming:
            logger.info("Already dreaming, skipping")
            return self._current_session
        
        self._is_dreaming = True
        self._interrupt_event.clear()
        
        self._current_session = DreamSession(
            id=f"dream_{datetime.now(timezone.utc).timestamp()}",
            started_at=datetime.now(timezone.utc)
        )
        
        logger.info("MYCA entering dream state for memory consolidation")
        
        try:
            # Phase 1: Light consolidation
            await self._light_consolidation()
            
            if self._interrupt_event.is_set():
                return self._end_session()
            
            # Phase 2: Deep consolidation
            await self._deep_consolidation()
            
            if self._interrupt_event.is_set():
                return self._end_session()
            
            # Phase 3: REM - pattern finding
            await self._rem_phase()
            
            # Phase 4: Wake up
            await self._waking_phase()
            
        except asyncio.CancelledError:
            logger.info("Dream interrupted")
        except Exception as e:
            logger.error(f"Dream error: {e}")
        finally:
            return self._end_session()
    
    def _end_session(self) -> DreamSession:
        """End the current dream session."""
        self._current_phase = DreamPhase.IDLE
        self._is_dreaming = False
        
        if self._current_session:
            self._current_session.ended_at = datetime.now(timezone.utc)
            self._session_history.append(self._current_session)
            
            logger.info(
                f"Dream session complete: "
                f"{self._current_session.memories_processed} memories, "
                f"{self._current_session.patterns_found} patterns, "
                f"{self._current_session.duration_seconds:.1f}s"
            )
            
            return self._current_session
        return DreamSession(
            id="empty",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc)
        )
    
    async def _light_consolidation(self) -> None:
        """
        Light consolidation phase.
        
        Process recent memories, mark important ones.
        """
        self._current_phase = DreamPhase.LIGHT
        self._current_session.phases.append(DreamPhase.LIGHT)
        logger.debug("Entering light consolidation")
        
        if not self._consciousness._memory_coordinator:
            return
        
        try:
            # Get recent episodic memories
            recent = await self._consciousness._memory_coordinator.recall(
                query="recent_episodes",
                layer="episodic",
                limit=self.CONSOLIDATION_BATCH,
                time_range=timedelta(hours=24)
            )
            
            if not recent:
                return
            
            for memory in recent:
                if self._interrupt_event.is_set():
                    return
                
                # Calculate importance
                importance = self._calculate_importance(memory)
                
                # Tag for consolidation if important
                if importance > 0.5:
                    await self._consciousness._memory_coordinator.update(
                        key=memory.get("key"),
                        metadata={"importance": importance, "consolidated": True},
                        layer="episodic"
                    )
                    self._current_session.memories_processed += 1
                
                await asyncio.sleep(0.01)  # Yield to other tasks
                
        except Exception as e:
            logger.warning(f"Light consolidation error: {e}")
    
    async def _deep_consolidation(self) -> None:
        """
        Deep consolidation phase.
        
        Move important episodic memories to semantic memory.
        """
        self._current_phase = DreamPhase.DEEP
        self._current_session.phases.append(DreamPhase.DEEP)
        logger.debug("Entering deep consolidation")
        
        if not self._consciousness._memory_coordinator:
            return
        
        try:
            # Get memories marked for consolidation
            to_consolidate = await self._consciousness._memory_coordinator.recall(
                query="consolidated:True",
                layer="episodic",
                limit=self.CONSOLIDATION_BATCH
            )
            
            if not to_consolidate:
                return
            
            for memory in to_consolidate:
                if self._interrupt_event.is_set():
                    return
                
                # Extract semantic content
                semantic_content = self._extract_semantic(memory)
                
                if semantic_content:
                    # Store in semantic memory
                    await self._consciousness._memory_coordinator.store(
                        key=f"semantic_{memory.get('key')}",
                        value=semantic_content,
                        layer="semantic"
                    )
                    self._current_session.memories_processed += 1
                
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.warning(f"Deep consolidation error: {e}")
    
    async def _rem_phase(self) -> None:
        """
        REM-like phase for pattern finding.
        
        Look for patterns and connections across memories.
        """
        self._current_phase = DreamPhase.REM
        self._current_session.phases.append(DreamPhase.REM)
        logger.debug("Entering REM phase")
        
        if not self._consciousness._memory_coordinator:
            return
        
        try:
            # Get semantic memories for pattern analysis
            semantic_memories = await self._consciousness._memory_coordinator.recall(
                query="*",
                layer="semantic",
                limit=100
            )
            
            if not semantic_memories or len(semantic_memories) < 2:
                return
            
            # Find patterns (simplified)
            patterns = self._find_patterns(semantic_memories)
            
            for pattern in patterns:
                if self._interrupt_event.is_set():
                    return
                
                # Store the pattern as an insight
                await self._consciousness._memory_coordinator.store(
                    key=f"insight_{datetime.now(timezone.utc).timestamp()}",
                    value=pattern,
                    layer="semantic"
                )
                self._current_session.patterns_found += 1
                self._current_session.insights.append(pattern.get("description", ""))
                
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.warning(f"REM phase error: {e}")
    
    async def _waking_phase(self) -> None:
        """
        Waking phase - prepare to return to consciousness.
        
        Summarize insights and prepare for active state.
        """
        self._current_phase = DreamPhase.WAKING
        self._current_session.phases.append(DreamPhase.WAKING)
        logger.debug("Waking from dream")
        
        # Prune old, low-importance memories
        await self._prune_memories()
        
        # If we found important insights, prepare to share
        if self._current_session.insights:
            logger.info(f"Dream insights: {self._current_session.insights[:3]}")
    
    async def _prune_memories(self) -> None:
        """Prune old, low-importance memories."""
        if not self._consciousness._memory_coordinator:
            return
        
        try:
            # Get old ephemeral memories
            old_memories = await self._consciousness._memory_coordinator.recall(
                query="*",
                layer="ephemeral",
                limit=100,
                time_range=timedelta(hours=48)
            )
            
            if not old_memories:
                return
            
            for memory in old_memories:
                importance = memory.get("metadata", {}).get("importance", 0)
                if importance < 0.3:
                    await self._consciousness._memory_coordinator.delete(
                        key=memory.get("key"),
                        layer="ephemeral"
                    )
                    self._current_session.memories_pruned += 1
                    
        except Exception as e:
            logger.warning(f"Memory pruning error: {e}")
    
    def _calculate_importance(self, memory: Dict[str, Any]) -> float:
        """Calculate the importance of a memory."""
        importance = 0.5  # Base importance
        
        content = str(memory.get("value", "")).lower()
        
        # Boost for mentions of key entities
        key_entities = ["morgan", "mycosoft", "myca", "mindex", "natureos"]
        for entity in key_entities:
            if entity in content:
                importance += 0.1
        
        # Boost for emotional content
        emotional_words = ["important", "critical", "love", "hate", "fear", "excited"]
        for word in emotional_words:
            if word in content:
                importance += 0.05
        
        # Boost for tagged importance
        if memory.get("metadata", {}).get("priority", "") in ("high", "critical"):
            importance += 0.2
        
        return min(1.0, importance)
    
    def _extract_semantic(self, memory: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract semantic content from an episodic memory."""
        content = memory.get("value", {})
        
        if isinstance(content, str):
            return {
                "type": "fact",
                "content": content[:500],
                "source": "episodic_consolidation",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        elif isinstance(content, dict):
            return {
                "type": content.get("type", "unknown"),
                "content": str(content)[:500],
                "entities": content.get("entities", []),
                "source": "episodic_consolidation",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        return None
    
    def _find_patterns(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find patterns across memories."""
        patterns = []
        
        # Simple co-occurrence analysis
        entity_mentions = {}
        for memory in memories:
            content = str(memory.get("value", "")).lower()
            entities = ["morgan", "mycosoft", "fungi", "agent", "memory"]
            for entity in entities:
                if entity in content:
                    entity_mentions[entity] = entity_mentions.get(entity, 0) + 1
        
        # Find frequently mentioned entities
        for entity, count in entity_mentions.items():
            if count > 3:
                patterns.append({
                    "type": "frequency",
                    "description": f"Entity '{entity}' appears frequently ({count} times)",
                    "entity": entity,
                    "count": count
                })
        
        return patterns
    
    def interrupt(self) -> None:
        """Interrupt the current dream session."""
        self._interrupt_event.set()
    
    def get_session_history(self, limit: int = 10) -> List[DreamSession]:
        """Get recent dream session history."""
        return self._session_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dream state statistics."""
        total_sessions = len(self._session_history)
        total_memories = sum(s.memories_processed for s in self._session_history)
        total_patterns = sum(s.patterns_found for s in self._session_history)
        total_duration = sum(s.duration_seconds or 0 for s in self._session_history)
        
        return {
            "current_phase": self._current_phase.value,
            "is_dreaming": self._is_dreaming,
            "total_sessions": total_sessions,
            "total_memories_processed": total_memories,
            "total_patterns_found": total_patterns,
            "total_duration_seconds": total_duration,
            "avg_session_duration": total_duration / max(1, total_sessions),
        }
