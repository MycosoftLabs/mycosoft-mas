"""
Base Collector - February 6, 2026

Abstract base class for all data collectors.
"""

import asyncio
import logging
import os
from hashlib import sha1
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CollectorStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0


@dataclass
class RawEvent:
    """Raw event from data source."""
    source: str
    entity_id: str
    entity_type: str
    timestamp: datetime
    data: Dict[str, Any]
    raw_data: Optional[Any] = None


@dataclass
class TimelineEvent:
    """Processed event for timeline storage."""
    id: str
    entity_type: str
    timestamp: datetime
    lat: float
    lng: float
    altitude: Optional[float] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    quality_score: float = 1.0


@dataclass
class UnifiedEntity:
    """Unified entity payload emitted by collectors."""

    id: str
    type: str
    geometry: Dict[str, Any]
    state: Dict[str, Any]
    time: Dict[str, Any]
    confidence: float
    source: str
    properties: Dict[str, Any]
    s2_cell: str


@dataclass
class CollectorStats:
    """Runtime statistics for a collector."""
    total_fetches: int = 0
    successful_fetches: int = 0
    failed_fetches: int = 0
    total_events: int = 0
    last_fetch_time: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    avg_fetch_duration_ms: float = 0.0


class BaseCollector(ABC):
    """
    Abstract base class for data collectors.
    
    Collectors fetch data from external sources and transform it
    for ingestion into MINDEX.
    """
    
    name: str = "base"
    entity_type: str = "unknown"
    poll_interval_seconds: int = 60
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    
    def __init__(self):
        self.status = CollectorStatus.IDLE
        self.stats = CollectorStats()
        self.retry_config = RetryConfig()
        self._stop_event = asyncio.Event()
        self._pool = None
    
    async def initialize(self) -> None:
        """Initialize collector resources."""
        pass
    
    async def cleanup(self) -> None:
        """Cleanup collector resources."""
        pass
    
    @abstractmethod
    async def fetch(self) -> List[RawEvent]:
        """
        Fetch raw data from the source.
        
        Returns:
            List of raw events
        """
        pass
    
    @abstractmethod
    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """
        Transform raw event to timeline event.
        
        Args:
            raw: Raw event from source
            
        Returns:
            Processed timeline event
        """
        pass

    def _compute_s2_cell(self, lat: float, lng: float, level: int = 14) -> str:
        """
        Compute a stable cell identifier for spatial sharding.

        We use a deterministic hash fallback to avoid hard dependency on native bindings
        while still producing a repeatable cell key for channel routing.
        """
        precision_lat = round(lat, max(1, level // 2))
        precision_lng = round(lng, max(1, level // 2))
        digest = sha1(f"{precision_lat}:{precision_lng}:{level}".encode("utf-8")).hexdigest()
        return digest[:16]

    def to_unified_entity(self, event: TimelineEvent) -> UnifiedEntity:
        observed_at = event.timestamp.isoformat()
        geometry = {
            "type": "Point",
            "coordinates": [event.lng, event.lat] if event.altitude is None else [event.lng, event.lat, event.altitude],
        }
        return UnifiedEntity(
            id=event.id,
            type=event.entity_type,
            geometry=geometry,
            state={
                "altitude": event.altitude,
                "classification": event.properties.get("classification") if isinstance(event.properties, dict) else None,
            },
            time={
                "observed_at": observed_at,
                "valid_from": observed_at,
            },
            confidence=event.quality_score,
            source=event.source,
            properties=event.properties,
            s2_cell=self._compute_s2_cell(event.lat, event.lng),
        )
    
    async def ingest(self, events: List[TimelineEvent]) -> int:
        """
        Ingest events into MINDEX.
        
        Args:
            events: List of timeline events
            
        Returns:
            Number of events ingested
        """
        if not events:
            return 0
        
        try:
            import asyncpg
            import json
            import uuid
            
            if self._pool is None:
                self._pool = await asyncpg.create_pool(
                    os.getenv("MINDEX_DATABASE_URL", "postgresql://mindex:mindex@localhost:5432/mindex"),
                    min_size=1,
                    max_size=5
                )
            
            async with self._pool.acquire() as conn:
                for event in events:
                    await conn.execute("""
                        INSERT INTO mindex.timeline_entries 
                        (id, entity_type, timestamp, geom, properties, source, quality_score)
                        VALUES ($1, $2, $3, ST_SetSRID(ST_Point($4, $5), 4326), $6, $7, $8)
                        ON CONFLICT (id) DO UPDATE SET
                            timestamp = EXCLUDED.timestamp,
                            geom = EXCLUDED.geom,
                            properties = EXCLUDED.properties
                    """,
                        uuid.UUID(event.id),
                        event.entity_type,
                        event.timestamp,
                        event.lng,
                        event.lat,
                        json.dumps(event.properties),
                        event.source,
                        event.quality_score
                    )
            
            self.stats.total_events += len(events)
            return len(events)
            
        except Exception as e:
            logger.error(f"{self.name} ingest error: {e}")
            return 0
    
    async def run_once(self) -> List[TimelineEvent]:
        """Run a single fetch-transform-ingest cycle."""
        start_time = datetime.utcnow()
        
        try:
            # Fetch
            raw_events = await self.fetch()
            
            # Transform
            events = []
            for raw in raw_events:
                try:
                    event = await self.transform(raw)
                    events.append(event)
                except Exception as e:
                    logger.warning(f"{self.name} transform error: {e}")
            
            # Ingest
            await self.ingest(events)
            
            # Update stats
            self.stats.total_fetches += 1
            self.stats.successful_fetches += 1
            self.stats.last_fetch_time = datetime.utcnow()
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.stats.avg_fetch_duration_ms = (
                (self.stats.avg_fetch_duration_ms * (self.stats.total_fetches - 1) + duration_ms)
                / self.stats.total_fetches
            )
            
            return events
            
        except Exception as e:
            self.stats.failed_fetches += 1
            self.stats.last_error = str(e)
            self.stats.last_error_time = datetime.utcnow()
            logger.error(f"{self.name} run_once error: {e}")
            raise
    
    async def run_loop(self) -> None:
        """Run continuous collection loop."""
        self.status = CollectorStatus.RUNNING
        logger.info(f"{self.name} collector started")
        
        retry_count = 0
        retry_delay = self.retry_config.initial_delay
        
        while not self._stop_event.is_set():
            try:
                await self.run_once()
                retry_count = 0
                retry_delay = self.retry_config.initial_delay
                
            except Exception as e:
                self.status = CollectorStatus.ERROR
                retry_count += 1
                
                if retry_count >= self.retry_config.max_retries:
                    logger.error(f"{self.name} max retries reached, stopping")
                    break
                
                logger.warning(f"{self.name} error (retry {retry_count}): {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(
                    retry_delay * self.retry_config.exponential_base,
                    self.retry_config.max_delay
                )
                continue
            
            # Wait for next poll
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval_seconds
                )
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue loop
        
        self.status = CollectorStatus.STOPPED
        logger.info(f"{self.name} collector stopped")
    
    def stop(self) -> None:
        """Signal the collector to stop."""
        self._stop_event.set()
    
    def get_status(self) -> Dict[str, Any]:
        """Get collector status and stats."""
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "status": self.status.value,
            "poll_interval": self.poll_interval_seconds,
            "stats": {
                "total_fetches": self.stats.total_fetches,
                "successful_fetches": self.stats.successful_fetches,
                "failed_fetches": self.stats.failed_fetches,
                "total_events": self.stats.total_events,
                "last_fetch_time": self.stats.last_fetch_time.isoformat() if self.stats.last_fetch_time else None,
                "last_error": self.stats.last_error,
                "last_error_time": self.stats.last_error_time.isoformat() if self.stats.last_error_time else None,
                "avg_fetch_duration_ms": round(self.stats.avg_fetch_duration_ms, 2),
            }
        }