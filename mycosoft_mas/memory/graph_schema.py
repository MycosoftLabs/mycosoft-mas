"""
Graph Schema - February 6, 2026

Core data types for the knowledge graph.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""
    SPECIES = "species"
    DEVICE = "device"
    LOCATION = "location"
    EVENT = "event"
    USER = "user"
    SESSION = "session"
    CONCEPT = "concept"
    PREDICTION = "prediction"
    OBSERVATION = "observation"
    ENTITY = "entity"
    FACT = "fact"


class EdgeType(str, Enum):
    """Types of edges in the knowledge graph."""
    RELATED_TO = "related_to"
    CONTAINS = "contains"
    LOCATED_AT = "located_at"
    OBSERVED_BY = "observed_by"
    BELONGS_TO = "belongs_to"
    DERIVED_FROM = "derived_from"
    SIMILAR_TO = "similar_to"
    PRECEDED_BY = "preceded_by"
    FOLLOWED_BY = "followed_by"
    CAUSED_BY = "caused_by"
    PART_OF = "part_of"


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    node_type: NodeType
    name: str
    description: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    source: Optional[str] = None
    confidence: float = 1.0
    importance: float = 0.5
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    is_deleted: bool = False

    @classmethod
    def from_db_row(cls, row: Dict) -> "KnowledgeNode":
        return cls(
            id=str(row["id"]),
            node_type=NodeType(row["node_type"]),
            name=row["name"],
            description=row.get("description"),
            properties=row.get("properties", {}),
            embedding=row.get("embedding"),
            source=row.get("source"),
            confidence=row.get("confidence", 1.0),
            importance=row.get("importance", 0.5),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            last_accessed_at=row.get("last_accessed_at"),
            is_deleted=row.get("is_deleted", False),
        )


@dataclass
class KnowledgeEdge:
    """An edge in the knowledge graph."""
    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    is_bidirectional: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: Dict) -> "KnowledgeEdge":
        return cls(
            id=str(row["id"]),
            source_id=str(row["source_id"]),
            target_id=str(row["target_id"]),
            edge_type=EdgeType(row["edge_type"]),
            properties=row.get("properties", {}),
            weight=row.get("weight", 1.0),
            is_bidirectional=row.get("is_bidirectional", False),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )


@dataclass
class GraphSearchResult:
    """Result from a graph search."""
    nodes: List[KnowledgeNode]
    edges: List[KnowledgeEdge]
    total_count: int


@dataclass
class GraphTraversalResult:
    """Result from graph traversal."""
    start_node: KnowledgeNode
    neighbors: List[Dict[str, Any]]
    depth: int


@dataclass
class SemanticSearchResult:
    """Result from semantic search."""
    node: KnowledgeNode
    similarity: float


@dataclass
class EntityReference:
    """Reference to an entity viewed by user."""
    entity_id: str
    entity_type: str
    entity_name: str
    viewed_at: str


@dataclass
class BoundingBox:
    """Geographic bounding box."""
    north: float
    south: float
    east: float
    west: float


@dataclass
class TimeRange:
    """Time range specification."""
    start: str
    end: str


@dataclass
class SavedView:
    """User saved map view."""
    id: str
    name: str
    center_lat: float
    center_lng: float
    zoom: int
    layers: List[str]
    filters: Dict[str, Any]
    created_at: str


@dataclass
class ConversationSummary:
    """Summary of a conversation session."""
    session_id: str
    summary: str
    key_topics: List[str]
    timestamp: str