"""
Search Memory API - February 5, 2026

API endpoints for managing search sessions with memory integration:
- POST /start: Start a new search session
- POST /query: Record a search query
- POST /focus: Record focusing on a species/topic
- POST /ai: Record AI conversation turn
- POST /click: Record clicking a search result
- GET /context/{session_id}: Get current session context
- POST /end/{session_id}: End a search session
- GET /history: Get user's search history
- POST /enrich: Enrich MINDEX with search data
- GET /stats: Get search memory statistics
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("SearchMemoryAPI")

router = APIRouter(prefix="/api/search/memory", tags=["search-memory"])


# ============================================================================
# Request/Response Models
# ============================================================================

class StartSessionRequest(BaseModel):
    """Request to start a new search session."""
    user_id: str = Field(..., description="User identifier")
    voice_session_id: Optional[str] = Field(None, description="Associated voice session ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional session metadata")


class StartSessionResponse(BaseModel):
    """Response after starting a session."""
    session_id: str
    user_id: str
    started_at: str
    existing_session: bool = False


class AddQueryRequest(BaseModel):
    """Request to record a search query."""
    session_id: str = Field(..., description="Active session ID")
    query: str = Field(..., description="Search query text")
    result_count: int = Field(0, description="Number of results returned")
    result_types: Optional[Dict[str, int]] = Field(None, description="Result types and counts")
    source: str = Field("text", description="Query source: text, voice, suggestion")


class QueryResponse(BaseModel):
    """Response after recording a query."""
    query_id: str
    session_id: str
    query: str
    result_count: int


class FocusRequest(BaseModel):
    """Request to record focusing on a species/topic."""
    session_id: str = Field(..., description="Active session ID")
    species_id: str = Field(..., description="Species/taxon identifier")
    topic: Optional[str] = Field(None, description="Topic: species, chemistry, genetics, research, taxonomy, gallery, ai_chat")


class ClickRequest(BaseModel):
    """Request to record clicking a search result."""
    session_id: str = Field(..., description="Active session ID")
    result_id: str = Field(..., description="Clicked result identifier")


class AITurnRequest(BaseModel):
    """Request to record an AI conversation turn."""
    session_id: str = Field(..., description="Active session ID")
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    topic: Optional[str] = Field(None, description="Topic context for this message")


class AITurnResponse(BaseModel):
    """Response after recording AI turn."""
    message_id: str
    session_id: str
    role: str


class SessionContextResponse(BaseModel):
    """Current session context."""
    session_id: str
    user_id: str
    duration_seconds: float
    queries: List[str]
    current_species: Optional[str]
    focused_species: List[str]
    explored_topics: List[str]
    ai_message_count: int
    recent_ai: List[Dict[str, str]]
    voice_linked: bool


class EndSessionResponse(BaseModel):
    """Response after ending a session."""
    session_id: str
    duration_seconds: float
    query_count: int
    unique_species_explored: int
    topics_explored: List[str]
    ai_message_count: int
    top_interests: List[Dict[str, Any]]


class SearchHistoryResponse(BaseModel):
    """User's search history."""
    user_id: str
    sessions: List[Dict[str, Any]]
    total_count: int


class EnrichRequest(BaseModel):
    """Request to enrich MINDEX with search data."""
    query: str = Field(..., description="Search query")
    user_id: str = Field(..., description="User identifier")
    taxon_ids: Optional[List[int]] = Field(None, description="Related taxon IDs")


class StatsResponse(BaseModel):
    """Search memory statistics."""
    active_sessions: int
    active_users: int
    database_connected: bool
    initialized: bool
    sessions: Dict[str, Any]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/start", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest):
    """Start a new search session for a user."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        voice_uuid = None
        if request.voice_session_id:
            try:
                voice_uuid = UUID(request.voice_session_id)
            except ValueError:
                pass
        
        session = await search_memory.start_session(
            user_id=request.user_id,
            voice_session_id=voice_uuid,
            metadata=request.metadata
        )
        
        # Check if this was an existing session
        existing = len(session.queries) > 0 or len(session.focused_species) > 0
        
        logger.info(f"Started search session {session.id} for user {request.user_id}")
        
        return StartSessionResponse(
            session_id=str(session.id),
            user_id=session.user_id,
            started_at=session.started_at.isoformat(),
            existing_session=existing
        )
        
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
async def add_query(request: AddQueryRequest):
    """Record a search query in the session."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        session_uuid = UUID(request.session_id)
        
        query = await search_memory.add_query(
            session_id=session_uuid,
            query=request.query,
            result_count=request.result_count,
            result_types=request.result_types,
            source=request.source
        )
        
        if not query:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return QueryResponse(
            query_id=str(query.id),
            session_id=request.session_id,
            query=query.query,
            result_count=query.result_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/focus")
async def record_focus(request: FocusRequest):
    """Record focusing on a species/topic."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        session_uuid = UUID(request.session_id)
        
        success = await search_memory.record_focus(
            session_id=session_uuid,
            species_id=request.species_id,
            topic=request.topic
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "success": True,
            "session_id": request.session_id,
            "species_id": request.species_id,
            "topic": request.topic
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record focus: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/click")
async def record_click(request: ClickRequest):
    """Record clicking a search result."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        session_uuid = UUID(request.session_id)
        
        # Get session directly from manager
        session = search_memory._active_sessions.get(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.record_click(request.result_id)
        
        return {
            "success": True,
            "session_id": request.session_id,
            "result_id": request.result_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record click: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai", response_model=AITurnResponse)
async def add_ai_turn(request: AITurnRequest):
    """Record an AI conversation turn."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        session_uuid = UUID(request.session_id)
        
        message = await search_memory.add_ai_turn(
            session_id=session_uuid,
            role=request.role,
            content=request.content,
            topic=request.topic
        )
        
        if not message:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return AITurnResponse(
            message_id=str(message.id),
            session_id=request.session_id,
            role=message.role
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add AI turn: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/{session_id}", response_model=SessionContextResponse)
async def get_session_context(session_id: str):
    """Get the current context for a search session."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        session_uuid = UUID(session_id)
        
        context = await search_memory.get_session_context(session_uuid)
        
        if "error" in context:
            raise HTTPException(status_code=404, detail=context["error"])
        
        return SessionContextResponse(**context)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end/{session_id}", response_model=EndSessionResponse)
async def end_session(session_id: str):
    """End a search session and get summary."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        session_uuid = UUID(session_id)
        
        summary = await search_memory.end_session(session_uuid)
        
        if not summary:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return EndSessionResponse(
            session_id=str(summary.session_id),
            duration_seconds=summary.duration_seconds,
            query_count=summary.query_count,
            unique_species_explored=summary.unique_species_explored,
            topics_explored=summary.topics_explored,
            ai_message_count=summary.ai_message_count,
            top_interests=[
                {"species_id": sid, "score": score}
                for sid, score in summary.top_interests
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=SearchHistoryResponse)
async def get_search_history(
    user_id: str = Query(..., description="User identifier"),
    limit: int = Query(10, ge=1, le=50, description="Number of sessions to return")
):
    """Get a user's search history."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        sessions = await search_memory.get_user_search_history(user_id, limit)
        
        return SearchHistoryResponse(
            user_id=user_id,
            sessions=[s.to_dict() for s in sessions],
            total_count=len(sessions)
        )
        
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enrich")
async def enrich_mindex(request: EnrichRequest):
    """Enrich MINDEX with search data."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        success = await search_memory.enrich_to_mindex(
            query=request.query,
            user_id=request.user_id,
            taxon_ids=request.taxon_ids
        )
        
        return {
            "success": success,
            "query": request.query,
            "user_id": request.user_id,
            "taxon_count": len(request.taxon_ids) if request.taxon_ids else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to enrich MINDEX: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get search memory statistics."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        stats = await search_memory.get_stats()
        
        return StatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/{user_id}")
async def get_active_session(user_id: str):
    """Get the active search session for a user if one exists."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory
        
        search_memory = await get_search_memory()
        
        # Check if user has active session
        session_id = search_memory._user_sessions.get(user_id)
        if not session_id:
            return {"active": False, "session_id": None}
        
        session = search_memory._active_sessions.get(session_id)
        if not session:
            return {"active": False, "session_id": None}
        
        return {
            "active": True,
            "session_id": str(session_id),
            "user_id": user_id,
            "query_count": session.query_count,
            "focused_species": session.focused_species,
            "duration_seconds": session.duration.total_seconds()
        }
        
    except Exception as e:
        logger.error(f"Failed to get active session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/widget-interaction")
async def record_widget_interaction(
    session_id: str = Query(..., description="Session ID"),
    widget: str = Query(..., description="Widget type"),
    species_id: Optional[str] = Query(None, description="Species being viewed")
):
    """Record a widget interaction event."""
    try:
        from mycosoft_mas.memory.search_memory import get_search_memory, SearchTopic
        
        search_memory = await get_search_memory()
        
        session_uuid = UUID(session_id)
        session = search_memory._active_sessions.get(session_uuid)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        try:
            topic = SearchTopic(widget)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid widget type: {widget}")
        
        interaction = session.explore_topic(topic, species_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "widget": widget,
            "species_id": species_id,
            "started_at": interaction.started_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record widget interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))