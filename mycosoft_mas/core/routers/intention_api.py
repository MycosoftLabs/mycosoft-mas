"""
MYCA Intention API - Feb 11, 2026

Tracks user interactions and search context to enable MYCA to provide
intelligent suggestions, relevant widgets, and contextual responses.

Endpoints:
- POST /api/myca/intention - Record a user interaction
- GET /api/myca/intention/{session_id} - Get session intentions
- GET /api/myca/intention/{session_id}/suggestions - Get suggestions based on context
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/myca/intention", tags=["myca-intention"])


# In-memory storage for now (would be Redis in production)
_intention_store: Dict[str, List[Dict[str, Any]]] = {}


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
        
        # Initialize session if needed
        if session_id not in _intention_store:
            _intention_store[session_id] = []
        
        # Store event
        event_dict = event.model_dump()
        event_dict["timestamp"] = datetime.utcnow().isoformat()
        _intention_store[session_id].append(event_dict)
        
        # Keep only last 100 events per session
        if len(_intention_store[session_id]) > 100:
            _intention_store[session_id] = _intention_store[session_id][-100:]
        
        # Analyze intentions and generate suggestions
        suggestions = _analyze_intentions(session_id)
        
        logger.info(f"[Intention] {event.event_type} from session {session_id[:8]}...")
        
        return IntentionResponse(
            success=True,
            session_id=session_id,
            event_count=len(_intention_store[session_id]),
            suggested_widgets=suggestions.get("widgets", []),
            suggested_queries=suggestions.get("queries", []),
            insights=suggestions.get("insights", {}),
        )
    except Exception as e:
        logger.error(f"[Intention] Error tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionIntentions)
async def get_session_intentions(session_id: str) -> SessionIntentions:
    """Get all recorded intentions for a session"""
    events = _intention_store.get(session_id, [])
    
    # Build summary
    summary = _build_session_summary(events)
    
    return SessionIntentions(
        session_id=session_id,
        events=[IntentionEvent(**e) for e in events],
        summary=summary,
    )


@router.get("/{session_id}/suggestions", response_model=SuggestionResponse)
async def get_suggestions(session_id: str) -> SuggestionResponse:
    """Get intelligent suggestions based on session context"""
    events = _intention_store.get(session_id, [])
    
    if not events:
        return SuggestionResponse(
            widgets=["species", "ai"],
            queries=["Amanita muscaria", "medicinal fungi", "mycelium networks"],
            actions=[],
            reasoning="No session history - showing default suggestions",
        )
    
    suggestions = _analyze_intentions(session_id)
    
    return SuggestionResponse(
        widgets=suggestions.get("widgets", ["species"]),
        queries=suggestions.get("queries", []),
        actions=suggestions.get("actions", []),
        reasoning=suggestions.get("reasoning", "Based on your recent activity"),
    )


@router.delete("/{session_id}")
async def clear_session(session_id: str) -> Dict[str, Any]:
    """Clear all intentions for a session"""
    if session_id in _intention_store:
        count = len(_intention_store[session_id])
        del _intention_store[session_id]
        return {"success": True, "cleared_events": count}
    return {"success": True, "cleared_events": 0}


def _analyze_intentions(session_id: str) -> Dict[str, Any]:
    """Analyze session intentions and generate suggestions"""
    events = _intention_store.get(session_id, [])
    
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
