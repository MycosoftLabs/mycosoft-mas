"""
Investigation API Router - March 10, 2026

OpenPlanter-style investigation orchestration. Creates investigations,
delegates to MINDEX (research, observations, investigation artifacts),
and aggregates evidence-backed analysis.

Endpoints:
- POST /api/investigation/create - Create investigation and optionally resolve
- GET /api/investigation/{id} - Get investigation with aggregated evidence
- POST /api/investigation/resolve - Trigger evidence resolution (MINDEX research + observations)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MINDEX_API_URL = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
MINDEX_API_KEY = os.getenv("MINDEX_API_KEY", "")

router = APIRouter(prefix="/api/investigation", tags=["investigation"])


def _mindex_headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if MINDEX_API_KEY:
        h["X-API-Key"] = MINDEX_API_KEY
    return h


# --- Schemas ---


class InvestigationCreateRequest(BaseModel):
    """Create investigation request."""

    title: str
    description: Optional[str] = None
    query: Optional[str] = Field(None, description="Search query for research/observations")
    entity_id: Optional[str] = Field(None, description="Entity to resolve (e.g. taxon id)")
    agent_id: Optional[str] = None
    resolve: bool = Field(False, description="Immediately run evidence resolution")


class InvestigationOut(BaseModel):
    """Investigation response with aggregated evidence."""

    id: str
    title: str
    description: Optional[str]
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    research_papers: List[Dict[str, Any]] = Field(default_factory=list)
    observations: List[Dict[str, Any]] = Field(default_factory=list)


class ResolveRequest(BaseModel):
    """Trigger evidence resolution."""

    query: Optional[str] = None
    entity_id: Optional[str] = None
    limit: int = Field(10, ge=1, le=50)


# --- Endpoints ---


@router.post("/create", response_model=InvestigationOut)
async def create_investigation(body: InvestigationCreateRequest) -> InvestigationOut:
    """
    Create an investigation artifact in MINDEX. Optionally runs evidence
    resolution (research + observations) when resolve=True.
    """
    base = f"{MINDEX_API_URL}/api/mindex"
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Create artifact in MINDEX
        artifact_payload = {
            "title": body.title,
            "description": body.description or "",
            "source": "mas_investigation",
            "source_id": body.entity_id,
            "artifacts": [],
            "sources": [],
            "agent_id": body.agent_id,
        }
        try:
            r = await client.post(
                f"{base}/investigation/artifacts",
                json=artifact_payload,
                headers=_mindex_headers(),
            )
            r.raise_for_status()
            artifact = r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404 or "investigation" in str(e).lower():
                logger.warning("MINDEX investigation router not available")
                raise HTTPException(status_code=503, detail="MINDEX unavailable")
            raise HTTPException(status_code=502, detail=f"MINDEX error: {e.response.text}")
        except httpx.RequestError as e:
            logger.warning("MINDEX unreachable: %s", e)
            raise HTTPException(status_code=503, detail="MINDEX unavailable")

        inv_id = str(artifact.get("id", "stub"))
        artifacts_list = [artifact]
        research_papers: List[Dict[str, Any]] = []
        observations_list: List[Dict[str, Any]] = []
        evidence_list: List[Dict[str, Any]] = []

        if body.resolve and (body.query or body.entity_id):
            # 2. Fetch research (OpenAlex) if query provided
            if body.query:
                try:
                    res = await client.get(
                        f"{base}/research",
                        params={"search": body.query, "limit": 10},
                        headers=_mindex_headers(),
                    )
                    if res.status_code == 200:
                        data = res.json()
                        research_papers = data.get("papers", [])[:10]
                        for p in research_papers:
                            artifact_ids = artifact.get("artifacts", []) or []
                            artifact_ids.append(p.get("id", ""))
                except Exception as e:
                    logger.debug("Research fetch failed: %s", e)

            # 3. Fetch observations if entity_id (taxon) provided
            if body.entity_id:
                try:
                    obs = await client.get(
                        f"{base}/observations",
                        params={"taxon_id": body.entity_id, "limit": 20},
                        headers=_mindex_headers(),
                    )
                    if obs.status_code == 200:
                        data = obs.json()
                        observations_list = data.get("observations", [])[:20]
                except Exception as e:
                    logger.debug("Observations fetch failed: %s", e)

            # 4. Create evidence relationship in MINDEX
            evidence_ids = [a.get("id") for a in research_papers if a.get("id")]
            evidence_ids.extend([str(o.get("id", "")) for o in observations_list if o.get("id")])
            if evidence_ids and body.entity_id:
                try:
                    ev = await client.post(
                        f"{base}/investigation/evidence",
                        json={
                            "entity_id": body.entity_id,
                            "evidence_ids": evidence_ids,
                            "relationship_type": "supports",
                            "confidence": 0.8,
                        },
                        headers=_mindex_headers(),
                    )
                    if ev.status_code == 200:
                        evidence_list = [ev.json()]
                except Exception as e:
                    logger.debug("Evidence relationship create failed: %s", e)

        return InvestigationOut(
            id=inv_id,
            title=artifact.get("title", body.title),
            description=artifact.get("description") or body.description,
            artifacts=artifacts_list,
            evidence=evidence_list,
            research_papers=research_papers,
            observations=observations_list,
        )


@router.get("/{investigation_id}", response_model=InvestigationOut)
async def get_investigation(investigation_id: str) -> InvestigationOut:
    """Get investigation artifact and aggregated evidence from MINDEX."""
    base = f"{MINDEX_API_URL}/api/mindex"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(
                f"{base}/investigation/artifacts/{investigation_id}",
                headers=_mindex_headers(),
            )
            r.raise_for_status()
            artifact = r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Investigation not found")
            raise HTTPException(status_code=502, detail=f"MINDEX error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"MINDEX unreachable: {e}")

        return InvestigationOut(
            id=str(artifact.get("id", investigation_id)),
            title=artifact.get("title", ""),
            description=artifact.get("description"),
            artifacts=[artifact],
            evidence=[],
            research_papers=[],
            observations=[],
        )


@router.post("/resolve", response_model=Dict[str, Any])
async def resolve_evidence(body: ResolveRequest) -> Dict[str, Any]:
    """
    Run evidence resolution: query MINDEX research and observations,
    create artifacts and evidence relationships. Returns aggregated result.
    """
    base = f"{MINDEX_API_URL}/api/mindex"
    results: Dict[str, Any] = {
        "research": [],
        "observations": [],
        "evidence_created": False,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        if body.query:
            try:
                r = await client.get(
                    f"{base}/research",
                    params={"search": body.query, "limit": body.limit},
                    headers=_mindex_headers(),
                )
                if r.status_code == 200:
                    results["research"] = r.json().get("papers", [])
            except Exception as e:
                logger.warning("Research resolve failed: %s", e)
        if body.entity_id:
            try:
                r = await client.get(
                    f"{base}/observations",
                    params={"taxon_id": body.entity_id, "limit": body.limit},
                    headers=_mindex_headers(),
                )
                if r.status_code == 200:
                    results["observations"] = r.json().get("observations", [])
            except Exception as e:
                logger.warning("Observations resolve failed: %s", e)
    return results
