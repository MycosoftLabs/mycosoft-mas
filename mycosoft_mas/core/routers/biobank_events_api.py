"""
Biobank event receiver — BLOCKS/MYCODAO tissue catalog → MYCA.

POST /api/biobank/events accepts JSON from `lib/server/biobank-notify.ts` on
blocks.mycodao.com when tissue is provisioned, updated, transferred, or contaminated.
"""

from __future__ import annotations

import logging
import os
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/biobank", tags=["biobank"])

_MAX_EVENTS = 500
_recent: Deque[Dict[str, Any]] = deque(maxlen=_MAX_EVENTS)

BiobankEventType = Literal[
    "species_added",
    "accession_created",
    "accession_updated",
    "tissue_transferred",
    "tissue_contaminated",
    "tissue_observed",
]


class BiobankEventIn(BaseModel):
    source: str = "mycodao-biobank"
    at: Optional[str] = None
    event: BiobankEventType
    accessionCode: Optional[str] = None
    taxonCode: Optional[str] = None
    scientificName: Optional[str] = None
    commonName: Optional[str] = None
    status: Optional[str] = None
    health: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None
    performedBy: Optional[str] = None


def _verify_token(authorization: Optional[str]) -> None:
    expected = os.environ.get("BIOBANK_WEBHOOK_TOKEN", "").strip()
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid bearer token")


async def _notify_myca(evt: BiobankEventIn) -> None:
    """Best-effort admin ping for lifecycle events MYCA should know about."""
    notify_types = {
        "species_added",
        "accession_created",
        "tissue_contaminated",
    }
    if evt.event not in notify_types:
        return
    try:
        from mycosoft_mas.services.admin_notifications import notify_morgan

        label = evt.commonName or evt.scientificName or evt.accessionCode or evt.taxonCode or "Biobank"
        priority = "high" if evt.event == "tissue_contaminated" else "normal"
        ntype = "warning" if evt.event == "tissue_contaminated" else "discovery"
        message = f"{evt.event.replace('_', ' ')}: {label}"
        if evt.accessionCode:
            message += f" ({evt.accessionCode})"
        await notify_morgan(
            title="Biobank update",
            message=message,
            type=ntype,
            agent="Biobank",
            priority=priority,
            data=evt.model_dump(exclude_none=True),
        )
    except Exception as exc:
        logger.debug("biobank notify_morgan skipped: %s", exc)


@router.post("/events")
async def receive_biobank_event(
    body: BiobankEventIn,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Ingest a biobank lifecycle event from BLOCKS."""
    _verify_token(authorization)
    record = {
        "id": str(uuid4()),
        "receivedAt": datetime.now(timezone.utc).isoformat(),
        **body.model_dump(exclude_none=True),
    }
    _recent.append(record)
    logger.info(
        "biobank event %s accession=%s taxon=%s",
        body.event,
        body.accessionCode,
        body.taxonCode,
    )
    await _notify_myca(body)
    return {"ok": True, "id": record["id"], "event": body.event}


@router.get("/events/recent")
async def list_recent_biobank_events(limit: int = 50) -> Dict[str, Any]:
    """Recent biobank events (in-memory ring buffer; for ops/debug)."""
    cap = max(1, min(limit, _MAX_EVENTS))
    items: List[Dict[str, Any]] = list(_recent)[-cap:]
    return {"count": len(items), "items": list(reversed(items))}


@router.get("/health")
async def biobank_receiver_health() -> Dict[str, str]:
    return {"status": "healthy", "receiver": "mas"}
