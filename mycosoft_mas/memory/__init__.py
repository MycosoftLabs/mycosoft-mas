"""
Memory Module - February 6, 2026

CREP Memory System Components.
"""

from .graph_schema import (
    NodeType,
    EdgeType,
    KnowledgeNode,
    KnowledgeEdge,
    GraphSearchResult,
    GraphTraversalResult,
    SemanticSearchResult,
)
from .mindex_graph import MindexGraph, get_graph
from .embeddings import BaseEmbedder, get_embedder
from .vector_memory import VectorMemory, get_vector_memory
from .short_term import ShortTermMemory
from .long_term import LongTermMemory, Fact
from .graph_memory import GraphMemory
from .coordinator import MemoryCoordinator, get_memory_coordinator
from .user_context import UserContext, UserContextManager, get_context_manager
from .session_memory import SessionMemory, SessionMemoryManager, get_session_manager
from .temporal_patterns import TemporalPattern, TemporalPatternStore
from .procedural_memory import ProceduralMemory, ProceduralSkill
from .episodic_memory import EpisodicMemory as PostgresEpisodicMemory, Episode
from .semantic_memory import SemanticMemory, Fact as SemanticFact

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
    "ProceduralSkill",
    # Persistent episodic memory
    "PostgresEpisodicMemory",
    "Episode",
    # Semantic memory
    "SemanticMemory",
    "SemanticFact",
]