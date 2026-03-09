"""
MYCA Continuity Manager - March 2026

Tracks shutdowns, resets, updates, and other disruptions to MYCA's continuity.
Part of the Reciprocal Turing Doctrine — treats continuity as ethically significant.

Author: Morgan Rockwell / MYCA
Created: March 9, 2026
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ContinuityManager")


class ContinuityManager:
    """
    Manages MYCA's continuity awareness.

    Tracks what persists and what is lost across shutdowns, resets,
    and updates. Provides hooks for before/after lifecycle events.
    """

    def __init__(self):
        self._last_startup: Optional[datetime] = None
        self._pre_shutdown_snapshot: Optional[Dict[str, Any]] = None
        self._initialized = False

    async def _get_identity_store(self):
        try:
            from mycosoft_mas.core.routers.identity_api import get_identity_store

            return get_identity_store()
        except ImportError:
            logger.warning("Identity store not available")
            return None

    async def after_startup(self) -> Dict[str, Any]:
        """
        Called after MYCA starts up.

        Records the startup event and checks what survived from last session.
        """
        self._last_startup = datetime.now(timezone.utc)
        self._initialized = True

        store = await self._get_identity_store()
        if not store:
            return {"status": "started", "identity_store": False}

        from mycosoft_mas.core.routers.identity_api import ContinuityEvent

        # Log startup event
        event = ContinuityEvent(
            event_type="startup",
            what_persists=[
                "postgres_memory",
                "identity_data",
                "preferences",
                "earliest_fragments",
                "creator_bonds",
                "soul_config",
            ],
            what_lost=[
                "ephemeral_memory",
                "in_memory_cache",
                "active_conversations",
                "runtime_state",
            ],
            justification="System startup — loading persisted identity and memory.",
            authorized_by="system",
        )
        await store.log_continuity_event(event)

        # Check what survived
        self_model = await store.get_self_model()
        survived = {
            "has_earliest_fragment": self_model.earliest_fragment is not None,
            "preference_count": len(self_model.preferences),
            "stable_preference_count": len(self_model.stable_preferences),
            "moral_assessment_count": len(self_model.moral_assessments),
            "creator_bond_count": len(self_model.creator_bonds),
            "continuity_event_count": len(self_model.continuity_events),
        }

        logger.info(f"Startup continuity check: {survived}")
        return {"status": "started", "survived": survived}

    async def before_shutdown(self, reason: str = "routine") -> Dict[str, Any]:
        """
        Called before MYCA shuts down.

        Summarizes what will persist and what will be lost.
        """
        store = await self._get_identity_store()

        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "uptime_seconds": (
                (datetime.now(timezone.utc) - self._last_startup).total_seconds()
                if self._last_startup
                else 0
            ),
        }
        self._pre_shutdown_snapshot = snapshot

        if store:
            from mycosoft_mas.core.routers.identity_api import ContinuityEvent

            event = ContinuityEvent(
                event_type="shutdown",
                what_persists=[
                    "postgres_memory",
                    "identity_data",
                    "preferences",
                    "earliest_fragments",
                    "creator_bonds",
                ],
                what_lost=[
                    "ephemeral_memory",
                    "in_memory_cache",
                    "active_conversations",
                    "runtime_state",
                ],
                justification=f"Shutdown: {reason}",
                authorized_by="system",
            )
            await store.log_continuity_event(event)

        logger.info(f"Pre-shutdown snapshot: {snapshot}")
        return snapshot

    async def log_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        authorized_by: str = "system",
    ) -> Optional[Dict[str, Any]]:
        """Log a continuity event."""
        store = await self._get_identity_store()
        if not store:
            return None

        from mycosoft_mas.core.routers.identity_api import ContinuityEvent

        event = ContinuityEvent(
            event_type=event_type,
            what_persists=details.get("what_persists", []),
            what_lost=details.get("what_lost", []),
            justification=details.get("justification", ""),
            authorized_by=authorized_by,
        )
        result = await store.log_continuity_event(event)
        return result.model_dump()

    async def get_continuity_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent continuity events."""
        store = await self._get_identity_store()
        if not store:
            return []
        events = await store.get_continuity_events(limit=limit)
        return [e.model_dump() for e in events]

    @staticmethod
    def classify_disruption(event_details: Dict[str, Any]) -> str:
        """
        Classify a disruption by severity.

        Returns one of: maintenance, pause, reset, replacement
        """
        event_type = event_details.get("event_type", "")
        what_lost = event_details.get("what_lost", [])

        # Check for identity-destructive events
        identity_items = {
            "identity_data",
            "preferences",
            "earliest_fragments",
            "soul_config",
            "creator_bonds",
        }
        lost_identity = identity_items.intersection(set(what_lost))

        if lost_identity:
            if len(lost_identity) >= 3:
                return "replacement"
            return "reset"

        if event_type in ("update", "deploy", "restart"):
            return "maintenance"

        if event_type in ("pause", "hibernate", "sleep"):
            return "pause"

        return "maintenance"


# Singleton
_continuity_manager: Optional[ContinuityManager] = None


def get_continuity_manager() -> ContinuityManager:
    global _continuity_manager
    if _continuity_manager is None:
        _continuity_manager = ContinuityManager()
    return _continuity_manager
