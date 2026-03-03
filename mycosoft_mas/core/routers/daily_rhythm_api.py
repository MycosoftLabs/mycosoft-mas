"""
MYCA Daily Rhythm API — endpoints for autonomous daily schedule.

Triggered by n8n cron workflows or called directly.
Each endpoint maps to a step in MYCA's daily routine.

Created: March 3, 2026
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rhythm", tags=["rhythm"])

_rhythm_agent = None


def _get_agent():
    global _rhythm_agent
    if _rhythm_agent is None:
        try:
            from mycosoft_mas.agents.daily_rhythm_agent import DailyRhythmAgent

            _rhythm_agent = DailyRhythmAgent(
                agent_id="daily_rhythm_agent",
                name="MYCA Daily Rhythm",
                config={},
            )
        except Exception as e:
            logger.warning("DailyRhythmAgent not available: %s", e)
    return _rhythm_agent


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
async def rhythm_health():
    return {
        "status": "healthy",
        "service": "myca-daily-rhythm",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Schedule Info
# ---------------------------------------------------------------------------


@router.get("/schedule")
async def get_schedule():
    """Get MYCA's daily schedule and recent rhythm log."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "DailyRhythmAgent not available")
    return await agent.process_task({"type": "get_schedule"})


# ---------------------------------------------------------------------------
# Rhythm Triggers (called by n8n cron or manually)
# ---------------------------------------------------------------------------


@router.post("/morning-brief")
async def morning_brief():
    """8 AM — Morning briefing: health check, task review, daily plan, Discord post."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "DailyRhythmAgent not available")
    return await agent.process_task({"type": "morning_brief"})


@router.post("/hourly-status")
async def hourly_status():
    """Hourly — Status check: health, tasks, messages."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "DailyRhythmAgent not available")
    return await agent.process_task({"type": "hourly_status"})


@router.post("/midday-sync")
async def midday_sync():
    """12 PM — Midday sync: progress update, re-prioritize."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "DailyRhythmAgent not available")
    return await agent.process_task({"type": "midday_sync"})


@router.post("/end-of-day")
async def end_of_day():
    """5 PM — End-of-day: summary, email to Morgan, archive tasks."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "DailyRhythmAgent not available")
    return await agent.process_task({"type": "end_of_day"})


@router.post("/night-mode")
async def night_mode():
    """10 PM — Switch to monitoring-only mode."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "DailyRhythmAgent not available")
    return await agent.process_task({"type": "night_mode"})


@router.post("/process-tasks")
async def process_tasks():
    """Process the next task in the daily plan queue."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "DailyRhythmAgent not available")
    return await agent.process_task({"type": "process_tasks"})
