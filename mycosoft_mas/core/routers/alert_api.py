"""
Alert Service API Router - February 19, 2026

Alert CRUD + rules management backed by Redis with pub/sub integration.
Publishes to Redis channel system:alerts for real-time delivery.

NO MOCK DATA - all data stored in Redis (VM 192.168.0.189 by default).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mycosoft_mas.realtime.redis_pubsub import Channel, get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/iot/alerts", tags=["IoT Alerts"])

ALERT_KEY_PREFIX = "iot:alert:"
ALERTS_INDEX_KEY = "iot:alerts:timeline"
RULE_KEY_PREFIX = "iot:alert_rule:"
RULES_SET_KEY = "iot:alert_rules"


class AlertSeverity(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class AlertStatus(str, Enum):
    open = "open"
    acknowledged = "acknowledged"
    dismissed = "dismissed"
    resolved = "resolved"


class AlertRecord(BaseModel):
    id: str
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    device_id: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class AlertCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    severity: AlertSeverity = AlertSeverity.warning
    device_id: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertUpdateRequest(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    status: Optional[AlertStatus] = None
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AlertRuleRecord(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    condition: Dict[str, Any]
    severity: AlertSeverity
    is_enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class AlertRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    condition: Dict[str, Any]
    severity: AlertSeverity = AlertSeverity.warning
    is_enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertRuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    severity: Optional[AlertSeverity] = None
    is_enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


_redis_client: Optional[redis.Redis] = None


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


def _parse_iso_to_epoch(timestamp: str) -> float:
    try:
        dt = datetime.fromisoformat(timestamp)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return datetime.now(timezone.utc).timestamp()


def _alert_key(alert_id: str) -> str:
    return f"{ALERT_KEY_PREFIX}{alert_id}"


def _rule_key(rule_id: str) -> str:
    return f"{RULE_KEY_PREFIX}{rule_id}"


async def _publish_alert_event(event_type: str, alert: AlertRecord) -> None:
    try:
        client = await get_client()
        await client.publish(
            Channel.SYSTEM_ALERTS.value,
            {"event": event_type, "alert": alert.model_dump()},
            source=alert.source or "alert-service",
        )
    except Exception as exc:
        logger.warning("Alert pubsub publish failed: %s", exc)


async def _load_alert(alert_id: str) -> AlertRecord:
    redis_client = await _get_redis()
    payload = await redis_client.get(_alert_key(alert_id))
    if not payload:
        raise HTTPException(status_code=404, detail="Alert not found")
    try:
        data = json.loads(payload)
        return AlertRecord(**data)
    except Exception as exc:
        logger.error("Alert decode failed: %s", exc)
        raise HTTPException(status_code=500, detail="Alert record corrupted")


async def _save_alert(alert: AlertRecord) -> None:
    redis_client = await _get_redis()
    await redis_client.set(_alert_key(alert.id), alert.model_dump_json())
    await redis_client.zadd(ALERTS_INDEX_KEY, {alert.id: _parse_iso_to_epoch(alert.created_at)})


async def _delete_alert(alert_id: str) -> None:
    redis_client = await _get_redis()
    await redis_client.delete(_alert_key(alert_id))
    await redis_client.zrem(ALERTS_INDEX_KEY, alert_id)


async def _load_rule(rule_id: str) -> AlertRuleRecord:
    redis_client = await _get_redis()
    payload = await redis_client.get(_rule_key(rule_id))
    if not payload:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    try:
        data = json.loads(payload)
        return AlertRuleRecord(**data)
    except Exception as exc:
        logger.error("Alert rule decode failed: %s", exc)
        raise HTTPException(status_code=500, detail="Alert rule record corrupted")


async def _save_rule(rule: AlertRuleRecord) -> None:
    redis_client = await _get_redis()
    await redis_client.set(_rule_key(rule.id), rule.model_dump_json())
    await redis_client.sadd(RULES_SET_KEY, rule.id)


async def _delete_rule(rule_id: str) -> None:
    redis_client = await _get_redis()
    await redis_client.delete(_rule_key(rule_id))
    await redis_client.srem(RULES_SET_KEY, rule_id)


@router.get("/health")
async def alerts_health() -> Dict[str, Any]:
    """Health check for alert service and Redis connectivity."""
    redis_client = await _get_redis()
    try:
        pong = await redis_client.ping()
        return {
            "status": "healthy" if pong else "degraded",
            "service": "alert-service",
            "redis": "ok" if pong else "unreachable",
            "timestamp": _now_iso(),
        }
    except Exception as exc:
        logger.error("Alert service health check failed: %s", exc)
        return {
            "status": "degraded",
            "service": "alert-service",
            "redis": "error",
            "error": str(exc),
            "timestamp": _now_iso(),
        }


@router.post("", response_model=AlertRecord)
async def create_alert(payload: AlertCreateRequest) -> AlertRecord:
    """Create a new alert and publish to Redis pub/sub."""
    alert_id = str(uuid4())
    now = _now_iso()
    alert = AlertRecord(
        id=alert_id,
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        status=AlertStatus.open,
        device_id=payload.device_id,
        source=payload.source,
        category=payload.category,
        metadata=payload.metadata,
        created_at=now,
        updated_at=now,
    )
    await _save_alert(alert)
    await _publish_alert_event("created", alert)
    return alert


@router.get("", response_model=List[AlertRecord])
async def list_alerts(
    status: Optional[AlertStatus] = Query(default=None),
    severity: Optional[AlertSeverity] = Query(default=None),
    device_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> List[AlertRecord]:
    """List alerts with optional filters."""
    redis_client = await _get_redis()
    alert_ids = await redis_client.zrevrange(ALERTS_INDEX_KEY, offset, offset + limit - 1)
    if not alert_ids:
        return []

    keys = [_alert_key(alert_id) for alert_id in alert_ids]
    payloads = await redis_client.mget(keys)
    alerts: List[AlertRecord] = []
    for payload in payloads:
        if not payload:
            continue
        try:
            data = json.loads(payload)
            record = AlertRecord(**data)
        except Exception as exc:
            logger.warning("Skipping invalid alert record: %s", exc)
            continue
        if status and record.status != status:
            continue
        if severity and record.severity != severity:
            continue
        if device_id and record.device_id != device_id:
            continue
        alerts.append(record)
    return alerts


@router.get("/{alert_id}", response_model=AlertRecord)
async def get_alert(alert_id: str) -> AlertRecord:
    """Fetch a single alert by ID."""
    return await _load_alert(alert_id)


@router.patch("/{alert_id}", response_model=AlertRecord)
async def update_alert(alert_id: str, payload: AlertUpdateRequest) -> AlertRecord:
    """Update alert properties (status, severity, metadata)."""
    alert = await _load_alert(alert_id)
    updated = alert.model_copy(deep=True)
    if payload.title is not None:
        updated.title = payload.title
    if payload.message is not None:
        updated.message = payload.message
    if payload.severity is not None:
        updated.severity = payload.severity
    if payload.status is not None:
        updated.status = payload.status
    if payload.category is not None:
        updated.category = payload.category
    if payload.metadata is not None:
        updated.metadata = payload.metadata
    updated.updated_at = _now_iso()
    await _save_alert(updated)
    await _publish_alert_event("updated", updated)
    return updated


@router.post("/{alert_id}/acknowledge", response_model=AlertRecord)
async def acknowledge_alert(alert_id: str) -> AlertRecord:
    """Acknowledge an alert."""
    alert = await _load_alert(alert_id)
    updated = alert.model_copy(deep=True)
    updated.status = AlertStatus.acknowledged
    updated.updated_at = _now_iso()
    await _save_alert(updated)
    await _publish_alert_event("acknowledged", updated)
    return updated


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str) -> Dict[str, Any]:
    """Delete an alert."""
    await _load_alert(alert_id)
    await _delete_alert(alert_id)
    return {"status": "deleted", "alert_id": alert_id}


@router.get("/rules", response_model=List[AlertRuleRecord])
async def list_rules() -> List[AlertRuleRecord]:
    redis_client = await _get_redis()
    rule_ids = await redis_client.smembers(RULES_SET_KEY)
    if not rule_ids:
        return []
    keys = [_rule_key(rule_id) for rule_id in rule_ids]
    payloads = await redis_client.mget(keys)
    rules: List[AlertRuleRecord] = []
    for payload in payloads:
        if not payload:
            continue
        try:
            data = json.loads(payload)
            rules.append(AlertRuleRecord(**data))
        except Exception as exc:
            logger.warning("Skipping invalid alert rule: %s", exc)
    return sorted(rules, key=lambda r: r.created_at, reverse=True)


@router.post("/rules", response_model=AlertRuleRecord)
async def create_rule(payload: AlertRuleCreateRequest) -> AlertRuleRecord:
    rule_id = str(uuid4())
    now = _now_iso()
    rule = AlertRuleRecord(
        id=rule_id,
        name=payload.name,
        description=payload.description,
        condition=payload.condition,
        severity=payload.severity,
        is_enabled=payload.is_enabled,
        metadata=payload.metadata,
        created_at=now,
        updated_at=now,
    )
    await _save_rule(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=AlertRuleRecord)
async def update_rule(rule_id: str, payload: AlertRuleUpdateRequest) -> AlertRuleRecord:
    rule = await _load_rule(rule_id)
    updated = rule.model_copy(deep=True)
    if payload.name is not None:
        updated.name = payload.name
    if payload.description is not None:
        updated.description = payload.description
    if payload.condition is not None:
        updated.condition = payload.condition
    if payload.severity is not None:
        updated.severity = payload.severity
    if payload.is_enabled is not None:
        updated.is_enabled = payload.is_enabled
    if payload.metadata is not None:
        updated.metadata = payload.metadata
    updated.updated_at = _now_iso()
    await _save_rule(updated)
    return updated


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str) -> Dict[str, Any]:
    await _load_rule(rule_id)
    await _delete_rule(rule_id)
    return {"status": "deleted", "rule_id": rule_id}
