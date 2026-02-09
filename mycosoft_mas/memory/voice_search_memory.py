"""
Voice Search Memory Bridge - February 5, 2026

Bridges PersonaPlex voice sessions with the Search Memory system:
- Links voice sessions to search sessions
- Enables voice-initiated search queries
- Provides voice context to search AI conversations
- Tracks species discussed via voice for search interest enrichment

This bridge allows seamless transition between:
1. User searching visually -> Asking voice questions about results
2. User asking voice questions -> Opening visual search for details
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger("VoiceSearchMemory")


@dataclass
class VoiceSearchLink:
    """Links a voice session to a search session."""
    id: UUID = field(default_factory=uuid4)
    voice_session_id: UUID = None
    search_session_id: UUID = None
    user_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    voice_queries: List[str] = field(default_factory=list)
    species_discussed: List[str] = field(default_factory=list)
    topics_discussed: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "voice_session_id": str(self.voice_session_id) if self.voice_session_id else None,
            "search_session_id": str(self.search_session_id) if self.search_session_id else None,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "voice_queries": self.voice_queries,
            "species_discussed": self.species_discussed,
            "topics_discussed": self.topics_discussed
        }


class VoiceSearchBridge:
    """
    Bridges voice sessions with search sessions for seamless context.
    
    Capabilities:
    - Link voice session to active search session
    - Record voice queries for search enrichment
    - Track species discussed for MINDEX interest
    - Provide unified context for AI responses
    """
    
    def __init__(self):
        self._links: Dict[UUID, VoiceSearchLink] = {}  # link_id -> link
        self._voice_to_link: Dict[UUID, UUID] = {}  # voice_session_id -> link_id
        self._search_to_link: Dict[UUID, UUID] = {}  # search_session_id -> link_id
        self._user_to_link: Dict[str, UUID] = {}  # user_id -> active link_id
        self._initialized = False
        
        # Reference to memory systems
        self._personaplex_memory = None
        self._search_memory = None
    
    async def initialize(self) -> None:
        """Initialize the bridge with memory system references."""
        if self._initialized:
            return
        
        try:
            # Get PersonaPlex memory
            from mycosoft_mas.memory.personaplex_memory import get_personaplex_memory
            self._personaplex_memory = await get_personaplex_memory()
            
            # Get Search memory
            from mycosoft_mas.memory.search_memory import get_search_memory
            self._search_memory = await get_search_memory()
            
            self._initialized = True
            logger.info("Voice-Search bridge initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize bridge: {e}")
            # Still mark as initialized to allow partial functionality
            self._initialized = True
    
    async def create_link(
        self,
        user_id: str,
        voice_session_id: Optional[UUID] = None,
        search_session_id: Optional[UUID] = None
    ) -> VoiceSearchLink:
        """
        Create a link between voice and search sessions.
        
        Args:
            user_id: User identifier
            voice_session_id: Optional voice session to link
            search_session_id: Optional search session to link
        
        Returns:
            Created link object
        """
        if not self._initialized:
            await self.initialize()
        
        # Check if user already has an active link
        if user_id in self._user_to_link:
            existing_link_id = self._user_to_link[user_id]
            if existing_link_id in self._links:
                link = self._links[existing_link_id]
                
                # Update with new session IDs if provided
                if voice_session_id and not link.voice_session_id:
                    link.voice_session_id = voice_session_id
                    self._voice_to_link[voice_session_id] = link.id
                
                if search_session_id and not link.search_session_id:
                    link.search_session_id = search_session_id
                    self._search_to_link[search_session_id] = link.id
                
                link.last_activity = datetime.now(timezone.utc)
                logger.debug(f"Updated existing link {link.id} for user {user_id}")
                return link
        
        # Create new link
        link = VoiceSearchLink(
            voice_session_id=voice_session_id,
            search_session_id=search_session_id,
            user_id=user_id
        )
        
        self._links[link.id] = link
        self._user_to_link[user_id] = link.id
        
        if voice_session_id:
            self._voice_to_link[voice_session_id] = link.id
        if search_session_id:
            self._search_to_link[search_session_id] = link.id
        
        logger.info(f"Created voice-search link {link.id} for user {user_id}")
        return link
    
    async def link_voice_to_search(
        self,
        voice_session_id: UUID,
        search_session_id: UUID
    ) -> Optional[VoiceSearchLink]:
        """Link an existing voice session to a search session."""
        # Find link by voice session
        link_id = self._voice_to_link.get(voice_session_id)
        if link_id and link_id in self._links:
            link = self._links[link_id]
            link.search_session_id = search_session_id
            self._search_to_link[search_session_id] = link.id
            link.last_activity = datetime.now(timezone.utc)
            return link
        
        # Find link by search session
        link_id = self._search_to_link.get(search_session_id)
        if link_id and link_id in self._links:
            link = self._links[link_id]
            link.voice_session_id = voice_session_id
            self._voice_to_link[voice_session_id] = link.id
            link.last_activity = datetime.now(timezone.utc)
            return link
        
        return None
    
    async def record_voice_query(
        self,
        voice_session_id: UUID,
        query: str,
        species_mentioned: Optional[List[str]] = None,
        topic: Optional[str] = None
    ) -> bool:
        """
        Record a voice query and propagate to search memory.
        
        Args:
            voice_session_id: Voice session ID
            query: The voice query text
            species_mentioned: Optional species IDs mentioned
            topic: Optional topic category
        
        Returns:
            True if recorded successfully
        """
        if not self._initialized:
            await self.initialize()
        
        link_id = self._voice_to_link.get(voice_session_id)
        if not link_id or link_id not in self._links:
            return False
        
        link = self._links[link_id]
        link.voice_queries.append(query)
        link.last_activity = datetime.now(timezone.utc)
        
        if species_mentioned:
            link.species_discussed.extend(species_mentioned)
        
        if topic and topic not in link.topics_discussed:
            link.topics_discussed.append(topic)
        
        # Propagate to search memory if linked
        if link.search_session_id and self._search_memory:
            try:
                # Add voice query to search session
                await self._search_memory.add_query(
                    session_id=link.search_session_id,
                    query=query,
                    source="voice"
                )
                
                # Record species focus
                if species_mentioned:
                    for species_id in species_mentioned:
                        await self._search_memory.record_focus(
                            session_id=link.search_session_id,
                            species_id=species_id,
                            topic=topic
                        )
                
                logger.debug(f"Propagated voice query to search session {link.search_session_id}")
                
            except Exception as e:
                logger.error(f"Failed to propagate to search memory: {e}")
        
        return True
    
    async def record_voice_ai_exchange(
        self,
        voice_session_id: UUID,
        role: str,
        content: str,
        topic: Optional[str] = None
    ) -> bool:
        """
        Record a voice AI exchange and propagate to search memory.
        
        Args:
            voice_session_id: Voice session ID
            role: Message role ('user' or 'assistant')
            content: Message content
            topic: Optional topic context
        
        Returns:
            True if recorded successfully
        """
        if not self._initialized:
            await self.initialize()
        
        link_id = self._voice_to_link.get(voice_session_id)
        if not link_id or link_id not in self._links:
            return False
        
        link = self._links[link_id]
        link.last_activity = datetime.now(timezone.utc)
        
        # Propagate to search memory if linked
        if link.search_session_id and self._search_memory:
            try:
                await self._search_memory.add_ai_turn(
                    session_id=link.search_session_id,
                    role=role,
                    content=content,
                    topic=topic
                )
                logger.debug(f"Propagated AI turn to search session")
            except Exception as e:
                logger.error(f"Failed to propagate AI turn: {e}")
        
        return True
    
    async def get_search_context_for_voice(
        self,
        voice_session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get search session context for a voice session.
        
        Enables voice responses to be aware of what the user is viewing/searching.
        
        Args:
            voice_session_id: Voice session ID
        
        Returns:
            Search session context dict or None
        """
        if not self._initialized:
            await self.initialize()
        
        link_id = self._voice_to_link.get(voice_session_id)
        if not link_id or link_id not in self._links:
            return None
        
        link = self._links[link_id]
        if not link.search_session_id or not self._search_memory:
            return None
        
        try:
            context = await self._search_memory.get_session_context(link.search_session_id)
            if "error" not in context:
                # Enhance with link data
                context["voice_linked"] = True
                context["voice_queries"] = link.voice_queries[-5:]
                context["species_discussed_voice"] = list(set(link.species_discussed))[-5:]
                return context
        except Exception as e:
            logger.error(f"Failed to get search context: {e}")
        
        return None
    
    async def get_voice_context_for_search(
        self,
        search_session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get voice session context for a search session.
        
        Enables search AI to know what the user has asked via voice.
        
        Args:
            search_session_id: Search session ID
        
        Returns:
            Voice session context dict or None
        """
        if not self._initialized:
            await self.initialize()
        
        link_id = self._search_to_link.get(search_session_id)
        if not link_id or link_id not in self._links:
            return None
        
        link = self._links[link_id]
        if not link.voice_session_id or not self._personaplex_memory:
            return None
        
        try:
            # Get voice session from PersonaPlex memory
            voice_sessions = await self._personaplex_memory.get_user_context(link.user_id)
            
            return {
                "voice_linked": True,
                "voice_session_id": str(link.voice_session_id),
                "voice_queries": link.voice_queries[-5:],
                "species_discussed": list(set(link.species_discussed))[-5:],
                "topics_discussed": list(set(link.topics_discussed)),
                "sessions_count": voice_sessions.get("sessions_count", 0) if voice_sessions else 0
            }
        except Exception as e:
            logger.error(f"Failed to get voice context: {e}")
        
        return None
    
    async def end_link(self, link_id: UUID) -> Optional[Dict[str, Any]]:
        """
        End a voice-search link and return summary.
        
        Args:
            link_id: Link ID to end
        
        Returns:
            Link summary dict or None
        """
        link = self._links.pop(link_id, None)
        if not link:
            return None
        
        # Cleanup mappings
        if link.voice_session_id:
            self._voice_to_link.pop(link.voice_session_id, None)
        if link.search_session_id:
            self._search_to_link.pop(link.search_session_id, None)
        if link.user_id:
            self._user_to_link.pop(link.user_id, None)
        
        summary = link.to_dict()
        summary["duration_seconds"] = (datetime.now(timezone.utc) - link.created_at).total_seconds()
        summary["voice_query_count"] = len(link.voice_queries)
        summary["unique_species"] = len(set(link.species_discussed))
        
        logger.info(f"Ended link {link_id} with {len(link.voice_queries)} voice queries")
        return summary
    
    async def end_user_link(self, user_id: str) -> Optional[Dict[str, Any]]:
        """End the active link for a user."""
        link_id = self._user_to_link.get(user_id)
        if link_id:
            return await self.end_link(link_id)
        return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "active_links": len(self._links),
            "voice_linked": len(self._voice_to_link),
            "search_linked": len(self._search_to_link),
            "users_with_links": len(self._user_to_link),
            "initialized": self._initialized,
            "personaplex_connected": self._personaplex_memory is not None,
            "search_memory_connected": self._search_memory is not None
        }
    
    async def shutdown(self) -> None:
        """Shutdown the bridge."""
        # End all active links
        for link_id in list(self._links.keys()):
            await self.end_link(link_id)
        
        logger.info("Voice-Search bridge shutdown")


# Singleton instance
_voice_search_bridge: Optional[VoiceSearchBridge] = None


async def get_voice_search_bridge() -> VoiceSearchBridge:
    """Get or create the singleton voice-search bridge."""
    global _voice_search_bridge
    if _voice_search_bridge is None:
        _voice_search_bridge = VoiceSearchBridge()
        await _voice_search_bridge.initialize()
    return _voice_search_bridge