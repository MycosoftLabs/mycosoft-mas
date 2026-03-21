"""
Voice v9 REST API Router - March 2, 2026.

Session lifecycle, transcript/event inspection, command endpoints.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.voice_v9.schemas import EventSource, LatencyTrace, VoiceSession
from mycosoft_mas.voice_v9.services import (
    get_event_pipeline,
    get_interrupt_manager,
    get_latency_monitor,
    get_persona_lock_service,
    get_truth_mirror_bus,
    get_voice_gateway,
)

logger = logging.getLogger("voice_v9.api")

router = APIRouter(prefix="/api/voice/v9", tags=["voice-v9"])


# --- Request/Response models ---


class CreateSessionRequest(BaseModel):
    user_id: str = Field("morgan", description="User identifier")
    conversation_id: Optional[str] = Field(None, description="Conversation thread ID")


class AddTranscriptRequest(BaseModel):
    session_id: str
    text: str
    role: str = "user"
    is_final: bool = False
    source: str = "browser_stt"


class IngestEventRequest(BaseModel):
    source: str = Field(
        ...,
        description="Event source: mdp_device, mas_task, tool_completion, crep, nlm, mycorrhizae, system",
    )
    raw: dict = Field(default_factory=dict, description="Raw event payload")


class BargeInRequest(BaseModel):
    user_input: Optional[str] = Field(
        None, description="Optional user transcript when barge-in is triggered"
    )


class PersonaApplyRequest(BaseModel):
    text: str = Field(..., description="Text to apply persona lock to")


# --- Endpoints ---


@router.post("/sessions", response_model=VoiceSession)
async def create_session(req: CreateSessionRequest) -> VoiceSession:
    """Create a new v9 voice session."""
    gateway = get_voice_gateway()
    session = gateway.create_session(user_id=req.user_id, conversation_id=req.conversation_id)
    return session


@router.get("/sessions/{session_id}", response_model=Optional[VoiceSession])
async def get_session(session_id: str) -> Optional[VoiceSession]:
    """Get session by ID."""
    gateway = get_voice_gateway()
    return gateway.get_session(session_id)


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str) -> dict:
    """End a session and clean up."""
    gateway = get_voice_gateway()
    ok = gateway.end_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "ended", "session_id": session_id}


@router.get("/sessions/{session_id}/transcripts", response_model=List[dict])
async def get_transcripts(session_id: str, limit: int = 100) -> List[dict]:
    """Get recent transcript chunks for a session."""
    bus = get_truth_mirror_bus()
    chunks = bus.get_chunks(session_id, limit=limit)
    return [c.model_dump() for c in chunks]


@router.get("/sessions/{session_id}/events", response_model=List[dict])
async def get_events(session_id: str, limit: int = 50) -> List[dict]:
    """Get recent speechworthy events for a session."""
    bus = get_truth_mirror_bus()
    events = bus.get_events(session_id, limit=limit)
    return [e.model_dump() for e in events]


@router.get("/sessions/{session_id}/latency", response_model=List[LatencyTrace])
async def get_latency_traces(session_id: str, limit: int = 50) -> List[LatencyTrace]:
    """Get latency traces for a session."""
    monitor = get_latency_monitor()
    return monitor.get_traces(session_id, limit=limit)


@router.post("/sessions/{session_id}/events/ingest")
async def ingest_event(session_id: str, req: IngestEventRequest) -> dict:
    """
    Ingest a raw event into the v9 event rail.
    Translates -> arbitrates -> grounds -> pushes to truth mirror.
    """
    try:
        source_enum = EventSource(req.source)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {[s.value for s in EventSource]}",
        )
    pipeline = get_event_pipeline()
    event = pipeline.ingest(session_id, source_enum, req.raw)
    if event is None:
        return {"status": "skipped", "reason": "translation returned None"}
    return {"status": "ingested", "event_id": event.event_id, "summary": event.summary}


@router.get("/sessions/{session_id}/interrupt")
async def get_interrupt_state(session_id: str) -> dict:
    """Get current interrupt/duplex state for a session."""
    gateway = get_voice_gateway()
    if not gateway.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    mgr = get_interrupt_manager(session_id)
    state = mgr.get_interrupt_state()
    return {
        "is_speaking": state.is_speaking,
        "has_interrupted_draft": state.has_interrupted_draft,
        "interrupted_draft_text": state.interrupted_draft_text,
        "barge_in_count": state.barge_in_count,
        "last_barge_in_at": state.last_barge_in_at,
        "state": state.state,
    }


@router.post("/sessions/{session_id}/interrupt/barge-in")
async def request_barge_in(session_id: str, req: BargeInRequest = BargeInRequest()) -> dict:
    """Manually trigger barge-in (e.g., when browser STT detects user speech)."""
    gateway = get_voice_gateway()
    if not gateway.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    mgr = get_interrupt_manager(session_id)
    mgr.request_barge_in(req.user_input)
    return {"status": "barge_in_triggered", "session_id": session_id}


@router.get("/sessions/{session_id}/persona")
async def get_persona_state(session_id: str) -> dict:
    """Get current persona lock state for a session."""
    gateway = get_voice_gateway()
    if not gateway.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    svc = get_persona_lock_service()
    state = svc.get_state(session_id)
    return state.model_dump()


@router.post("/sessions/{session_id}/persona/apply")
async def apply_persona(session_id: str, req: PersonaApplyRequest) -> dict:
    """Apply persona lock to text (for testing or pre-TTS validation)."""
    gateway = get_voice_gateway()
    if not gateway.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    svc = get_persona_lock_service()
    result = svc.apply(session_id, req.text)
    return {
        "text": result.text,
        "was_rewritten": result.was_rewritten,
        "rewrite_reason": result.rewrite_reason,
        "drift_detected": result.drift_detected,
        "confidence": result.confidence,
    }


@router.get("/health")
async def health() -> dict:
    """v9 voice health check."""
    return {"status": "healthy", "version": "v9"}
