"""Serving profile CRUD and lifecycle management.

Manages versioned serving configurations for model builds. Profiles move through:
    draft → calibrating → ready → shadow → canary → active → retired

Date: 2026-03-21
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .schemas import (
    CacheMode,
    ServingProfile,
    ServingProfileCreate,
    TargetStack,
)

logger = logging.getLogger(__name__)

# In-memory store — production uses MINDEX Postgres
_profiles: dict[UUID, ServingProfile] = {}

VALID_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["calibrating", "ready"],
    "calibrating": ["ready", "draft"],
    "ready": ["shadow"],
    "shadow": ["canary", "retired"],
    "canary": ["active", "retired"],
    "active": ["retired"],
    "retired": [],
}


class ProfileManager:
    """CRUD operations for serving profiles."""

    def create_profile(self, request: ServingProfileCreate) -> ServingProfile:
        """Create a new serving profile in draft status."""
        profile = ServingProfile(
            **request.model_dump(),
            serving_profile_id=uuid4(),
            status="draft",
            created_at=datetime.utcnow(),
        )
        _profiles[profile.serving_profile_id] = profile
        logger.info(
            "Created serving profile %s for model %s (cache_mode=%s, stack=%s)",
            profile.serving_profile_id,
            profile.model_build_id,
            profile.cache_mode.value,
            profile.target_stack.value,
        )
        return profile

    def get_profile(self, profile_id: UUID) -> Optional[ServingProfile]:
        """Get a serving profile by ID."""
        return _profiles.get(profile_id)

    def list_profiles(
        self,
        model_build_id: Optional[UUID] = None,
        status: Optional[str] = None,
        cache_mode: Optional[CacheMode] = None,
    ) -> list[ServingProfile]:
        """List serving profiles with optional filters."""
        results = list(_profiles.values())
        if model_build_id:
            results = [p for p in results if p.model_build_id == model_build_id]
        if status:
            results = [p for p in results if p.status == status]
        if cache_mode:
            results = [p for p in results if p.cache_mode == cache_mode]
        return sorted(results, key=lambda p: p.created_at, reverse=True)

    def update_status(self, profile_id: UUID, new_status: str) -> ServingProfile:
        """Transition a profile to a new status.

        Raises:
            KeyError: If profile not found.
            ValueError: If transition is not valid.
        """
        profile = _profiles.get(profile_id)
        if not profile:
            raise KeyError(f"Serving profile {profile_id} not found")

        valid_next = VALID_STATUS_TRANSITIONS.get(profile.status, [])
        if new_status not in valid_next:
            raise ValueError(
                f"Cannot transition from '{profile.status}' to '{new_status}'. "
                f"Valid transitions: {valid_next}"
            )

        old_status = profile.status
        profile.status = new_status
        _profiles[profile_id] = profile

        logger.info(
            "Profile %s: %s → %s",
            profile_id,
            old_status,
            new_status,
        )
        return profile

    def link_artifact(self, profile_id: UUID, artifact_id: UUID) -> ServingProfile:
        """Link a KVTC artifact to a serving profile."""
        profile = _profiles.get(profile_id)
        if not profile:
            raise KeyError(f"Serving profile {profile_id} not found")

        profile.artifact_ref = artifact_id
        _profiles[profile_id] = profile
        logger.info("Profile %s linked to artifact %s", profile_id, artifact_id)
        return profile

    def delete_profile(self, profile_id: UUID) -> bool:
        """Delete a profile (only if in draft status)."""
        profile = _profiles.get(profile_id)
        if not profile:
            return False
        if profile.status != "draft":
            raise ValueError(
                f"Cannot delete profile in '{profile.status}' status. Only draft profiles can be deleted."
            )
        del _profiles[profile_id]
        logger.info("Deleted profile %s", profile_id)
        return True


# Module-level singleton
_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Get or create the profile manager singleton."""
    global _manager
    if _manager is None:
        _manager = ProfileManager()
    return _manager
