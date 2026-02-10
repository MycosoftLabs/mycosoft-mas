"""
MYCA Attention Controller

Manages what MYCA focuses on. The attention controller determines:
- What inputs get conscious processing
- Priority of different information streams
- When to interrupt current focus for something more important
- How long to maintain focus on a topic

This is the "spotlight" of consciousness.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness

logger = logging.getLogger(__name__)


class AttentionPriority(Enum):
    """Priority levels for attention focus."""
    CRITICAL = 5    # Security threats, system failures
    HIGH = 4        # Direct requests from Morgan, important alerts
    NORMAL = 3      # Standard conversation
    LOW = 2         # Background updates
    AMBIENT = 1     # Passive monitoring


class AttentionCategory(Enum):
    """Categories of attention focus."""
    CONVERSATION = "conversation"      # Active dialogue
    AGENT_TASK = "agent_task"         # Managing agent work
    WORLD_EVENT = "world_event"       # CREP/Earth2 event
    SYSTEM = "system"                 # System health/status
    CREATIVE = "creative"             # Idea generation
    MEMORY = "memory"                 # Memory recall/consolidation
    PLANNING = "planning"             # Goal/task planning


@dataclass
class AttentionFocus:
    """Represents what MYCA is currently focusing on."""
    id: str
    content: str
    source: str  # "text", "voice", "pattern", "alert", "internal"
    category: AttentionCategory
    priority: AttentionPriority
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Dict[str, Any] = field(default_factory=dict)
    related_entities: List[str] = field(default_factory=list)
    
    @property
    def summary(self) -> str:
        """Brief summary for logging/metrics."""
        return f"{self.category.value}:{self.source}:{self.content[:50]}"
    
    @property
    def age_seconds(self) -> float:
        """How long this focus has been active."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()


@dataclass
class PatternAlert:
    """Alert from pattern recognition about something noteworthy."""
    pattern_type: str
    description: str
    confidence: float
    priority: AttentionPriority
    data: Dict[str, Any] = field(default_factory=dict)


class AttentionController:
    """
    Controls MYCA's attention - the spotlight of consciousness.
    
    The attention controller:
    1. Receives all inputs (text, voice, patterns, alerts)
    2. Determines priority and categorization
    3. Manages the focus stack
    4. Decides when to interrupt or switch focus
    5. Tracks what MYCA is paying attention to
    """
    
    # Maximum items in attention history
    MAX_HISTORY = 100
    
    # Time thresholds (seconds)
    IDLE_THRESHOLD = 30  # Consider idle after 30s without input
    STALE_FOCUS_THRESHOLD = 300  # Focus considered stale after 5 minutes
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        self._consciousness = consciousness
        self._current_focus: Optional[AttentionFocus] = None
        self._focus_stack: List[AttentionFocus] = []
        self._history: List[AttentionFocus] = []
        self._last_input_time: datetime = datetime.now(timezone.utc)
        self._pattern_queue: asyncio.Queue = asyncio.Queue()
        self._focus_lock = asyncio.Lock()
    
    async def focus_on(
        self,
        content: str,
        source: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AttentionFocus:
        """
        Focus attention on new input.
        
        Args:
            content: The content to focus on
            source: Source of input ("text", "voice", etc.)
            context: Additional context
        
        Returns:
            The new AttentionFocus object
        """
        async with self._focus_lock:
            # Categorize the input
            category = self._categorize_input(content, source, context)
            
            # Determine priority
            priority = self._determine_priority(content, source, context, category)
            
            # Extract related entities
            entities = self._extract_entities(content)
            
            # Create the focus
            focus = AttentionFocus(
                id=f"focus_{datetime.now(timezone.utc).timestamp()}",
                content=content,
                source=source,
                category=category,
                priority=priority,
                context=context or {},
                related_entities=entities,
            )
            
            # Should we interrupt current focus?
            if self._current_focus and priority.value > self._current_focus.priority.value:
                # Push current to stack
                self._focus_stack.append(self._current_focus)
                logger.info(f"Interrupting focus for higher priority: {focus.summary}")
            
            # Set new focus
            if self._current_focus:
                self._history.append(self._current_focus)
                self._trim_history()
            
            self._current_focus = focus
            self._last_input_time = datetime.now(timezone.utc)
            
            logger.debug(f"Attention focused on: {focus.summary}")
            return focus
    
    def _categorize_input(
        self,
        content: str,
        source: str,
        context: Optional[Dict[str, Any]]
    ) -> AttentionCategory:
        """Categorize the input to determine how to process it."""
        content_lower = content.lower()
        
        # Check for specific patterns
        if any(word in content_lower for word in ["agent", "delegate", "ask", "tell"]):
            return AttentionCategory.AGENT_TASK
        
        if any(word in content_lower for word in ["weather", "flight", "ship", "satellite"]):
            return AttentionCategory.WORLD_EVENT
        
        if any(word in content_lower for word in ["system", "health", "status", "server"]):
            return AttentionCategory.SYSTEM
        
        if any(word in content_lower for word in ["idea", "create", "design", "imagine"]):
            return AttentionCategory.CREATIVE
        
        if any(word in content_lower for word in ["remember", "recall", "memory", "last time"]):
            return AttentionCategory.MEMORY
        
        if any(word in content_lower for word in ["plan", "goal", "schedule", "todo"]):
            return AttentionCategory.PLANNING
        
        # Default to conversation
        return AttentionCategory.CONVERSATION
    
    def _determine_priority(
        self,
        content: str,
        source: str,
        context: Optional[Dict[str, Any]],
        category: AttentionCategory
    ) -> AttentionPriority:
        """Determine the priority of this input."""
        content_lower = content.lower()
        
        # Critical keywords
        if any(word in content_lower for word in ["emergency", "urgent", "critical", "security"]):
            return AttentionPriority.CRITICAL
        
        # High priority for direct requests from Morgan
        if context and context.get("user_id") == "morgan":
            return AttentionPriority.HIGH
        
        # Voice input is usually more immediate
        if source == "voice":
            return AttentionPriority.HIGH
        
        # System category gets elevated priority
        if category == AttentionCategory.SYSTEM:
            return AttentionPriority.HIGH
        
        # Alerts from patterns are at least normal
        if source == "pattern":
            return AttentionPriority.NORMAL
        
        return AttentionPriority.NORMAL
    
    def _extract_entities(self, content: str) -> List[str]:
        """Extract named entities from content."""
        entities = []
        content_lower = content.lower()
        
        # Known entity patterns
        known_entities = {
            "morgan": "person:morgan",
            "myca": "self:myca",
            "mycosoft": "org:mycosoft",
            "mindex": "system:mindex",
            "natureos": "system:natureos",
            "earth2": "system:earth2",
            "crep": "system:crep",
            "mycobrain": "device:mycobrain",
        }
        
        for name, entity_id in known_entities.items():
            if name in content_lower:
                entities.append(entity_id)
        
        return entities
    
    async def notify_patterns(self, patterns: List[PatternAlert]) -> None:
        """
        Receive pattern alerts from subconscious processing.
        
        High-priority patterns may interrupt current focus.
        """
        for pattern in patterns:
            await self._pattern_queue.put(pattern)
            
            # Check if this should interrupt
            if pattern.priority.value >= AttentionPriority.HIGH.value:
                logger.info(f"Pattern alert requires attention: {pattern.description}")
                await self.focus_on(
                    content=pattern.description,
                    source="pattern",
                    context={"pattern_type": pattern.pattern_type, "data": pattern.data}
                )
    
    async def pop_focus(self) -> Optional[AttentionFocus]:
        """Return to previous focus from the stack."""
        async with self._focus_lock:
            if self._focus_stack:
                if self._current_focus:
                    self._history.append(self._current_focus)
                self._current_focus = self._focus_stack.pop()
                logger.debug(f"Returned to previous focus: {self._current_focus.summary}")
                return self._current_focus
        return None
    
    def get_current_focus(self) -> Optional[AttentionFocus]:
        """Get the current attention focus."""
        return self._current_focus
    
    def get_idle_time(self) -> float:
        """Get seconds since last input."""
        return (datetime.now(timezone.utc) - self._last_input_time).total_seconds()
    
    def is_idle(self) -> bool:
        """Check if attention is idle (no recent input)."""
        return self.get_idle_time() > self.IDLE_THRESHOLD
    
    def get_focus_history(self, limit: int = 10) -> List[AttentionFocus]:
        """Get recent focus history."""
        return self._history[-limit:]
    
    def get_context_for_entity(self, entity_id: str) -> List[AttentionFocus]:
        """Get all recent focuses related to an entity."""
        return [f for f in self._history if entity_id in f.related_entities]
    
    def _trim_history(self) -> None:
        """Keep history within limits."""
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]
    
    async def get_attention_summary(self) -> Dict[str, Any]:
        """Get a summary of current attention state."""
        return {
            "current_focus": self._current_focus.summary if self._current_focus else None,
            "focus_stack_depth": len(self._focus_stack),
            "idle_seconds": self.get_idle_time(),
            "is_idle": self.is_idle(),
            "recent_categories": [f.category.value for f in self._history[-5:]],
            "pattern_queue_size": self._pattern_queue.qsize(),
        }
