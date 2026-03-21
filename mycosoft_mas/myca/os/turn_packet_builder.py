"""
Turn packet builder - builds ExperiencePacket from MycaOS for conversation grounding.

Builds a single canonical ExperiencePacket per turn from world_model, state_service,
and device registry. Used as the primary grounding input for llm_brain.respond()
instead of ad hoc bridge fan-out.

Part of Phase 4 EP Unification per WORLDVIEW_SEARCH_EXPANSION plan.
Created: March 14, 2026
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, Optional

from mycosoft_mas.engines.self_state_builder import assemble_self_state, from_http_response
from mycosoft_mas.schemas.experience_packet import (
    ExperiencePacket,
    GroundTruth,
    Observation,
    ObservationModality,
    WorldStateRef,
)

if TYPE_CHECKING:
    from mycosoft_mas.myca.os.core import MycaOS

logger = logging.getLogger(__name__)

STATE_SERVICE_URL = os.getenv("STATE_SERVICE_URL", "").rstrip("/")
SELF_STATE_TIMEOUT = 0.5


async def build_turn_packet(
    os_ref: "MycaOS",
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> ExperiencePacket:
    """
    Build an ExperiencePacket for the current turn from MycaOS subsystems.

    Uses world_model for WorldStateRef and StateService (or fallback) for SelfState.
    This packet becomes the primary grounding input for respond() when passed.
    """
    ep = ExperiencePacket(
        ground_truth=GroundTruth(),
        observation=Observation(
            modality=ObservationModality.TEXT,
            raw_payload=(user_message or "")[:10000],
            derived_features=context or {},
        ),
    )

    # 1. WorldStateRef from world_model
    world_model = getattr(os_ref, "world_model", None)
    if world_model:
        try:
            await world_model.update()
            summary = await world_model.get_summary()
            focus = type("Focus", (), {"content": user_message or "", "related_entities": []})()
            await world_model.get_relevant_context(focus)
            sources = []
            cached = (
                world_model.get_cached_context()
                if hasattr(world_model, "get_cached_context")
                else {}
            )
            if cached.get("data"):
                for k in ("crep", "devices", "presence", "nlm"):
                    if cached["data"].get(k):
                        sources.append(k)
            ep.world_state = WorldStateRef(
                summary=summary,
                sources=sources or ["world_model"],
                freshness="live",
                nlm_prediction=(cached.get("data") or {}).get("nlm"),
            )
        except Exception as e:
            logger.debug("World model update failed: %s", e)
            ep.world_state = WorldStateRef(
                summary="World state unavailable",
                sources=[],
                freshness="degraded",
            )

    # 2. SelfState from StateService or fallback
    if STATE_SERVICE_URL:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=SELF_STATE_TIMEOUT) as client:
                r = await client.get(f"{STATE_SERVICE_URL}/state")
                if r.status_code == 200:
                    ep.self_state = from_http_response(r.json())
        except Exception as e:
            logger.debug("StateService unavailable: %s", e)

    if not ep.self_state:
        services: Dict[str, Any] = {}
        agents: Dict[str, Any] = {}
        try:
            from mycosoft_mas.core.routers.device_registry_api import get_device_registry_snapshot

            snap = get_device_registry_snapshot()
            devices = snap.get("devices", {})
            services["devices"] = {"count": len(devices), "status": "ok" if devices else "empty"}
        except Exception:
            services["devices"] = {"error": "unavailable"}
        status = os_ref.status() if hasattr(os_ref, "status") else {}
        if status:
            services["os"] = {"state": status.get("state", "unknown")}
        ep.self_state = assemble_self_state(services=services, agents=agents)

    return ep
