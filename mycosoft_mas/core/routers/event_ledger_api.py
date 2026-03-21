"""
Event Ledger API Router — March 19, 2026

Exposes the append-only event ledger for dashboard consumption, audit trail,
and real-time monitoring. Uses the existing EventLedger from
mycosoft_mas/myca/event_ledger/ledger_writer.py.

NO MOCK DATA — reads from the real JSONL event log.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["Event Ledger"])


def _get_ledger():
    """Get the event ledger singleton."""
    from mycosoft_mas.myca.event_ledger.ledger_writer import get_ledger

    return get_ledger()


@router.get("/recent")
async def get_recent_events(
    limit: int = Query(100, ge=1, le=1000),
    agent: Optional[str] = Query(None, description="Filter by agent name"),
    tool: Optional[str] = Query(None, description="Filter by tool name"),
    status: Optional[str] = Query(None, description="Filter by result_status"),
    since_ts: Optional[int] = Query(None, description="Only events after this unix timestamp"),
) -> Dict[str, Any]:
    """Get recent events from the event ledger with optional filtering."""
    ledger = _get_ledger()
    events = ledger.read_events(
        since_ts=since_ts,
        agent=agent,
        tool=tool,
        status=status,
        limit=limit,
    )

    return {
        "events": events,
        "count": len(events),
        "filters": {
            "agent": agent,
            "tool": tool,
            "status": status,
            "since_ts": since_ts,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/failures")
async def get_failure_summary(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
) -> Dict[str, Any]:
    """Get failure summary for the specified time window."""
    ledger = _get_ledger()
    summary = ledger.get_failure_summary(hours=hours)

    return {
        "summary": summary,
        "hours": hours,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/telemetry")
async def get_telemetry_chain(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    limit: int = Query(100, ge=1, le=1000),
) -> Dict[str, Any]:
    """Get telemetry provenance chain from the event ledger."""
    ledger = _get_ledger()
    chain = ledger.read_telemetry_chain(device_id=device_id, limit=limit)

    return {
        "chain": chain,
        "count": len(chain),
        "device_id": device_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stream")
async def stream_events():
    """
    SSE endpoint for real-time event streaming.

    Tails the event ledger file and pushes new events as they arrive.
    Clients connect via EventSource: new EventSource('/api/events/stream')
    """

    async def event_generator():
        ledger = _get_ledger()
        ledger_file = ledger.current_ledger_file

        # Start from end of file
        try:
            with open(ledger_file, "r") as f:
                f.seek(0, 2)  # Seek to end
                last_pos = f.tell()
        except FileNotFoundError:
            last_pos = 0

        yield f"data: {json.dumps({'event': 'connected', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"

        while True:
            try:
                with open(ledger_file, "r") as f:
                    f.seek(last_pos)
                    new_lines = f.readlines()
                    last_pos = f.tell()

                for line in new_lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        yield f"data: {json.dumps(event)}\n\n"
                    except json.JSONDecodeError:
                        continue

            except FileNotFoundError:
                pass

            # Send keepalive ping every 15 seconds
            yield f": keepalive {datetime.now(timezone.utc).isoformat()}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stats")
async def get_ledger_stats() -> Dict[str, Any]:
    """Get overall ledger statistics."""
    ledger = _get_ledger()
    all_events = ledger.read_events(limit=10000)

    # Count by type
    by_status: Dict[str, int] = {}
    by_agent: Dict[str, int] = {}
    by_type: Dict[str, int] = {}

    for event in all_events:
        status = event.get("result_status", "unknown")
        agent = event.get("agent", "unknown")
        event_type = event.get("event_type", "tool_call")

        by_status[status] = by_status.get(status, 0) + 1
        by_agent[agent] = by_agent.get(agent, 0) + 1
        by_type[event_type] = by_type.get(event_type, 0) + 1

    return {
        "total_events": len(all_events),
        "by_status": by_status,
        "by_agent": by_agent,
        "by_type": by_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
