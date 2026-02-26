"""
Grounding Gate - wraps all inputs in Experience Packets.

Enforces: no cognition without grounded context.
Every input gets an EP with GroundTruth, SelfState, WorldState,
and provenance before entering the pipeline.

Created: February 17, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from mycosoft_mas.schemas.experience_packet import (
    ExperiencePacket,
    GroundTruth,
    Observation,
    ObservationModality,
    SelfState,
    Uncertainty,
    WorldStateRef,
    Provenance,
)
from mycosoft_mas.schemas.codec import canonical_json, hash_sha256

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness

logger = logging.getLogger(__name__)

SELF_STATE_TIMEOUT = 0.5
WORLD_STATE_TIMEOUT = 1.0


def _source_to_modality(source: str) -> ObservationModality:
    """Map source string to ObservationModality."""
    m = source.lower()
    if m in ("voice", "speech"):
        return ObservationModality.VOICE
    if m in ("image", "vision"):
        return ObservationModality.IMAGE
    if m in ("sensor", "bioelectric", "voc"):
        return ObservationModality(m) if m in ("bioelectric", "voc") else ObservationModality.SENSOR
    return ObservationModality.TEXT


class GroundingGate:
    """
    Wraps inputs in Experience Packets and enforces grounding before LLM.
    """

    def __init__(self, consciousness: "MYCAConsciousness"):
        self._consciousness = consciousness

    async def build_experience_packet(
        self,
        content: str,
        source: str = "text",
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ExperiencePacket:
        """
        Create a base Experience Packet from raw input.
        Does not attach SelfState or WorldState - those are separate steps.
        """
        modality = _source_to_modality(source)
        observation = Observation(
            modality=modality,
            raw_payload=content[:10000],  # Cap size
            derived_features=context or {},
        )
        ep = ExperiencePacket(
            ground_truth=GroundTruth(),
            observation=observation,
            uncertainty=Uncertainty(),
            provenance=Provenance(),
        )
        # Mark geo missing if not in context
        if not (context and context.get("geo")):
            ep.uncertainty.missingness["geo"] = True
        return ep

    def validate(self, ep: ExperiencePacket) -> Tuple[bool, List[str]]:
        """
        Validate EP has required fields for grounding.
        Returns (valid, list of error messages).
        """
        errors: List[str] = []
        if not ep.self_state:
            errors.append("missing self_state")
        if not ep.world_state:
            errors.append("missing world_state")
        if not ep.ground_truth or not ep.ground_truth.monotonic_ts:
            errors.append("missing ground_truth")
        valid = len(errors) == 0
        return valid, errors

    async def attach_self_state(self, ep: ExperiencePacket) -> ExperiencePacket:
        """
        Attach SelfState snapshot with 500ms timeout.
        Fallback to minimal SelfState on timeout.
        """
        services: Dict[str, Any] = {}
        agents: Dict[str, Any] = {}
        active_plans: List[str] = []

        async def _gather_self_state() -> None:
            nonlocal services, agents, active_plans
            # Health checker
            try:
                from mycosoft_mas.monitoring.health_check import get_health_checker
                checker = get_health_checker()
                health = await checker.check_all()
                services = {
                    "health": health.get("status", "unknown"),
                    "components": [
                        {"name": c.get("name"), "status": c.get("status")}
                        for c in health.get("components", [])
                    ],
                }
            except Exception as e:
                from mycosoft_mas.llm.error_sanitizer import sanitize_for_log
                services = {"error": sanitize_for_log(e), "fallback": True}

            # Presence (online users, sessions, staff) from WorldModel
            wm = getattr(self._consciousness, "_world_model", None)
            if wm and hasattr(wm, "get_cached_context"):
                try:
                    ctx = wm.get_cached_context()
                    presence = (ctx.get("data") or {}).get("presence") or {}
                    if presence:
                        services["presence"] = {
                            "online_count": presence.get("online_count", 0),
                            "sessions_count": presence.get("sessions_count", 0),
                            "staff_count": presence.get("staff_count", 0),
                            "superuser_online": presence.get("superuser_online", False),
                        }
                except Exception:
                    pass

            # Agent registry
            reg = getattr(self._consciousness, "_agent_registry", None)
            if reg:
                try:
                    all_agents = reg.get_all_agents()
                    agents = {
                        "count": len(all_agents),
                        "by_status": {},
                    }
                    for a in all_agents:
                        s = getattr(a.status, "value", str(a.status))
                        agents["by_status"][s] = agents["by_status"].get(s, 0) + 1
                except Exception as e:
                    from mycosoft_mas.llm.error_sanitizer import sanitize_for_log
                    agents = {"error": sanitize_for_log(e)}

            # Active goals from consciousness metrics
            metrics = getattr(self._consciousness, "_metrics", None)
            if metrics and hasattr(metrics, "active_goals"):
                active_plans = list(metrics.active_goals or [])

        try:
            await asyncio.wait_for(_gather_self_state(), timeout=SELF_STATE_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning("SelfState gathering timed out, using minimal")
            ep.uncertainty.missingness["self_state_timeout"] = True
            services = {"timeout": True, "fallback": True}

        ep.self_state = SelfState(
            snapshot_ts=datetime.now(timezone.utc).isoformat(),
            services=services,
            agents=agents,
            active_plans=active_plans,
        )
        return ep

    async def attach_world_state(self, ep: ExperiencePacket) -> ExperiencePacket:
        """
        Attach WorldStateRef from cached context with 1s timeout.
        Uses WorldModel.get_cached_context() for fast path.
        """
        sources: List[str] = []
        summary: Optional[str] = None
        freshness = "unknown"

        wm = getattr(self._consciousness, "_world_model", None)
        if wm and hasattr(wm, "get_cached_context"):

            async def _fetch_world() -> None:
                nonlocal sources, summary, freshness
                ctx = wm.get_cached_context()
                if ctx:
                    summary = ctx.get("summary", "Cached world context")
                    data = ctx.get("data", {})
                    sources = list(data.keys()) if data else ["cached"]
                    age = ctx.get("age_seconds", 0)
                    if age < 60:
                        freshness = "live"
                    elif age < 300:
                        freshness = "recent"
                    else:
                        freshness = "stale"

            try:
                await asyncio.wait_for(_fetch_world(), timeout=WORLD_STATE_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning("WorldState gathering timed out, using minimal")
                ep.uncertainty.missingness["world_state_timeout"] = True
                sources = ["timeout_fallback"]
                summary = "World state unavailable (timeout)"
        else:
            ep.uncertainty.missingness["world_model"] = True
            sources = []
            summary = "World model not available"

        nlm_prediction: Optional[Dict[str, Any]] = None
        try:
            import os
            import httpx
            mas_url = os.getenv("MAS_API_URL", "http://localhost:8001")
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.post(
                    f"{mas_url.rstrip('/')}/api/nlm/predict/sensors",
                    json={"entity_id": "sporebase", "horizon_minutes": 60},
                )
                if r.status_code == 200:
                    data = r.json()
                    if not data.get("fallback"):
                        nlm_prediction = data
                        sources = sources + ["nlm_prediction"]
        except Exception as e:
            logger.debug("NLM predict/sensors unavailable: %s", e)

        ep.world_state = WorldStateRef(
            snapshot_ts=datetime.now(timezone.utc).isoformat(),
            sources=sources,
            freshness=freshness,
            summary=summary,
            nlm_prediction=nlm_prediction,
        )
        return ep

    def compute_provenance(self, ep: ExperiencePacket) -> ExperiencePacket:
        """Compute SHA256 hash of canonical EP for chain-of-custody."""
        try:
            canonical = canonical_json(ep, redact_secrets=True)
            ep.provenance.sha256_hash = hash_sha256(canonical)
        except Exception as e:
            from mycosoft_mas.llm.error_sanitizer import sanitize_for_log
            logger.warning(f"Provenance hash failed: {sanitize_for_log(e)}")
            ep.uncertainty.missingness["provenance_hash"] = sanitize_for_log(e)
        return ep

    async def _store_ep(
        self,
        ep: ExperiencePacket,
        session_id: Optional[str],
        user_id: Optional[str],
    ) -> None:
        """Persist EP to MINDEX. Soft-fail: log and return on error."""
        try:
            import os
            import httpx
            from mycosoft_mas.schemas.codec import _to_json_serializable
            url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
            path = "/api/mindex/grounding/experience-packets"
            payload = _to_json_serializable(ep)
            if isinstance(payload, dict):
                body = {
                    "id": ep.id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "ground_truth": payload.get("ground_truth", {}),
                    "self_state": payload.get("self_state"),
                    "world_state": payload.get("world_state"),
                    "observation": payload.get("observation", {}),
                    "uncertainty": payload.get("uncertainty", {}),
                    "provenance": payload.get("provenance", {}),
                }
            else:
                body = {"id": ep.id, "session_id": session_id, "user_id": user_id, "ground_truth": {}}
            headers = {}
            if os.getenv("MINDEX_API_KEY"):
                headers["X-API-Key"] = os.getenv("MINDEX_API_KEY")
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{url}{path}", json=body, headers=headers or None)
        except Exception as e:
            logger.warning("EP store failed (soft-fail): %s", e)

    async def wire_spatial_and_temporal(
        self,
        ep: ExperiencePacket,
        context: Optional[Dict[str, Any]],
        session_id: Optional[str],
    ) -> None:
        """Wire spatial/temporal: store_point if geo, check episode. Soft-fail, non-blocking."""
        try:
            geo = (context or {}).get("geo") if context else None
            if geo and session_id:
                lat = geo.get("lat") if isinstance(geo, dict) else getattr(geo, "lat", None)
                lon = geo.get("lon") if isinstance(geo, dict) else getattr(geo, "lon", None)
                if lat is not None and lon is not None:
                    from mycosoft_mas.engines.spatial.service import SpatialService
                    svc = SpatialService()
                    await svc.store_point(session_id, float(lat), float(lon), ep_id=ep.id)
        except Exception as e:
            logger.debug("Spatial wire failed: %s", e)
        try:
            if session_id:
                from mycosoft_mas.engines.temporal.service import TemporalService
                from datetime import datetime, timezone
                svc = TemporalService()
                now = datetime.now(timezone.utc)
                if svc.should_start_episode(session_id, None, now):
                    await svc.store_episode(session_id, now, end_ts=None, ep_ids=[ep.id])
        except Exception as e:
            logger.debug("Temporal wire failed: %s", e)
