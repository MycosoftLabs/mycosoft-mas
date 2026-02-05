"""
Additional Memory Modules for MYCA Memory System.
Created: February 5, 2026

Contains:
- ConversationMemory: Tracks conversation history with summarization
- EpisodicMemory: Event-based memory storage
- SemanticCompressor: Compresses memories for long-term storage
- AdaptiveDecay: Intelligent memory decay based on importance
- CrossSessionMemory: Memory sharing across sessions
"""

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger("MemoryModules")


# ============================================================================
# Conversation Memory
# ============================================================================

@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    id: UUID
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSummary:
    """Summary of a conversation segment."""
    id: UUID
    start_turn: int
    end_turn: int
    summary: str
    key_topics: List[str]
    sentiment: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationMemory:
    """
    Manages conversation history with automatic summarization.
    
    Features:
    - Turn tracking with timestamps
    - Rolling summarization
    - Topic extraction
    - Context window management
    """
    
    def __init__(self, max_turns: int = 100, summary_interval: int = 20):
        self._turns: List[ConversationTurn] = []
        self._summaries: List[ConversationSummary] = []
        self._max_turns = max_turns
        self._summary_interval = summary_interval
        self._turn_count = 0
    
    def add_turn(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationTurn:
        """Add a conversation turn."""
        turn = ConversationTurn(
            id=uuid4(),
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self._turns.append(turn)
        self._turn_count += 1
        
        # Trim if too long
        if len(self._turns) > self._max_turns:
            # Summarize before trimming
            self._create_summary(0, len(self._turns) - self._max_turns + 10)
            self._turns = self._turns[-(self._max_turns - 10):]
        
        # Create rolling summary
        if self._turn_count % self._summary_interval == 0:
            self._create_summary(
                len(self._turns) - self._summary_interval,
                len(self._turns)
            )
        
        return turn
    
    def _create_summary(self, start: int, end: int) -> ConversationSummary:
        """Create summary of turns."""
        if start < 0:
            start = 0
        if end > len(self._turns):
            end = len(self._turns)
        
        turns = self._turns[start:end]
        if not turns:
            return None
        
        # Simple extractive summary
        text = " ".join(t.content for t in turns)
        words = text.split()
        summary_text = " ".join(words[:50]) + "..." if len(words) > 50 else text
        
        # Extract topics (simple keyword extraction)
        topics = self._extract_topics(text)
        
        summary = ConversationSummary(
            id=uuid4(),
            start_turn=start,
            end_turn=end,
            summary=summary_text,
            key_topics=topics
        )
        self._summaries.append(summary)
        return summary
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract key topics from text."""
        # Simple word frequency approach
        words = text.lower().split()
        word_freq = {}
        
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", 
                     "being", "have", "has", "had", "do", "does", "did", "will",
                     "would", "could", "should", "may", "might", "must", "can",
                     "i", "you", "he", "she", "it", "we", "they", "what", "which",
                     "who", "whom", "this", "that", "these", "those", "am", "to",
                     "of", "in", "for", "on", "with", "at", "by", "from", "as"}
        
        for word in words:
            word = word.strip(".,!?;:\"'")
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:5]]
    
    def get_context(self, max_turns: int = 10) -> List[Dict[str, str]]:
        """Get recent context for LLM."""
        recent = self._turns[-max_turns:] if len(self._turns) > max_turns else self._turns
        return [{"role": t.role, "content": t.content} for t in recent]
    
    def get_full_context_with_summaries(self) -> Dict[str, Any]:
        """Get context with summaries for long conversations."""
        return {
            "summaries": [
                {"summary": s.summary, "topics": s.key_topics}
                for s in self._summaries
            ],
            "recent_turns": self.get_context(20)
        }
    
    def clear(self) -> None:
        """Clear conversation memory."""
        self._turns = []
        self._summaries = []
        self._turn_count = 0


# ============================================================================
# Episodic Memory
# ============================================================================

class EventType(str, Enum):
    """Types of episodic events."""
    INTERACTION = "interaction"
    TASK_COMPLETION = "task_completion"
    ERROR = "error"
    LEARNING = "learning"
    DECISION = "decision"
    OBSERVATION = "observation"


@dataclass
class Episode:
    """A memorable episode/event."""
    id: UUID
    event_type: EventType
    description: str
    participants: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    outcome: Optional[str] = None
    importance: float = 0.5
    emotional_valence: float = 0.0  # -1 to 1
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    related_episodes: List[UUID] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "event_type": self.event_type.value,
            "description": self.description,
            "participants": self.participants,
            "context": self.context,
            "outcome": self.outcome,
            "importance": self.importance,
            "emotional_valence": self.emotional_valence,
            "timestamp": self.timestamp.isoformat(),
            "related_episodes": [str(e) for e in self.related_episodes]
        }


class EpisodicMemory:
    """
    Event-based episodic memory storage.
    
    Features:
    - Event recording with context
    - Importance-based retrieval
    - Temporal clustering
    - Episode linking
    """
    
    def __init__(self, max_episodes: int = 1000):
        self._episodes: Dict[UUID, Episode] = {}
        self._max_episodes = max_episodes
    
    def record_episode(
        self,
        event_type: EventType,
        description: str,
        participants: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        outcome: Optional[str] = None,
        importance: float = 0.5,
        emotional_valence: float = 0.0
    ) -> Episode:
        """Record a new episode."""
        episode = Episode(
            id=uuid4(),
            event_type=event_type,
            description=description,
            participants=participants or [],
            context=context or {},
            outcome=outcome,
            importance=max(0, min(1, importance)),
            emotional_valence=max(-1, min(1, emotional_valence))
        )
        
        # Find related episodes
        related = self._find_related(episode)
        episode.related_episodes = [e.id for e in related[:3]]
        
        self._episodes[episode.id] = episode
        
        # Prune if too many
        if len(self._episodes) > self._max_episodes:
            self._prune_least_important()
        
        return episode
    
    def _find_related(self, episode: Episode) -> List[Episode]:
        """Find related episodes."""
        related = []
        
        for e in self._episodes.values():
            score = 0
            
            # Same type
            if e.event_type == episode.event_type:
                score += 0.3
            
            # Shared participants
            shared = set(e.participants) & set(episode.participants)
            if shared:
                score += 0.3 * len(shared)
            
            # Similar description words
            e_words = set(e.description.lower().split())
            ep_words = set(episode.description.lower().split())
            overlap = e_words & ep_words
            if overlap:
                score += 0.1 * len(overlap)
            
            if score > 0.3:
                related.append((score, e))
        
        related.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in related]
    
    def _prune_least_important(self) -> None:
        """Remove least important episodes."""
        if len(self._episodes) <= self._max_episodes:
            return
        
        sorted_eps = sorted(
            self._episodes.values(),
            key=lambda e: (e.importance, e.timestamp)
        )
        
        to_remove = len(self._episodes) - self._max_episodes + 100
        for ep in sorted_eps[:to_remove]:
            del self._episodes[ep.id]
    
    def recall(
        self,
        event_type: Optional[EventType] = None,
        participant: Optional[str] = None,
        min_importance: float = 0.0,
        since: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Episode]:
        """Recall episodes matching criteria."""
        results = []
        
        for ep in self._episodes.values():
            if event_type and ep.event_type != event_type:
                continue
            if participant and participant not in ep.participants:
                continue
            if ep.importance < min_importance:
                continue
            if since and ep.timestamp < since:
                continue
            
            results.append(ep)
        
        results.sort(key=lambda e: (e.importance, e.timestamp), reverse=True)
        return results[:limit]
    
    def get_episode(self, episode_id: UUID) -> Optional[Episode]:
        """Get a specific episode."""
        return self._episodes.get(episode_id)


# ============================================================================
# Semantic Compressor
# ============================================================================

class SemanticCompressor:
    """
    Compresses memories for efficient long-term storage.
    
    Features:
    - Redundancy elimination
    - Semantic clustering
    - Importance preservation
    - Lossy compression with quality control
    """
    
    def __init__(self, compression_ratio: float = 0.5):
        self._compression_ratio = compression_ratio
    
    def compress(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress a list of memories."""
        if not memories:
            return []
        
        # Group by similarity
        clusters = self._cluster_memories(memories)
        
        # Compress each cluster
        compressed = []
        for cluster in clusters:
            if len(cluster) == 1:
                compressed.append(cluster[0])
            else:
                merged = self._merge_cluster(cluster)
                compressed.append(merged)
        
        return compressed
    
    def _cluster_memories(self, memories: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Cluster similar memories."""
        if not memories:
            return []
        
        clusters = []
        assigned = [False] * len(memories)
        
        for i, mem in enumerate(memories):
            if assigned[i]:
                continue
            
            cluster = [mem]
            assigned[i] = True
            
            for j, other in enumerate(memories[i+1:], i+1):
                if assigned[j]:
                    continue
                
                if self._are_similar(mem, other):
                    cluster.append(other)
                    assigned[j] = True
            
            clusters.append(cluster)
        
        return clusters
    
    def _are_similar(self, m1: Dict[str, Any], m2: Dict[str, Any]) -> bool:
        """Check if two memories are similar enough to merge."""
        content1 = str(m1.get("content", "")).lower()
        content2 = str(m2.get("content", "")).lower()
        
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1 & words2)
        union = len(words1 | words2)
        
        jaccard = overlap / union if union > 0 else 0
        return jaccard > 0.5
    
    def _merge_cluster(self, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge a cluster of similar memories."""
        if len(cluster) == 1:
            return cluster[0]
        
        # Keep highest importance
        sorted_cluster = sorted(
            cluster,
            key=lambda m: m.get("importance", 0),
            reverse=True
        )
        
        merged = sorted_cluster[0].copy()
        merged["merged_count"] = len(cluster)
        merged["sources"] = [m.get("id") for m in cluster if m.get("id")]
        
        return merged
    
    def decompress(self, compressed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Decompress a merged memory (lossy - returns what we can)."""
        if "merged_count" not in compressed:
            return [compressed]
        
        # Can't fully recover, just return the compressed version
        return [compressed]


# ============================================================================
# Adaptive Decay
# ============================================================================

class DecayStrategy(str, Enum):
    """Memory decay strategies."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    STEP = "step"
    IMPORTANCE_WEIGHTED = "importance_weighted"


class AdaptiveDecay:
    """
    Intelligent memory decay based on importance and access patterns.
    
    Features:
    - Multiple decay strategies
    - Access-based reinforcement
    - Importance preservation
    - Configurable decay rates
    """
    
    def __init__(
        self,
        strategy: DecayStrategy = DecayStrategy.IMPORTANCE_WEIGHTED,
        base_half_life_hours: float = 24.0
    ):
        self._strategy = strategy
        self._base_half_life = timedelta(hours=base_half_life_hours)
    
    def calculate_strength(
        self,
        created_at: datetime,
        importance: float,
        access_count: int,
        last_accessed: Optional[datetime] = None
    ) -> float:
        """Calculate current memory strength."""
        now = datetime.now(timezone.utc)
        age = now - created_at
        
        if self._strategy == DecayStrategy.LINEAR:
            return self._linear_decay(age, importance)
        elif self._strategy == DecayStrategy.EXPONENTIAL:
            return self._exponential_decay(age, importance)
        elif self._strategy == DecayStrategy.STEP:
            return self._step_decay(age, importance)
        else:  # IMPORTANCE_WEIGHTED
            return self._importance_weighted_decay(
                age, importance, access_count, last_accessed
            )
    
    def _linear_decay(self, age: timedelta, importance: float) -> float:
        """Linear decay over time."""
        half_life = self._base_half_life * (1 + importance)
        ratio = age.total_seconds() / half_life.total_seconds()
        return max(0, 1 - ratio * 0.5)
    
    def _exponential_decay(self, age: timedelta, importance: float) -> float:
        """Exponential decay."""
        import math
        half_life = self._base_half_life * (1 + importance)
        ratio = age.total_seconds() / half_life.total_seconds()
        return math.exp(-0.693 * ratio)  # ln(2) â‰ˆ 0.693
    
    def _step_decay(self, age: timedelta, importance: float) -> float:
        """Step-based decay at intervals."""
        hours = age.total_seconds() / 3600
        
        if hours < 1:
            return 1.0
        elif hours < 24:
            return 0.9
        elif hours < 168:  # 1 week
            return 0.7
        elif hours < 720:  # 1 month
            return 0.5
        else:
            return 0.3 * importance
    
    def _importance_weighted_decay(
        self,
        age: timedelta,
        importance: float,
        access_count: int,
        last_accessed: Optional[datetime]
    ) -> float:
        """Decay weighted by importance and access patterns."""
        # Base exponential decay
        base = self._exponential_decay(age, importance)
        
        # Access reinforcement
        access_bonus = min(0.3, access_count * 0.05)
        
        # Recency bonus
        recency_bonus = 0
        if last_accessed:
            since_access = datetime.now(timezone.utc) - last_accessed
            if since_access.total_seconds() < 3600:  # Accessed in last hour
                recency_bonus = 0.2
            elif since_access.total_seconds() < 86400:  # Last day
                recency_bonus = 0.1
        
        return min(1.0, base + access_bonus + recency_bonus)
    
    def should_forget(
        self,
        created_at: datetime,
        importance: float,
        access_count: int,
        last_accessed: Optional[datetime] = None,
        threshold: float = 0.1
    ) -> bool:
        """Determine if a memory should be forgotten."""
        strength = self.calculate_strength(
            created_at, importance, access_count, last_accessed
        )
        return strength < threshold


# ============================================================================
# Cross-Session Memory
# ============================================================================

class CrossSessionMemory:
    """
    Memory sharing and persistence across sessions.
    
    Features:
    - Session-independent storage
    - User profile persistence
    - Learned preferences
    - Cross-session context
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
            "MINDEX_DATABASE_URL",
            "postgresql://mycosoft:Mushroom1!Mushroom1!@192.168.0.189:5432/mindex"
        )
        self._pool = None
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self) -> None:
        """Initialize database connection."""
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=3
            )
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
    
    async def save_user_context(
        self,
        user_id: str,
        context_key: str,
        context_data: Dict[str, Any]
    ) -> bool:
        """Save user context for cross-session access."""
        cache_key = f"{user_id}:{context_key}"
        self._cache[cache_key] = {
            "data": context_data,
            "saved_at": datetime.now(timezone.utc).isoformat()
        }
        
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO cross_session.user_context (user_id, context_key, context_data)
                        VALUES ($1, $2, $3::jsonb)
                        ON CONFLICT (user_id, context_key) DO UPDATE SET
                            context_data = EXCLUDED.context_data,
                            updated_at = NOW()
                    """, user_id, context_key, json.dumps(context_data))
                return True
            except Exception as e:
                logger.error(f"Failed to save context: {e}")
        
        return True  # Saved in cache at least
    
    async def load_user_context(
        self,
        user_id: str,
        context_key: str
    ) -> Optional[Dict[str, Any]]:
        """Load user context from previous sessions."""
        cache_key = f"{user_id}:{context_key}"
        
        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]["data"]
        
        # Check database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow("""
                        SELECT context_data FROM cross_session.user_context
                        WHERE user_id = $1 AND context_key = $2
                    """, user_id, context_key)
                    
                    if row:
                        data = json.loads(row["context_data"]) if isinstance(row["context_data"], str) else row["context_data"]
                        self._cache[cache_key] = {"data": data}
                        return data
            except Exception as e:
                logger.error(f"Failed to load context: {e}")
        
        return None
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get aggregated user profile from all sessions."""
        profile = {
            "user_id": user_id,
            "preferences": await self.load_user_context(user_id, "preferences") or {},
            "learned_facts": await self.load_user_context(user_id, "learned_facts") or [],
            "interaction_summary": await self.load_user_context(user_id, "interaction_summary") or {}
        }
        return profile
    
    async def update_learned_fact(
        self,
        user_id: str,
        fact: Dict[str, Any]
    ) -> bool:
        """Add a learned fact to user profile."""
        facts = await self.load_user_context(user_id, "learned_facts") or []
        
        # Check for duplicates
        fact_hash = hashlib.sha256(
            json.dumps(fact, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        for existing in facts:
            if existing.get("hash") == fact_hash:
                return False  # Already exists
        
        fact["hash"] = fact_hash
        fact["learned_at"] = datetime.now(timezone.utc).isoformat()
        facts.append(fact)
        
        # Keep last 100 facts
        if len(facts) > 100:
            facts = facts[-100:]
        
        await self.save_user_context(user_id, "learned_facts", facts)
        return True
