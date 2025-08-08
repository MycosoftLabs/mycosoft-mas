from __future__ import annotations

"""Simple event ingestion service for Mycosoft MAS.

This service ingests events from external systems and stores them in the
:class:`KnowledgeGraph`. Events must contain at minimum ``id``, ``type`` and
``data`` fields. An optional ``source`` field creates a relationship from the
source entity to the event node in the knowledge graph.
"""

from typing import Any, Dict
from datetime import datetime

from ..core.knowledge_graph import KnowledgeGraph


class EventIngestionService:
    """Service responsible for processing external events."""

    def __init__(self, knowledge_graph: KnowledgeGraph) -> None:
        self.knowledge_graph = knowledge_graph

    async def process_event(self, event: Dict[str, Any]) -> None:
        """Validate and ingest an event into the knowledge graph.

        Parameters
        ----------
        event:
            Dictionary containing the event payload. Must include ``id``,
            ``type`` and ``data`` keys. Optionally may include ``source`` and
            ``timestamp``.
        """
        required = {"id", "type", "data"}
        missing = required - event.keys()
        if missing:
            raise ValueError(f"Event missing required fields: {', '.join(sorted(missing))}")

        metadata = {
            "event_type": event["type"],
            "timestamp": event.get("timestamp", datetime.utcnow().isoformat()),
            "data": event["data"],
        }

        # Add event node
        await self.knowledge_graph.add_agent(event["id"], metadata)

        # Link to source if provided
        source = event.get("source")
        if source:
            if source not in self.knowledge_graph.graph:
                await self.knowledge_graph.add_agent(source, {"type": "source"})
            await self.knowledge_graph.add_relationship(source, event["id"], "generated")
