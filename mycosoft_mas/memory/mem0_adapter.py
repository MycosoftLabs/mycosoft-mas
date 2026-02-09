"""
Mem0 Adapter - LoCoMo-style Fact Extraction and Three-Layer Architecture.
Created: February 5, 2026

Implements mem0-compatible memory operations with:
- LoCoMo-style fact extraction from conversations
- Three-layer architecture (Short-term, Long-term, Semantic)
- Entity extraction and relationship mapping
- Automatic fact deduplication
- Memory consolidation and compression

Based on mem0 (https://github.com/mem0ai/mem0) architecture patterns.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger("Mem0Adapter")


class MemoryType(str, Enum):
    """Types of memories in the three-layer architecture."""
    SHORT_TERM = "short_term"   # Recent conversation context
    LONG_TERM = "long_term"     # Persisted facts and knowledge
    SEMANTIC = "semantic"       # Conceptual and relational knowledge


class FactType(str, Enum):
    """Types of facts that can be extracted."""
    PREFERENCE = "preference"       # User preferences
    BIOGRAPHICAL = "biographical"   # Personal information
    BEHAVIORAL = "behavioral"       # Behavior patterns
    CONTEXTUAL = "contextual"       # Context-specific facts
    RELATIONAL = "relational"       # Relationships between entities
    PROCEDURAL = "procedural"       # How-to knowledge
    DECLARATIVE = "declarative"     # General facts


@dataclass
class ExtractedFact:
    """A fact extracted from conversation."""
    id: UUID
    fact_type: FactType
    subject: str           # Who/what the fact is about
    predicate: str         # The relationship or attribute
    object: str            # The value or related entity
    confidence: float      # 0-1 confidence score
    source_text: str       # Original text the fact was extracted from
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_triple(self) -> Tuple[str, str, str]:
        """Return as subject-predicate-object triple."""
        return (self.subject, self.predicate, self.object)
    
    def to_natural_language(self) -> str:
        """Convert to natural language statement."""
        return f"{self.subject} {self.predicate} {self.object}"
    
    def hash(self) -> str:
        """Generate unique hash for deduplication."""
        content = f"{self.subject}|{self.predicate}|{self.object}".lower()
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class Memory:
    """A memory entry compatible with mem0 format."""
    id: str
    memory: str            # The memory content in natural language
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    categories: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory": self.memory,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "hash": self.hash,
            "metadata": self.metadata,
            "categories": self.categories,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class LoCoMoFactExtractor:
    """
    LoCoMo-style fact extraction from conversations.
    
    Extracts structured facts from free-form text using pattern matching
    and optional LLM enhancement. Based on LoCoMo (Long Context Memory)
    paper approach.
    """
    
    # Patterns for extracting different fact types
    PREFERENCE_PATTERNS = [
        r"(?:I|i) (?:like|love|prefer|enjoy|hate|dislike) (.+?)(?:\.|,|$)",
        r"(?:I|i)'m (?:a fan of|into|interested in) (.+?)(?:\.|,|$)",
        r"my favorite (.+?) is (.+?)(?:\.|,|$)",
    ]
    
    BIOGRAPHICAL_PATTERNS = [
        r"(?:I|i) (?:am|work as|live in|was born in) (.+?)(?:\.|,|$)",
        r"my (?:name|job|location|age) is (.+?)(?:\.|,|$)",
        r"(?:I|i)'m (\d+) years old",
    ]
    
    BEHAVIORAL_PATTERNS = [
        r"(?:I|i) (?:usually|always|often|sometimes|never) (.+?)(?:\.|,|$)",
        r"(?:I|i) tend to (.+?)(?:\.|,|$)",
    ]
    
    def __init__(self, llm_url: Optional[str] = None):
        self._llm_url = llm_url or os.getenv("PERSONAPLEX_URL", "http://localhost:8999")
    
    async def extract_facts(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        use_llm: bool = False
    ) -> List[ExtractedFact]:
        """Extract facts from text."""
        facts = []
        
        # Pattern-based extraction
        facts.extend(self._extract_preferences(text))
        facts.extend(self._extract_biographical(text))
        facts.extend(self._extract_behavioral(text))
        
        # LLM-enhanced extraction for complex facts
        if use_llm:
            llm_facts = await self._llm_extract(text, context)
            facts.extend(llm_facts)
        
        # Deduplicate
        seen_hashes = set()
        unique_facts = []
        for fact in facts:
            h = fact.hash()
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique_facts.append(fact)
        
        return unique_facts
    
    def _extract_preferences(self, text: str) -> List[ExtractedFact]:
        """Extract preference facts."""
        facts = []
        for pattern in self.PREFERENCE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if "favorite" in pattern:
                    facts.append(ExtractedFact(
                        id=uuid4(),
                        fact_type=FactType.PREFERENCE,
                        subject="user",
                        predicate=f"favorite_{match.group(1).strip()}",
                        object=match.group(2).strip() if len(match.groups()) > 1 else match.group(1).strip(),
                        confidence=0.8,
                        source_text=match.group(0)
                    ))
                else:
                    facts.append(ExtractedFact(
                        id=uuid4(),
                        fact_type=FactType.PREFERENCE,
                        subject="user",
                        predicate="prefers" if "like" in pattern or "love" in pattern else "dislikes",
                        object=match.group(1).strip(),
                        confidence=0.7,
                        source_text=match.group(0)
                    ))
        return facts
    
    def _extract_biographical(self, text: str) -> List[ExtractedFact]:
        """Extract biographical facts."""
        facts = []
        for pattern in self.BIOGRAPHICAL_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                facts.append(ExtractedFact(
                    id=uuid4(),
                    fact_type=FactType.BIOGRAPHICAL,
                    subject="user",
                    predicate="has_attribute",
                    object=match.group(1).strip(),
                    confidence=0.85,
                    source_text=match.group(0)
                ))
        return facts
    
    def _extract_behavioral(self, text: str) -> List[ExtractedFact]:
        """Extract behavioral facts."""
        facts = []
        for pattern in self.BEHAVIORAL_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                facts.append(ExtractedFact(
                    id=uuid4(),
                    fact_type=FactType.BEHAVIORAL,
                    subject="user",
                    predicate="typically",
                    object=match.group(1).strip(),
                    confidence=0.6,
                    source_text=match.group(0)
                ))
        return facts
    
    async def _llm_extract(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedFact]:
        """Use LLM to extract complex facts."""
        facts = []
        
        try:
            import aiohttp
            
            prompt = f"""Extract key facts from the following text as JSON array.
Each fact should have: subject, predicate, object, type.
Types: preference, biographical, behavioral, contextual, relational, procedural, declarative.

Text: {text}

Respond with valid JSON array only."""

            async with aiohttp.ClientSession() as client:
                async with client.post(
                    f"{self._llm_url}/v1/chat/completions",
                    json={
                        "model": "moshi-7b",
                        "messages": [
                            {"role": "system", "content": "You are a fact extraction assistant. Output only valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 500,
                        "temperature": 0.1
                    },
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        content = data["choices"][0]["message"]["content"]
                        
                        # Parse JSON response
                        try:
                            extracted = json.loads(content)
                            for item in extracted:
                                facts.append(ExtractedFact(
                                    id=uuid4(),
                                    fact_type=FactType(item.get("type", "declarative")),
                                    subject=item.get("subject", "unknown"),
                                    predicate=item.get("predicate", "related_to"),
                                    object=item.get("object", ""),
                                    confidence=0.75,
                                    source_text=text[:100]
                                ))
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
        
        return facts


class Mem0Adapter:
    """
    Mem0-compatible memory adapter with three-layer architecture.
    
    Provides:
    - add() - Add memories from messages
    - get_all() - Get all memories for user/agent
    - search() - Semantic search memories
    - update() - Update existing memory
    - delete() - Delete memory
    - get_all_memories() - Get all with filters
    
    Three-layer architecture:
    1. Short-term: Recent conversation buffer (last N turns)
    2. Long-term: Extracted facts and persistent memories
    3. Semantic: Conceptual knowledge and relationships
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
            "MINDEX_DATABASE_URL",
            "postgresql://mycosoft:REDACTED_VM_SSH_PASSWORD@192.168.0.189:5432/mindex"
        )
        self._pool = None
        self._extractor = LoCoMoFactExtractor()
        
        # In-memory layers
        self._short_term: Dict[str, List[Dict[str, Any]]] = {}  # user_id -> messages
        self._long_term: Dict[str, List[Memory]] = {}           # user_id -> memories
        self._semantic: Dict[str, List[ExtractedFact]] = {}     # user_id -> facts
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the adapter."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=5
            )
            logger.info("Mem0 adapter connected to database")
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
        
        self._initialized = True
    
    async def add(
        self,
        messages: List[Dict[str, str]],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        infer: bool = True
    ) -> Dict[str, Any]:
        """Add memories from messages (mem0-compatible API)."""
        user_id = user_id or "default"
        
        # Add to short-term buffer
        if user_id not in self._short_term:
            self._short_term[user_id] = []
        self._short_term[user_id].extend(messages)
        
        # Keep only recent messages in short-term
        self._short_term[user_id] = self._short_term[user_id][-50:]
        
        added_memories = []
        
        if infer:
            # Extract facts from user messages
            for msg in messages:
                if msg.get("role") == "user":
                    facts = await self._extractor.extract_facts(
                        msg.get("content", ""),
                        use_llm=False
                    )
                    
                    for fact in facts:
                        # Convert fact to memory
                        memory = Memory(
                            id=str(fact.id),
                            memory=fact.to_natural_language(),
                            user_id=user_id,
                            agent_id=agent_id,
                            hash=fact.hash(),
                            metadata={
                                "fact_type": fact.fact_type.value,
                                "confidence": fact.confidence,
                                "source": fact.source_text,
                                **(metadata or {})
                            },
                            categories=[fact.fact_type.value]
                        )
                        
                        # Check for duplicates
                        if not await self._is_duplicate(user_id, memory.hash):
                            if user_id not in self._long_term:
                                self._long_term[user_id] = []
                            self._long_term[user_id].append(memory)
                            
                            # Persist to database
                            await self._persist_memory(memory)
                            added_memories.append(memory.to_dict())
                        
                        # Add to semantic layer
                        if user_id not in self._semantic:
                            self._semantic[user_id] = []
                        self._semantic[user_id].append(fact)
        
        return {
            "message": f"Added {len(added_memories)} memories",
            "memories": added_memories
        }
    
    async def _is_duplicate(self, user_id: str, memory_hash: str) -> bool:
        """Check if memory already exists."""
        if user_id in self._long_term:
            for mem in self._long_term[user_id]:
                if mem.hash == memory_hash:
                    return True
        return False
    
    async def _persist_memory(self, memory: Memory) -> bool:
        """Persist memory to database."""
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO mem0.memories (id, memory, user_id, agent_id, hash, 
                        metadata, categories, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9)
                    ON CONFLICT (id) DO UPDATE SET
                        memory = EXCLUDED.memory,
                        metadata = EXCLUDED.metadata,
                        updated_at = EXCLUDED.updated_at
                """, memory.id, memory.memory, memory.user_id, memory.agent_id,
                    memory.hash, json.dumps(memory.metadata), memory.categories,
                    memory.created_at, memory.updated_at)
            return True
        except Exception as e:
            logger.error(f"Failed to persist memory: {e}")
            return False
    
    async def get_all(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all memories for user/agent (mem0-compatible API)."""
        user_id = user_id or "default"
        
        memories = []
        
        # Get from in-memory cache
        if user_id in self._long_term:
            memories = [m.to_dict() for m in self._long_term[user_id]]
        
        # Get from database if available
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT * FROM mem0.memories 
                        WHERE user_id = $1 
                        ORDER BY created_at DESC LIMIT $2
                    """, user_id, limit)
                    
                    for row in rows:
                        memories.append({
                            "id": row["id"],
                            "memory": row["memory"],
                            "user_id": row["user_id"],
                            "agent_id": row["agent_id"],
                            "hash": row["hash"],
                            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                            "categories": row["categories"] or [],
                            "created_at": row["created_at"].isoformat(),
                            "updated_at": row["updated_at"].isoformat()
                        })
            except Exception as e:
                logger.error(f"Failed to get memories: {e}")
        
        # Deduplicate by ID
        seen_ids = set()
        unique = []
        for m in memories:
            if m["id"] not in seen_ids:
                seen_ids.add(m["id"])
                unique.append(m)
        
        return unique[:limit]
    
    async def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search memories by query (mem0-compatible API)."""
        user_id = user_id or "default"
        
        # Simple keyword search for now
        # TODO: Implement vector search with embeddings
        all_memories = await self.get_all(user_id, agent_id, limit=1000)
        
        query_lower = query.lower()
        scored = []
        for mem in all_memories:
            memory_text = mem["memory"].lower()
            score = 0
            
            # Simple scoring based on word overlap
            query_words = set(query_lower.split())
            memory_words = set(memory_text.split())
            overlap = query_words & memory_words
            
            if overlap:
                score = len(overlap) / len(query_words)
            
            if score > 0:
                scored.append((mem, score))
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:limit]]
    
    async def update(self, memory_id: str, data: str) -> Dict[str, Any]:
        """Update a memory (mem0-compatible API)."""
        # Update in cache
        for user_memories in self._long_term.values():
            for mem in user_memories:
                if mem.id == memory_id:
                    mem.memory = data
                    mem.updated_at = datetime.now(timezone.utc)
                    await self._persist_memory(mem)
                    return {"message": "Memory updated", "id": memory_id}
        
        # Update in database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE mem0.memories SET memory = $1, updated_at = NOW()
                        WHERE id = $2
                    """, data, memory_id)
                return {"message": "Memory updated", "id": memory_id}
            except Exception as e:
                logger.error(f"Failed to update memory: {e}")
        
        return {"message": "Memory not found", "id": memory_id}
    
    async def delete(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory (mem0-compatible API)."""
        # Delete from cache
        for user_memories in self._long_term.values():
            for i, mem in enumerate(user_memories):
                if mem.id == memory_id:
                    user_memories.pop(i)
                    break
        
        # Delete from database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute("DELETE FROM mem0.memories WHERE id = $1", memory_id)
                return {"message": "Memory deleted", "id": memory_id}
            except Exception as e:
                logger.error(f"Failed to delete memory: {e}")
        
        return {"message": "Memory deleted", "id": memory_id}
    
    async def get_short_term(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get short-term memory (recent messages)."""
        if user_id in self._short_term:
            return self._short_term[user_id][-limit:]
        return []
    
    async def get_semantic_facts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get semantic layer facts for a user."""
        if user_id in self._semantic:
            return [
                {
                    "id": str(f.id),
                    "triple": f.to_triple(),
                    "natural": f.to_natural_language(),
                    "type": f.fact_type.value,
                    "confidence": f.confidence
                }
                for f in self._semantic[user_id]
            ]
        return []
    
    async def consolidate(self, user_id: str) -> int:
        """Consolidate and compress memories for a user."""
        if user_id not in self._long_term:
            return 0
        
        memories = self._long_term[user_id]
        if len(memories) < 10:
            return 0
        
        # Group by category
        by_category: Dict[str, List[Memory]] = {}
        for mem in memories:
            cat = mem.categories[0] if mem.categories else "general"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(mem)
        
        # Merge similar memories within each category
        # This is a placeholder - real implementation would use embeddings
        consolidated = 0
        
        return consolidated
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        total_users = len(self._long_term)
        total_memories = sum(len(m) for m in self._long_term.values())
        total_facts = sum(len(f) for f in self._semantic.values())
        
        return {
            "total_users": total_users,
            "total_memories": total_memories,
            "total_facts": total_facts,
            "database_connected": self._pool is not None,
            "initialized": self._initialized
        }


# Singleton instance
_mem0_adapter: Optional[Mem0Adapter] = None


async def get_mem0_adapter() -> Mem0Adapter:
    """Get or create the singleton Mem0 adapter instance."""
    global _mem0_adapter
    if _mem0_adapter is None:
        _mem0_adapter = Mem0Adapter()
        await _mem0_adapter.initialize()
    return _mem0_adapter
