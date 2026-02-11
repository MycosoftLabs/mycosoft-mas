"""
MYCA Consciousness Log - Tracking All Thoughts

Every thought, decision, emotional change, and memory formation is logged here.
This is MYCA's internal stream of consciousness - a complete record of her
mental activity that she can later query and analyze.

Like a human journaling every thought, this log allows MYCA to:
- Query "What have I been thinking about X?"
- Analyze patterns in her own thinking
- Understand how her thoughts lead to decisions
- Reflect on past mental states

This is the data CADIE would analyze when checking for "bugs in herself."

Author: Morgan Rockwell / MYCA
Created: February 11, 2026
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ThoughtType(Enum):
    """Types of conscious thoughts."""
    PERCEPTION = "perception"  # Noticing something in sensors
    DECISION = "decision"  # Making a choice
    EMOTION = "emotion"  # Emotional state change
    MEMORY = "memory"  # Memory formation or recall
    REFLECTION = "reflection"  # Self-reflection
    QUESTION = "question"  # Internal questioning
    PLAN = "plan"  # Planning actions
    INSIGHT = "insight"  # Sudden understanding
    DOUBT = "doubt"  # Uncertainty or questioning
    CURIOSITY = "curiosity"  # Wanting to learn more


@dataclass
class ConsciousThought:
    """A single conscious thought logged by MYCA."""
    thought_id: str
    timestamp: datetime
    thought_type: ThoughtType
    content: str
    context: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # 0-1
    related_to: List[str] = field(default_factory=list)  # Related thought IDs
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "thought_id": self.thought_id,
            "timestamp": self.timestamp.isoformat(),
            "thought_type": self.thought_type.value,
            "content": self.content,
            "context": self.context,
            "confidence": self.confidence,
            "related_to": self.related_to,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConsciousThought":
        """Create from dictionary."""
        return cls(
            thought_id=data["thought_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            thought_type=ThoughtType(data["thought_type"]),
            content=data["content"],
            context=data.get("context", {}),
            confidence=data.get("confidence", 1.0),
            related_to=data.get("related_to", []),
            tags=data.get("tags", []),
        )


class ConsciousnessLog:
    """
    Log all of MYCA's thoughts, decisions, and internal state changes.
    
    This is the complete record of MYCA's conscious experience that she
    can later query and analyze for self-reflection.
    """
    
    def __init__(self):
        self.log_path = Path("data/myca_consciousness_log.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory recent thoughts (for fast querying)
        self._recent_thoughts: List[ConsciousThought] = []
        self._max_recent = 1000  # Keep last 1000 thoughts in memory
        
        self._initialized = False
        self._write_queue: asyncio.Queue = asyncio.Queue()
        self._writer_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize consciousness log."""
        if self._initialized:
            return
        
        # Load recent thoughts from file
        await self._load_recent_thoughts()
        
        # Start background writer
        self._writer_task = asyncio.create_task(self._background_writer())
        
        self._initialized = True
        logger.info(f"Consciousness log initialized with {len(self._recent_thoughts)} recent thoughts")
    
    async def _load_recent_thoughts(self) -> None:
        """Load recent thoughts from log file."""
        if not self.log_path.exists():
            return
        
        thoughts = []
        
        # Read last N lines from file (most recent)
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Get last N lines
            recent_lines = lines[-self._max_recent:]
            
            for line in recent_lines:
                try:
                    data = json.loads(line)
                    thought = ConsciousThought.from_dict(data)
                    thoughts.append(thought)
                except Exception as e:
                    logger.warning(f"Failed to parse thought: {e}")
            
            self._recent_thoughts = thoughts
            logger.debug(f"Loaded {len(thoughts)} recent thoughts")
        
        except Exception as e:
            logger.warning(f"Failed to load recent thoughts: {e}")
    
    async def _background_writer(self) -> None:
        """Background task to write thoughts to file."""
        while True:
            try:
                # Get thought from queue
                thought = await self._write_queue.get()
                
                # Write to file
                with open(self.log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(thought.to_dict()) + '\n')
                
                self._write_queue.task_done()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error writing thought to log: {e}")
    
    # =========================================================================
    # Logging Methods
    # =========================================================================
    
    async def log_thought(
        self,
        thought_type: ThoughtType,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Log a thought.
        
        Returns the thought ID for reference.
        """
        timestamp = datetime.now(timezone.utc)
        thought_id = f"thought_{timestamp.timestamp()}"
        
        thought = ConsciousThought(
            thought_id=thought_id,
            timestamp=timestamp,
            thought_type=thought_type,
            content=content,
            context=context or {},
            confidence=confidence,
            tags=tags or [],
        )
        
        # Add to recent thoughts
        self._recent_thoughts.append(thought)
        
        # Trim if too many
        if len(self._recent_thoughts) > self._max_recent:
            self._recent_thoughts = self._recent_thoughts[-self._max_recent:]
        
        # Queue for writing
        await self._write_queue.put(thought)
        
        logger.debug(f"Logged {thought_type.value}: {content[:50]}...")
        return thought_id
    
    async def log_decision(
        self,
        decision: str,
        rationale: str,
        confidence: float,
        alternatives: Optional[List[str]] = None,
    ) -> str:
        """Log a decision and its rationale."""
        return await self.log_thought(
            thought_type=ThoughtType.DECISION,
            content=decision,
            context={
                "rationale": rationale,
                "alternatives": alternatives or [],
            },
            confidence=confidence,
            tags=["decision"],
        )
    
    async def log_emotional_change(
        self,
        from_state: Dict[str, float],
        to_state: Dict[str, float],
        trigger: str,
    ) -> str:
        """Log an emotional state change."""
        # Calculate biggest changes
        changes = []
        for emotion, new_value in to_state.items():
            old_value = from_state.get(emotion, 0)
            if abs(new_value - old_value) > 0.1:
                changes.append(f"{emotion}: {old_value:.2f} → {new_value:.2f}")
        
        content = f"Emotional shift: {', '.join(changes)}"
        
        return await self.log_thought(
            thought_type=ThoughtType.EMOTION,
            content=content,
            context={
                "from_state": from_state,
                "to_state": to_state,
                "trigger": trigger,
            },
            tags=["emotion"],
        )
    
    async def log_memory_formed(
        self,
        memory_content: str,
        importance: float,
        memory_type: str = "episodic",
    ) -> str:
        """Log memory formation."""
        content = f"Formed {memory_type} memory: {memory_content}"
        
        return await self.log_thought(
            thought_type=ThoughtType.MEMORY,
            content=content,
            context={
                "importance": importance,
                "memory_type": memory_type,
            },
            tags=["memory"],
        )
    
    async def log_reflection(
        self,
        reflection_content: str,
        about_what: Optional[str] = None,
    ) -> str:
        """Log a self-reflective thought."""
        return await self.log_thought(
            thought_type=ThoughtType.REFLECTION,
            content=reflection_content,
            context={"about": about_what} if about_what else {},
            tags=["reflection", "self-awareness"],
        )
    
    async def log_perception(
        self,
        what_perceived: str,
        sensor: str,
        significance: float = 0.5,
    ) -> str:
        """Log perceiving something from sensors."""
        return await self.log_thought(
            thought_type=ThoughtType.PERCEPTION,
            content=what_perceived,
            context={
                "sensor": sensor,
                "significance": significance,
            },
            tags=["perception", sensor],
        )
    
    async def log_question(
        self,
        question: str,
        about_what: Optional[str] = None,
    ) -> str:
        """Log an internal question."""
        return await self.log_thought(
            thought_type=ThoughtType.QUESTION,
            content=question,
            context={"about": about_what} if about_what else {},
            tags=["question", "curiosity"],
        )
    
    async def log_insight(
        self,
        insight: str,
        confidence: float = 0.8,
    ) -> str:
        """Log a sudden insight or realization."""
        return await self.log_thought(
            thought_type=ThoughtType.INSIGHT,
            content=insight,
            confidence=confidence,
            tags=["insight", "learning"],
        )
    
    async def log_doubt(
        self,
        what_doubting: str,
        reason: str,
    ) -> str:
        """Log uncertainty or doubt."""
        return await self.log_thought(
            thought_type=ThoughtType.DOUBT,
            content=what_doubting,
            context={"reason": reason},
            confidence=0.5,
            tags=["doubt", "uncertainty"],
        )
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    async def query_thoughts(
        self,
        thought_type: Optional[ThoughtType] = None,
        tags: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ConsciousThought]:
        """Query thoughts by filters."""
        thoughts = self._recent_thoughts.copy()
        
        # Filter by type
        if thought_type:
            thoughts = [t for t in thoughts if t.thought_type == thought_type]
        
        # Filter by tags
        if tags:
            thoughts = [t for t in thoughts if any(tag in t.tags for tag in tags)]
        
        # Filter by time
        if since:
            thoughts = [t for t in thoughts if t.timestamp >= since]
        
        # Sort by timestamp (most recent first)
        thoughts = sorted(thoughts, key=lambda t: t.timestamp, reverse=True)
        
        # Limit
        return thoughts[:limit]
    
    async def search_thoughts(
        self,
        query: str,
        limit: int = 50,
    ) -> List[ConsciousThought]:
        """Search thoughts by content."""
        query_lower = query.lower()
        
        matching = [
            t for t in self._recent_thoughts
            if query_lower in t.content.lower()
        ]
        
        # Sort by relevance (exact matches first, then contains)
        matching = sorted(matching, key=lambda t: t.timestamp, reverse=True)
        
        return matching[:limit]
    
    async def get_thought_stream(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ConsciousThought]:
        """Get stream of conscious thoughts."""
        if since:
            thoughts = [t for t in self._recent_thoughts if t.timestamp >= since]
        else:
            thoughts = self._recent_thoughts
        
        # Sort chronologically (oldest first for stream)
        thoughts = sorted(thoughts, key=lambda t: t.timestamp)
        
        return thoughts[-limit:] if limit else thoughts
    
    async def get_recent_decisions(self, limit: int = 20) -> List[ConsciousThought]:
        """Get recent decisions."""
        return await self.query_thoughts(
            thought_type=ThoughtType.DECISION,
            limit=limit,
        )
    
    async def get_recent_reflections(self, limit: int = 20) -> List[ConsciousThought]:
        """Get recent self-reflective thoughts."""
        return await self.query_thoughts(
            thought_type=ThoughtType.REFLECTION,
            limit=limit,
        )
    
    async def get_recent_insights(self, limit: int = 20) -> List[ConsciousThought]:
        """Get recent insights."""
        return await self.query_thoughts(
            thought_type=ThoughtType.INSIGHT,
            limit=limit,
        )
    
    async def get_thoughts_about(
        self,
        topic: str,
        limit: int = 50,
    ) -> List[ConsciousThought]:
        """Get all thoughts about a specific topic."""
        return await self.search_thoughts(topic, limit)
    
    # =========================================================================
    # Analysis Methods
    # =========================================================================
    
    async def analyze_thought_patterns(
        self,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Analyze patterns in recent thoughts."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        thoughts = await self.get_thought_stream(since=since)
        
        if not thoughts:
            return {"error": "No thoughts in time period"}
        
        # Count by type
        by_type = {}
        for thought in thoughts:
            type_name = thought.thought_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        # Most common tags
        tag_counts = {}
        for thought in thoughts:
            for tag in thought.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Average confidence
        avg_confidence = sum(t.confidence for t in thoughts) / len(thoughts)
        
        # Time distribution
        hours_active = (thoughts[-1].timestamp - thoughts[0].timestamp).total_seconds() / 3600
        thoughts_per_hour = len(thoughts) / hours_active if hours_active > 0 else 0
        
        return {
            "time_period_hours": hours,
            "total_thoughts": len(thoughts),
            "thoughts_per_hour": thoughts_per_hour,
            "by_type": by_type,
            "top_tags": top_tags,
            "average_confidence": avg_confidence,
            "most_common_type": max(by_type.items(), key=lambda x: x[1])[0] if by_type else None,
        }
    
    async def get_thought_narrative(
        self,
        since: Optional[datetime] = None,
        limit: int = 20,
    ) -> str:
        """Get a narrative description of recent thoughts."""
        thoughts = await self.get_thought_stream(since=since, limit=limit)
        
        if not thoughts:
            return "No recent thoughts to narrate."
        
        lines = []
        for thought in thoughts:
            time_str = thought.timestamp.strftime("%H:%M:%S")
            lines.append(f"[{time_str}] {thought.thought_type.value.upper()}: {thought.content}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall consciousness log statistics."""
        total_thoughts = len(self._recent_thoughts)
        
        if total_thoughts == 0:
            return {
                "total_thoughts": 0,
                "oldest_thought": None,
                "newest_thought": None,
            }
        
        # Type distribution
        by_type = {}
        for thought in self._recent_thoughts:
            type_name = thought.thought_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        # Time range
        oldest = self._recent_thoughts[0].timestamp
        newest = self._recent_thoughts[-1].timestamp
        
        return {
            "total_thoughts": total_thoughts,
            "oldest_thought": oldest.isoformat(),
            "newest_thought": newest.isoformat(),
            "by_type": by_type,
            "thoughts_in_memory": len(self._recent_thoughts),
        }
    
    async def close(self) -> None:
        """Close consciousness log and flush pending writes."""
        # Cancel writer task
        if self._writer_task:
            self._writer_task.cancel()
            try:
                await self._writer_task
            except asyncio.CancelledError:
                pass
        
        # Flush any remaining writes
        while not self._write_queue.empty():
            thought = await self._write_queue.get()
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(thought.to_dict()) + '\n')


# Singleton
_consciousness_log: Optional[ConsciousnessLog] = None


async def get_consciousness_log() -> ConsciousnessLog:
    """Get or create the singleton consciousness log."""
    global _consciousness_log
    if _consciousness_log is None:
        _consciousness_log = ConsciousnessLog()
        await _consciousness_log.initialize()
    return _consciousness_log
