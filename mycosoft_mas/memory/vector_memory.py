"""Vector-based semantic memory. Created: February 3, 2026"""
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import math

class MemoryEntry:
    def __init__(self, entry_id: UUID, content: str, embedding: List[float], metadata: Dict[str, Any] = None):
        self.entry_id = entry_id
        self.content = content
        self.embedding = embedding
        self.metadata = metadata or {}

class VectorMemory:
    """Semantic memory with vector embeddings."""
    
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self._entries: Dict[UUID, MemoryEntry] = {}
    
    async def add(self, content: str, embedding: List[float], metadata: Dict[str, Any] = None) -> UUID:
        entry_id = uuid4()
        self._entries[entry_id] = MemoryEntry(entry_id, content, embedding, metadata)
        return entry_id
    
    async def search(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[UUID, float, str]]:
        scored = []
        for entry in self._entries.values():
            score = self._cosine_similarity(query_embedding, entry.embedding)
            scored.append((entry.entry_id, score, entry.content))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    def get(self, entry_id: UUID) -> Optional[MemoryEntry]:
        return self._entries.get(entry_id)
    
    def delete(self, entry_id: UUID) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False
