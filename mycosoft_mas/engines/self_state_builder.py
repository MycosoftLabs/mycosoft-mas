"""
Canonical SelfState builder - single source of truth for SelfState assembly.

Used by GroundingGate (when StateService unavailable) and for mapping
StateService /state HTTP response to SelfState. Ensures one coherent
SelfState contract per WORLDSTATE_CONTRACT_MAR14_2026.md.

Created: March 14, 2026
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mycosoft_mas.schemas.experience_packet import SelfState


def assemble_self_state(
    services: Dict[str, Any],
    agents: Dict[str, Any],
    active_plans: Optional[List[str]] = None,
    snapshot_ts: Optional[str] = None,
) -> SelfState:
    """
    Assemble SelfState from raw components.

    Single canonical builder for SelfState. Used by GroundingGate fallback
    and for normalizing StateService /state responses.
    """
    return SelfState(
        snapshot_ts=snapshot_ts or datetime.now(timezone.utc).isoformat(),
        services=services,
        agents=agents,
        active_plans=active_plans or [],
    )


def from_http_response(data: Dict[str, Any]) -> SelfState:
    """
    Build SelfState from StateService /state HTTP response.

    Normalizes the StateService response shape to SelfState. Used by
    GroundingGate.attach_self_state() when STATE_SERVICE_URL is set.
    """
    return assemble_self_state(
        services=data.get("services", {}),
        agents=data.get("agents", {}),
        active_plans=data.get("active_goals", []),
        snapshot_ts=data.get("timestamp"),
    )
