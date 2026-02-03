"""
MYCA Memory Summarization Service - February 2026

End-of-session memory archival with:
- Conversation summarization using LLM
- Automatic archival to long-term memory
- Key information extraction
- Cross-session context continuity
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("MemorySummarization")


class MemorySummarizationService:
    """
    Service for summarizing and archiving conversation memory.
    
    Responsibilities:
    - Summarize conversation turns at end of session
    - Extract key information (preferences, decisions, action items)
    - Archive to long-term user memory
    - Maintain cross-session context continuity
    """
    
    def __init__(self):
        self._n8n_url = os.getenv("N8N_WEBHOOK_URL") or os.getenv("N8N_URL")
        self._memory_manager = None
    
    def _get_memory_manager(self):
        """Lazy load memory manager."""
        if self._memory_manager is None:
            try:
                from mycosoft_mas.core.routers.memory_api import get_memory_manager
                self._memory_manager = get_memory_manager()
            except ImportError:
                logger.warning("MemoryManager not available")
        return self._memory_manager
    
    async def summarize_conversation(
        self,
        conversation_id: str,
        user_id: str = "anonymous",
        max_turns: int = 50,
    ) -> Optional[Dict[str, Any]]:
        """
        Summarize a conversation and extract key information.
        
        Args:
            conversation_id: The conversation to summarize
            user_id: User ID for archival
            max_turns: Maximum turns to include in summary
            
        Returns:
            Summary dict with text and extracted info
        """
        memory = self._get_memory_manager()
        if not memory:
            logger.warning("Memory manager not available for summarization")
            return None
        
        try:
            from mycosoft_mas.core.routers.memory_api import MemoryScope
            
            # Read conversation history
            conversation_data = await memory.read(
                scope=MemoryScope.CONVERSATION,
                namespace=conversation_id,
            )
            
            if not conversation_data:
                logger.info(f"No conversation data found for {conversation_id}")
                return None
            
            # Convert to list of turns
            turns = []
            if isinstance(conversation_data, dict):
                # Sort by key to get chronological order
                for key in sorted(conversation_data.keys()):
                    turn_data = conversation_data[key]
                    if isinstance(turn_data, dict):
                        turns.append({
                            "role": turn_data.get("role", "unknown"),
                            "content": turn_data.get("content", ""),
                        })
            
            if not turns:
                return None
            
            # Limit to max_turns
            if len(turns) > max_turns:
                turns = turns[-max_turns:]
            
            # Generate summary
            summary = await self._generate_summary(turns)
            
            # Extract key information
            extracted_info = self._extract_key_info(turns)
            
            result = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "summarized_at": datetime.now(timezone.utc).isoformat(),
                "turn_count": len(turns),
                "summary_text": summary,
                "extracted_info": extracted_info,
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return None
    
    async def archive_session(
        self,
        conversation_id: str,
        user_id: str = "anonymous",
        session_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Archive a completed session to long-term memory.
        
        This is called at the end of a voice/chat session.
        
        Args:
            conversation_id: The conversation to archive
            user_id: User ID for archival namespace
            session_metadata: Additional metadata (RTF, duration, etc.)
            
        Returns:
            True if successful
        """
        # Get summary
        summary = await self.summarize_conversation(conversation_id, user_id)
        if not summary:
            logger.warning(f"Could not summarize conversation {conversation_id}")
            return False
        
        # Add metadata
        if session_metadata:
            summary["session_metadata"] = session_metadata
        
        # Archive to user's long-term memory
        memory = self._get_memory_manager()
        if not memory:
            return False
        
        try:
            from mycosoft_mas.core.routers.memory_api import MemoryScope
            
            archive_key = f"session_archive_{conversation_id}"
            
            await memory.write(
                scope=MemoryScope.USER,
                namespace=user_id,
                key=archive_key,
                value=summary,
            )
            
            logger.info(f"Archived session {conversation_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Archive failed: {e}")
            return False
    
    async def _generate_summary(self, turns: List[Dict[str, Any]]) -> str:
        """
        Generate a text summary of conversation turns.
        
        Uses LLM via n8n if available, otherwise creates simple summary.
        """
        # Try n8n for LLM summarization
        if self._n8n_url:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self._n8n_url.rstrip('/')}/webhook/myca/summarize",
                        json={
                            "turns": turns,
                            "task": "summarize_conversation",
                        }
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if isinstance(result, dict) and result.get("summary"):
                            return result["summary"]
            except Exception as e:
                logger.debug(f"N8N summarization failed: {e}")
        
        # Fallback: Simple summary
        user_messages = [t["content"] for t in turns if t.get("role") == "user"]
        assistant_messages = [t["content"] for t in turns if t.get("role") == "assistant"]
        
        topics = self._extract_topics(user_messages)
        
        summary_parts = [
            f"Conversation with {len(turns)} turns.",
        ]
        
        if topics:
            summary_parts.append(f"Topics discussed: {', '.join(topics[:5])}.")
        
        if user_messages:
            summary_parts.append(f"User asked {len(user_messages)} questions/statements.")
        
        return " ".join(summary_parts)
    
    def _extract_topics(self, messages: List[str]) -> List[str]:
        """Extract likely topics from messages."""
        # Simple keyword extraction
        keywords = set()
        topic_indicators = [
            "status", "health", "check", "deploy", "restart", "monitor",
            "agent", "workflow", "proxmox", "unifi", "network", "server",
            "database", "api", "error", "log", "memory", "cpu", "disk",
        ]
        
        for msg in messages:
            msg_lower = msg.lower()
            for topic in topic_indicators:
                if topic in msg_lower:
                    keywords.add(topic)
        
        return list(keywords)
    
    def _extract_key_info(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract key information from conversation.
        
        Looks for:
        - User preferences expressed
        - Decisions made
        - Action items mentioned
        - Errors encountered
        """
        info = {
            "preferences": [],
            "decisions": [],
            "action_items": [],
            "errors_mentioned": [],
        }
        
        for turn in turns:
            content = turn.get("content", "").lower()
            
            # Look for preferences
            if any(word in content for word in ["prefer", "like", "want", "always", "never"]):
                info["preferences"].append(turn.get("content", "")[:100])
            
            # Look for decisions
            if any(word in content for word in ["decided", "will do", "going to", "let's"]):
                info["decisions"].append(turn.get("content", "")[:100])
            
            # Look for action items
            if any(word in content for word in ["need to", "should", "must", "todo", "reminder"]):
                info["action_items"].append(turn.get("content", "")[:100])
            
            # Look for errors
            if any(word in content for word in ["error", "failed", "broken", "issue", "problem", "bug"]):
                info["errors_mentioned"].append(turn.get("content", "")[:100])
        
        # Limit lists
        for key in info:
            info[key] = info[key][:5]  # Keep max 5 of each
        
        return info
    
    async def get_user_context(
        self,
        user_id: str,
        max_sessions: int = 5,
    ) -> Dict[str, Any]:
        """
        Get cross-session context for a user.
        
        Retrieves recent session summaries to provide continuity.
        
        Args:
            user_id: User to get context for
            max_sessions: Maximum number of recent sessions to include
            
        Returns:
            Context dict with recent summaries and extracted patterns
        """
        memory = self._get_memory_manager()
        if not memory:
            return {"user_id": user_id, "sessions": [], "patterns": {}}
        
        try:
            from mycosoft_mas.core.routers.memory_api import MemoryScope
            
            # Read all session archives for user
            user_memory = await memory.read(
                scope=MemoryScope.USER,
                namespace=user_id,
            )
            
            if not user_memory or not isinstance(user_memory, dict):
                return {"user_id": user_id, "sessions": [], "patterns": {}}
            
            # Filter to session archives
            sessions = []
            for key, value in user_memory.items():
                if key.startswith("session_archive_") and isinstance(value, dict):
                    sessions.append(value)
            
            # Sort by date and limit
            sessions.sort(
                key=lambda s: s.get("summarized_at", ""),
                reverse=True
            )
            sessions = sessions[:max_sessions]
            
            # Extract patterns across sessions
            patterns = self._extract_patterns(sessions)
            
            return {
                "user_id": user_id,
                "sessions": sessions,
                "patterns": patterns,
                "total_sessions": len(sessions),
            }
            
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            return {"user_id": user_id, "sessions": [], "patterns": {}}
    
    def _extract_patterns(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract patterns across multiple sessions."""
        patterns = {
            "frequent_topics": {},
            "common_preferences": [],
            "recurring_issues": [],
        }
        
        for session in sessions:
            extracted = session.get("extracted_info", {})
            
            # Collect preferences
            for pref in extracted.get("preferences", []):
                if pref not in patterns["common_preferences"]:
                    patterns["common_preferences"].append(pref)
            
            # Collect errors as recurring issues
            for error in extracted.get("errors_mentioned", []):
                if error not in patterns["recurring_issues"]:
                    patterns["recurring_issues"].append(error)
        
        # Limit
        patterns["common_preferences"] = patterns["common_preferences"][:10]
        patterns["recurring_issues"] = patterns["recurring_issues"][:10]
        
        return patterns


# Singleton instance
_summarization_service: Optional[MemorySummarizationService] = None


def get_summarization_service() -> MemorySummarizationService:
    """Get singleton summarization service."""
    global _summarization_service
    if _summarization_service is None:
        _summarization_service = MemorySummarizationService()
    return _summarization_service
