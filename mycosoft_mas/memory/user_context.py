"""
User Context - February 6, 2026

Cross-session user preferences and history.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import asyncpg
except ImportError:
    asyncpg = None


@dataclass
class UserContext:
    """User preferences and cross-session context."""
    user_id: str
    display_name: Optional[str] = None
    language: str = "en"
    timezone: str = "UTC"
    preferred_layers: List[str] = field(default_factory=list)
    preferred_regions: List[Dict] = field(default_factory=list)
    default_zoom_level: int = 5
    preferred_species: List[str] = field(default_factory=list)
    preferred_entity_types: List[str] = field(default_factory=list)
    recent_entities: List[Dict] = field(default_factory=list)
    recent_regions: List[Dict] = field(default_factory=list)
    recent_time_ranges: List[Dict] = field(default_factory=list)
    recent_queries: List[str] = field(default_factory=list)
    saved_views: List[Dict] = field(default_factory=list)
    conversation_summaries: List[Dict] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_active_at: Optional[str] = None


class UserContextManager:
    """Manages user context persistence."""
    
    MAX_RECENT_ENTITIES = 50
    MAX_RECENT_QUERIES = 100
    MAX_SAVED_VIEWS = 20
    MAX_SUMMARIES = 50
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL",
            os.getenv("MINDEX_DATABASE_URL", "postgresql://mindex:mindex@localhost:5432/mindex")
        )
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> None:
        if asyncpg is None:
            raise ImportError("asyncpg required")
        self.pool = await asyncpg.create_pool(self.connection_string, min_size=2, max_size=10)
    
    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
    
    async def get_context(self, user_id: str) -> Optional[UserContext]:
        """Get user context."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mindex.user_contexts WHERE user_id = $1",
                user_id
            )
            
            if not row:
                return None
            
            preferences = row["preferences"] or {}
            recent = row["recent_activity"] or {}
            
            return UserContext(
                user_id=row["user_id"],
                display_name=row["display_name"],
                language=row["language"],
                timezone=row["timezone"],
                preferred_layers=preferences.get("layers", []),
                preferred_regions=preferences.get("regions", []),
                default_zoom_level=preferences.get("zoom", 5),
                preferred_species=preferences.get("species", []),
                preferred_entity_types=preferences.get("entity_types", []),
                recent_entities=recent.get("entities", []),
                recent_regions=recent.get("regions", []),
                recent_time_ranges=recent.get("time_ranges", []),
                recent_queries=recent.get("queries", []),
                saved_views=row["saved_views"] or [],
                conversation_summaries=row["conversation_summaries"] or [],
                created_at=row["created_at"].isoformat() if row["created_at"] else None,
                updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
                last_active_at=row["last_active_at"].isoformat() if row["last_active_at"] else None,
            )
    
    async def create_context(
        self,
        user_id: str,
        display_name: Optional[str] = None,
    ) -> UserContext:
        """Create new user context."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.user_contexts (user_id, display_name)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO NOTHING
                """,
                user_id,
                display_name,
            )
        
        return await self.get_context(user_id) or UserContext(user_id=user_id)
    
    async def update_context(self, context: UserContext) -> UserContext:
        """Update user context."""
        preferences = {
            "layers": context.preferred_layers,
            "regions": context.preferred_regions,
            "zoom": context.default_zoom_level,
            "species": context.preferred_species,
            "entity_types": context.preferred_entity_types,
        }
        
        recent = {
            "entities": context.recent_entities[:self.MAX_RECENT_ENTITIES],
            "regions": context.recent_regions[:20],
            "time_ranges": context.recent_time_ranges[:20],
            "queries": context.recent_queries[:self.MAX_RECENT_QUERIES],
        }
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE mindex.user_contexts
                SET display_name = $2,
                    language = $3,
                    timezone = $4,
                    preferences = $5,
                    recent_activity = $6,
                    saved_views = $7,
                    conversation_summaries = $8,
                    last_active_at = NOW()
                WHERE user_id = $1
                """,
                context.user_id,
                context.display_name,
                context.language,
                context.timezone,
                json.dumps(preferences),
                json.dumps(recent),
                json.dumps(context.saved_views[:self.MAX_SAVED_VIEWS]),
                json.dumps(context.conversation_summaries[:self.MAX_SUMMARIES]),
            )
        
        return await self.get_context(context.user_id)
    
    async def track_entity_view(
        self,
        user_id: str,
        entity_id: str,
        entity_type: str,
        entity_name: str,
    ) -> None:
        """Track that user viewed an entity."""
        context = await self.get_context(user_id)
        if not context:
            context = await self.create_context(user_id)
        
        entry = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "entity_name": entity_name,
            "viewed_at": datetime.utcnow().isoformat(),
        }
        
        # Remove duplicate if exists
        context.recent_entities = [
            e for e in context.recent_entities
            if e.get("entity_id") != entity_id
        ]
        
        # Add to front
        context.recent_entities.insert(0, entry)
        
        await self.update_context(context)
    
    async def add_query(self, user_id: str, query: str) -> None:
        """Add a query to history."""
        context = await self.get_context(user_id)
        if not context:
            context = await self.create_context(user_id)
        
        if query not in context.recent_queries:
            context.recent_queries.insert(0, query)
        
        await self.update_context(context)
    
    async def get_context_for_llm(self, user_id: str) -> str:
        """Get context formatted for LLM prompts."""
        context = await self.get_context(user_id)
        if not context:
            return "No user context available."
        
        parts = []
        
        if context.recent_entities:
            entities = context.recent_entities[:5]
            parts.append(f"Recently viewed: {', '.join(e['entity_name'] for e in entities)}")
        
        if context.preferred_layers:
            parts.append(f"Preferred layers: {', '.join(context.preferred_layers[:5])}")
        
        if context.recent_queries:
            parts.append(f"Recent queries: {', '.join(context.recent_queries[:3])}")
        
        return " | ".join(parts) if parts else "No specific preferences."


# Global instance
_context_manager: Optional[UserContextManager] = None


async def get_context_manager() -> UserContextManager:
    global _context_manager
    if _context_manager is None:
        _context_manager = UserContextManager()
        await _context_manager.initialize()
    return _context_manager