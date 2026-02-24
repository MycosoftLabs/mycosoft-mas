"""
MYCA Intention API - Feb 11, 2026

Tracks user interactions and search context to enable MYCA to provide
intelligent suggestions, relevant widgets, and contextual responses.

Persistence: Redis (when available) for cross-session restoration.
Fallback: in-memory when Redis unavailable.

Endpoints:
- POST /api/myca/intention - Record a user interaction
- GET /api/myca/intention/{session_id} - Get session intentions
- GET /api/myca/intention/{session_id}/suggestions - Get suggestions based on context
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/myca/intention", tags=["myca-intention"])

# In-memory fallback when Redis unavailable
_intention_store: Dict[str, List[Dict[str, Any]]] = {}

# Redis key prefix for intention storage
INTENTION_KEY_PREFIX = "myca:intention:"
INTENTION_MAX_EVENTS = 100
INTENTION_TTL_SECONDS = 86400 * 7  # 7 days


def _get_redis():
    """Get Redis client if available."""
    try:
        import redis.asyncio as redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        return redis.from_url(url, decode_responses=True)
    except Exception as e:
        logger.debug("Redis not available for intention store: %s", e)
        return None


async def _intention_append(session_id: str, event_dict: Dict[str, Any]) -> None:
    """Append event to intention store (Redis or in-memory)."""
    r = _get_redis()
    if r:
        try:
            key = f"{INTENTION_KEY_PREFIX}{session_id}"
            data = json.dumps(event_dict)
            await r.rpush(key, data)
            await r.ltrim(key, -INTENTION_MAX_EVENTS, -1)
            await r.expire(key, INTENTION_TTL_SECONDS)
            return
        except Exception as e:
            logger.warning("Redis append failed: %s", e)
    if session_id not in _intention_store:
        _intention_store[session_id] = []
    _intention_store[session_id].append(event_dict)
    if len(_intention_store[session_id]) > INTENTION_MAX_EVENTS:
        _intention_store[session_id] = _intention_store[session_id][-INTENTION_MAX_EVENTS:]


async def _intention_get_all(session_id: str) -> List[Dict[str, Any]]:
    """Get all events for session (Redis or in-memory)."""
    r = _get_redis()
    if r:
        try:
            key = f"{INTENTION_KEY_PREFIX}{session_id}"
            raw = await r.lrange(key, 0, -1)
            return [json.loads(x) for x in raw] if raw else []
        except Exception as e:
            logger.warning("Redis get failed: %s", e)
    return _intention_store.get(session_id, [])


async def _intention_clear(session_id: str) -> int:
    """Clear session intentions. Returns count cleared."""
    r = _get_redis()
    if r:
        try:
            key = f"{INTENTION_KEY_PREFIX}{session_id}"
            count = await r.llen(key)
            await r.delete(key)
            return count
        except Exception as e:
            logger.warning("Redis clear failed: %s", e)
    if session_id in _intention_store:
        count = len(_intention_store[session_id])
        del _intention_store[session_id]
        return count
    return 0


class IntentionEvent(BaseModel):
    """A single user interaction event"""
    session_id: str = Field(..., description="Unique session identifier")
    event_type: Literal["search", "click", "focus", "note", "voice", "navigate", "hover"] = Field(..., description="Type of interaction")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    context: Dict[str, Any] = Field(default_factory=dict, description="Current context (query, widgets visible, etc.)")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class IntentionResponse(BaseModel):
    """Response after recording an intention"""
    success: bool
    session_id: str
    event_count: int
    suggested_widgets: List[str] = Field(default_factory=list)
    suggested_queries: List[str] = Field(default_factory=list)
    insights: Dict[str, Any] = Field(default_factory=dict)


class SessionIntentions(BaseModel):
    """All intentions for a session"""
    session_id: str
    events: List[IntentionEvent]
    summary: Dict[str, Any]


class SuggestionResponse(BaseModel):
    """Suggestions based on user intent"""
    widgets: List[str]
    queries: List[str]
    actions: List[Dict[str, Any]]
    reasoning: str


@router.post("", response_model=IntentionResponse)
async def track_intention(event: IntentionEvent) -> IntentionResponse:
    """
    Record a user interaction event for MYCA intention tracking.
    
    Use this to track:
    - Search queries and refinements
    - Widget clicks and focuses
    - Notepad additions
    - Voice commands
    - Navigation events
    """
    try:
        session_id = event.session_id
        event_dict = event.model_dump()
        event_dict["timestamp"] = datetime.utcnow().isoformat()

        await _intention_append(session_id, event_dict)
        events = await _intention_get_all(session_id)
        suggestions = _analyze_intentions_sync(events)

        logger.info("[Intention] %s from session %s...", event.event_type, session_id[:8] if session_id else "?")

        return IntentionResponse(
            success=True,
            session_id=session_id,
            event_count=len(events),
            suggested_widgets=suggestions.get("widgets", []),
            suggested_queries=suggestions.get("queries", []),
            insights=suggestions.get("insights", {}),
        )
    except Exception as e:
        logger.error("[Intention] Error tracking: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionIntentions)
async def get_session_intentions(session_id: str) -> SessionIntentions:
    """Get all recorded intentions for a session"""
    events = await _intention_get_all(session_id)
    summary = _build_session_summary(events)

    return SessionIntentions(
        session_id=session_id,
        events=[IntentionEvent(**e) for e in events],
        summary=summary,
    )


@router.get("/{session_id}/suggestions", response_model=SuggestionResponse)
async def get_suggestions(session_id: str) -> SuggestionResponse:
    """Get intelligent suggestions based on session context"""
    events = await _intention_get_all(session_id)

    if not events:
        return SuggestionResponse(
            widgets=["species", "ai"],
            queries=["Amanita muscaria", "medicinal fungi", "mycelium networks"],
            actions=[],
            reasoning="No session history - showing default suggestions",
        )

    suggestions = _analyze_intentions_sync(events)

    return SuggestionResponse(
        widgets=suggestions.get("widgets", ["species"]),
        queries=suggestions.get("queries", []),
        actions=suggestions.get("actions", []),
        reasoning=suggestions.get("reasoning", "Based on your recent activity"),
    )


@router.delete("/{session_id}")
async def clear_session(session_id: str) -> Dict[str, Any]:
    """Clear all intentions for a session"""
    count = await _intention_clear(session_id)
    return {"success": True, "cleared_events": count}


def _analyze_intentions_sync(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze session intentions and generate suggestions (sync, accepts events list)."""
    if not events:
        return {}
    
    # Extract patterns
    search_queries = [e["data"].get("query", "") for e in events if e["event_type"] == "search"]
    clicked_types = [e["data"].get("widget_type", "") for e in events if e["event_type"] == "click"]
    focused_widgets = [e["data"].get("widget_type", "") for e in events if e["event_type"] == "focus"]
    
    # Determine user interests
    widgets = []
    queries = []
    insights = {}
    
    # If user has searched, suggest related widgets
    if search_queries:
        latest_query = search_queries[-1].lower() if search_queries else ""
        
        if any(term in latest_query for term in ["compound", "chemistry", "psilocybin", "muscimol"]):
            widgets.append("chemistry")
            queries.append("psychoactive compounds")
        
        if any(term in latest_query for term in ["gene", "dna", "sequence", "genome"]):
            widgets.append("genetics")
            queries.append("fungal genome sequences")
        
        if any(term in latest_query for term in ["research", "paper", "study", "journal"]):
            widgets.append("research")
            queries.append("recent mycology papers")
        
        if any(term in latest_query for term in ["species", "mushroom", "fungus", "fungi"]):
            widgets.append("species")
            queries.append("rare mushroom species")
    
    # If user clicks on certain widgets, suggest related ones
    if "chemistry" in clicked_types or "chemistry" in focused_widgets:
        if "genetics" not in widgets:
            widgets.append("genetics")
        insights["chemistry_interest"] = True
    
    if "species" in clicked_types or "species" in focused_widgets:
        if "research" not in widgets:
            widgets.append("research")
        insights["species_interest"] = True
    
    # Always suggest AI widget if not already
    if "ai" not in widgets:
        widgets.append("ai")
    
    return {
        "widgets": widgets[:4],  # Max 4 suggestions
        "queries": queries[:3],  # Max 3 query suggestions
        "insights": insights,
        "reasoning": f"Based on {len(events)} recent interactions",
    }


def _build_session_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a summary of session activity"""
    if not events:
        return {"total_events": 0}
    
    event_types = {}
    for e in events:
        t = e.get("event_type", "unknown")
        event_types[t] = event_types.get(t, 0) + 1
    
    searches = [e["data"].get("query", "") for e in events if e["event_type"] == "search"]
    
    return {
        "total_events": len(events),
        "event_types": event_types,
        "unique_searches": len(set(searches)),
        "recent_searches": searches[-5:] if searches else [],
        "first_event": events[0].get("timestamp") if events else None,
        "last_event": events[-1].get("timestamp") if events else None,
    }
