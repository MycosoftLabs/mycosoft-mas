"""
Knowledge API - MYCA's Universal Expert Knowledge Endpoints
=============================================================

Provides API endpoints for querying MYCA's universal knowledge across
ALL scientific domains. This is how users, agents, and systems access
MYCA's expertise in physics, chemistry, biology, mycology, and beyond.

Author: MYCA / Morgan Rockwell
Created: March 3, 2026
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# ============================================================================
# Models
# ============================================================================


class KnowledgeQueryRequest(BaseModel):
    """Request to query MYCA's knowledge."""
    query: str
    domain: Optional[str] = None
    depth: str = "comprehensive"  # quick, moderate, comprehensive, exhaustive
    include_sources: bool = True
    include_images: bool = False
    include_widgets: bool = True
    max_sources: int = 5


class KnowledgeQueryResponse(BaseModel):
    """Response from a knowledge query."""
    query: str
    domain: str
    answer: str
    confidence: float
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    related_topics: List[str] = Field(default_factory=list)
    suggested_widgets: List[Dict[str, Any]] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0


class DeepResearchRequest(BaseModel):
    """Request for deep multi-domain research."""
    query: str
    domains: List[str] = Field(default_factory=list)
    max_sources_per_domain: int = 10
    include_genetic_data: bool = False
    include_simulations: bool = False


# ============================================================================
# Singleton agent instance
# ============================================================================

_knowledge_agent = None


def _get_knowledge_agent():
    """Get or create the knowledge domain agent."""
    global _knowledge_agent
    if _knowledge_agent is None:
        try:
            from mycosoft_mas.agents.v2.knowledge_domain_agent import KnowledgeDomainAgent
            _knowledge_agent = KnowledgeDomainAgent()
        except Exception as e:
            logger.error("Failed to create KnowledgeDomainAgent: %s", e)
    return _knowledge_agent


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/health")
async def knowledge_health():
    """Check knowledge system health."""
    agent = _get_knowledge_agent()
    return {
        "status": "healthy" if agent else "degraded",
        "agent_available": agent is not None,
        "domains_available": len(agent.capabilities) if agent else 0,
        "total_queries": agent.query_count if agent else 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/query")
async def query_knowledge(request: KnowledgeQueryRequest) -> KnowledgeQueryResponse:
    """
    Query MYCA's universal knowledge.

    This is the primary endpoint for asking MYCA anything across all
    scientific domains. MYCA will:
    1. Classify the domain automatically (or use the specified one)
    2. Query relevant data sources in parallel
    3. Synthesize a comprehensive answer
    4. Suggest relevant widgets/visualizations
    """
    agent = _get_knowledge_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="Knowledge agent not available")

    result = await agent.process_task({
        "type": "query",
        "query": request.query,
        "domain": request.domain,
        "depth": request.depth,
    })

    # Suggest widgets if requested
    suggested_widgets = []
    if request.include_widgets:
        try:
            from mycosoft_mas.core.routers.widget_api import _suggest_widgets_for_query
            suggestions = _suggest_widgets_for_query(request.query)
            suggested_widgets = [{"type": s.widget_type.value, "title": s.title,
                                  "relevance": s.relevance} for s in suggestions]
        except Exception:
            pass

    return KnowledgeQueryResponse(
        query=request.query,
        domain=result.get("domain", "general"),
        answer=result.get("answer", ""),
        confidence=result.get("confidence", 0.0),
        sources=result.get("sources", [])[:request.max_sources],
        related_topics=result.get("related_topics", []),
        suggested_widgets=suggested_widgets,
        images=result.get("images", []) if request.include_images else [],
        processing_time_ms=result.get("processing_time_ms", 0.0),
    )


@router.post("/classify")
async def classify_domain(query: str) -> Dict[str, Any]:
    """Classify a query into a knowledge domain."""
    agent = _get_knowledge_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="Knowledge agent not available")

    result = await agent.process_task({"type": "classify_domain", "query": query})
    return result


@router.post("/research")
async def deep_research(request: DeepResearchRequest) -> Dict[str, Any]:
    """
    Perform deep research across multiple domains.

    This is for complex questions that span multiple fields of science.
    MYCA will research each domain independently and synthesize results.
    """
    agent = _get_knowledge_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="Knowledge agent not available")

    result = await agent.process_task({
        "type": "deep_research",
        "query": request.query,
        "domains": request.domains or ["biology", "chemistry", "environmental_science"],
    })
    return result


@router.get("/domains")
async def list_domains() -> Dict[str, Any]:
    """List all knowledge domains MYCA masters."""
    agent = _get_knowledge_agent()
    if not agent:
        return {"status": "degraded", "domains": []}

    result = agent._get_domain_stats()
    return result


@router.get("/sources/{domain}")
async def get_sources(domain: str) -> Dict[str, Any]:
    """Get available data sources for a domain."""
    agent = _get_knowledge_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="Knowledge agent not available")

    result = await agent.process_task({"type": "get_sources", "domain": domain})
    return result


@router.get("/stats")
async def get_knowledge_stats() -> Dict[str, Any]:
    """Get knowledge system statistics."""
    agent = _get_knowledge_agent()
    if not agent:
        return {"status": "degraded"}

    stats = agent._get_domain_stats()
    return {
        "status": "success",
        "total_queries": stats.get("total_queries", 0),
        "domain_usage": stats.get("domain_counts", {}),
        "total_domains": stats.get("total_domains", 0),
        "available_domains": stats.get("available_domains", []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
