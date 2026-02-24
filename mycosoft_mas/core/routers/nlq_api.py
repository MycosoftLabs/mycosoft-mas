"""
NLQ API - Unified natural language query processing for search.

Provides a single API surface to interpret search intent and return
structured results using MYCA consciousness + SearchAgent.

Endpoints:
- POST /api/nlq/parse - Intent detection via LLM (search, metabase, mindex)
- POST /api/nlq/execute - Route to SearchAgent, Metabase, MINDEX
- POST /api/nlq/query - Full query processing (parse + execute)
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.consciousness import get_consciousness
from mycosoft_mas.agents.clusters.search_discovery.search_agent import (
    SearchAgent,
    SearchQuery,
    SearchType,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/nlq", tags=["nlq"])
MAS_API_URL = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
METABASE_URL = os.getenv("METABASE_URL", "http://192.168.0.188:3000")


class NLQRequest(BaseModel):
    """Request for unified NLQ search processing."""

    query: str = Field(..., description="User query text")
    context: Optional[Dict[str, Any]] = Field(None, description="Search context filters")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    mode: str = Field("auto", description="auto | keyword | semantic | fuzzy | regex | structured")
    limit: int = Field(10, description="Maximum results per search type")


class NLQResponse(BaseModel):
    """Response for NLQ processing."""

    status: str
    result: Dict[str, Any]
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@router.get("/health")
async def health():
    """Health check for NLQ API."""

    return {"status": "healthy", "service": "nlq"}


class NLQParseRequest(BaseModel):
    """Request for intent parsing."""

    query: str = Field(..., description="User query text")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")


class NLQParseResponse(BaseModel):
    """Parsed intent from query."""

    intent: Literal["search", "query_metabase", "mindex", "unknown"]
    confidence: float
    search_type: Optional[str] = None  # keyword, semantic, fuzzy, etc.
    metabase_hint: Optional[str] = None
    explanation: str = ""


async def _parse_intent_via_llm(query: str) -> Dict[str, Any]:
    """Use MAS Brain to detect query intent."""
    prompt = f"""Classify this user query into ONE intent. Return ONLY valid JSON with keys: intent, confidence (0-1), search_type (if intent=search), explanation.
Valid intents: search, query_metabase, mindex, unknown.
- search: user wants to find species, compounds, genetics, research (use search_type: keyword|semantic|fuzzy)
- query_metabase: user wants database/analytics insights, dashboards, counts, aggregations
- mindex: user explicitly asks for MINDEX or fungal database content
- unknown: unclear or general question

Query: "{query}"
JSON:"""
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            res = await client.post(
                f"{MAS_API_URL}/voice/brain/chat",
                json={
                    "message": prompt,
                    "provider": "auto",
                    "include_memory_context": False,
                    "user_id": "nlq-parse",
                    "session_id": f"nlq-parse-{datetime.now(timezone.utc).timestamp()}",
                },
            )
        if res.status_code != 200:
            return {"intent": "search", "confidence": 0.5, "search_type": "semantic", "explanation": "Fallback"}
        data = res.json()
        raw = (data.get("response") or data.get("message") or data.get("content") or "").strip()
        if not raw:
            return {"intent": "search", "confidence": 0.5, "search_type": "semantic", "explanation": "No response"}
        # Extract JSON from response (LLM may wrap in markdown)
        if "```" in raw:
            parts = raw.split("```")
            for p in parts:
                p = p.strip().strip("json").strip()
                if p.startswith("{"):
                    return json.loads(p)
        return json.loads(raw)
    except Exception as e:
        logger.warning("NLQ parse LLM failed: %s", e)
        return {"intent": "search", "confidence": 0.5, "search_type": "semantic", "explanation": str(e)}


@router.post("/parse", response_model=NLQParseResponse)
async def parse_nlq(request: NLQParseRequest):
    """Parse natural language query to detect intent (search, metabase, mindex)."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query is required")

    parsed = await _parse_intent_via_llm(request.query)
    intent = parsed.get("intent", "search")
    if intent not in ("search", "query_metabase", "mindex", "unknown"):
        intent = "search"
    return NLQParseResponse(
        intent=intent,
        confidence=float(parsed.get("confidence", 0.7)),
        search_type=parsed.get("search_type"),
        metabase_hint=parsed.get("metabase_hint"),
        explanation=parsed.get("explanation", ""),
    )


class NLQExecuteRequest(BaseModel):
    """Request for executing a parsed NLQ."""

    query: str = Field(..., description="User query text")
    intent: Literal["search", "query_metabase", "mindex"] = Field("search")
    search_type: Optional[str] = Field(None, description="keyword|semantic|fuzzy|structured")
    context: Optional[Dict[str, Any]] = Field(None)
    user_id: Optional[str] = Field(None)
    session_id: Optional[str] = Field(None)
    limit: int = Field(10, ge=1, le=100)


@router.post("/execute", response_model=NLQResponse)
async def execute_nlq(request: NLQExecuteRequest):
    """Execute a natural language query by routing to SearchAgent, Metabase, or MINDEX."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query is required")

    if request.intent == "query_metabase":
        website_url = os.getenv("WEBSITE_API_URL", "http://localhost:3010")
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                res = await client.post(
                    f"{website_url}/api/metabase",
                    json={"action": "natural", "naturalQuery": request.query, "databaseId": 1},
                )
            if res.status_code == 200:
                data = res.json()
                return NLQResponse(
                    status="success",
                    result={
                        "source": "metabase",
                        "query": request.query,
                        "data": data,
                    },
                    actions=[{"type": "metabase_result", "data": data}],
                )
        except Exception as e:
            logger.warning("Metabase NLQ execute failed: %s", e)
        # Fallback to search - create new request with search intent
        req = NLQExecuteRequest(
            query=request.query,
            intent="search",
            search_type="semantic",
            context=request.context,
            user_id=request.user_id,
            session_id=request.session_id,
            limit=request.limit,
        )
        request = req

    consciousness = get_consciousness()
    if hasattr(consciousness, "process_search_query") and request.intent in ("search", "mindex"):
        try:
            result = await consciousness.process_search_query(
                query=request.query,
                search_context=request.context or {},
                user_id=request.user_id,
                session_id=request.session_id,
            )
            return NLQResponse(status="success", result=result)
        except Exception as e:
            logger.warning("Consciousness search failed: %s", e)

    search_agent = SearchAgent(agent_id="nlq-execute-agent")
    stype = {
        "keyword": SearchType.KEYWORD,
        "semantic": SearchType.SEMANTIC,
        "fuzzy": SearchType.FUZZY,
        "structured": SearchType.STRUCTURED,
        "regex": SearchType.REGEX,
    }.get(request.search_type or "semantic", SearchType.SEMANTIC)

    sq = SearchQuery(
        query_type=stype,
        query=request.query,
        filters=request.context or {},
        limit=request.limit,
    )
    if stype == SearchType.KEYWORD:
        results = await search_agent._keyword_search(sq)
    elif stype == SearchType.FUZZY:
        results = await search_agent._fuzzy_search(sq)
    elif stype == SearchType.REGEX:
        results = await search_agent._regex_search(sq)
    elif stype == SearchType.STRUCTURED:
        results = await search_agent._structured_search(sq)
    else:
        results = await search_agent._semantic_search(sq)

    return NLQResponse(
        status="success",
        result={
            "query": request.query,
            "mode": request.search_type or "semantic",
            "source": "search_agent",
            "results": results,
        },
    )


@router.post("/query", response_model=NLQResponse)
async def query_nlq(request: NLQRequest):
    """Process a natural language query into structured search results."""

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query is required")

    search_context = request.context or {}
    mode = request.mode.strip().lower()

    try:
        if mode == "auto":
            consciousness = get_consciousness()
            if hasattr(consciousness, "process_search_query"):
                result = await consciousness.process_search_query(
                    query=request.query,
                    search_context=search_context,
                    user_id=request.user_id,
                    session_id=request.session_id,
                )
                return NLQResponse(status="success", result=result)

        search_agent = SearchAgent(agent_id="nlq-search-agent")
        query_type = {
            "keyword": SearchType.KEYWORD,
            "semantic": SearchType.SEMANTIC,
            "fuzzy": SearchType.FUZZY,
            "regex": SearchType.REGEX,
            "structured": SearchType.STRUCTURED,
        }.get(mode, SearchType.SEMANTIC)

        search_query = SearchQuery(
            query_type=query_type,
            query=request.query,
            filters=search_context,
            limit=request.limit,
        )

        if query_type == SearchType.KEYWORD:
            results = await search_agent._keyword_search(search_query)
        elif query_type == SearchType.FUZZY:
            results = await search_agent._fuzzy_search(search_query)
        elif query_type == SearchType.REGEX:
            results = await search_agent._regex_search(search_query)
        elif query_type == SearchType.STRUCTURED:
            results = await search_agent._structured_search(search_query)
        else:
            results = await search_agent._semantic_search(search_query)

        return NLQResponse(
            status="success",
            result={
                "query": request.query,
                "mode": mode,
                "results": results,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
