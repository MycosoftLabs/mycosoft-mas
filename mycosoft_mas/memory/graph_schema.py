"""
Graph Schema - February 6, 2026

Core data types for the knowledge graph.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(str, Enum):
    """Unified types of nodes in the knowledge graph.

    Merges types from persistent_graph (system/infra), mindex_graph (scientific),
    and palace (data sources) into a single comprehensive enum.
    """

    # Original graph_schema types
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

    # From persistent_graph (system architecture)
    SYSTEM = "system"
    AGENT = "agent"
    API = "api"
    SERVICE = "service"
    DATABASE = "database"
    FILE = "file"
    WORKFLOW = "workflow"
    MEMORY = "memory"

    # Scientific / MINDEX types
    TRAIT = "trait"
    COMPOUND = "compound"
    BEHAVIOR = "behavior"
    HABITAT = "habitat"
    GENE = "gene"
    PUBLICATION = "publication"

    # Palace / data source types
    CREP_EVENT = "crep_event"
    WEATHER = "weather"
    SENSOR = "sensor"
    WING = "wing"
    ROOM = "room"


class EdgeType(str, Enum):
    """Unified types of edges in the knowledge graph.

    Merges relationships from all three graph systems plus temporal
    predicates inspired by mempalace.
    """

    # Original graph_schema types
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

    # From persistent_graph
    DEPENDS_ON = "depends_on"
    CALLS = "calls"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    CONNECTS_TO = "connects_to"
    MANAGES = "manages"
    HOSTS = "hosts"
    IMPLEMENTS = "implements"

    # Scientific / MINDEX types
    IS_A = "is_a"
    HAS_TRAIT = "has_trait"
    FOUND_IN = "found_in"
    ENCODES = "encodes"

    # Temporal predicates (from mempalace)
    DECIDED = "decided"
    OBSERVED = "observed"
    DETECTED = "detected"
    PREDICTED = "predicted"
    MEASURED = "measured"


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
    """An edge in the knowledge graph with temporal validity."""

    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    is_bidirectional: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Temporal validity (from mempalace temporal knowledge graph)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    confidence: float = 1.0
    source_closet: Optional[str] = None
    source_file: Optional[str] = None

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
            valid_from=row.get("valid_from"),
            valid_to=row.get("valid_to"),
            confidence=row.get("confidence", 1.0),
            source_closet=row.get("source_closet"),
            source_file=row.get("source_file"),
        )

    @property
    def is_currently_valid(self) -> bool:
        """Check if this edge is currently valid (no end date or future end)."""
        if self.valid_to is None:
            return True
        now = datetime.utcnow()
        return self.valid_to > now


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
