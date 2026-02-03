"""Short-term conversational memory. Created: February 3, 2026"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from collections import deque
from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime

class ConversationContext(BaseModel):
    conversation_id: UUID
    user_id: Optional[UUID] = None
    messages: List[Message] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    last_active: datetime

class ShortTermMemory:
    """Session-based short-term memory."""
    
    def __init__(self, max_messages: int = 100, ttl_seconds: int = 3600):
        self.max_messages = max_messages
        self.ttl_seconds = ttl_seconds
        self._contexts: Dict[UUID, ConversationContext] = {}
    
    def create_context(self, user_id: Optional[UUID] = None) -> ConversationContext:
        now = datetime.now(timezone.utc)
        ctx = ConversationContext(conversation_id=uuid4(), user_id=user_id, created_at=now, last_active=now)
        self._contexts[ctx.conversation_id] = ctx
        return ctx
    
    def add_message(self, conversation_id: UUID, role: str, content: str) -> bool:
        if conversation_id not in self._contexts:
            return False
        ctx = self._contexts[conversation_id]
        ctx.messages.append(Message(role=role, content=content, timestamp=datetime.now(timezone.utc)))
        if len(ctx.messages) > self.max_messages:
            ctx.messages = ctx.messages[-self.max_messages:]
        ctx.last_active = datetime.now(timezone.utc)
        return True
    
    def get_context(self, conversation_id: UUID) -> Optional[ConversationContext]:
        return self._contexts.get(conversation_id)
    
    def get_recent_messages(self, conversation_id: UUID, n: int = 10) -> List[Message]:
        ctx = self._contexts.get(conversation_id)
        if not ctx:
            return []
        return ctx.messages[-n:]
    
    def summarize(self, conversation_id: UUID) -> str:
        ctx = self._contexts.get(conversation_id)
        if not ctx:
            return ""
        return f"Conversation with {len(ctx.messages)} messages"
    
    def clear(self, conversation_id: UUID) -> bool:
        if conversation_id in self._contexts:
            del self._contexts[conversation_id]
            return True
        return False
