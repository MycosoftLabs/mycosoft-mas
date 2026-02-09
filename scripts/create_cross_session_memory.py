"""Helper script to create cross_session_memory.py"""
import os

content = '''"""
Cross-Session Memory System for MYCA Voice System
Created: February 4, 2026

Persistent memory across sessions with user preferences,
conversation history, and context management.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import os as os_module
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class MemoryScope(Enum):
    """Scope of memory storage."""
    SESSION = "session"          # Current session only
    USER = "user"                # User-specific, persistent
    GLOBAL = "global"            # All users, persistent
    CONVERSATION = "conversation" # Current conversation thread


class MemoryType(Enum):
    """Type of memory entry."""
    FACT = "fact"                # Factual information
    PREFERENCE = "preference"    # User preference
    CONTEXT = "context"          # Contextual information
    HISTORY = "history"          # Conversation history
    ENTITY = "entity"            # Named entity
    SKILL = "skill"              # Learned skill reference


@dataclass
class MemoryEntry:
    """A single memory entry."""
    memory_id: str
    content: str
    memory_type: MemoryType
    scope: MemoryScope
    user_id: str
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # Relationships
    related_memories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Importance and usage
    importance: float = 0.5
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Source
    source: str = "voice"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def boost_importance(self, amount: float = 0.1):
        self.importance = min(1.0, self.importance + amount)
    
    def decay_importance(self, factor: float = 0.95):
        self.importance = max(0.1, self.importance * factor)


@dataclass
class UserPreferences:
    """User preferences loaded on session start."""
    user_id: str
    
    # Voice preferences
    voice_speed: float = 1.0
    voice_pitch: float = 1.0
    preferred_voice: str = "default"
    
    # Interaction preferences
    confirmation_level: str = "normal"  # minimal, normal, verbose
    response_verbosity: str = "normal"  # brief, normal, detailed
    
    # Working context
    default_project: Optional[str] = None
    preferred_tools: List[str] = field(default_factory=list)
    
    # Privacy
    save_history: bool = True
    share_context: bool = True
    
    # Custom settings
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ConversationContext:
    """Current conversation context."""
    conversation_id: str
    user_id: str
    started_at: datetime = field(default_factory=datetime.now)
    
    # Current context
    current_topic: Optional[str] = None
    current_task: Optional[str] = None
    current_entities: Dict[str, str] = field(default_factory=dict)
    
    # History
    recent_intents: List[str] = field(default_factory=list)
    recent_responses: List[str] = field(default_factory=list)
    
    # State
    pending_confirmation: Optional[str] = None
    last_error: Optional[str] = None
    
    def add_intent(self, intent: str):
        self.recent_intents.append(intent)
        if len(self.recent_intents) > 10:
            self.recent_intents.pop(0)
    
    def add_response(self, response: str):
        self.recent_responses.append(response)
        if len(self.recent_responses) > 10:
            self.recent_responses.pop(0)


class CrossSessionMemory:
    """
    Cross-session memory management system.
    
    Features:
    - Persistent memory across sessions
    - User preference loading
    - Conversation context management
    - Memory decay and importance scoring
    - Multi-scope storage (session, user, global)
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or "data/memory"
        
        self.memories: Dict[str, MemoryEntry] = {}
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.conversations: Dict[str, ConversationContext] = {}
        
        # Memory indices
        self.memories_by_user: Dict[str, set] = {}
        self.memories_by_type: Dict[MemoryType, set] = {}
        self.memories_by_tag: Dict[str, set] = {}
        
        # Load persisted data
        self._load_all()
        
        logger.info(f"CrossSessionMemory initialized with {len(self.memories)} memories")
    
    def store(
        self,
        content: str,
        memory_type: MemoryType,
        user_id: str,
        scope: MemoryScope = MemoryScope.USER,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        expires_in_hours: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """Store a new memory."""
        memory_id = self._generate_id(content, user_id)
        
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        memory = MemoryEntry(
            memory_id=memory_id,
            content=content,
            memory_type=memory_type,
            scope=scope,
            user_id=user_id,
            tags=tags or [],
            importance=importance,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        
        self.memories[memory_id] = memory
        self._index_memory(memory)
        
        # Persist if user or global scope
        if scope in (MemoryScope.USER, MemoryScope.GLOBAL):
            self._save_memory(memory)
        
        logger.info(f"Stored memory: {memory_id} ({memory_type.value})")
        return memory
    
    def recall(
        self,
        query: str,
        user_id: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Recall memories matching a query."""
        results = []
        query_lower = query.lower()
        
        for memory in self.memories.values():
            # Check access
            if not self._can_access(memory, user_id):
                continue
            
            # Check type filter
            if memory_types and memory.memory_type not in memory_types:
                continue
            
            # Check expiration
            if memory.is_expired():
                continue
            
            # Score match
            score = 0.0
            if query_lower in memory.content.lower():
                score += 0.5
            if any(query_lower in tag.lower() for tag in memory.tags):
                score += 0.3
            
            # Factor in importance
            score *= memory.importance
            
            if score > 0:
                results.append((memory, score))
        
        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Update access stats and return
        returned = []
        for memory, _ in results[:limit]:
            memory.access_count += 1
            memory.last_accessed = datetime.now()
            memory.boost_importance(0.05)
            returned.append(memory)
        
        return returned
    
    def forget(self, memory_id: str, user_id: str) -> bool:
        """Remove a memory."""
        if memory_id not in self.memories:
            return False
        
        memory = self.memories[memory_id]
        
        # Only owner or system can delete
        if memory.user_id != user_id and user_id != "system":
            return False
        
        self._unindex_memory(memory)
        del self.memories[memory_id]
        
        logger.info(f"Forgot memory: {memory_id}")
        return True
    
    def load_user_preferences(self, user_id: str) -> UserPreferences:
        """Load or create user preferences."""
        if user_id in self.user_preferences:
            return self.user_preferences[user_id]
        
        # Try to load from storage
        prefs = self._load_preferences(user_id)
        if prefs:
            self.user_preferences[user_id] = prefs
            return prefs
        
        # Create default
        prefs = UserPreferences(user_id=user_id)
        self.user_preferences[user_id] = prefs
        return prefs
    
    def save_user_preferences(self, prefs: UserPreferences):
        """Save user preferences."""
        self.user_preferences[prefs.user_id] = prefs
        self._save_preferences(prefs)
    
    def start_conversation(self, user_id: str) -> ConversationContext:
        """Start a new conversation context."""
        conv_id = self._generate_id(f"conv_{user_id}", str(datetime.now()))
        
        context = ConversationContext(
            conversation_id=conv_id,
            user_id=user_id,
        )
        
        self.conversations[conv_id] = context
        
        # Load recent context
        recent = self.recall(
            query="",
            user_id=user_id,
            memory_types=[MemoryType.CONTEXT],
            limit=5,
        )
        for mem in recent:
            if "topic" in mem.tags:
                context.current_topic = mem.content
                break
        
        logger.info(f"Started conversation: {conv_id}")
        return context
    
    def get_conversation(self, conv_id: str) -> Optional[ConversationContext]:
        """Get an existing conversation context."""
        return self.conversations.get(conv_id)
    
    def update_context(
        self,
        conv_id: str,
        topic: Optional[str] = None,
        task: Optional[str] = None,
        entities: Optional[Dict[str, str]] = None,
    ):
        """Update conversation context."""
        if conv_id not in self.conversations:
            return
        
        context = self.conversations[conv_id]
        
        if topic:
            context.current_topic = topic
        if task:
            context.current_task = task
        if entities:
            context.current_entities.update(entities)
    
    def get_memory_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of user's memories."""
        user_memories = [
            m for m in self.memories.values()
            if self._can_access(m, user_id) and not m.is_expired()
        ]
        
        return {
            "total_memories": len(user_memories),
            "by_type": {t.value: len([m for m in user_memories if m.memory_type == t]) for t in MemoryType},
            "by_scope": {s.value: len([m for m in user_memories if m.scope == s]) for s in MemoryScope},
            "most_important": sorted(user_memories, key=lambda m: m.importance, reverse=True)[:5],
            "recently_accessed": sorted(
                [m for m in user_memories if m.last_accessed],
                key=lambda m: m.last_accessed,
                reverse=True
            )[:5],
        }
    
    def decay_memories(self):
        """Apply decay to memory importance."""
        for memory in self.memories.values():
            if memory.scope == MemoryScope.SESSION:
                continue
            memory.decay_importance()
    
    def cleanup_expired(self) -> int:
        """Remove expired memories."""
        expired = [mid for mid, m in self.memories.items() if m.is_expired()]
        for mid in expired:
            self.forget(mid, "system")
        return len(expired)
    
    def _can_access(self, memory: MemoryEntry, user_id: str) -> bool:
        if memory.scope == MemoryScope.GLOBAL:
            return True
        if memory.user_id == user_id:
            return True
        if user_id == "system":
            return True
        return False
    
    def _generate_id(self, content: str, salt: str) -> str:
        return hashlib.md5(f"{content}{salt}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    
    def _index_memory(self, memory: MemoryEntry):
        if memory.user_id not in self.memories_by_user:
            self.memories_by_user[memory.user_id] = set()
        self.memories_by_user[memory.user_id].add(memory.memory_id)
        
        if memory.memory_type not in self.memories_by_type:
            self.memories_by_type[memory.memory_type] = set()
        self.memories_by_type[memory.memory_type].add(memory.memory_id)
        
        for tag in memory.tags:
            if tag not in self.memories_by_tag:
                self.memories_by_tag[tag] = set()
            self.memories_by_tag[tag].add(memory.memory_id)
    
    def _unindex_memory(self, memory: MemoryEntry):
        if memory.user_id in self.memories_by_user:
            self.memories_by_user[memory.user_id].discard(memory.memory_id)
        if memory.memory_type in self.memories_by_type:
            self.memories_by_type[memory.memory_type].discard(memory.memory_id)
        for tag in memory.tags:
            if tag in self.memories_by_tag:
                self.memories_by_tag[tag].discard(memory.memory_id)
    
    def _load_all(self):
        """Load all persisted data."""
        try:
            memories_path = Path(self.storage_path) / "memories.json"
            if memories_path.exists():
                with open(memories_path, 'r') as f:
                    data = json.load(f)
                for m in data.get("memories", []):
                    memory = MemoryEntry(
                        memory_id=m["memory_id"],
                        content=m["content"],
                        memory_type=MemoryType(m["memory_type"]),
                        scope=MemoryScope(m["scope"]),
                        user_id=m["user_id"],
                        created_at=datetime.fromisoformat(m["created_at"]),
                        tags=m.get("tags", []),
                        importance=m.get("importance", 0.5),
                    )
                    self.memories[memory.memory_id] = memory
                    self._index_memory(memory)
                logger.info(f"Loaded {len(self.memories)} memories")
        except Exception as e:
            logger.error(f"Failed to load memories: {e}")
    
    def _save_memory(self, memory: MemoryEntry):
        """Save a single memory."""
        try:
            path = Path(self.storage_path)
            path.mkdir(parents=True, exist_ok=True)
            
            memories_path = path / "memories.json"
            data = {"memories": []}
            
            if memories_path.exists():
                with open(memories_path, 'r') as f:
                    data = json.load(f)
            
            # Update or add
            found = False
            for i, m in enumerate(data["memories"]):
                if m["memory_id"] == memory.memory_id:
                    data["memories"][i] = self._serialize_memory(memory)
                    found = True
                    break
            if not found:
                data["memories"].append(self._serialize_memory(memory))
            
            with open(memories_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def _serialize_memory(self, memory: MemoryEntry) -> Dict[str, Any]:
        return {
            "memory_id": memory.memory_id,
            "content": memory.content,
            "memory_type": memory.memory_type.value,
            "scope": memory.scope.value,
            "user_id": memory.user_id,
            "created_at": memory.created_at.isoformat(),
            "tags": memory.tags,
            "importance": memory.importance,
        }
    
    def _load_preferences(self, user_id: str) -> Optional[UserPreferences]:
        try:
            path = Path(self.storage_path) / f"prefs_{user_id}.json"
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                return UserPreferences(
                    user_id=user_id,
                    voice_speed=data.get("voice_speed", 1.0),
                    voice_pitch=data.get("voice_pitch", 1.0),
                    preferred_voice=data.get("preferred_voice", "default"),
                    confirmation_level=data.get("confirmation_level", "normal"),
                    response_verbosity=data.get("response_verbosity", "normal"),
                    save_history=data.get("save_history", True),
                    custom=data.get("custom", {}),
                )
        except Exception as e:
            logger.error(f"Failed to load preferences: {e}")
        return None
    
    def _save_preferences(self, prefs: UserPreferences):
        try:
            path = Path(self.storage_path)
            path.mkdir(parents=True, exist_ok=True)
            
            with open(path / f"prefs_{prefs.user_id}.json", 'w') as f:
                json.dump({
                    "voice_speed": prefs.voice_speed,
                    "voice_pitch": prefs.voice_pitch,
                    "preferred_voice": prefs.preferred_voice,
                    "confirmation_level": prefs.confirmation_level,
                    "response_verbosity": prefs.response_verbosity,
                    "save_history": prefs.save_history,
                    "custom": prefs.custom,
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")


# Singleton
_memory_instance: Optional[CrossSessionMemory] = None


def get_cross_session_memory() -> CrossSessionMemory:
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = CrossSessionMemory()
    return _memory_instance


__all__ = [
    "CrossSessionMemory",
    "MemoryEntry",
    "UserPreferences",
    "ConversationContext",
    "MemoryScope",
    "MemoryType",
    "get_cross_session_memory",
]
'''

os.makedirs('mycosoft_mas/voice', exist_ok=True)
with open('mycosoft_mas/voice/cross_session_memory.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Created cross_session_memory.py')
