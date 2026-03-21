"""
Memory Module - February 6, 2026

CREP Memory System Components.
"""

from .coordinator import MemoryCoordinator, get_memory_coordinator
from .embeddings import BaseEmbedder, get_embedder
from .episodic_memory import Episode
from .episodic_memory import EpisodicMemory as PostgresEpisodicMemory
from .graph_memory import GraphMemory
from .graph_schema import (
    EdgeType,
    GraphSearchResult,
    GraphTraversalResult,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
    SemanticSearchResult,
)
from .long_term import Fact, LongTermMemory
from .mindex_graph import MindexGraph, get_graph
from .procedural_memory import ProceduralMemory
from .semantic_memory import Fact as SemanticFact
from .semantic_memory import SemanticMemory
from .session_memory import SessionMemory, SessionMemoryManager, get_session_manager
from .short_term import ShortTermMemory
from .temporal_patterns import TemporalPattern, TemporalPatternStore
from .user_context import UserContext, UserContextManager, get_context_manager
from .vector_memory import VectorMemory, get_vector_memory

__all__ = [
    # Schema
    "NodeType",
    "EdgeType",
    "KnowledgeNode",
    "KnowledgeEdge",
    "GraphSearchResult",
    "GraphTraversalResult",
    "SemanticSearchResult",
    # Graph
    "MindexGraph",
    "get_graph",
    # Embeddings
    "BaseEmbedder",
    "get_embedder",
    # Vector Memory
    "VectorMemory",
    "get_vector_memory",
    # Short/Long term memory
    "ShortTermMemory",
    "LongTermMemory",
    "Fact",
    # Graph memory
    "GraphMemory",
    # Coordinator
    "MemoryCoordinator",
    "get_memory_coordinator",
    # User Context
    "UserContext",
    "UserContextManager",
    "get_context_manager",
    # Session Memory
    "SessionMemory",
    "SessionMemoryManager",
    "get_session_manager",
    # Temporal patterns (biospheric sensor patterns)
    "TemporalPattern",
    "TemporalPatternStore",
    # Procedural memory
    "ProceduralMemory",
    # Persistent episodic memory
    "PostgresEpisodicMemory",
    "Episode",
    # Semantic memory
    "SemanticMemory",
    "SemanticFact",
]
