"""
LLM-Powered Memory Summarization for MYCA Voice System
Created: February 4, 2026

Intelligent conversation and memory summarization using LLM.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: Optional[str] = None
    entities: List[str] = field(default_factory=list)


@dataclass
class ConversationSummary:
    """Summary of a conversation."""
    summary_id: str
    conversation_id: str
    summary: str
    key_points: List[str]
    topics_discussed: List[str]
    decisions_made: List[str]
    action_items: List[str]
    entities_mentioned: List[str]
    sentiment: str
    turn_count: int
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemorySummary:
    """Summary of memories."""
    summary_id: str
    user_id: str
    summary: str
    key_facts: List[str]
    preferences_noted: List[str]
    skills_referenced: List[str]
    memory_count: int
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


class MemorySummarizer:
    """
    LLM-powered summarization for conversations and memories.
    
    Features:
    - Conversation summarization
    - Memory consolidation
    - Key point extraction
    - Action item identification
    - Sentiment analysis
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client
        self.conversation_buffer: Dict[str, List[ConversationTurn]] = {}
        self.summaries: Dict[str, ConversationSummary] = {}
        
        logger.info("MemorySummarizer initialized")
    
    async def summarize_conversation(
        self,
        conversation_id: str,
        turns: List[ConversationTurn],
        max_summary_length: int = 200,
    ) -> ConversationSummary:
        """
        Summarize a conversation.
        
        Args:
            conversation_id: ID of the conversation
            turns: List of conversation turns
            max_summary_length: Maximum summary length in words
            
        Returns:
            ConversationSummary
        """
        logger.info(f"Summarizing conversation: {conversation_id} ({len(turns)} turns)")
        
        # Build conversation text
        conv_text = self._format_conversation(turns)
        
        # Generate summary using LLM
        if self.llm_client:
            summary_data = await self._llm_summarize_conversation(conv_text, max_summary_length)
        else:
            summary_data = self._basic_summarize_conversation(turns)
        
        import hashlib
        summary_id = hashlib.md5(f"{conversation_id}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        summary = ConversationSummary(
            summary_id=summary_id,
            conversation_id=conversation_id,
            summary=summary_data.get("summary", ""),
            key_points=summary_data.get("key_points", []),
            topics_discussed=summary_data.get("topics", []),
            decisions_made=summary_data.get("decisions", []),
            action_items=summary_data.get("action_items", []),
            entities_mentioned=summary_data.get("entities", []),
            sentiment=summary_data.get("sentiment", "neutral"),
            turn_count=len(turns),
        )
        
        self.summaries[summary_id] = summary
        return summary
    
    async def _llm_summarize_conversation(self, conv_text: str, max_length: int) -> Dict[str, Any]:
        """Use LLM to summarize conversation."""
        prompt = f"""Summarize this conversation concisely (max {max_length} words).

Conversation:
{conv_text}

Provide JSON with:
{{
    "summary": "brief summary",
    "key_points": ["point 1", "point 2"],
    "topics": ["topic 1", "topic 2"],
    "decisions": ["decision 1"],
    "action_items": ["action 1"],
    "entities": ["entity 1"],
    "sentiment": "positive/negative/neutral"
}}
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            return json.loads(response)
        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}")
            return {"summary": "Summarization failed", "key_points": []}
    
    def _basic_summarize_conversation(self, turns: List[ConversationTurn]) -> Dict[str, Any]:
        """Basic summarization without LLM."""
        # Extract key info from turns
        topics = set()
        entities = set()
        
        for turn in turns:
            # Simple topic extraction
            words = turn.content.lower().split()
            for word in words:
                if len(word) > 5:
                    topics.add(word)
            
            # Get entities if available
            entities.update(turn.entities)
        
        # Create basic summary
        user_turns = [t for t in turns if t.role == "user"]
        assistant_turns = [t for t in turns if t.role == "assistant"]
        
        summary = f"Conversation with {len(user_turns)} user messages and {len(assistant_turns)} responses."
        
        return {
            "summary": summary,
            "key_points": [t.content[:50] + "..." for t in user_turns[:3]],
            "topics": list(topics)[:5],
            "decisions": [],
            "action_items": [],
            "entities": list(entities),
            "sentiment": "neutral",
        }
    
    async def summarize_memories(
        self,
        user_id: str,
        memories: List[Any],  # MemoryEntry objects
    ) -> MemorySummary:
        """
        Summarize a collection of memories.
        
        Args:
            user_id: User ID
            memories: List of memory entries
            
        Returns:
            MemorySummary
        """
        logger.info(f"Summarizing {len(memories)} memories for user {user_id}")
        
        if self.llm_client:
            summary_data = await self._llm_summarize_memories(memories)
        else:
            summary_data = self._basic_summarize_memories(memories)
        
        import hashlib
        summary_id = hashlib.md5(f"mem_{user_id}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Get time range
        timestamps = [m.created_at for m in memories if hasattr(m, 'created_at')]
        time_start = min(timestamps) if timestamps else None
        time_end = max(timestamps) if timestamps else None
        
        return MemorySummary(
            summary_id=summary_id,
            user_id=user_id,
            summary=summary_data.get("summary", ""),
            key_facts=summary_data.get("key_facts", []),
            preferences_noted=summary_data.get("preferences", []),
            skills_referenced=summary_data.get("skills", []),
            memory_count=len(memories),
            time_range_start=time_start,
            time_range_end=time_end,
        )
    
    async def _llm_summarize_memories(self, memories: List[Any]) -> Dict[str, Any]:
        """Use LLM to summarize memories."""
        memory_text = "\n".join([
            f"- {m.content}" for m in memories if hasattr(m, 'content')
        ])
        
        prompt = f"""Summarize these user memories:

{memory_text}

Provide JSON with:
{{
    "summary": "overall summary",
    "key_facts": ["fact 1", "fact 2"],
    "preferences": ["preference 1"],
    "skills": ["skill 1"]
}}
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            return json.loads(response)
        except Exception as e:
            logger.warning(f"LLM memory summarization failed: {e}")
            return {"summary": "Summarization failed", "key_facts": []}
    
    def _basic_summarize_memories(self, memories: List[Any]) -> Dict[str, Any]:
        """Basic memory summarization without LLM."""
        facts = []
        preferences = []
        
        for mem in memories[:10]:
            content = getattr(mem, 'content', str(mem))
            if len(content) < 100:
                mem_type = getattr(mem, 'memory_type', None)
                if mem_type and 'preference' in str(mem_type).lower():
                    preferences.append(content)
                else:
                    facts.append(content)
        
        return {
            "summary": f"{len(memories)} memories stored.",
            "key_facts": facts[:5],
            "preferences": preferences[:3],
            "skills": [],
        }
    
    def add_turn(self, conversation_id: str, turn: ConversationTurn):
        """Add a turn to the conversation buffer."""
        if conversation_id not in self.conversation_buffer:
            self.conversation_buffer[conversation_id] = []
        self.conversation_buffer[conversation_id].append(turn)
    
    def get_buffer(self, conversation_id: str) -> List[ConversationTurn]:
        """Get buffered turns for a conversation."""
        return self.conversation_buffer.get(conversation_id, [])
    
    def clear_buffer(self, conversation_id: str):
        """Clear the conversation buffer."""
        if conversation_id in self.conversation_buffer:
            del self.conversation_buffer[conversation_id]
    
    async def get_context_for_prompt(
        self,
        conversation_id: str,
        max_turns: int = 10,
        include_summary: bool = True,
    ) -> str:
        """
        Get conversation context for prompting.
        
        Args:
            conversation_id: Conversation ID
            max_turns: Maximum recent turns to include
            include_summary: Whether to include summary of older turns
            
        Returns:
            Formatted context string
        """
        turns = self.get_buffer(conversation_id)
        
        if len(turns) <= max_turns:
            return self._format_conversation(turns)
        
        # Split into old and recent
        old_turns = turns[:-max_turns]
        recent_turns = turns[-max_turns:]
        
        context_parts = []
        
        if include_summary and old_turns:
            summary = await self.summarize_conversation(
                f"{conversation_id}_partial",
                old_turns,
                max_summary_length=100
            )
            context_parts.append(f"[Previous context summary: {summary.summary}]")
        
        context_parts.append(self._format_conversation(recent_turns))
        
        return "\n\n".join(context_parts)
    
    def _format_conversation(self, turns: List[ConversationTurn]) -> str:
        """Format turns into readable text."""
        lines = []
        for turn in turns:
            role = turn.role.capitalize()
            lines.append(f"{role}: {turn.content}")
        return "\n".join(lines)
    
    def get_summary(self, summary_id: str) -> Optional[ConversationSummary]:
        """Get a summary by ID."""
        return self.summaries.get(summary_id)


# Singleton
_summarizer_instance: Optional[MemorySummarizer] = None


def get_memory_summarizer() -> MemorySummarizer:
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = MemorySummarizer()
    return _summarizer_instance


__all__ = [
    "MemorySummarizer",
    "ConversationTurn",
    "ConversationSummary",
    "MemorySummary",
    "get_memory_summarizer",
]
