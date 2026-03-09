"""
Liquid Fungal Integration API — REST Endpoints

Exposes the Liquid AI-inspired fungal integration stack:
  - Adaptive temporal biosignal processing
  - Fungal memory bridging (memristive state, bookmarks, hysteresis)
  - Recursive self-improvement cycles with benchmarks
  - Adaptation metrics across all subsystems

Created: March 9, 2026
(c) 2026 Mycosoft Labs
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/liquid-fungal", tags=["liquid-fungal"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ProcessBiosignalRequest(BaseModel):
    channel_id: str = "ch0"
    samples: List[float] = Field(..., min_length=1)
    timestamps: Optional[List[float]] = None


class CreateBookmarkRequest(BaseModel):
    channel_id: str = "ch0"
    from_state: str = "unknown"
    to_state: str = "unknown"
    significance: float = Field(0.5, ge=0.0, le=1.0)
    fungal_state_snapshot: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrackMemristiveRequest(BaseModel):
    channel_id: str = "ch0"
    stimulus: float = 0.0
    response: float = 0.0


# ---------------------------------------------------------------------------
# Singleton engine instances (lazy-init)
# ---------------------------------------------------------------------------

_processor = None
_memory_bridge = None
_improvement_engine = None


def _get_processor():
    global _processor
    if _processor is None:
        from mycosoft_mas.engines.liquid_temporal import LiquidTemporalProcessor
        _processor = LiquidTemporalProcessor()
    return _processor


def _get_memory_bridge():
    global _memory_bridge
    if _memory_bridge is None:
        from mycosoft_mas.memory.fungal_memory_bridge import FungalMemoryBridge
        _memory_bridge = FungalMemoryBridge()
    return _memory_bridge


def _get_improvement_engine():
    global _improvement_engine
    if _improvement_engine is None:
        from mycosoft_mas.engines.recursive_improvement import (
            RecursiveSelfImprovementEngine,
        )
        learning_feedback = None
        try:
            from mycosoft_mas.services.learning_feedback import get_learning_service
            learning_feedback = get_learning_service()
        except Exception:
            pass
        _improvement_engine = RecursiveSelfImprovementEngine(
            learning_feedback=learning_feedback,
        )
    return _improvement_engine


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    """Health check for liquid-fungal integration stack."""
    return {
        "status": "healthy",
        "service": "liquid-fungal-integration",
        "components": {
            "temporal_processor": _processor is not None,
            "memory_bridge": _memory_bridge is not None,
            "improvement_engine": _improvement_engine is not None,
        },
    }


# ---------------------------------------------------------------------------
# Temporal Processing
# ---------------------------------------------------------------------------

@router.post("/process")
async def process_biosignal(req: ProcessBiosignalRequest):
    """Process FCI biosignal through liquid temporal processor."""
    processor = _get_processor()

    result = processor.process_continuous(
        channel_id=req.channel_id,
        samples=req.samples,
        timestamps=req.timestamps,
    )

    transition = processor.detect_state_transition(req.channel_id)
    bookmark_created = False

    if transition and transition.confidence >= 0.6:
        bridge = _get_memory_bridge()
        await bridge.create_biological_bookmark(
            channel_id=req.channel_id,
            from_state=transition.from_state,
            to_state=transition.to_state,
            significance=transition.confidence,
            fungal_state_snapshot=result.signal_dynamics,
        )
        bookmark_created = True

    return {
        "processed_stream": result.to_dict(),
        "transition": transition.to_dict() if transition else None,
        "bookmark_created": bookmark_created,
    }


@router.get("/adaptation/metrics")
async def get_adaptation_metrics():
    """Current adaptation metrics (time constants, rates) across all channels."""
    processor = _get_processor()
    return processor.get_adaptation_metrics()


# ---------------------------------------------------------------------------
# Memory Bridge
# ---------------------------------------------------------------------------

@router.post("/memory/bookmark")
async def create_bookmark(req: CreateBookmarkRequest):
    """Create a biological bookmark for a state transition."""
    bridge = _get_memory_bridge()
    bookmark = await bridge.create_biological_bookmark(
        channel_id=req.channel_id,
        from_state=req.from_state,
        to_state=req.to_state,
        significance=req.significance,
        fungal_state_snapshot=req.fungal_state_snapshot,
        metadata=req.metadata,
    )
    return {"bookmark": bookmark.to_dict()}


@router.get("/memory/bookmarks")
async def query_bookmarks(
    channel_id: Optional[str] = None,
    min_significance: float = 0.0,
):
    """Query biological bookmarks with optional filters."""
    bridge = _get_memory_bridge()
    bookmarks = bridge.query_biological_memory(
        channel_id=channel_id,
        min_significance=min_significance,
    )
    return {
        "bookmarks": [b.to_dict() for b in bookmarks[:50]],
        "total": len(bookmarks),
    }


@router.get("/memory/hysteresis")
async def get_hysteresis():
    """Get memristive state report across all tracked channels."""
    bridge = _get_memory_bridge()
    return bridge.get_hysteresis_report()


@router.post("/memory/memristive")
async def track_memristive(req: TrackMemristiveRequest):
    """Track memristive (history-dependent) state for a channel."""
    bridge = _get_memory_bridge()
    state = bridge.track_memristive_state(
        channel_id=req.channel_id,
        stimulus=req.stimulus,
        response=req.response,
    )
    return state.to_dict()


@router.post("/memory/consolidate")
async def consolidate_patterns():
    """Promote recurring biological patterns to semantic memory."""
    bridge = _get_memory_bridge()
    count = await bridge.consolidate_to_semantic()
    return {"patterns_consolidated": count}


# ---------------------------------------------------------------------------
# Recursive Self-Improvement
# ---------------------------------------------------------------------------

@router.post("/improvement/cycle")
async def run_improvement_cycle():
    """Trigger one recursive self-improvement cycle."""
    engine = _get_improvement_engine()
    result = engine.run_cycle()
    return result.to_dict()


@router.get("/improvement/history")
async def get_improvement_history():
    """Get improvement cycle history."""
    engine = _get_improvement_engine()
    return {"cycles": engine.get_improvement_history()}


@router.get("/improvement/benchmarks")
async def get_benchmarks():
    """Get all benchmark records."""
    engine = _get_improvement_engine()
    return {"benchmarks": engine.get_benchmarks()}


@router.get("/improvement/hypotheses")
async def get_hypotheses(status: Optional[str] = None):
    """Get improvement hypotheses, optionally filtered by status."""
    engine = _get_improvement_engine()
    return {"hypotheses": engine.get_hypotheses(status=status)}


@router.get("/improvement/summary")
async def get_improvement_summary():
    """Get improvement engine summary with current state."""
    engine = _get_improvement_engine()
    return engine.get_summary()
