"""
MYCA Working Memory

Working memory is the active context that MYCA holds "in mind" during processing.
Like human working memory, it has limited capacity (7±2 items) and represents
what MYCA is actively thinking about.

This integrates with the 6-layer memory system but provides the conscious
"workspace" for current thought.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass, field
from collections import OrderedDict

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness
    from mycosoft_mas.consciousness.attention import AttentionFocus

logger = logging.getLogger(__name__)


class ItemType(Enum):
    """Types of items in working memory."""
    INPUT = "input"           # Current input being processed
    CONTEXT = "context"       # Contextual information
    MEMORY = "memory"         # Recalled memory
    GOAL = "goal"             # Active goal
    ENTITY = "entity"         # Entity being discussed
    WORLD_STATE = "world"     # World model excerpt
    TOOL_RESULT = "tool"      # Result from tool/agent


@dataclass
class WorkingMemoryItem:
    """A single item in working memory."""
    id: str
    type: ItemType
    content: Any
    relevance: float = 1.0  # 0-1, decays over time
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def touch(self) -> None:
        """Mark as recently accessed."""
        self.last_accessed = datetime.now(timezone.utc)
        self.relevance = min(1.0, self.relevance + 0.1)
    
    def decay(self, amount: float = 0.05) -> None:
        """Reduce relevance over time."""
        self.relevance = max(0.0, self.relevance - amount)
    
    @property
    def age_seconds(self) -> float:
        """How old this item is."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()
    
    @property
    def idle_seconds(self) -> float:
        """How long since last accessed."""
        return (datetime.now(timezone.utc) - self.last_accessed).total_seconds()


@dataclass
class WorkingContext:
    """The full working context for a thought process."""
    items: List[WorkingMemoryItem]
    session_id: Optional[str]
    user_id: Optional[str]
    conversation_history: List[Dict[str, Any]]
    active_goals: List[str]
    world_state_summary: Optional[str]
    
    def to_prompt_context(self) -> str:
        """Convert to text for LLM prompt injection."""
        parts = []
        
        # Conversation history
        if self.conversation_history:
            parts.append("Recent conversation:")
            for turn in self.conversation_history[-5:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")[:200]
                parts.append(f"  {role}: {content}")
        
        # Active goals
        if self.active_goals:
            parts.append(f"Active goals: {', '.join(self.active_goals[:3])}")
        
        # World state
        if self.world_state_summary:
            parts.append(f"World state: {self.world_state_summary}")
        
        # Key items
        key_items = [i for i in self.items if i.relevance > 0.5]
        if key_items:
            parts.append("In mind:")
            for item in key_items[:5]:
                if isinstance(item.content, str):
                    parts.append(f"  - {item.content[:100]}")
                else:
                    parts.append(f"  - [{item.type.value}]")
        
        return "\n".join(parts)


class WorkingMemory:
    """
    MYCA's working memory - the conscious workspace.
    
    Limited to 7±2 items like human working memory. Items decay
    if not accessed, and least relevant items are displaced when
    new items are added beyond capacity.
    """
    
    # Capacity limits (7±2)
    MIN_CAPACITY = 5
    MAX_CAPACITY = 9
    TARGET_CAPACITY = 7
    
    # Decay settings
    DECAY_INTERVAL = 30  # seconds between decay cycles
    DECAY_AMOUNT = 0.05
    EVICTION_THRESHOLD = 0.2
    
    def __init__(self, consciousness: Optional["MYCAConsciousness"] = None, capacity: int = TARGET_CAPACITY):
        # `consciousness` is optional for unit tests.
        self._consciousness = consciousness
        # Legacy tests treat `_items` as a list.
        self._items: List[WorkingMemoryItem] = []
        self._capacity = int(capacity)
        self._conversation_buffer: List[Dict[str, Any]] = []
        self._active_goals: List[str] = []
        self._lock = asyncio.Lock()
        self._decay_task: Optional[asyncio.Task] = None

    @property
    def capacity(self) -> int:
        return self._capacity
    
    async def start(self) -> None:
        """Start the decay background task."""
        if self._decay_task is None:
            self._decay_task = asyncio.create_task(self._decay_loop())
    
    async def stop(self) -> None:
        """Stop the decay background task."""
        if self._decay_task:
            self._decay_task.cancel()
            self._decay_task = None
    
    async def _decay_loop(self) -> None:
        """Periodically decay item relevance and evict stale items."""
        while True:
            try:
                await asyncio.sleep(self.DECAY_INTERVAL)
                await self._decay_and_evict()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Decay loop error: {e}")
    
    async def _decay_and_evict(self) -> None:
        """Decay all items and evict those below threshold."""
        async with self._lock:
            to_evict = []
            for item_id, item in self._items.items():
                item.decay(self.DECAY_AMOUNT)
                if item.relevance < self.EVICTION_THRESHOLD:
                    to_evict.append(item_id)
            
            for item_id in to_evict:
                del self._items[item_id]
                logger.debug(f"Evicted item from working memory: {item_id}")
    
    async def add(
        self,
        content: Any,
        item_type: Any = ItemType.INPUT,
        relevance: float = 1.0,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkingMemoryItem:
        """
        Add an item to working memory.
        
        If at capacity, the least relevant item is displaced.
        """
        async with self._lock:
            # Normalize legacy string type.
            if isinstance(item_type, ItemType):
                type_value: Any = item_type.value
            else:
                type_value = str(item_type)

            item = WorkingMemoryItem(
                id=f"wm_{datetime.now(timezone.utc).timestamp()}_{type_value}",
                type=type_value,
                content=content,
                relevance=float(relevance),
                source=source,
                metadata=metadata or {},
            )

            self._items.append(item)

            # Enforce capacity (legacy semantics)
            while len(self._items) > self._capacity:
                least = min(self._items, key=lambda i: i.relevance)
                self._items.remove(least)

            return item
    
    async def get(self, item_id: str) -> Optional[WorkingMemoryItem]:
        """Get an item by ID, touching it to update access time."""
        async with self._lock:
            for item in self._items:
                if item.id == item_id:
                    item.touch()
                    return item
        return None
    
    async def remove(self, item_id: str) -> bool:
        """Remove an item from working memory."""
        async with self._lock:
            for item in list(self._items):
                if item.id == item_id:
                    self._items.remove(item)
                    return True
        return False
    
    def clear(self) -> None:
        """Clear all items (legacy sync API used by unit tests)."""
        self._items.clear()
        self._conversation_buffer.clear()

    async def clear_async(self) -> None:
        """Async clear for internal use."""
        async with self._lock:
            self.clear()

    async def decay(self) -> None:
        """Legacy relevance decay used by unit tests."""
        async with self._lock:
            for item in self._items:
                item.decay(self.DECAY_AMOUNT)
    
    async def get_all(self) -> List[WorkingMemoryItem]:
        """Get all items sorted by relevance."""
        async with self._lock:
            return sorted(self._items, key=lambda i: i.relevance, reverse=True)
    
    async def get_by_type(self, item_type: Any) -> List[WorkingMemoryItem]:
        """Get all items of a specific type."""
        async with self._lock:
            value = item_type.value if isinstance(item_type, ItemType) else str(item_type)
            return [i for i in self._items if str(i.type) == value]

    async def get_context(self) -> List[Dict[str, Any]]:
        """Legacy context serialization used by unit tests."""
        items = await self.get_all()
        return [
            {"id": i.id, "type": i.type, "content": i.content, "relevance": i.relevance}
            for i in items
            if i.relevance > 0
        ]

    def add_to_conversation(self, role: str, content: str) -> None:
        """Legacy sync conversation buffer used by unit tests."""
        self._conversation_buffer.append({"role": role, "content": content})

    def get_conversation_buffer(self) -> List[Dict[str, Any]]:
        """Legacy sync conversation buffer getter used by unit tests."""
        return list(self._conversation_buffer)
    
    async def add_conversation_turn(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a conversation turn to the buffer."""
        async with self._lock:
            self._conversation_buffer.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(metadata or {})
            })
            # Keep buffer reasonable
            if len(self._conversation_buffer) > 20:
                self._conversation_buffer = self._conversation_buffer[-20:]
    
    async def set_goals(self, goals: List[str]) -> None:
        """Set the active goals."""
        async with self._lock:
            self._active_goals = goals[:5]  # Max 5 active goals
    
    async def load_context(
        self,
        focus: "AttentionFocus",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> WorkingContext:
        """
        Load the full working context for a thought process.
        
        This gathers:
        - Current working memory items
        - Conversation history
        - Active goals
        - World state summary
        """
        async with self._lock:
            # Add the current focus as an input item
            category = focus.category.value if hasattr(focus.category, "value") else str(focus.category)
            await self.add(
                focus.content,
                ItemType.INPUT,
                relevance=1.0,
                source=focus.source,
                metadata={"focus_id": focus.id, "category": category},
            )
            
            # Get world state summary
            world_summary = None
            if self._consciousness.world_model:
                world_summary = await self._consciousness.world_model.get_summary()
            
            return WorkingContext(
                items=list(self._items),
                session_id=session_id,
                user_id=user_id,
                conversation_history=self._conversation_buffer.copy(),
                active_goals=self._active_goals.copy(),
                world_state_summary=world_summary,
            )
    
    async def boost_relevance(self, item_id: str, amount: float = 0.2) -> None:
        """Boost the relevance of an item (e.g., when it becomes relevant again)."""
        async with self._lock:
            for item in self._items:
                if item.id == item_id:
                    item.relevance = min(1.0, item.relevance + amount)
                    item.touch()
                    break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about working memory."""
        avg_rel = sum(i.relevance for i in self._items) / max(1, len(self._items))
        return {
            "item_count": len(self._items),
            "capacity": self._capacity,
            "utilization": len(self._items) / max(1, self._capacity),
            "avg_relevance": avg_rel,
            "conversation_turns": len(self._conversation_buffer),
            "active_goals": len(self._active_goals),
            "types": {},
        }
