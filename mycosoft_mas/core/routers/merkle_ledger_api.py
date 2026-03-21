"""
MICA / MYCA Merkleized Cognition Ledger API.

Endpoints for event leaf hashing, root building (temporal, spatial, event,
self, world, thought), and thought root retrieval.

See merkle/mica_merkle_spec/README.md for architecture.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.merkle import (
    EventIndexRow,
    EventRootBuilder,
    ThoughtRootBuilder,
    build_inclusion_proof,
    hex32,
    leaf_hash_from_cbor_object,
)
from mycosoft_mas.merkle.world_root_service import build_world_root

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/merkle", tags=["merkle-ledger"])

# Default tick width: 1 second
TICK_WIDTH_NS_DEFAULT = 1_000_000_000


# --- Request/Response models ---


class EventHashRequest(BaseModel):
    """Request to compute event leaf hash from canonical object (as CBOR-like dict)."""

    event: dict[str, Any] = Field(..., description="Canonical event object (will be CBOR-encoded)")


class EventHashResponse(BaseModel):
    event_hash_hex: str = Field(..., description="BLAKE3-256 hash as hex")
    event_hash_b64: Optional[str] = None


class TemporalRootRequest(BaseModel):
    tick_id: int = Field(..., ge=0)
    tick_width_ns: int = Field(TICK_WIDTH_NS_DEFAULT, gt=0)
    event_hashes: list[dict[str, Any]] = Field(
        ...,
        description="List of {event_hash (bytes as b64 or hex), event_time_ns, device_id, event_id, h3_cell?}",
    )
    status: str = Field("provisional", description="open|provisional|final")
    previous_root_hash_hex: Optional[str] = None


class WorldRootRequest(BaseModel):
    """Optional slot data for world root. If empty, device_registry + device_health are auto-fetched."""

    slot_data: Optional[dict[str, Any]] = Field(
        default=None, description="Slot name -> data (from WORLD_SLOT_ORDER)"
    )


class ThoughtRootRequest(BaseModel):
    tick_id: int = Field(..., ge=0)
    thought_time_ns: int = Field(..., ge=0)
    actor_id: str = Field("myca", description="Actor producing the thought")
    self_root_hash_hex: str = Field(...)
    world_root_hash_hex: str = Field(...)
    event_root_hash_hex: str = Field(...)
    truth_mirror_root_hash_hex: Optional[str] = None
    previous_thought_root_hash_hex: Optional[str] = None
    policy_root_hash_hex: Optional[str] = None
    session_id: Optional[str] = None


class RootResponse(BaseModel):
    root_hash_hex: str
    root_type: str
    tick_id: Optional[int] = None
    child_count: int
    status: str
    manifest_hash_hex: Optional[str] = None


# --- Helpers ---


def _hex_to_bytes(h: str) -> bytes:
    if len(h) == 64 and all(c in "0123456789abcdefABCDEF" for c in h):
        return bytes.fromhex(h)
    raise ValueError("invalid hex32")


# --- Endpoints ---


@router.get("/health")
async def merkle_health() -> dict:
    """Health check for Merkle ledger API."""
    return {"status": "ok", "service": "merkle-ledger", "version": "1.0.0"}


@router.post("/event/hash", response_model=EventHashResponse)
async def compute_event_hash(req: EventHashRequest) -> EventHashResponse:
    """Compute BLAKE3-256 leaf hash of a canonical event object (deterministic CBOR)."""
    try:
        digest = leaf_hash_from_cbor_object(req.event)
        return EventHashResponse(event_hash_hex=hex32(digest))
    except Exception as e:
        logger.exception("event hash failed")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/roots/temporal", response_model=RootResponse)
async def build_temporal_root(req: TemporalRootRequest) -> RootResponse:
    """Build temporal Merkle root for a tick from event index rows."""
    try:
        rows: list[EventIndexRow] = []
        for e in req.event_hashes:
            h = e.get("event_hash")
            if isinstance(h, str):
                event_hash = _hex_to_bytes(h)
            elif isinstance(h, bytes):
                event_hash = h
            else:
                raise ValueError("event_hash must be hex string or bytes")
            rows.append(
                EventIndexRow(
                    event_hash=event_hash,
                    event_time_ns=e.get("event_time_ns", 0),
                    device_id=e.get("device_id", ""),
                    event_id=e.get("event_id", ""),
                    h3_cell=e.get("h3_cell"),
                )
            )
        prev = _hex_to_bytes(req.previous_root_hash_hex) if req.previous_root_hash_hex else None
        builder = EventRootBuilder(tick_width_ns=req.tick_width_ns)
        rec = builder.build_temporal_root(
            tick_id=req.tick_id,
            events=rows,
            status=req.status,
            previous_root_hash=prev,
        )
        return RootResponse(
            root_hash_hex=hex32(rec.root_hash),
            root_type=rec.root_type,
            tick_id=rec.tick_id,
            child_count=rec.child_count,
            status=rec.status,
            manifest_hash_hex=hex32(rec.manifest_hash) if rec.manifest_hash else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("temporal root build failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/roots/thought", response_model=RootResponse)
async def build_thought_root(req: ThoughtRootRequest) -> RootResponse:
    """Build ThoughtPlanRoot for a tick (super-root for reasoning/actions)."""
    try:
        self_root = _hex_to_bytes(req.self_root_hash_hex)
        world_root = _hex_to_bytes(req.world_root_hash_hex)
        event_root = _hex_to_bytes(req.event_root_hash_hex)
        truth_mirror = (
            _hex_to_bytes(req.truth_mirror_root_hash_hex)
            if req.truth_mirror_root_hash_hex
            else None
        )
        prev = (
            _hex_to_bytes(req.previous_thought_root_hash_hex)
            if req.previous_thought_root_hash_hex
            else None
        )
        policy = _hex_to_bytes(req.policy_root_hash_hex) if req.policy_root_hash_hex else None

        builder = ThoughtRootBuilder()
        root_hash, _ = builder.build_thought_root(
            tick_id=req.tick_id,
            thought_time_ns=req.thought_time_ns,
            actor_id=req.actor_id,
            self_root_hash=self_root,
            world_root_hash=world_root,
            event_root_hash=event_root,
            truth_mirror_root_hash=truth_mirror,
            previous_thought_root_hash=prev,
            policy_root_hash=policy,
            session_id=req.session_id,
        )
        return RootResponse(
            root_hash_hex=hex32(root_hash),
            root_type="thought",
            tick_id=req.tick_id,
            child_count=3,
            status="provisional",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("thought root build failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/roots/world", response_model=RootResponse)
async def build_world_root_endpoint(req: WorldRootRequest) -> RootResponse:
    """Build Merkle world root from slot data. If slot_data omitted, fetches device registry snapshot."""
    try:
        from mycosoft_mas.core.routers.device_registry_api import get_device_registry_snapshot

        slot_data = req.slot_data or {}
        if not slot_data:
            snap = get_device_registry_snapshot()
            slot_data["device_registry"] = snap
            slot_data["device_health"] = {
                k: v.get("status", "unknown") for k, v in snap.get("devices", {}).items()
            }
        root_hex = build_world_root(slot_data)
        return RootResponse(
            root_hash_hex=root_hex,
            root_type="world",
            tick_id=None,
            child_count=len(slot_data),
            status="provisional",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("world root build failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/proof/inclusion")
async def build_inclusion_proof_endpoint(
    ordered_hashes_hex: list[str],
    target_hash_hex: str,
) -> dict:
    """Build Merkle inclusion proof for target leaf in ordered hash list."""
    try:
        ordered = [_hex_to_bytes(h) for h in ordered_hashes_hex]
        target = _hex_to_bytes(target_hash_hex)
        proof = build_inclusion_proof(ordered, target)
        return {
            "target_hash_hex": target_hash_hex,
            "proof": [{"side": side, "hash_hex": hex32(h)} for side, h in proof],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
