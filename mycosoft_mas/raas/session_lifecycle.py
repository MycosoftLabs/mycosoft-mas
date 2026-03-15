"""RaaS Worldstate Session Lifecycle — start, heartbeat, stop, balance, usage.

External agents use these endpoints to run metered live worldstate sessions.
All endpoints require X-API-Key (require_raas_auth). Return 402 when balance
is exhausted or session cannot be continued.

Created: March 14, 2026
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from mycosoft_mas.raas.middleware import require_raas_auth
from mycosoft_mas.raas.models import (
    AgentAccount,
    BalanceUsageResponse,
    SessionHeartbeatRequest,
    SessionHeartbeatResponse,
    SessionStartResponse,
    SessionStopRequest,
    SessionStopResponse,
    WorldstateBalance,
)
from mycosoft_mas.raas.worldstate_session import (
    get_balance,
    get_usage,
    heartbeat_session,
    start_session,
    stop_session,
)

router = APIRouter(prefix="/api/raas/worldstate", tags=["RaaS - Worldstate Sessions"])

HTTP_402_PAYMENT_REQUIRED = 402


def _402(detail: str, balance_minutes: int = 0) -> HTTPException:
    """Return 402 Payment Required with JSON body."""
    return HTTPException(
        status_code=HTTP_402_PAYMENT_REQUIRED,
        detail=detail,
        headers={"X-Balance-Minutes": str(balance_minutes)},
    )


@router.post("/start", response_model=SessionStartResponse)
async def session_start(
    agent: AgentAccount = Depends(require_raas_auth),
) -> Dict[str, Any]:
    """Start a paid worldstate session. Requires balance > 0."""
    session_id, balance, err = await start_session(agent.agent_id)
    if err == "insufficient_balance":
        raise _402("Insufficient balance to start session", balance_minutes=balance)
    if err or not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Failed to start session",
        )
    return SessionStartResponse(
        session_id=session_id,
        balance_minutes=balance,
    )


@router.post("/heartbeat", response_model=SessionHeartbeatResponse)
async def session_heartbeat(
    body: SessionHeartbeatRequest,
    agent: AgentAccount = Depends(require_raas_auth),
) -> SessionHeartbeatResponse:
    """Send heartbeat to keep session active. Deducts 1 minute per elapsed minute."""
    success, balance, minutes_used, err = await heartbeat_session(
        body.session_id, agent.agent_id
    )
    if not success and err == "insufficient_balance":
        raise _402("Insufficient balance to continue session", balance_minutes=balance)
    if not success and err == "session_not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or not owned by this agent",
        )
    if not success and err == "session_stopped":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already stopped",
        )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Heartbeat failed",
        )
    return SessionHeartbeatResponse(
        session_id=body.session_id,
        balance_minutes=balance,
        minutes_used_this_session=minutes_used,
    )


@router.post("/stop", response_model=SessionStopResponse)
async def session_stop(
    body: SessionStopRequest,
    agent: AgentAccount = Depends(require_raas_auth),
) -> SessionStopResponse:
    """Stop an active session."""
    success, total_used, balance, err = await stop_session(
        body.session_id, agent.agent_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=err or "Session not found",
        )
    return SessionStopResponse(
        session_id=body.session_id,
        total_minutes_used=total_used,
        balance_minutes=balance,
    )


@router.get("/balance", response_model=WorldstateBalance)
async def get_balance_endpoint(
    agent: AgentAccount = Depends(require_raas_auth),
) -> WorldstateBalance:
    """Get current minute balance for worldstate access."""
    return await get_balance(agent.agent_id)


@router.get("/usage", response_model=BalanceUsageResponse)
async def get_usage_endpoint(
    agent: AgentAccount = Depends(require_raas_auth),
    limit: int = 20,
) -> BalanceUsageResponse:
    """Get balance and recent session usage."""
    bal, active_session_id, recent_sessions = await get_usage(
        agent.agent_id, limit=limit
    )
    return BalanceUsageResponse(
        agent_id=bal.agent_id,
        balance_minutes=bal.balance_minutes,
        total_purchased_minutes=bal.total_purchased_minutes,
        total_used_minutes=bal.total_used_minutes,
        active_session_id=active_session_id,
        recent_sessions=recent_sessions,
    )
