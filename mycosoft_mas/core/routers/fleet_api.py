"""
Fleet Management API Router - February 19, 2026

Device groups, bulk operations, and provisioning workflows for NatureOS IoT.
State is stored in Redis; device operations are executed via device registry.

NO MOCK DATA - returns empty datasets when no fleet state exists.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.core.routers import device_registry_api

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/iot/fleet", tags=["IoT Fleet"])

FLEET_GROUP_PREFIX = "iot:fleet:group:"
FLEET_GROUPS_SET = "iot:fleet:groups"
PROVISION_TOKEN_PREFIX = "iot:fleet:provision:"

_redis_client: Optional[redis.Redis] = None


class FleetGroupRecord(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    device_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class FleetGroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    device_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FleetGroupUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    device_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class BulkCommandRequest(BaseModel):
    device_ids: List[str] = Field(..., min_items=1)
    command: str = Field(..., min_length=1)
    params: Dict[str, Any] = Field(default_factory=dict)
    timeout: float = Field(default=5.0, ge=1.0, le=60.0)


class FirmwareDeployRequest(BaseModel):
    device_ids: List[str] = Field(..., min_items=1)
    firmware_version: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProvisionRequest(BaseModel):
    device_role: str
    device_name: Optional[str] = None
    location: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ttl_seconds: int = Field(default=3600, ge=300, le=86400)


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


def _group_key(group_id: str) -> str:
    return f"{FLEET_GROUP_PREFIX}{group_id}"


def _provision_key(token: str) -> str:
    return f"{PROVISION_TOKEN_PREFIX}{token}"


async def _load_group(group_id: str) -> FleetGroupRecord:
    redis_client = await _get_redis()
    payload = await redis_client.get(_group_key(group_id))
    if not payload:
        raise HTTPException(status_code=404, detail="Fleet group not found")
    try:
        data = json.loads(payload)
        return FleetGroupRecord(**data)
    except Exception as exc:
        logger.error("Fleet group decode failed: %s", exc)
        raise HTTPException(status_code=500, detail="Fleet group record corrupted")


async def _save_group(group: FleetGroupRecord) -> None:
    redis_client = await _get_redis()
    await redis_client.set(_group_key(group.id), group.model_dump_json())
    await redis_client.sadd(FLEET_GROUPS_SET, group.id)


async def _delete_group(group_id: str) -> None:
    redis_client = await _get_redis()
    await redis_client.delete(_group_key(group_id))
    await redis_client.srem(FLEET_GROUPS_SET, group_id)


def _registry_has_device(device_id: str) -> bool:
    return device_id in device_registry_api._device_registry  # noqa: SLF001


@router.get("/health")
async def fleet_health() -> Dict[str, Any]:
    redis_client = await _get_redis()
    try:
        pong = await redis_client.ping()
        return {
            "status": "healthy" if pong else "degraded",
            "service": "fleet-management",
            "redis": "ok" if pong else "unreachable",
            "timestamp": _now_iso(),
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "service": "fleet-management",
            "redis": "error",
            "error": str(exc),
            "timestamp": _now_iso(),
        }


@router.get("/groups", response_model=List[FleetGroupRecord])
async def list_groups() -> List[FleetGroupRecord]:
    redis_client = await _get_redis()
    group_ids = await redis_client.smembers(FLEET_GROUPS_SET)
    if not group_ids:
        return []
    payloads = await redis_client.mget([_group_key(group_id) for group_id in group_ids])
    groups: List[FleetGroupRecord] = []
    for payload in payloads:
        if not payload:
            continue
        try:
            data = json.loads(payload)
            groups.append(FleetGroupRecord(**data))
        except Exception as exc:
            logger.warning("Skipping invalid fleet group: %s", exc)
    return sorted(groups, key=lambda g: g.created_at, reverse=True)


@router.post("/groups", response_model=FleetGroupRecord)
async def create_group(payload: FleetGroupCreateRequest) -> FleetGroupRecord:
    group_id = str(uuid4())
    now = _now_iso()
    group = FleetGroupRecord(
        id=group_id,
        name=payload.name,
        description=payload.description,
        device_ids=list(dict.fromkeys(payload.device_ids)),
        metadata=payload.metadata,
        created_at=now,
        updated_at=now,
    )
    await _save_group(group)
    return group


@router.get("/groups/{group_id}", response_model=FleetGroupRecord)
async def get_group(group_id: str) -> FleetGroupRecord:
    return await _load_group(group_id)


@router.patch("/groups/{group_id}", response_model=FleetGroupRecord)
async def update_group(group_id: str, payload: FleetGroupUpdateRequest) -> FleetGroupRecord:
    group = await _load_group(group_id)
    updated = group.model_copy(deep=True)
    if payload.name is not None:
        updated.name = payload.name
    if payload.description is not None:
        updated.description = payload.description
    if payload.device_ids is not None:
        updated.device_ids = list(dict.fromkeys(payload.device_ids))
    if payload.metadata is not None:
        updated.metadata = payload.metadata
    updated.updated_at = _now_iso()
    await _save_group(updated)
    return updated


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str) -> Dict[str, Any]:
    await _load_group(group_id)
    await _delete_group(group_id)
    return {"status": "deleted", "group_id": group_id}


@router.post("/groups/{group_id}/devices")
async def add_devices_to_group(group_id: str, device_ids: List[str]) -> Dict[str, Any]:
    if not device_ids:
        raise HTTPException(status_code=400, detail="device_ids list required")
    group = await _load_group(group_id)
    unknown = [device_id for device_id in device_ids if not _registry_has_device(device_id)]
    updated = group.model_copy(deep=True)
    updated.device_ids = list(dict.fromkeys(updated.device_ids + device_ids))
    updated.updated_at = _now_iso()
    await _save_group(updated)
    return {
        "status": "updated",
        "group_id": group_id,
        "added": device_ids,
        "unknown_devices": unknown,
    }


@router.post("/bulk/commands")
async def bulk_command(payload: BulkCommandRequest) -> Dict[str, Any]:
    results = []
    failures = []
    for device_id in payload.device_ids:
        cmd = device_registry_api.DeviceCommand(
            command=payload.command,
            params=payload.params,
            timeout=payload.timeout,
        )
        try:
            result = await device_registry_api.send_device_command(device_id, cmd)
            results.append(result)
        except HTTPException as exc:
            failures.append({"device_id": device_id, "error": exc.detail})
        except Exception as exc:
            failures.append({"device_id": device_id, "error": str(exc)})
    return {
        "status": "completed",
        "requested": len(payload.device_ids),
        "succeeded": len(results),
        "failed": len(failures),
        "results": results,
        "failures": failures,
        "timestamp": _now_iso(),
    }


@router.post("/firmware/deploy")
async def deploy_firmware(payload: FirmwareDeployRequest) -> Dict[str, Any]:
    results = []
    failures = []
    for device_id in payload.device_ids:
        cmd = device_registry_api.DeviceCommand(
            command="firmware_update",
            params={"version": payload.firmware_version, **payload.metadata},
            timeout=10.0,
        )
        try:
            result = await device_registry_api.send_device_command(device_id, cmd)
            results.append(result)
        except HTTPException as exc:
            failures.append({"device_id": device_id, "error": exc.detail})
        except Exception as exc:
            failures.append({"device_id": device_id, "error": str(exc)})
    return {
        "status": "completed",
        "firmware_version": payload.firmware_version,
        "requested": len(payload.device_ids),
        "succeeded": len(results),
        "failed": len(failures),
        "results": results,
        "failures": failures,
        "timestamp": _now_iso(),
    }


@router.post("/provisioning")
async def create_provisioning_token(payload: ProvisionRequest) -> Dict[str, Any]:
    token = str(uuid4())
    redis_client = await _get_redis()
    record = {
        "token": token,
        "device_role": payload.device_role,
        "device_name": payload.device_name,
        "location": payload.location,
        "metadata": payload.metadata,
        "created_at": _now_iso(),
    }
    await redis_client.set(_provision_key(token), json.dumps(record), ex=payload.ttl_seconds)
    return {"status": "created", "token": token, "expires_in": payload.ttl_seconds}


@router.get("/provisioning/{token}")
async def get_provisioning_token(token: str) -> Dict[str, Any]:
    redis_client = await _get_redis()
    payload = await redis_client.get(_provision_key(token))
    if not payload:
        raise HTTPException(status_code=404, detail="Provisioning token not found")
    return json.loads(payload)
