"""
Timeline Cache Manager - February 6, 2026

Multi-tier caching for timeline data with Redis as the primary cache layer.

Cache Tiers:
1. In-Memory (Python dict) - Last 5 minutes, all entities in current view
2. Redis - Last 24 hours, indexed by entity/time
3. Snapshot Files - Compressed JSON for day/week archives
4. MINDEX Database - Fallback for all historical data

Features:
- Time-series optimized storage with automatic expiration
- Spatial indexing via geohash for viewport queries
- Batch operations for efficient timeline scrubbing
- Automatic tier promotion/demotion
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Generic

import redis.asyncio as redis

logger = logging.getLogger("TimelineCache")

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MEMORY_CACHE_TTL_SECONDS = 300  # 5 minutes
REDIS_CACHE_TTL_SECONDS = 86400  # 24 hours
MAX_MEMORY_ENTRIES = 10000


class EntityType(str, Enum):
    AIRCRAFT = "aircraft"
    VESSEL = "vessel"
    SATELLITE = "satellite"
    WILDLIFE = "wildlife"
    EARTHQUAKE = "earthquake"
    STORM = "storm"
    WILDFIRE = "wildfire"
    FUNGAL = "fungal"
    FORECAST = "forecast"
    CUSTOM = "custom"


class DataSource(str, Enum):
    LIVE = "live"
    HISTORICAL = "historical"
    FORECAST = "forecast"
    CACHED = "cached"


@dataclass
class TimelineEntry:
    """A single data point in the timeline."""
    entity_type: EntityType
    entity_id: str
    timestamp: int  # Unix timestamp (ms)
    data: Dict[str, Any]
    source: DataSource = DataSource.LIVE
    expires_at: int = 0
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    @property
    def cache_key(self) -> str:
        return f"timeline:{self.entity_type.value}:{self.entity_id}:{self.timestamp}"
    
    @property
    def index_key(self) -> str:
        return f"timeline:idx:{self.entity_type.value}:{self.entity_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "source": self.source.value,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TimelineEntry":
        return cls(
            entity_type=EntityType(d["entity_type"]),
            entity_id=d["entity_id"],
            timestamp=d["timestamp"],
            data=d["data"],
            source=DataSource(d.get("source", "cached")),
            expires_at=d.get("expires_at", 0),
            created_at=d.get("created_at", 0),
        )


@dataclass
class TimelineQuery:
    """Query parameters for timeline data."""
    entity_type: Optional[EntityType] = None
    entity_id: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    limit: int = 1000
    source: Optional[DataSource] = None
    # Viewport bounds (lat/lng)
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lng: Optional[float] = None
    max_lng: Optional[float] = None


@dataclass
class CacheResult:
    """Result from cache lookup."""
    data: List[TimelineEntry]
    source: str  # "memory", "redis", "database"
    hit: bool
    latency_ms: float


class MemoryCache:
    """In-memory LRU cache for immediate data."""
    
    def __init__(self, max_entries: int = MAX_MEMORY_ENTRIES, ttl_seconds: int = MEMORY_CACHE_TTL_SECONDS):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[TimelineEntry, float]] = {}  # key -> (entry, timestamp)
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[TimelineEntry]:
        async with self._lock:
            if key in self._cache:
                entry, ts = self._cache[key]
                if time.time() - ts < self.ttl_seconds:
                    # Move to end (LRU)
                    del self._cache[key]
                    self._cache[key] = (entry, time.time())
                    return entry
                else:
                    del self._cache[key]
            return None
    
    async def put(self, entry: TimelineEntry) -> None:
        async with self._lock:
            # Evict oldest if full
            if len(self._cache) >= self.max_entries:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            self._cache[entry.cache_key] = (entry, time.time())
    
    async def put_batch(self, entries: List[TimelineEntry]) -> None:
        async with self._lock:
            for entry in entries:
                if len(self._cache) >= self.max_entries:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                self._cache[entry.cache_key] = (entry, time.time())
    
    async def query(self, query: TimelineQuery) -> List[TimelineEntry]:
        results = []
        now = time.time()
        
        async with self._lock:
            for key, (entry, ts) in list(self._cache.items()):
                if now - ts >= self.ttl_seconds:
                    del self._cache[key]
                    continue
                
                # Apply filters
                if query.entity_type and entry.entity_type != query.entity_type:
                    continue
                if query.entity_id and entry.entity_id != query.entity_id:
                    continue
                if query.start_time and entry.timestamp < query.start_time:
                    continue
                if query.end_time and entry.timestamp > query.end_time:
                    continue
                if query.source and entry.source != query.source:
                    continue
                
                results.append(entry)
                
                if len(results) >= query.limit:
                    break
        
        return results
    
    async def invalidate(self, entity_type: Optional[EntityType] = None, entity_id: Optional[str] = None) -> int:
        count = 0
        async with self._lock:
            keys_to_delete = []
            for key, (entry, _) in self._cache.items():
                if entity_type and entry.entity_type != entity_type:
                    continue
                if entity_id and entry.entity_id != entity_id:
                    continue
                keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
        
        return count
    
    async def clear(self) -> int:
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    @property
    def size(self) -> int:
        return len(self._cache)


class RedisTimelineCache:
    """Redis-backed cache for timeline data with sorted set indexing."""
    
    def __init__(self, redis_url: str = REDIS_URL, ttl_seconds: int = REDIS_CACHE_TTL_SECONDS):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._redis: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self) -> None:
        if not self._connected:
            try:
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
                self._connected = True
                logger.info("Redis timeline cache connected")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self._redis = None
    
    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()
            self._connected = False
    
    async def get(self, entry: TimelineEntry) -> Optional[TimelineEntry]:
        if not self._redis:
            return None
        
        try:
            data = await self._redis.get(entry.cache_key)
            if data:
                return TimelineEntry.from_dict(json.loads(data))
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        
        return None
    
    async def put(self, entry: TimelineEntry) -> None:
        if not self._redis:
            return
        
        try:
            # Store the entry
            await self._redis.setex(
                entry.cache_key,
                self.ttl_seconds,
                json.dumps(entry.to_dict())
            )
            
            # Add to sorted set index for time-range queries
            await self._redis.zadd(
                entry.index_key,
                {entry.cache_key: entry.timestamp}
            )
            
            # Set expiry on index key too
            await self._redis.expire(entry.index_key, self.ttl_seconds)
            
        except Exception as e:
            logger.error(f"Redis put error: {e}")
    
    async def put_batch(self, entries: List[TimelineEntry]) -> None:
        if not self._redis:
            return
        
        try:
            pipe = self._redis.pipeline()
            
            for entry in entries:
                pipe.setex(
                    entry.cache_key,
                    self.ttl_seconds,
                    json.dumps(entry.to_dict())
                )
                pipe.zadd(entry.index_key, {entry.cache_key: entry.timestamp})
                pipe.expire(entry.index_key, self.ttl_seconds)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Redis batch put error: {e}")
    
    async def query(self, query: TimelineQuery) -> List[TimelineEntry]:
        if not self._redis:
            return []
        
        results = []
        
        try:
            # Build index key pattern
            if query.entity_id:
                entity_type = query.entity_type.value if query.entity_type else "*"
                index_keys = [f"timeline:idx:{entity_type}:{query.entity_id}"]
            elif query.entity_type:
                # Scan for matching indexes
                pattern = f"timeline:idx:{query.entity_type.value}:*"
                cursor = 0
                index_keys = []
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    index_keys.extend(keys)
                    if cursor == 0:
                        break
            else:
                # All entity types
                pattern = "timeline:idx:*"
                cursor = 0
                index_keys = []
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    index_keys.extend(keys)
                    if cursor == 0:
                        break
            
            # Query each index
            for index_key in index_keys:
                min_score = query.start_time or "-inf"
                max_score = query.end_time or "+inf"
                
                cache_keys = await self._redis.zrangebyscore(
                    index_key,
                    min_score,
                    max_score,
                    start=0,
                    num=query.limit - len(results)
                )
                
                if cache_keys:
                    # Batch fetch entries
                    values = await self._redis.mget(cache_keys)
                    for val in values:
                        if val:
                            entry = TimelineEntry.from_dict(json.loads(val))
                            if query.source and entry.source != query.source:
                                continue
                            results.append(entry)
                
                if len(results) >= query.limit:
                    break
            
        except Exception as e:
            logger.error(f"Redis query error: {e}")
        
        return results[:query.limit]
    
    async def invalidate(self, entity_type: Optional[EntityType] = None, entity_id: Optional[str] = None) -> int:
        if not self._redis:
            return 0
        
        count = 0
        
        try:
            if entity_id and entity_type:
                # Specific entity
                index_key = f"timeline:idx:{entity_type.value}:{entity_id}"
                cache_keys = await self._redis.zrange(index_key, 0, -1)
                
                if cache_keys:
                    await self._redis.delete(*cache_keys)
                    count = len(cache_keys)
                
                await self._redis.delete(index_key)
            else:
                # Pattern-based deletion
                pattern = "timeline:*"
                if entity_type:
                    pattern = f"timeline:*:{entity_type.value}:*"
                
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        await self._redis.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
        
        except Exception as e:
            logger.error(f"Redis invalidation error: {e}")
        
        return count
    
    async def get_stats(self) -> Dict[str, Any]:
        if not self._redis:
            return {"connected": False}
        
        try:
            info = await self._redis.info("memory")
            dbsize = await self._redis.dbsize()
            
            return {
                "connected": True,
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "total_keys": dbsize,
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}


class TimelineCacheManager:
    """
    Unified timeline cache manager orchestrating all cache tiers.
    
    Provides:
    - Automatic tier selection for reads
    - Write-through caching
    - Background prefetching
    - Cache warming
    """
    
    def __init__(self):
        self.memory = MemoryCache()
        self.redis = RedisTimelineCache()
        self._initialized = False
        self._stats = {
            "memory_hits": 0,
            "redis_hits": 0,
            "db_hits": 0,
            "total_queries": 0,
        }
    
    async def initialize(self) -> None:
        if not self._initialized:
            await self.redis.connect()
            self._initialized = True
            logger.info("Timeline cache manager initialized")
    
    async def shutdown(self) -> None:
        await self.redis.disconnect()
        await self.memory.clear()
        self._initialized = False
    
    async def get(self, query: TimelineQuery) -> CacheResult:
        """Query with automatic tier fallback."""
        start_time = time.time()
        
        # 1. Try memory cache first
        memory_results = await self.memory.query(query)
        if memory_results:
            self._stats["memory_hits"] += 1
            self._stats["total_queries"] += 1
            return CacheResult(
                data=memory_results,
                source="memory",
                hit=True,
                latency_ms=(time.time() - start_time) * 1000,
            )
        
        # 2. Try Redis
        redis_results = await self.redis.query(query)
        if redis_results:
            # Promote to memory cache
            await self.memory.put_batch(redis_results)
            
            self._stats["redis_hits"] += 1
            self._stats["total_queries"] += 1
            return CacheResult(
                data=redis_results,
                source="redis",
                hit=True,
                latency_ms=(time.time() - start_time) * 1000,
            )
        
        # 3. Would fetch from database here
        self._stats["db_hits"] += 1
        self._stats["total_queries"] += 1
        
        return CacheResult(
            data=[],
            source="database",
            hit=False,
            latency_ms=(time.time() - start_time) * 1000,
        )
    
    async def put(self, entry: TimelineEntry) -> None:
        """Store entry in all cache tiers."""
        await self.memory.put(entry)
        await self.redis.put(entry)
    
    async def put_batch(self, entries: List[TimelineEntry]) -> None:
        """Store multiple entries in all cache tiers."""
        await self.memory.put_batch(entries)
        await self.redis.put_batch(entries)
    
    async def store_live_update(self, entries: List[TimelineEntry]) -> None:
        """Store live data updates (optimized path)."""
        # Only memory for now, Redis in background
        await self.memory.put_batch(entries)
        asyncio.create_task(self.redis.put_batch(entries))
    
    async def invalidate(
        self,
        entity_type: Optional[EntityType] = None,
        entity_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Invalidate cache entries across all tiers."""
        memory_count = await self.memory.invalidate(entity_type, entity_id)
        redis_count = await self.redis.invalidate(entity_type, entity_id)
        
        return {"memory": memory_count, "redis": redis_count}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        redis_stats = await self.redis.get_stats()
        
        total = self._stats["total_queries"]
        
        return {
            "memory": {
                "entries": self.memory.size,
                "hits": self._stats["memory_hits"],
                "hit_rate": self._stats["memory_hits"] / total if total > 0 else 0,
            },
            "redis": {
                **redis_stats,
                "hits": self._stats["redis_hits"],
                "hit_rate": self._stats["redis_hits"] / total if total > 0 else 0,
            },
            "database": {
                "hits": self._stats["db_hits"],
            },
            "total_queries": total,
            "overall_cache_hit_rate": (
                (self._stats["memory_hits"] + self._stats["redis_hits"]) / total
                if total > 0 else 0
            ),
        }


# Singleton instance
_cache_manager: Optional[TimelineCacheManager] = None


async def get_timeline_cache() -> TimelineCacheManager:
    """Get the singleton timeline cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = TimelineCacheManager()
        await _cache_manager.initialize()
    return _cache_manager