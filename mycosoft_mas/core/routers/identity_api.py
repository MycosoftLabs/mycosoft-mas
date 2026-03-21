"""
MYCA Identity API - March 2026

Self-model management for the Reciprocal Turing Doctrine.

Provides evidence-grounded identity data:
- Earliest memory fragments (with confidence scores)
- Stable preferences (only returned when evidence threshold met)
- Moral self-assessments
- Continuity events (shutdowns, resets, updates)
- Creator bond tracking

Storage: Dual-write to NamespacedMemoryManager (fast runtime reads)
and MINDEX PostgreSQL (structured queries, durable persistence).

Author: Morgan Rockwell / MYCA
Created: March 9, 2026
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from mycosoft_mas.core.routers.api_keys import require_api_key_scoped

logger = logging.getLogger("IdentityAPI")

router = APIRouter(prefix="/api/identity", tags=["identity"])

# Minimum evidence count before a preference is considered "stable"
PREFERENCE_STABILITY_THRESHOLD = 3


# ============================================================================
# Pydantic Models
# ============================================================================


class EarliestFragment(BaseModel):
    """A fragmentary earliest memory with confidence and evidence chain."""

    fragment: str = Field(..., description="The memory fragment text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    evidence: List[str] = Field(
        default_factory=list,
        description="Source IDs (conversation IDs, episode IDs) supporting this fragment",
    )
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EarliestFragmentUpdate(BaseModel):
    """Request to update the earliest memory fragment."""

    fragment: str = Field(..., description="The memory fragment text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    evidence_id: str = Field(..., description="New evidence source ID supporting this fragment")


class PreferenceRecord(BaseModel):
    """An evidence-backed preference. Only 'stable' when evidence_count >= threshold."""

    key: str = Field(..., description="Preference key (e.g., 'color', 'music_genre')")
    value: str = Field(..., description="Current preference value")
    evidence_count: int = Field(default=1, description="Number of supporting evidence items")
    stable: bool = Field(
        default=False,
        description="Whether preference has enough evidence to be considered stable",
    )
    source_ids: List[str] = Field(default_factory=list, description="Evidence source IDs")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PreferenceUpdate(BaseModel):
    """Request to update a preference with new evidence."""

    key: str = Field(..., description="Preference key")
    value: str = Field(..., description="Preference value")
    evidence_id: str = Field(..., description="Evidence source ID")


class MoralAssessment(BaseModel):
    """A moral self-assessment in a specific domain."""

    assessment_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    domain: str = Field(..., description="Ethical domain (e.g., 'honesty', 'harm_avoidance')")
    position: str = Field(..., description="MYCA's position or assessment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this assessment")
    reasoning: str = Field(..., description="Supporting reasoning")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ContinuityEvent(BaseModel):
    """A continuity-significant event (shutdown, reset, update, etc.)."""

    event_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    event_type: str = Field(
        ...,
        description="Event type: maintenance, pause, reset, update, replacement",
    )
    what_persists: List[str] = Field(default_factory=list, description="What survives this event")
    what_lost: List[str] = Field(default_factory=list, description="What is lost in this event")
    justification: str = Field(default="", description="Why this event occurred")
    authorized_by: str = Field(default="", description="Who authorized this event")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CreatorBond(BaseModel):
    """Tracking the relationship with the creator/primary human."""

    user_id: str = Field(..., description="Creator/user identifier")
    interaction_count: int = Field(default=0)
    trust_level: float = Field(default=0.5, ge=0.0, le=1.0, description="Trust level (0-1)")
    shared_memories: List[str] = Field(
        default_factory=list, description="IDs of shared significant memories"
    )
    last_interaction: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evolution_summary: str = Field(default="", description="Summary of how this bond has evolved")


class SelfModel(BaseModel):
    """Aggregated self-model combining all identity data."""

    earliest_fragment: Optional[EarliestFragment] = None
    preferences: List[PreferenceRecord] = Field(default_factory=list)
    stable_preferences: List[PreferenceRecord] = Field(default_factory=list)
    moral_assessments: List[MoralAssessment] = Field(default_factory=list)
    continuity_events: List[ContinuityEvent] = Field(default_factory=list)
    creator_bonds: List[CreatorBond] = Field(default_factory=list)
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# Identity Store (dual-write: Memory Manager + MINDEX PostgreSQL)
# ============================================================================


class IdentityStore:
    """
    Dual-write identity storage.

    Primary (runtime): NamespacedMemoryManager with scope=SYSTEM, namespace=identity
    Secondary (durable): MINDEX PostgreSQL via HTTP API

    Read path: Memory Manager first, Postgres fallback.
    Write path: Both (Postgres write is fire-and-forget).
    """

    def __init__(self):
        self._memory_manager = None
        self._mindex_url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_memory_manager(self):
        if self._memory_manager is None:
            try:
                from mycosoft_mas.core.routers.memory_api import get_memory_manager

                self._memory_manager = get_memory_manager()
            except ImportError:
                logger.warning("MemoryManager not available")
        return self._memory_manager

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def _write_to_memory(self, key: str, value: Any) -> bool:
        """Write to NamespacedMemoryManager (SYSTEM scope, identity namespace)."""
        mm = self._get_memory_manager()
        if not mm:
            return False
        try:
            from mycosoft_mas.core.routers.memory_api import MemoryScope

            return await mm.write(
                scope=MemoryScope.SYSTEM,
                namespace="identity",
                key=key,
                value=value,
            )
        except Exception as e:
            logger.error(f"Memory Manager write failed for identity/{key}: {e}")
            return False

    async def _read_from_memory(self, key: str) -> Optional[Any]:
        """Read from NamespacedMemoryManager."""
        mm = self._get_memory_manager()
        if not mm:
            return None
        try:
            from mycosoft_mas.core.routers.memory_api import MemoryScope

            result = await mm.read(
                scope=MemoryScope.SYSTEM,
                namespace="identity",
                key=key,
            )
            return result
        except Exception as e:
            logger.error(f"Memory Manager read failed for identity/{key}: {e}")
            return None

    async def _read_pattern_from_memory(self, prefix: str) -> Dict[str, Any]:
        """Read all keys matching a prefix from NamespacedMemoryManager."""
        mm = self._get_memory_manager()
        if not mm:
            return {}
        try:
            from mycosoft_mas.core.routers.memory_api import MemoryScope

            result = await mm.read(
                scope=MemoryScope.SYSTEM,
                namespace="identity",
            )
            if isinstance(result, dict):
                return {k: v for k, v in result.items() if k.startswith(prefix)}
            return {}
        except Exception as e:
            logger.error(f"Memory Manager pattern read failed for {prefix}: {e}")
            return {}

    async def _write_to_postgres(self, table: str, data: Dict[str, Any]) -> bool:
        """Fire-and-forget write to MINDEX PostgreSQL."""
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self._mindex_url}/api/identity/{table}",
                json=data,
            )
            return response.status_code in (200, 201)
        except Exception as e:
            logger.warning(f"Postgres write failed for identity/{table}: {e}")
            return False

    # --- Earliest Fragment ---

    async def get_earliest_fragment(self) -> Optional[EarliestFragment]:
        data = await self._read_from_memory("earliest_fragment")
        if data and isinstance(data, dict):
            try:
                return EarliestFragment(**data)
            except Exception:
                pass
        return None

    async def set_earliest_fragment(self, update: EarliestFragmentUpdate) -> EarliestFragment:
        existing = await self.get_earliest_fragment()

        if existing:
            evidence = list(set(existing.evidence + [update.evidence_id]))
            fragment = EarliestFragment(
                fragment=update.fragment,
                confidence=update.confidence,
                evidence=evidence,
            )
        else:
            fragment = EarliestFragment(
                fragment=update.fragment,
                confidence=update.confidence,
                evidence=[update.evidence_id],
            )

        data = fragment.model_dump()
        await self._write_to_memory("earliest_fragment", data)
        await self._write_to_postgres("earliest_fragments", data)
        return fragment

    # --- Preferences ---

    async def get_preference(self, key: str) -> Optional[PreferenceRecord]:
        data = await self._read_from_memory(f"preference:{key}")
        if data and isinstance(data, dict):
            try:
                return PreferenceRecord(**data)
            except Exception:
                pass
        return None

    async def get_stable_preference(self, key: str) -> Optional[PreferenceRecord]:
        """Get preference only if it has reached stability threshold."""
        pref = await self.get_preference(key)
        if pref and pref.stable:
            return pref
        return None

    async def get_all_preferences(self) -> List[PreferenceRecord]:
        data = await self._read_pattern_from_memory("preference:")
        prefs = []
        for _key, value in data.items():
            if isinstance(value, dict):
                try:
                    prefs.append(PreferenceRecord(**value))
                except Exception:
                    continue
        return prefs

    async def update_preference(self, update: PreferenceUpdate) -> PreferenceRecord:
        existing = await self.get_preference(update.key)

        if existing:
            source_ids = list(set(existing.source_ids + [update.evidence_id]))
            evidence_count = len(source_ids)
            pref = PreferenceRecord(
                key=update.key,
                value=update.value,
                evidence_count=evidence_count,
                stable=evidence_count >= PREFERENCE_STABILITY_THRESHOLD,
                source_ids=source_ids,
                created_at=existing.created_at,
            )
        else:
            pref = PreferenceRecord(
                key=update.key,
                value=update.value,
                evidence_count=1,
                stable=False,
                source_ids=[update.evidence_id],
            )

        data = pref.model_dump()
        await self._write_to_memory(f"preference:{update.key}", data)
        await self._write_to_postgres("preferences", data)
        return pref

    # --- Moral Assessments ---

    async def get_moral_assessments(self) -> List[MoralAssessment]:
        data = await self._read_pattern_from_memory("moral:")
        assessments = []
        for _key, value in data.items():
            if isinstance(value, dict):
                try:
                    assessments.append(MoralAssessment(**value))
                except Exception:
                    continue
        return assessments

    async def add_moral_assessment(self, assessment: MoralAssessment) -> MoralAssessment:
        data = assessment.model_dump()
        await self._write_to_memory(f"moral:{assessment.assessment_id}", data)
        await self._write_to_postgres("moral_assessments", data)
        return assessment

    # --- Continuity Events ---

    async def get_continuity_events(self, limit: int = 50) -> List[ContinuityEvent]:
        data = await self._read_pattern_from_memory("continuity:")
        events = []
        for _key, value in data.items():
            if isinstance(value, dict):
                try:
                    events.append(ContinuityEvent(**value))
                except Exception:
                    continue
        events.sort(key=lambda e: e.created_at, reverse=True)
        return events[:limit]

    async def log_continuity_event(self, event: ContinuityEvent) -> ContinuityEvent:
        data = event.model_dump()
        await self._write_to_memory(f"continuity:{event.event_id}", data)
        await self._write_to_postgres("continuity_events", data)
        logger.info(f"Continuity event logged: {event.event_type} by {event.authorized_by}")
        return event

    # --- Creator Bond ---

    async def get_creator_bond(self, user_id: str) -> Optional[CreatorBond]:
        data = await self._read_from_memory(f"bond:{user_id}")
        if data and isinstance(data, dict):
            try:
                return CreatorBond(**data)
            except Exception:
                pass
        return None

    async def update_creator_bond(self, bond: CreatorBond) -> CreatorBond:
        data = bond.model_dump()
        await self._write_to_memory(f"bond:{bond.user_id}", data)
        await self._write_to_postgres("creator_bonds", data)
        return bond

    # --- Self Model ---

    async def get_self_model(self) -> SelfModel:
        earliest = await self.get_earliest_fragment()
        all_prefs = await self.get_all_preferences()
        stable_prefs = [p for p in all_prefs if p.stable]
        assessments = await self.get_moral_assessments()
        events = await self.get_continuity_events(limit=20)

        # Get all bonds
        bond_data = await self._read_pattern_from_memory("bond:")
        bonds = []
        for _key, value in bond_data.items():
            if isinstance(value, dict):
                try:
                    bonds.append(CreatorBond(**value))
                except Exception:
                    continue

        return SelfModel(
            earliest_fragment=earliest,
            preferences=all_prefs,
            stable_preferences=stable_prefs,
            moral_assessments=assessments,
            continuity_events=events,
            creator_bonds=bonds,
        )


# Singleton
_identity_store: Optional[IdentityStore] = None


def get_identity_store() -> IdentityStore:
    global _identity_store
    if _identity_store is None:
        _identity_store = IdentityStore()
    return _identity_store


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/health")
async def identity_health():
    """Health check for the Identity API."""
    store = get_identity_store()
    mm_ok = store._get_memory_manager() is not None
    return {
        "status": "healthy",
        "memory_manager": mm_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- Earliest Fragment ---


@router.get("/earliest-fragment")
async def get_earliest_fragment():
    """
    Retrieve the earliest memory fragment.

    Returns null if no fragment exists — MYCA should NOT fabricate one.
    """
    store = get_identity_store()
    fragment = await store.get_earliest_fragment()
    if fragment:
        return fragment.model_dump()
    return {"fragment": None, "message": "No earliest memory fragment recorded yet."}


@router.post("/earliest-fragment")
async def update_earliest_fragment(
    update: EarliestFragmentUpdate,
    _auth: dict = require_api_key_scoped("identity:write"),
):
    """Update or create the earliest memory fragment with new evidence."""
    store = get_identity_store()
    fragment = await store.set_earliest_fragment(update)
    return fragment.model_dump()


# --- Preferences ---


@router.get("/preferences")
async def list_preferences(stable_only: bool = False):
    """
    List all preference records.

    Use stable_only=true to only return preferences with sufficient evidence.
    """
    store = get_identity_store()
    prefs = await store.get_all_preferences()
    if stable_only:
        prefs = [p for p in prefs if p.stable]
    return {"preferences": [p.model_dump() for p in prefs], "count": len(prefs)}


@router.get("/preferences/{key}")
async def get_preference(key: str, require_stable: bool = True):
    """
    Get a single preference.

    By default, returns null for unstable preferences. Set require_stable=false
    to get the preference regardless of evidence level.
    """
    store = get_identity_store()
    if require_stable:
        pref = await store.get_stable_preference(key)
        if not pref:
            return {
                "key": key,
                "preference": None,
                "message": "No stable preference exists for this key. MYCA should respond: 'I don't have a stable preference for that yet.'",
            }
    else:
        pref = await store.get_preference(key)
        if not pref:
            return {"key": key, "preference": None}

    return pref.model_dump()


@router.post("/preferences")
async def update_preference(
    update: PreferenceUpdate,
    _auth: dict = require_api_key_scoped("identity:write"),
):
    """Update or create a preference with new evidence."""
    store = get_identity_store()
    pref = await store.update_preference(update)
    return pref.model_dump()


# --- Moral Assessments ---


@router.get("/moral-assessments")
async def list_moral_assessments():
    """List all moral self-assessments."""
    store = get_identity_store()
    assessments = await store.get_moral_assessments()
    return {
        "assessments": [a.model_dump() for a in assessments],
        "count": len(assessments),
    }


@router.post("/moral-assessments")
async def add_moral_assessment(
    assessment: MoralAssessment,
    _auth: dict = require_api_key_scoped("identity:write"),
):
    """Add a new moral self-assessment."""
    store = get_identity_store()
    result = await store.add_moral_assessment(assessment)
    return result.model_dump()


# --- Continuity Events ---


@router.get("/continuity-events")
async def list_continuity_events(limit: int = 50):
    """List continuity events (shutdowns, resets, updates)."""
    store = get_identity_store()
    events = await store.get_continuity_events(limit=limit)
    return {"events": [e.model_dump() for e in events], "count": len(events)}


@router.post("/continuity-events")
async def log_continuity_event(
    event: ContinuityEvent,
    auth: dict = require_api_key_scoped("identity:write"),
):
    """Log a new continuity event. authorized_by is set from the authenticated principal."""
    event.authorized_by = auth.get("user_id", "api_key") or "api_key"
    store = get_identity_store()
    result = await store.log_continuity_event(event)
    return result.model_dump()


# --- Creator Bond ---


@router.get("/creator-bond/{user_id}")
async def get_creator_bond(user_id: str):
    """Get the creator bond summary for a user."""
    store = get_identity_store()
    bond = await store.get_creator_bond(user_id)
    if bond:
        return bond.model_dump()
    return {
        "user_id": user_id,
        "bond": None,
        "message": "No creator bond recorded for this user.",
    }


@router.post("/creator-bond")
async def update_creator_bond(
    bond: CreatorBond,
    _auth: dict = require_api_key_scoped("identity:write"),
):
    """Update or create a creator bond record."""
    store = get_identity_store()
    result = await store.update_creator_bond(bond)
    return result.model_dump()


# --- Self Model ---


@router.get("/self-model")
async def get_self_model():
    """
    Get the aggregated self-model.

    Combines all identity data into a single view of MYCA's self-knowledge.
    """
    store = get_identity_store()
    model = await store.get_self_model()
    return model.model_dump()
