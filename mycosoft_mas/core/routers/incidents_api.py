"""
SOC incidents API — persisted in Postgres soc_ops.security_incidents.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incidents", tags=["soc-incidents"])


def _pg_ready() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


class IncidentCreate(BaseModel):
    title: str
    description: str = ""
    severity: str = Field(default="medium", pattern="^(info|low|medium|high|critical)$")
    status: str = Field(default="open")
    source: Optional[str] = None
    kind: Optional[str] = None
    source_ip: Optional[str] = None
    host: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)


class IncidentPatch(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    timeline_append: Optional[Dict[str, Any]] = None


@router.get("/health")
async def incidents_health():
    return {"ok": True, "postgres_configured": _pg_ready()}


@router.get("")
async def list_incidents_api(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.soc import repository as soc_repo

        items = await soc_repo.list_incidents(
            status=status, severity=severity, limit=limit, offset=offset
        )
        return {"incidents": items, "count": len(items)}
    except Exception as e:
        logger.exception("list_incidents failed: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("")
async def create_incident_api(body: IncidentCreate):
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.soc import repository as soc_repo

        row = await soc_repo.create_incident(
            title=body.title,
            description=body.description,
            severity=body.severity,
            status=body.status,
            source=body.source,
            kind=body.kind,
            source_ip=body.source_ip,
            host=body.host,
            details=body.details,
            tags=body.tags,
            timeline=body.timeline,
        )
        return row
    except Exception as e:
        logger.exception("create_incident failed: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/{incident_id}")
async def get_incident_api(incident_id: str):
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    from uuid import UUID

    from mycosoft_mas.memory.palace.db_pool import get_shared_pool

    try:
        pool = await get_shared_pool()
        async with pool.acquire() as conn:
            from mycosoft_mas.soc.repository import get_incident_by_id

            row = await get_incident_by_id(conn, UUID(incident_id))
        if not row:
            raise HTTPException(status_code=404, detail="incident not found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_incident failed: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.patch("/{incident_id}")
async def patch_incident_api(incident_id: str, body: IncidentPatch):
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.soc import repository as soc_repo

        row = await soc_repo.update_incident(
            incident_id,
            status=body.status,
            assigned_to=body.assigned_to,
            timeline_append=body.timeline_append,
        )
        if not row:
            raise HTTPException(status_code=404, detail="incident not found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("patch_incident failed: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/{incident_id}/chain")
async def incident_chain_api(incident_id: str, limit: int = Query(200, ge=1, le=2000)):
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.soc import repository as soc_repo

        chain = await soc_repo.list_chain_for_incident(incident_id, limit=limit)
        return {"incident_id": incident_id, "chain": chain}
    except Exception as e:
        logger.exception("incident_chain failed: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
