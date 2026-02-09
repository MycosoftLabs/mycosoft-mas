"""
Timeline API Router - February 6, 2026

FastAPI endpoints for timeline data with multi-tier caching.
Provides efficient access to historical and live timeline data.

Endpoints:
- GET /api/timeline/range - Query data for a time range
- GET /api/timeline/entity/{type}/{id} - Get entity timeline
- GET /api/timeline/at - Get entity state at specific time
- POST /api/timeline/batch - Batch query multiple entities
- GET /api/timeline/stats - Cache statistics
- POST /api/timeline/ingest - Ingest new data
- WebSocket /ws/timeline - Live updates subscription
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from mycosoft_mas.cache import (
    TimelineCacheManager,
    TimelineEntry,
    TimelineQuery,
    EntityType,
    DataSource,
    get_timeline_cache,
    get_snapshot_manager,
)

logger = logging.getLogger("TimelineAPI")
router = APIRouter(prefix="/timeline", tags=["timeline"])


# --- Pydantic Models ---

class TimelineDataPoint(BaseModel):
    """A single timeline data point."""
    entity_type: str
    entity_id: str
    timestamp: int
    position: Optional[Dict[str, float]] = None  # lat, lng, altitude
    velocity: Optional[Dict[str, float]] = None  # speed, heading, climb
    metadata: Optional[Dict[str, Any]] = None
    source: str = "live"


class TimelineRangeRequest(BaseModel):
    """Request for time range query."""
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    limit: int = Field(default=1000, le=10000)
    source: Optional[str] = None
    # Viewport bounds
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lng: Optional[float] = None
    max_lng: Optional[float] = None


class TimelineRangeResponse(BaseModel):
    """Response for time range query."""
    data: List[TimelineDataPoint]
    count: int
    source: str  # cache tier that served the request
    latency_ms: float
    has_more: bool = False


class BatchQueryRequest(BaseModel):
    """Batch query for multiple entities."""
    queries: List[TimelineRangeRequest]


class BatchQueryResponse(BaseModel):
    """Response for batch query."""
    results: List[TimelineRangeResponse]
    total_count: int
    total_latency_ms: float


class IngestRequest(BaseModel):
    """Request to ingest new timeline data."""
    entries: List[TimelineDataPoint]


class IngestResponse(BaseModel):
    """Response for ingest request."""
    ingested: int
    errors: List[str] = []


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    memory: Dict[str, Any]
    redis: Dict[str, Any]
    snapshots: Dict[str, Any]
    overall_hit_rate: float


# --- Helper Functions ---

def entry_to_datapoint(entry: TimelineEntry) -> TimelineDataPoint:
    """Convert TimelineEntry to TimelineDataPoint."""
    return TimelineDataPoint(
        entity_type=entry.entity_type.value,
        entity_id=entry.entity_id,
        timestamp=entry.timestamp,
        position=entry.data.get("position"),
        velocity=entry.data.get("velocity"),
        metadata=entry.data.get("metadata"),
        source=entry.source.value,
    )


def datapoint_to_entry(dp: TimelineDataPoint) -> TimelineEntry:
    """Convert TimelineDataPoint to TimelineEntry."""
    return TimelineEntry(
        entity_type=EntityType(dp.entity_type),
        entity_id=dp.entity_id,
        timestamp=dp.timestamp,
        data={
            "position": dp.position,
            "velocity": dp.velocity,
            "metadata": dp.metadata,
        },
        source=DataSource(dp.source) if dp.source else DataSource.LIVE,
    )


def request_to_query(req: TimelineRangeRequest) -> TimelineQuery:
    """Convert request to TimelineQuery."""
    return TimelineQuery(
        entity_type=EntityType(req.entity_type) if req.entity_type else None,
        entity_id=req.entity_id,
        start_time=req.start_time,
        end_time=req.end_time,
        limit=req.limit,
        source=DataSource(req.source) if req.source else None,
        min_lat=req.min_lat,
        max_lat=req.max_lat,
        min_lng=req.min_lng,
        max_lng=req.max_lng,
    )


# --- API Endpoints ---

@router.get("/range", response_model=TimelineRangeResponse)
async def query_time_range(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    start_time: Optional[int] = Query(None, description="Start timestamp (ms)"),
    end_time: Optional[int] = Query(None, description="End timestamp (ms)"),
    limit: int = Query(1000, le=10000, description="Maximum entries to return"),
    source: Optional[str] = Query(None, description="Filter by data source"),
):
    """
    Query timeline data for a time range.
    
    Returns data from the fastest available cache tier.
    """
    try:
        cache = await get_timeline_cache()
        
        query = TimelineQuery(
            entity_type=EntityType(entity_type) if entity_type else None,
            entity_id=entity_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            source=DataSource(source) if source else None,
        )
        
        result = await cache.get(query)
        
        # If cache miss, try snapshots for historical data
        if not result.hit and start_time:
            snapshot_mgr = get_snapshot_manager()
            et = entity_type or "aircraft"  # Default entity type for snapshots
            snapshot_data = await snapshot_mgr.query_snapshots(
                et,
                start_time,
                end_time or int(datetime.now().timestamp() * 1000),
            )
            
            if snapshot_data:
                # Convert to TimelineDataPoint
                data = [TimelineDataPoint(**d) for d in snapshot_data[:limit]]
                return TimelineRangeResponse(
                    data=data,
                    count=len(data),
                    source="snapshot",
                    latency_ms=result.latency_ms,
                    has_more=len(snapshot_data) > limit,
                )
        
        data = [entry_to_datapoint(e) for e in result.data]
        
        return TimelineRangeResponse(
            data=data,
            count=len(data),
            source=result.source,
            latency_ms=result.latency_ms,
            has_more=len(data) >= limit,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Timeline range query error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/entity/{entity_type}/{entity_id}", response_model=TimelineRangeResponse)
async def get_entity_timeline(
    entity_type: str,
    entity_id: str,
    start_time: Optional[int] = Query(None),
    end_time: Optional[int] = Query(None),
    limit: int = Query(1000, le=10000),
):
    """
    Get timeline for a specific entity.
    """
    try:
        cache = await get_timeline_cache()
        
        query = TimelineQuery(
            entity_type=EntityType(entity_type),
            entity_id=entity_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        
        result = await cache.get(query)
        data = [entry_to_datapoint(e) for e in result.data]
        
        return TimelineRangeResponse(
            data=data,
            count=len(data),
            source=result.source,
            latency_ms=result.latency_ms,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Entity timeline error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/at", response_model=Optional[TimelineDataPoint])
async def get_entity_at_time(
    entity_type: str = Query(..., description="Entity type"),
    entity_id: str = Query(..., description="Entity ID"),
    timestamp: int = Query(..., description="Timestamp (ms) to query"),
    tolerance_ms: int = Query(60000, description="Time tolerance for finding nearest"),
):
    """
    Get entity state at a specific timestamp.
    
    Returns the closest available data point within the tolerance window.
    """
    try:
        cache = await get_timeline_cache()
        
        # Query a window around the timestamp
        query = TimelineQuery(
            entity_type=EntityType(entity_type),
            entity_id=entity_id,
            start_time=timestamp - tolerance_ms,
            end_time=timestamp + tolerance_ms,
            limit=10,
        )
        
        result = await cache.get(query)
        
        if not result.data:
            return None
        
        # Find closest point
        closest = min(result.data, key=lambda e: abs(e.timestamp - timestamp))
        
        return entry_to_datapoint(closest)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Entity at time error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch", response_model=BatchQueryResponse)
async def batch_query(request: BatchQueryRequest):
    """
    Batch query for multiple entities/time ranges.
    
    More efficient than multiple individual requests.
    """
    import time
    start = time.time()
    
    try:
        cache = await get_timeline_cache()
        results = []
        total_count = 0
        
        # Execute queries in parallel
        async def execute_query(req: TimelineRangeRequest):
            query = request_to_query(req)
            return await cache.get(query)
        
        tasks = [execute_query(q) for q in request.queries]
        query_results = await asyncio.gather(*tasks)
        
        for result in query_results:
            data = [entry_to_datapoint(e) for e in result.data]
            total_count += len(data)
            
            results.append(TimelineRangeResponse(
                data=data,
                count=len(data),
                source=result.source,
                latency_ms=result.latency_ms,
            ))
        
        return BatchQueryResponse(
            results=results,
            total_count=total_count,
            total_latency_ms=(time.time() - start) * 1000,
        )
        
    except Exception as e:
        logger.error(f"Batch query error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_data(request: IngestRequest):
    """
    Ingest new timeline data.
    
    Data is stored in all cache tiers for immediate availability.
    """
    try:
        cache = await get_timeline_cache()
        
        entries = [datapoint_to_entry(dp) for dp in request.entries]
        errors = []
        
        try:
            await cache.put_batch(entries)
        except Exception as e:
            errors.append(str(e))
        
        return IngestResponse(
            ingested=len(entries) - len(errors),
            errors=errors,
        )
        
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/cache")
async def invalidate_cache(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
):
    """
    Invalidate cache entries.
    
    If no parameters provided, clears all cache.
    """
    try:
        cache = await get_timeline_cache()
        
        et = EntityType(entity_type) if entity_type else None
        result = await cache.invalidate(et, entity_id)
        
        return {"invalidated": result}
        
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get comprehensive cache statistics.
    """
    try:
        cache = await get_timeline_cache()
        snapshot_mgr = get_snapshot_manager()
        
        cache_stats = await cache.get_stats()
        snapshot_stats = await snapshot_mgr.get_stats()
        
        return CacheStatsResponse(
            memory=cache_stats.get("memory", {}),
            redis=cache_stats.get("redis", {}),
            snapshots=snapshot_stats,
            overall_hit_rate=cache_stats.get("overall_cache_hit_rate", 0),
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check():
    """Timeline API health check."""
    try:
        cache = await get_timeline_cache()
        stats = await cache.get_stats()
        
        return {
            "status": "healthy",
            "cache_connected": stats.get("redis", {}).get("connected", False),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# --- WebSocket for Live Updates ---

class ConnectionManager:
    """Manage WebSocket connections for live updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, entity_types: List[str]):
        await websocket.accept()
        for et in entity_types:
            if et not in self.active_connections:
                self.active_connections[et] = []
            self.active_connections[et].append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        for et, connections in self.active_connections.items():
            if websocket in connections:
                connections.remove(websocket)
    
    async def broadcast(self, entity_type: str, data: Dict[str, Any]):
        if entity_type in self.active_connections:
            for connection in self.active_connections[entity_type]:
                try:
                    await connection.send_json(data)
                except Exception:
                    self.disconnect(connection)


ws_manager = ConnectionManager()


@router.websocket("/ws/timeline")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for live timeline updates.
    
    Subscribe to entity types and receive real-time updates.
    """
    await websocket.accept()
    subscribed_types: List[str] = []
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "subscribe":
                entity_types = data.get("entityTypes", [])
                await ws_manager.connect(websocket, entity_types)
                subscribed_types.extend(entity_types)
                await websocket.send_json({
                    "type": "subscribed",
                    "entityTypes": entity_types,
                })
            
            elif data.get("type") == "unsubscribe":
                ws_manager.disconnect(websocket)
                subscribed_types.clear()
                await websocket.send_json({"type": "unsubscribed"})
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


async def broadcast_live_update(entry: TimelineEntry):
    """Broadcast a live update to all subscribed clients."""
    await ws_manager.broadcast(
        entry.entity_type.value,
        {
            "type": "update",
            "data": [entry_to_datapoint(entry).model_dump()],
        },
    )