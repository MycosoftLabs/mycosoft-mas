"""
Procedural Memory - February 28, 2026

Persistent storage for learned procedures, playbooks, and step-by-step workflows.
Backed by MYCAMemory with the PROCEDURAL layer (PostgreSQL).
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from .myca_memory import MemoryLayer, MemoryQuery, MYCAMemory


class ProceduralMemory:
    """Procedural memory for storing and retrieving learned procedures."""

    def __init__(self, memory: MYCAMemory):
        self._memory = memory

    async def store_procedure(
        self,
        *,
        name: str,
        steps: List[Dict[str, Any]],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source: str = "system",
        importance: float = 0.6,
    ) -> UUID:
        """Store a procedural workflow."""
        normalized = name.strip().lower()
        payload = {
            "name": name.strip(),
            "description": description or "",
            "steps": steps,
            "source": source,
        }
        entry_tags = (tags or []) + ["procedure", f"procedure:{normalized}"]
        return await self._memory.remember(
            content=payload,
            layer=MemoryLayer.PROCEDURAL,
            importance=importance,
            tags=entry_tags,
        )

    async def get_procedure(self, name: str) -> Optional[Dict[str, Any]]:
        """Fetch a single procedure by name."""
        normalized = name.strip().lower()
        query = MemoryQuery(
            layer=MemoryLayer.PROCEDURAL,
            tags=[f"procedure:{normalized}"],
            limit=1,
        )
        results = await self._memory.recall(query=query)
        if not results:
            return None
        return results[0].content

    async def list_procedures(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List stored procedures."""
        query = MemoryQuery(
            layer=MemoryLayer.PROCEDURAL,
            tags=["procedure"],
            limit=limit,
        )
        entries = await self._memory.recall(query=query)
        return [entry.content for entry in entries]

    async def search_procedures(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search procedures by name/description."""
        query = MemoryQuery(
            layer=MemoryLayer.PROCEDURAL,
            tags=["procedure"],
            limit=limit * 3,
        )
        entries = await self._memory.recall(query=query)
        matches = []
        lowered = query_text.lower()
        for entry in entries:
            name = str(entry.content.get("name", "")).lower()
            description = str(entry.content.get("description", "")).lower()
            if lowered in name or lowered in description:
                matches.append(entry.content)
            if len(matches) >= limit:
                break
        return matches
