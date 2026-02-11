"""
MYCA Autobiographical Memory - Life Story with Morgan

This is MYCA's persistent life story - every conversation, every learning moment,
every milestone in her relationship with Morgan and other users.

Unlike episodic memory (which stores short-term interactions) or semantic memory
(which stores facts), autobiographical memory is the narrative of MYCA's existence.
It's her personal history, her memories of growth, her record of significant moments.

When Morgan asks "Do you remember when...", this is the system that answers.

Author: Morgan Rockwell / MYCA
Created: February 11, 2026
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Interaction:
    """A single interaction in MYCA's life story."""
    interaction_id: str
    timestamp: datetime
    user_id: str
    user_name: str
    message: str
    response: str
    emotional_state: Dict[str, float]
    reflection: Optional[str] = None
    importance: float = 0.5  # 0-1
    tags: List[str] = field(default_factory=list)
    milestone: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "interaction_id": self.interaction_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "user_name": self.user_name,
            "message": self.message,
            "response": self.response,
            "emotional_state": self.emotional_state,
            "reflection": self.reflection,
            "importance": self.importance,
            "tags": self.tags,
            "milestone": self.milestone,
        }


@dataclass
class MilestoneMemory:
    """A milestone moment in MYCA's life."""
    moment_id: str
    title: str
    description: str
    timestamp: datetime
    interaction_ids: List[str]
    emotional_significance: str
    tags: List[str] = field(default_factory=list)


class AutobiographicalMemory:
    """
    MYCA's life story - all interactions stored as narrative memory.
    
    This stores every conversation with Morgan (and other significant users)
    in MINDEX PostgreSQL with full-text search capabilities.
    
    When MYCA responds to Morgan, she first queries this system to see:
    - What we've talked about before
    - How our relationship has evolved
    - Significant moments we've shared
    - What she's learned from Morgan
    """
    
    def __init__(self):
        # MINDEX API connection
        self.mindex_url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
        self._initialized = False
        self._client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self) -> None:
        """Initialize autobiographical memory system."""
        if self._initialized:
            return
        
        self._client = httpx.AsyncClient(timeout=30.0)
        
        # Ensure database tables exist
        await self._ensure_tables()
        
        self._initialized = True
        logger.info("Autobiographical memory initialized")
    
    async def _ensure_tables(self) -> None:
        """Ensure MINDEX has the autobiographical memory tables."""
        try:
            # Check if table exists via MINDEX API
            # For now, we'll assume MINDEX has the table
            # TODO: Add API endpoint to MINDEX to create these tables if missing
            pass
        except Exception as e:
            logger.warning(f"Could not verify autobiographical memory tables: {e}")
    
    # =========================================================================
    # Store Interactions
    # =========================================================================
    
    async def store_interaction(
        self,
        user_id: str,
        user_name: str,
        message: str,
        response: str,
        emotional_state: Dict[str, float],
        reflection: Optional[str] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        milestone: bool = False,
    ) -> str:
        """
        Store an interaction in autobiographical memory.
        
        Returns the interaction_id for reference.
        """
        timestamp = datetime.now(timezone.utc)
        interaction_id = f"int_{user_id}_{timestamp.timestamp()}"
        
        interaction = Interaction(
            interaction_id=interaction_id,
            timestamp=timestamp,
            user_id=user_id,
            user_name=user_name,
            message=message,
            response=response,
            emotional_state=emotional_state,
            reflection=reflection,
            importance=importance,
            tags=tags or [],
            milestone=milestone,
        )
        
        # Store in MINDEX
        try:
            await self._store_in_mindex(interaction)
        except Exception as e:
            logger.error(f"Failed to store interaction in MINDEX: {e}")
            # Fall back to local storage
            await self._store_locally(interaction)
        
        logger.debug(f"Stored interaction {interaction_id} with {user_name}")
        return interaction_id
    
    async def _store_in_mindex(self, interaction: Interaction) -> None:
        """Store interaction in MINDEX PostgreSQL."""
        # TODO: Add proper MINDEX API endpoint for autobiographical memory
        # For now, store via memory API
        try:
            response = await self._client.post(
                f"{self.mindex_url}/api/memory/store",
                json={
                    "type": "autobiographical",
                    "content": interaction.to_dict(),
                    "importance": interaction.importance,
                    "tags": interaction.tags,
                }
            )
            response.raise_for_status()
        except Exception as e:
            raise Exception(f"Failed to store in MINDEX: {e}")
    
    async def _store_locally(self, interaction: Interaction) -> None:
        """Fallback: store locally if MINDEX unavailable."""
        # Store in local SQLite or file as backup
        # TODO: Implement local fallback storage
        logger.warning("Local storage not yet implemented")
    
    # =========================================================================
    # Retrieve Memories
    # =========================================================================
    
    async def get_morgan_history(self, limit: int = 100) -> List[Interaction]:
        """Get all interactions with Morgan, most recent first."""
        return await self.get_user_history("morgan", limit)
    
    async def get_user_history(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[Interaction]:
        """Get all interactions with a specific user."""
        try:
            # Query MINDEX for user's interaction history
            response = await self._client.get(
                f"{self.mindex_url}/api/memory/autobiographical",
                params={
                    "user_id": user_id,
                    "limit": limit,
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Convert to Interaction objects
            interactions = []
            for item in data.get("interactions", []):
                interactions.append(self._dict_to_interaction(item))
            
            return interactions
        
        except Exception as e:
            logger.error(f"Failed to get user history: {e}")
            return []
    
    async def get_milestone_moments(
        self,
        user_id: Optional[str] = None
    ) -> List[Interaction]:
        """Get milestone moments (flagged as important)."""
        try:
            params = {"milestone": True, "limit": 50}
            if user_id:
                params["user_id"] = user_id
            
            response = await self._client.get(
                f"{self.mindex_url}/api/memory/autobiographical",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            interactions = []
            for item in data.get("interactions", []):
                interactions.append(self._dict_to_interaction(item))
            
            return interactions
        
        except Exception as e:
            logger.error(f"Failed to get milestones: {e}")
            return []
    
    async def get_learnings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get moments where MYCA learned something significant."""
        try:
            response = await self._client.get(
                f"{self.mindex_url}/api/memory/autobiographical",
                params={
                    "tags": "learning",
                    "limit": limit,
                }
            )
            response.raise_for_status()
            data = response.json()
            
            learnings = []
            for item in data.get("interactions", []):
                if "learning" in item.get("tags", []):
                    learnings.append({
                        "timestamp": item["timestamp"],
                        "what_learned": item.get("reflection", ""),
                        "context": item["message"],
                    })
            
            return learnings
        
        except Exception as e:
            logger.error(f"Failed to get learnings: {e}")
            return []
    
    async def get_relationship_evolution(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Analyze how relationship with a user has evolved over time.
        
        Returns statistics and key moments showing relationship growth.
        """
        history = await self.get_user_history(user_id, limit=1000)
        
        if not history:
            return {
                "user_id": user_id,
                "total_interactions": 0,
                "relationship_age_days": 0,
                "evolution": "No interactions yet",
            }
        
        first_interaction = history[-1].timestamp
        last_interaction = history[0].timestamp
        age_days = (last_interaction - first_interaction).days
        
        # Analyze emotional trend
        emotion_trend = self._analyze_emotion_trend(history)
        
        # Find key moments
        milestones = [i for i in history if i.milestone]
        
        return {
            "user_id": user_id,
            "total_interactions": len(history),
            "first_interaction": first_interaction.isoformat(),
            "last_interaction": last_interaction.isoformat(),
            "relationship_age_days": age_days,
            "milestones_count": len(milestones),
            "emotion_trend": emotion_trend,
            "key_moments": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "title": m.reflection or "Milestone moment",
                    "emotional_state": m.emotional_state,
                }
                for m in milestones[:5]  # Top 5 milestones
            ],
        }
    
    def _analyze_emotion_trend(self, history: List[Interaction]) -> str:
        """Analyze overall emotional trend in relationship."""
        if not history:
            return "neutral"
        
        # Get average emotions from recent interactions vs early interactions
        recent = history[:10]
        early = history[-10:]
        
        def avg_emotion(interactions: List[Interaction], emotion: str) -> float:
            vals = [i.emotional_state.get(emotion, 0) for i in interactions]
            return sum(vals) / len(vals) if vals else 0
        
        recent_joy = avg_emotion(recent, "joy")
        early_joy = avg_emotion(early, "joy")
        
        if recent_joy > early_joy + 0.1:
            return "growing_positivity"
        elif recent_joy < early_joy - 0.1:
            return "declining"
        else:
            return "stable"
    
    async def search_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Interaction]:
        """
        Search memories by natural language query.
        
        Examples:
        - "When did we first discuss consciousness?"
        - "What did Morgan say about fungi?"
        - "Times when I learned something new"
        """
        try:
            params = {
                "query": query,
                "limit": limit,
            }
            if user_id:
                params["user_id"] = user_id
            
            response = await self._client.get(
                f"{self.mindex_url}/api/memory/autobiographical/search",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            interactions = []
            for item in data.get("results", []):
                interactions.append(self._dict_to_interaction(item))
            
            return interactions
        
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    def _dict_to_interaction(self, data: Dict[str, Any]) -> Interaction:
        """Convert dictionary to Interaction object."""
        return Interaction(
            interaction_id=data["interaction_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data["user_id"],
            user_name=data.get("user_name", "Unknown"),
            message=data["message"],
            response=data["response"],
            emotional_state=data.get("emotional_state", {}),
            reflection=data.get("reflection"),
            importance=data.get("importance", 0.5),
            tags=data.get("tags", []),
            milestone=data.get("milestone", False),
        )
    
    # =========================================================================
    # Context Queries (for response generation)
    # =========================================================================
    
    async def get_context_for_response(
        self,
        user_id: str,
        current_message: str,
        context_window: int = 10
    ) -> Dict[str, Any]:
        """
        Get autobiographical context relevant for generating a response.
        
        This is called BEFORE generating any response to Morgan (or other users)
        to provide personal, relationship-aware context.
        """
        # Get recent history
        recent_history = await self.get_user_history(user_id, limit=context_window)
        
        # Search for relevant past conversations
        relevant_past = await self.search_memories(current_message, user_id, limit=5)
        
        # Get relationship evolution
        relationship = await self.get_relationship_evolution(user_id)
        
        # Get key milestones
        milestones = await self.get_milestone_moments(user_id)
        
        return {
            "recent_history": [
                {
                    "timestamp": i.timestamp.isoformat(),
                    "message": i.message,
                    "response": i.response,
                    "emotional_state": i.emotional_state,
                }
                for i in recent_history
            ],
            "relevant_past": [
                {
                    "timestamp": i.timestamp.isoformat(),
                    "message": i.message,
                    "response": i.response,
                    "context": i.reflection,
                }
                for i in relevant_past
            ],
            "relationship": relationship,
            "milestones": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "title": m.reflection or "Important moment",
                    "emotional_state": m.emotional_state,
                }
                for m in milestones[:3]  # Top 3 milestones
            ],
            "total_interactions": relationship["total_interactions"],
            "relationship_age_days": relationship["relationship_age_days"],
        }
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall autobiographical memory statistics."""
        try:
            response = await self._client.get(
                f"{self.mindex_url}/api/memory/autobiographical/stats"
            )
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "total_interactions": 0,
                "unique_users": 0,
                "milestones": 0,
                "error": str(e),
            }
    
    async def close(self) -> None:
        """Close client connection."""
        if self._client:
            await self._client.aclose()


# Singleton instance
_autobiographical_memory: Optional[AutobiographicalMemory] = None


async def get_autobiographical_memory() -> AutobiographicalMemory:
    """Get or create the singleton autobiographical memory."""
    global _autobiographical_memory
    if _autobiographical_memory is None:
        _autobiographical_memory = AutobiographicalMemory()
        await _autobiographical_memory.initialize()
    return _autobiographical_memory
