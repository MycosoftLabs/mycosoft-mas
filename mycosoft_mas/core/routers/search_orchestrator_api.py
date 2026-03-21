"""
Search Orchestrator API — HTTP endpoint for website and clients to call MAS unified search.

POST /api/search/execute — run canonical search pipeline (MINDEX -> memory -> specialists).
Returns orchestrator payload: query, focus, world_context, working_context, memories, results.keyword, results.semantic.

Created: March 14, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.consciousness import get_consciousness

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchExecuteRequest(BaseModel):
    """Request for unified search execution."""

    query: str = Field(..., min_length=1)
    search_context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    limit: int = Field(10, ge=1, le=100)


@router.post("/execute")
async def search_execute(request: SearchExecuteRequest) -> Dict[str, Any]:
    """
    Run the canonical MAS search orchestrator. Used by the website as the single
    search entry point instead of direct MINDEX/provider calls.
    """
    try:
        from mycosoft_mas.consciousness.search_orchestrator import run_unified_search

        consciousness = get_consciousness()
        result = await run_unified_search(
            query=request.query,
            search_context=request.search_context or {},
            user_id=request.user_id,
            session_id=request.session_id,
            consciousness=consciousness,
            limit=request.limit,
        )
        return result
    except Exception as e:
        logger.warning("Search execute failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
