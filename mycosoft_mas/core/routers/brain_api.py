"""
MYCA Brain API Router - February 5, 2026

REST and streaming API endpoints for the MYCA Memory-Integrated Brain.
This provides the PersonaPlex bridge with memory-aware LLM responses.

Endpoints:
- POST /voice/brain/chat - Non-streaming brain response
- POST /voice/brain/stream - Streaming brain response (SSE)
- GET /voice/brain/status - Brain status and providers
- GET /voice/brain/context - Get memory context for a user/conversation
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("BrainAPI")

router = APIRouter(prefix="/voice/brain", tags=["brain"])


# ============================================================================
# Request/Response Models
# ============================================================================

class BrainChatRequest(BaseModel):
    """Request to the MYCA memory-integrated brain."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Voice/chat session ID")
    conversation_id: Optional[str] = Field(None, description="Conversation thread ID")
    user_id: str = Field("morgan", description="User identifier")
    history: Optional[List[Dict[str, str]]] = Field(None, description="Conversation history")
    provider: str = Field("auto", description="LLM provider: auto, gemini, claude, openai")
    include_memory_context: bool = Field(True, description="Include recalled memories in response")


class BrainChatResponse(BaseModel):
    """Response from the MYCA memory-integrated brain."""
    response: str = Field(..., description="Brain response text")
    provider: str = Field(..., description="LLM provider used")
    session_id: str = Field(..., description="Session ID")
    conversation_id: str = Field(..., description="Conversation ID")
    memory_context: Optional[Dict[str, Any]] = Field(None, description="Memory context used")
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MemoryContextResponse(BaseModel):
    """Memory context for a conversation."""
    user_id: str
    conversation_id: Optional[str]
    memories: List[Dict[str, Any]]
    episodes: List[Dict[str, Any]]
    user_profile: Optional[Dict[str, Any]]
    voice_context: Optional[Dict[str, Any]]


# ============================================================================
# Brain API Endpoints
# ============================================================================

_brain = None


async def get_brain():
    """Get or create the memory brain singleton."""
    global _brain
    if _brain is None:
        from mycosoft_mas.llm.memory_brain import get_memory_brain
        _brain = await get_memory_brain()
    return _brain


@router.post("/chat", response_model=BrainChatResponse)
async def brain_chat(request: BrainChatRequest):
    """
    Get a memory-aware response from MYCA's brain.
    
    This endpoint:
    1. Loads relevant memories for context
    2. Injects user profile and preferences
    3. Routes to the best available LLM (Gemini/Claude/OpenAI)
    4. Stores the conversation turn in memory
    5. Returns structured response with actions taken
    """
    try:
        brain = await get_brain()
        
        # Ensure IDs
        session_id = request.session_id or str(uuid4())
        conversation_id = request.conversation_id or str(uuid4())
        
        # Get response
        response = await brain.get_response(
            message=request.message,
            session_id=session_id,
            conversation_id=conversation_id,
            user_id=request.user_id,
            history=request.history,
            provider=request.provider
        )
        
        # Get memory context if requested
        memory_context = None
        if request.include_memory_context:
            try:
                memory_context = await brain.recall_context(
                    query=request.message,
                    user_id=request.user_id,
                    limit=5
                )
            except Exception as e:
                logger.warning(f"Failed to get memory context: {e}")
        
        # Determine provider used (from brain stats)
        stats = await brain.get_stats()
        provider_used = request.provider if request.provider != "auto" else "gemini"
        if stats.get("frontier_router") and stats.get("provider_health"):
            for p, health in stats["provider_health"].items():
                if health.get("healthy", False):
                    provider_used = p
                    break
        
        return BrainChatResponse(
            response=response,
            provider=provider_used,
            session_id=session_id,
            conversation_id=conversation_id,
            memory_context=memory_context,
            actions_taken=[
                {"type": "memory_recalled", "count": len(memory_context.get("memories", [])) if memory_context else 0},
                {"type": "turn_persisted", "session_id": session_id},
            ]
        )
        
    except Exception as e:
        logger.error(f"Brain chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def brain_stream(request: BrainChatRequest):
    """
    Stream a memory-aware response from MYCA's brain.
    
    Returns Server-Sent Events (SSE) for real-time token streaming.
    """
    try:
        brain = await get_brain()
        
        session_id = request.session_id or str(uuid4())
        conversation_id = request.conversation_id or str(uuid4())
        
        async def generate():
            try:
                async for token in brain.stream_response(
                    message=request.message,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    history=request.history,
                    provider=request.provider
                ):
                    # Send as SSE event
                    yield f"data: {json.dumps({'token': token})}\n\n"
                
                # Send done event
                yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'conversation_id': conversation_id})}\n\n"
                
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except Exception as e:
        logger.error(f"Brain stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def brain_status():
    """
    Get MYCA brain status and health.
    
    Returns:
    - Initialization status
    - Available LLM providers and health
    - Memory system status
    """
    try:
        brain = await get_brain()
        stats = await brain.get_stats()
        
        return {
            "status": "healthy" if stats.get("initialized") else "initializing",
            "brain": {
                "initialized": stats.get("initialized", False),
                "frontier_router": stats.get("frontier_router", False),
                "memory_coordinator": stats.get("memory_coordinator", False),
            },
            "providers": stats.get("provider_health", {}),
            "memory": stats.get("memory", {}),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Brain status error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/context/{user_id}")
async def get_memory_context(
    user_id: str,
    query: Optional[str] = None,
    limit: int = 10
):
    """
    Get memory context for a user.
    
    Returns:
    - Recalled memories relevant to query
    - Recent episodes
    - User profile and preferences
    - Voice session context
    """
    try:
        brain = await get_brain()
        
        context = await brain.recall_context(
            query=query or "general context",
            user_id=user_id,
            limit=limit
        )
        
        return MemoryContextResponse(
            user_id=user_id,
            conversation_id=None,
            memories=context.get("memories", []),
            episodes=context.get("episodes", []),
            user_profile=context.get("profile"),
            voice_context=None  # TODO: Add voice context
        )
        
    except Exception as e:
        logger.error(f"Memory context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/event")
async def record_brain_event(
    event_type: str,
    description: str,
    context: Optional[Dict[str, Any]] = None,
    importance: float = 0.7
):
    """
    Record a significant event in the brain's episodic memory.
    
    Use this for important events like:
    - Tool executions
    - Agent invocations
    - System status changes
    - User requests completed
    """
    try:
        brain = await get_brain()
        
        await brain.record_significant_event(
            event_type=event_type,
            description=description,
            context=context,
            importance=importance
        )
        
        return {
            "status": "recorded",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Event recording error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def brain_health():
    """Simple health check for brain API."""
    return {
        "status": "healthy",
        "service": "myca-brain-api",
        "version": "1.0.0-memory-integrated",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
