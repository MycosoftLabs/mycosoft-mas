"""
MINDEX Client

Client stub for MINDEX API integration.
MINDEX is a knowledge graph and data indexing service.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from mycosoft_mas.clients.base import BaseClient, ClientConfig, ClientError

logger = logging.getLogger(__name__)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class MINDEXEntity(BaseModel):
    """An entity in the MINDEX knowledge graph."""
    id: str
    type: str
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MINDEXRelation(BaseModel):
    """A relation between entities."""
    id: str
    source_id: str
    target_id: str
    relation_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class MINDEXSearchResult(BaseModel):
    """Search result from MINDEX."""
    entities: list[MINDEXEntity] = Field(default_factory=list)
    relations: list[MINDEXRelation] = Field(default_factory=list)
    total_count: int = 0
    query_time_ms: int = 0


class MINDEXIndexResult(BaseModel):
    """Result of indexing operation."""
    indexed_count: int = 0
    failed_count: int = 0
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# CLIENT
# =============================================================================

class MINDEXClient(BaseClient):
    """
    Client for MINDEX API.
    
    Provides methods for:
    - Searching the knowledge graph
    - Adding/updating entities
    - Managing relations
    - Semantic search
    
    Usage:
        client = MINDEXClient.from_env()
        
        # Search
        results = await client.search("fungal species", entity_type="Species")
        
        # Add entity
        entity = await client.add_entity(
            type="Species",
            name="Pleurotus ostreatus",
            properties={"common_name": "Oyster mushroom"},
        )
    """
    
    @classmethod
    def from_env(cls) -> "MINDEXClient":
        """Create client from environment variables."""
        config = ClientConfig(
            base_url=os.getenv("MINDEX_BASE_URL", "https://api.mindex.io"),
            api_key=os.getenv("MINDEX_API_KEY", ""),
            timeout=30,
            max_retries=3,
        )
        return cls(config)
    
    async def search(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        correlation_id: Optional[UUID] = None,
    ) -> MINDEXSearchResult:
        """
        Search the MINDEX knowledge graph.
        
        Args:
            query: Search query string
            entity_type: Optional entity type filter
            limit: Maximum results to return
            offset: Pagination offset
            correlation_id: Correlation ID for tracing
            
        Returns:
            MINDEXSearchResult with matching entities and relations
        """
        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
        }
        
        if entity_type:
            params["type"] = entity_type
        
        try:
            response = await self.get(
                "/v1/search",
                params=params,
                correlation_id=correlation_id,
            )
            return MINDEXSearchResult(**response)
        except ClientError as e:
            logger.error(f"MINDEX search failed: {e}")
            raise
    
    async def semantic_search(
        self,
        query: str,
        embedding: Optional[list[float]] = None,
        limit: int = 100,
        correlation_id: Optional[UUID] = None,
    ) -> MINDEXSearchResult:
        """
        Perform semantic search using embeddings.
        
        Args:
            query: Search query string
            embedding: Optional pre-computed embedding
            limit: Maximum results
            correlation_id: Correlation ID for tracing
            
        Returns:
            MINDEXSearchResult with semantically similar entities
        """
        data = {
            "query": query,
            "limit": limit,
        }
        
        if embedding:
            data["embedding"] = embedding
        
        try:
            response = await self.post(
                "/v1/search/semantic",
                data=data,
                correlation_id=correlation_id,
            )
            return MINDEXSearchResult(**response)
        except ClientError as e:
            logger.error(f"MINDEX semantic search failed: {e}")
            raise
    
    async def get_entity(
        self,
        entity_id: str,
        include_relations: bool = False,
        correlation_id: Optional[UUID] = None,
    ) -> Optional[MINDEXEntity]:
        """
        Get an entity by ID.
        
        Args:
            entity_id: Entity ID
            include_relations: Whether to include relations
            correlation_id: Correlation ID for tracing
            
        Returns:
            MINDEXEntity or None if not found
        """
        params = {"include_relations": include_relations}
        
        try:
            response = await self.get(
                f"/v1/entities/{entity_id}",
                params=params,
                correlation_id=correlation_id,
            )
            return MINDEXEntity(**response)
        except ClientError as e:
            if e.status_code == 404:
                return None
            raise
    
    async def add_entity(
        self,
        type: str,
        name: str,
        properties: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        correlation_id: Optional[UUID] = None,
    ) -> MINDEXEntity:
        """
        Add a new entity to the knowledge graph.
        
        Args:
            type: Entity type
            name: Entity name
            properties: Entity properties
            metadata: Additional metadata
            correlation_id: Correlation ID for tracing
            
        Returns:
            Created MINDEXEntity
        """
        data = {
            "type": type,
            "name": name,
            "properties": properties or {},
            "metadata": metadata or {},
        }
        
        response = await self.post(
            "/v1/entities",
            data=data,
            correlation_id=correlation_id,
        )
        return MINDEXEntity(**response)
    
    async def update_entity(
        self,
        entity_id: str,
        properties: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        correlation_id: Optional[UUID] = None,
    ) -> MINDEXEntity:
        """
        Update an existing entity.
        
        Args:
            entity_id: Entity ID to update
            properties: Updated properties
            metadata: Updated metadata
            correlation_id: Correlation ID for tracing
            
        Returns:
            Updated MINDEXEntity
        """
        data = {}
        
        if properties is not None:
            data["properties"] = properties
        if metadata is not None:
            data["metadata"] = metadata
        
        response = await self.put(
            f"/v1/entities/{entity_id}",
            data=data,
            correlation_id=correlation_id,
        )
        return MINDEXEntity(**response)
    
    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[dict[str, Any]] = None,
        correlation_id: Optional[UUID] = None,
    ) -> MINDEXRelation:
        """
        Add a relation between entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relation_type: Type of relation
            properties: Relation properties
            correlation_id: Correlation ID for tracing
            
        Returns:
            Created MINDEXRelation
        """
        data = {
            "source_id": source_id,
            "target_id": target_id,
            "relation_type": relation_type,
            "properties": properties or {},
        }
        
        response = await self.post(
            "/v1/relations",
            data=data,
            correlation_id=correlation_id,
        )
        return MINDEXRelation(**response)
    
    async def bulk_index(
        self,
        entities: list[dict[str, Any]],
        relations: Optional[list[dict[str, Any]]] = None,
        correlation_id: Optional[UUID] = None,
    ) -> MINDEXIndexResult:
        """
        Bulk index entities and relations.
        
        Args:
            entities: List of entity dicts
            relations: Optional list of relation dicts
            correlation_id: Correlation ID for tracing
            
        Returns:
            MINDEXIndexResult with indexing statistics
        """
        data = {
            "entities": entities,
            "relations": relations or [],
        }
        
        response = await self.post(
            "/v1/bulk",
            data=data,
            correlation_id=correlation_id,
        )
        return MINDEXIndexResult(**response)
