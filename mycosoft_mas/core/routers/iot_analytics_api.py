"""
IoT Analytics API Router - February 19, 2026

Fleet health, trends, and anomaly insights for NatureOS IoT.
Reads real device registry data and analytics records stored in Redis.

NO MOCK DATA - returns empty datasets when no analytics are stored.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mycosoft_mas.core.routers import device_registry_api

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/iot/analytics", tags=["IoT Analytics"])

FLEET_TRENDS_PREFIX = "iot:analytics:trend:"
FLEET_ANOMALIES_KEY = "iot:analytics:anomalies"

_redis_client: Optional[redis.Redis] = None


class FleetHealthResponse(BaseModel):
    total_devices: int
    online_devices: int
    stale_devices: int
    offline_devices: int
    uptime_pct: float
    by_role: Dict[str, int] = Field(default_factory=dict)
    timestamp: str


class TrendPoint(BaseModel):
    timestamp: str
    metrics: Dict[str, Any]


class TrendSeries(BaseModel):
    device_id: Optional[str] = None
    metric: Optional[str] = None
    points: List[TrendPoint]
    source: str


class AnomalyRecord(BaseModel):
    id: str
    device_id: Optional[str] = None
    severity: str
    message: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


async def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        redis_host = os.getenv("REDIS_HOST", "192.168.0.189")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )
    return _redis_client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_device_status(device_id: str) -> str:
    return device_registry_api._get_device_status(device_id)  # noqa: SLF001


def _get_registry_snapshot() -> List[Dict[str, Any]]:
    registry = device_registry_api._device_registry  # noqa: SLF001
    return list(registry.values())


async def _read_json_list(redis_client: redis.Redis, key: str, limit: int) -> List[Dict[str, Any]]:
    payloads = await redis_client.lrange(key, 0, max(limit - 1, 0))
    records: List[Dict[str, Any]] = []
    for payload in payloads:
        try:
            records.append(json.loads(payload))
        except Exception as exc:
            logger.warning("Skipping invalid analytics payload: %s", exc)
    return records


@router.get("/health")
async def analytics_health() -> Dict[str, Any]:
    redis_client = await _get_redis()
    try:
        pong = await redis_client.ping()
        return {
            "status": "healthy" if pong else "degraded",
            "service": "iot-analytics",
            "redis": "ok" if pong else "unreachable",
            "timestamp": _now_iso(),
        }
    except Exception as exc:
        logger.error("Analytics health check failed: %s", exc)
        return {
            "status": "degraded",
            "service": "iot-analytics",
            "redis": "error",
            "error": str(exc),
            "timestamp": _now_iso(),
        }


@router.get("/fleet-health", response_model=FleetHealthResponse)
async def fleet_health() -> FleetHealthResponse:
    """Calculate fleet health using the live device registry."""
    registry = _get_registry_snapshot()
    total = len(registry)
    by_role: Dict[str, int] = {}
    online = 0
    stale = 0

    for device in registry:
        device_id = device.get("device_id")
        if not device_id:
            continue
        status = _get_device_status(device_id)
        if status == "online":
            online += 1
        elif status == "stale":
            stale += 1
        role = device.get("device_role", "unknown") or "unknown"
        by_role[role] = by_role.get(role, 0) + 1

    offline = max(total - online - stale, 0)
    uptime_pct = round((online / total) * 100, 2) if total else 0.0

    return FleetHealthResponse(
        total_devices=total,
        online_devices=online,
        stale_devices=stale,
        offline_devices=offline,
        uptime_pct=uptime_pct,
        by_role=by_role,
        timestamp=_now_iso(),
    )


@router.get("/trends", response_model=TrendSeries)
async def telemetry_trends(
    device_id: Optional[str] = Query(default=None),
    metric: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> TrendSeries:
    """
    Return stored telemetry trend points from Redis.

    Records must be written by the telemetry pipeline to:
    - iot:analytics:trend:{device_id} (device-specific)
    - iot:analytics:trend:global (aggregate)
    """
    redis_client = await _get_redis()
    key_suffix = device_id or "global"
    key = f"{FLEET_TRENDS_PREFIX}{key_suffix}"
    records = await _read_json_list(redis_client, key, limit)
    points = [
        TrendPoint(
            timestamp=record.get("timestamp", ""),
            metrics=record.get("metrics", {}),
        )
        for record in records
    ]
    if metric:
        filtered_points = []
        for point in points:
            if metric in point.metrics:
                filtered_points.append(point)
        points = filtered_points

    return TrendSeries(
        device_id=device_id,
        metric=metric,
        points=points,
        source="redis",
    )


@router.get("/anomalies", response_model=List[AnomalyRecord])
async def list_anomalies(
    device_id: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> List[AnomalyRecord]:
    """
    Return stored anomaly records from Redis list iot:analytics:anomalies.
    Each record should be JSON with id, device_id, severity, message, timestamp, metadata.
    """
    redis_client = await _get_redis()
    records = await _read_json_list(redis_client, FLEET_ANOMALIES_KEY, limit)
    anomalies: List[AnomalyRecord] = []
    for record in records:
        if device_id and record.get("device_id") != device_id:
            continue
        try:
            anomalies.append(AnomalyRecord(**record))
        except Exception as exc:
            logger.warning("Skipping invalid anomaly record: %s", exc)
    return anomalies
