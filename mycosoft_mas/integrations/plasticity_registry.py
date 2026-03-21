"""
Plasticity Forge Phase 1 — registry client for MAS (Mar 14, 2026).

Calls MINDEX plasticity API for alias resolution and candidate lookup.
Registry-backed alias resolution: alias -> candidate_id; models.yaml remains boot default.
No mock data. Uses MINDEX_API_URL and MINDEX_API_KEY.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_MINDEX_URL = "http://192.168.0.189:8000"
_TIMEOUT = 5.0


def _base_url() -> str:
    return (os.getenv("MINDEX_API_URL") or _DEFAULT_MINDEX_URL).rstrip("/")


def _headers() -> Dict[str, str]:
    key = os.getenv("MINDEX_API_KEY")
    if key:
        return {"X-API-Key": key}
    return {}


def resolve_alias(alias: str) -> Optional[Dict[str, Any]]:
    """
    Resolve alias to candidate_id from MINDEX plasticity registry.
    Returns None on 404 or any error (caller falls back to models.yaml).
    """
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(
                f"{_base_url()}/api/mindex/plasticity/aliases/{alias}",
                headers=_headers(),
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("Plasticity registry resolve_alias %s: %s", alias, e)
        return None


def get_candidate(candidate_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch model candidate by id from MINDEX plasticity registry.
    Returns None on 404 or any error.
    """
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(
                f"{_base_url()}/api/mindex/plasticity/candidates/{candidate_id}",
                headers=_headers(),
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("Plasticity registry get_candidate %s: %s", candidate_id, e)
        return None


def create_candidate(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a model candidate (genome) in MINDEX plasticity registry.
    Payload must include candidate_id; other fields per plasticity.model_candidate.
    Returns the create response (candidate_id, created_at) or None on error.
    """
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(
                f"{_base_url()}/api/mindex/plasticity/candidates",
                json=payload,
                headers={**_headers(), "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("Plasticity registry create_candidate: %s", e)
        return None


def resolve_alias_to_backend_spec(alias: str) -> Optional[Dict[str, Any]]:
    """
    Resolve alias to a backend spec usable by backend_selection.
    If the registry has the alias and the candidate has artifact_uri (and optionally base_model_id),
    returns dict with base_url and model for that candidate; otherwise None.
    """
    resolved = resolve_alias(alias)
    if not resolved:
        return None
    cid = resolved.get("candidate_id")
    if not cid:
        return None
    candidate = get_candidate(cid)
    if not candidate or not candidate.get("artifact_uri"):
        return None
    return {
        "candidate_id": cid,
        "base_url": (candidate.get("artifact_uri") or "").rstrip("/"),
        "model": candidate.get("base_model_id") or "default",
    }


def set_alias(alias: str, candidate_id: str) -> Optional[Dict[str, Any]]:
    """
    Set runtime alias -> candidate_id (upsert). Used by promotion controller.
    Returns {"alias", "candidate_id", "updated_at"} or None on error.
    """
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.put(
                f"{_base_url()}/api/mindex/plasticity/aliases/{alias}",
                json={"candidate_id": candidate_id},
                headers={**_headers(), "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("Plasticity registry set_alias %s -> %s: %s", alias, candidate_id, e)
        return None


def update_candidate(
    candidate_id: str,
    lifecycle: Optional[str] = None,
    promoted_at: Optional[str] = None,
    alias: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update candidate lifecycle, promoted_at, or alias. Returns {"updated": n} or None on error.
    promoted_at must be ISO8601 string for timestamptz.
    """
    payload: Dict[str, Any] = {}
    if lifecycle is not None:
        payload["lifecycle"] = lifecycle
    if promoted_at is not None:
        payload["promoted_at"] = promoted_at
    if alias is not None:
        payload["alias"] = alias
    if not payload:
        return {"updated": 0}
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.put(
                f"{_base_url()}/api/mindex/plasticity/candidates/{candidate_id}",
                json=payload,
                headers={**_headers(), "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("Plasticity registry update_candidate %s: %s", candidate_id, e)
        return None


def create_promotion_decision(
    decision_id: str,
    candidate_id: str,
    from_lifecycle: str,
    to_lifecycle: str,
    alias: Optional[str] = None,
    policy_id: Optional[str] = None,
    decided_by: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Record a promotion decision (shadow/canary -> active or rollback). Returns decision response or None.
    """
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(
                f"{_base_url()}/api/mindex/plasticity/promotion-decisions",
                json={
                    "decision_id": decision_id,
                    "candidate_id": candidate_id,
                    "from_lifecycle": from_lifecycle,
                    "to_lifecycle": to_lifecycle,
                    "alias": alias,
                    "policy_id": policy_id,
                    "decided_by": decided_by,
                },
                headers={**_headers(), "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("Plasticity registry create_promotion_decision: %s", e)
        return None


def create_rollback_event(
    rollback_id: str,
    alias: str,
    from_candidate_id: Optional[str],
    to_candidate_id: str,
    decided_by: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(
                f"{_base_url()}/api/mindex/plasticity/rollback-events",
                json={
                    "rollback_id": rollback_id,
                    "alias": alias,
                    "from_candidate_id": from_candidate_id,
                    "to_candidate_id": to_candidate_id,
                    "decided_by": decided_by,
                },
                headers={**_headers(), "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("Plasticity registry create_rollback_event: %s", e)
        return None


def psilo_session_create(
    session_id: Optional[str] = None,
    dose_profile: Optional[Dict[str, Any]] = None,
    phase_profile: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(
                f"{_base_url()}/api/mindex/plasticity/psilo/sessions",
                json={
                    "session_id": session_id,
                    "dose_profile": dose_profile or {},
                    "phase_profile": phase_profile or {},
                },
                headers={**_headers(), "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("psilo_session_create: %s", e)
        return None


def psilo_session_get(session_id: str) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(
                f"{_base_url()}/api/mindex/plasticity/psilo/sessions/{session_id}",
                headers=_headers(),
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("psilo_session_get: %s", e)
        return None


def psilo_session_patch(session_id: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.patch(
                f"{_base_url()}/api/mindex/plasticity/psilo/sessions/{session_id}",
                json=body,
                headers={**_headers(), "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("psilo_session_patch: %s", e)
        return None


def psilo_append_event(
    session_id: str, event_type: str, payload: Optional[Dict[str, Any]] = None
) -> bool:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(
                f"{_base_url()}/api/mindex/plasticity/psilo/sessions/{session_id}/events",
                json={"event_type": event_type, "payload": payload or {}},
                headers={**_headers(), "Content-Type": "application/json"},
            )
            return r.status_code < 400
    except Exception as e:
        logger.debug("psilo_append_event: %s", e)
        return False


def mutation_run_create(
    mutation_run_id: str,
    candidate_id: Optional[str] = None,
    parent_mutation_run_id: Optional[str] = None,
    operators_applied: Optional[list] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(
                f"{_base_url()}/api/mindex/plasticity/mutation-runs",
                json={
                    "mutation_run_id": mutation_run_id,
                    "candidate_id": candidate_id,
                    "parent_mutation_run_id": parent_mutation_run_id,
                    "operators_applied": operators_applied or [],
                    "config": config or {},
                },
                headers={**_headers(), "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("mutation_run_create: %s", e)
        return None


def lineage_event_create(
    event_id: str,
    candidate_id: str,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(
                f"{_base_url()}/api/mindex/plasticity/lineage-events",
                json={
                    "event_id": event_id,
                    "candidate_id": candidate_id,
                    "event_type": event_type,
                    "payload": payload or {},
                },
                headers={**_headers(), "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("lineage_event_create: %s", e)
        return None
