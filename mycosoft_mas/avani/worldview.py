"""AVANI WorldState and Worldview governance contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


INTERNAL_WORLDVIEW_DOMAINS = frozenset({"devices", "telemetry", "raw_telemetry", "device_commands"})
SENSITIVE_DOMAIN_HINTS = frozenset(
    {
        "military_installations",
        "fusarium_tracks",
        "fusarium_correlations",
        "crep_entities",
        "infrastructure",
        "power_grid",
        "water_systems",
        "internet_cables",
    }
)
ECOLOGICAL_DOMAIN_HINTS = frozenset(
    {
        "taxa",
        "species",
        "observations",
        "genetics",
        "buoys",
        "stream_gauges",
        "wildfires",
        "floods",
        "storms",
        "weather",
        "air_quality",
        "greenhouse_gas",
        "remote_sensing",
        "maritime",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _count_items(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        if isinstance(data.get("results"), list):
            return len(data["results"])
        if isinstance(data.get("items"), list):
            return len(data["items"])
        return 1
    return 1 if data is not None else 0


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _source_freshness(world: Dict[str, Any]) -> Dict[str, str]:
    sources: Dict[str, str] = {}
    for key, value in (world or {}).items():
        if isinstance(value, dict) and "freshness" in value:
            sources[key] = str(value.get("freshness") or "unknown")
    return sources


def classify_device_telemetry_trust(telemetry: Optional[Dict[str, Any]]) -> str:
    """Classify observed device telemetry before AVANI permits hardware actions."""
    if not telemetry:
        return "uncertain"
    status = str(telemetry.get("status") or telemetry.get("state") or "").lower()
    if status in {"offline", "lost", "unreachable"}:
        return "offline"
    if telemetry.get("compromised") or telemetry.get("tamper_detected"):
        return "compromised"
    observed_at = _parse_timestamp(
        telemetry.get("observed_at") or telemetry.get("timestamp") or telemetry.get("last_seen")
    )
    if observed_at is not None:
        age_seconds = (datetime.now(timezone.utc) - observed_at).total_seconds()
        if age_seconds > 3600:
            return "stale"
    drift = telemetry.get("drift_score")
    if isinstance(drift, (int, float)) and drift >= 0.35:
        return "drifting"
    confidence = telemetry.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < 0.5:
        return "uncertain"
    return "trusted"


@dataclass(frozen=True)
class AvaniWorldStateSnapshot:
    """A compact, audit-friendly reference to the current MAS WorldState."""

    worldstate_snapshot_id: str
    timestamp: str
    degraded: bool
    source_counts: Dict[str, int] = field(default_factory=dict)
    source_freshness: Dict[str, str] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worldstate_snapshot_id": self.worldstate_snapshot_id,
            "timestamp": self.timestamp,
            "degraded": self.degraded,
            "source_counts": self.source_counts,
            "source_freshness": self.source_freshness,
            "provenance": self.provenance,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class AvaniWorldviewFrame:
    """Governance frame attached to customer-facing Worldview responses."""

    worldview_request_id: str
    worldstate_snapshot_id: Optional[str]
    source_domains: List[str]
    region: Optional[Dict[str, Any]]
    time_window: Optional[Dict[str, Any]]
    freshness: str
    degraded: bool
    confidence: float
    provenance: Dict[str, Any]
    sensitivity: str
    ecological_risk: float
    avani_verdict: str
    governance_notes: List[str]
    audit_trail_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worldview_request_id": self.worldview_request_id,
            "worldstate_snapshot_id": self.worldstate_snapshot_id,
            "source_domains": self.source_domains,
            "region": self.region,
            "time_window": self.time_window,
            "freshness": self.freshness,
            "degraded": self.degraded,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "sensitivity": self.sensitivity,
            "ecological_risk": self.ecological_risk,
            "avani_verdict": self.avani_verdict,
            "governance_notes": self.governance_notes,
            "audit_trail_id": self.audit_trail_id,
        }


@dataclass(frozen=True)
class AvaniDeviceReview:
    device_id: str
    action: str
    operator_id: str
    telemetry_trust: str
    verdict: str
    approved: bool
    risk_tier: str
    ecological_risk: float
    reversibility: float
    human_review: bool
    rollback_required: bool
    confidence: float
    governance_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "action": self.action,
            "operator_id": self.operator_id,
            "telemetry_trust": self.telemetry_trust,
            "verdict": self.verdict,
            "approved": self.approved,
            "risk_tier": self.risk_tier,
            "ecological_risk": self.ecological_risk,
            "reversibility": self.reversibility,
            "human_review": self.human_review,
            "rollback_required": self.rollback_required,
            "confidence": self.confidence,
            "governance_notes": self.governance_notes,
        }


def build_worldstate_snapshot(world_payload: Dict[str, Any]) -> AvaniWorldStateSnapshot:
    """Build a stable, compact snapshot reference from MAS worldstate output."""
    world = world_payload.get("world") if isinstance(world_payload, dict) else {}
    world = world if isinstance(world, dict) else {}
    degraded = bool(world_payload.get("degraded", False)) if isinstance(world_payload, dict) else True
    source_counts = {
        "crep_flights": int((world.get("crep") or {}).get("flights") or 0),
        "crep_vessels": int((world.get("crep") or {}).get("vessels") or 0),
        "crep_satellites": int((world.get("crep") or {}).get("satellites") or 0),
        "active_devices": int((world.get("devices") or {}).get("active_count") or 0),
        "online_users": int((world.get("presence") or {}).get("online_users") or 0),
        "active_sessions": int((world.get("presence") or {}).get("active_sessions") or 0),
    }
    source_freshness = _source_freshness(world)
    unavailable = sum(1 for value in source_freshness.values() if value in {"unavailable", "stale"})
    confidence = 0.35 if degraded else max(0.45, 1.0 - unavailable * 0.1)
    snapshot_base = {
        "timestamp": world_payload.get("timestamp") if isinstance(world_payload, dict) else _utc_now(),
        "degraded": degraded,
        "source_counts": source_counts,
        "source_freshness": source_freshness,
        "world_hash": _canonical_hash(world),
    }
    return AvaniWorldStateSnapshot(
        worldstate_snapshot_id=f"worldstate-{_canonical_hash(snapshot_base)[:24]}",
        timestamp=str(snapshot_base["timestamp"] or _utc_now()),
        degraded=degraded,
        source_counts=source_counts,
        source_freshness=source_freshness,
        provenance={"source": "mas_worldstate", "world_hash": snapshot_base["world_hash"]},
        confidence=round(confidence, 3),
    )


def review_worldview_payload(
    *,
    worldview_request_id: str,
    data: Any,
    source_domains: List[str],
    caller: Optional[Dict[str, Any]] = None,
    region: Optional[Dict[str, Any]] = None,
    time_window: Optional[Dict[str, Any]] = None,
    worldstate_snapshot_id: Optional[str] = None,
    worldstate_degraded: bool = False,
) -> AvaniWorldviewFrame:
    """Evaluate a customer-facing Worldview response before release."""
    domains = [domain for domain in source_domains if domain]
    domain_set = set(domains)
    notes: List[str] = []
    sensitivity = "public"
    verdict = "allow"
    confidence = 0.94

    if domain_set & INTERNAL_WORLDVIEW_DOMAINS:
        sensitivity = "internal"
        verdict = "deny"
        confidence = 0.99
        notes.append("Internal telemetry/device domain requested; Worldview release denied.")
    elif domain_set & SENSITIVE_DOMAIN_HINTS:
        sensitivity = "sensitive"
        verdict = "allow_with_audit"
        notes.append("Sensitive infrastructure/security-adjacent domain released with audit metadata.")

    if worldstate_degraded:
        confidence = min(confidence, 0.55)
        notes.append("WorldState context is degraded or unavailable.")

    item_count = _count_items(data)
    ecological_risk = 0.0
    if domain_set & ECOLOGICAL_DOMAIN_HINTS:
        ecological_risk = min(0.8, 0.1 + (item_count / 1000.0))
        notes.append("Ecological domain reviewed for customer release.")
    if item_count > 1000:
        ecological_risk = min(1.0, ecological_risk + 0.1)
        notes.append("Large result set increases downstream misuse and interpretation risk.")

    if verdict != "deny" and ecological_risk >= 0.75:
        verdict = "allow_with_audit"

    if not notes:
        notes.append("Worldview response approved for read-only customer release.")

    freshness = "degraded" if worldstate_degraded else "current"
    provenance = {
        "source": "mindex_worldview",
        "caller_plan": (caller or {}).get("plan"),
        "caller_type": (caller or {}).get("user_type"),
        "result_count": item_count,
    }
    return AvaniWorldviewFrame(
        worldview_request_id=worldview_request_id,
        worldstate_snapshot_id=worldstate_snapshot_id,
        source_domains=domains,
        region=region,
        time_window=time_window,
        freshness=freshness,
        degraded=worldstate_degraded,
        confidence=round(confidence, 3),
        provenance=provenance,
        sensitivity=sensitivity,
        ecological_risk=round(ecological_risk, 3),
        avani_verdict=verdict,
        governance_notes=notes,
    )


def review_device_action(
    *,
    device_id: str,
    action: str,
    operator_id: str,
    telemetry: Optional[Dict[str, Any]] = None,
    ecological_impact: float = 0.0,
    reversibility: float = 1.0,
    rollback_plan: Optional[str] = None,
) -> AvaniDeviceReview:
    """Review hardware/device action safety before execution."""
    trust = classify_device_telemetry_trust(telemetry)
    normalized_action = (action or "").strip().lower()
    notes: List[str] = []
    risk_tier = "low"
    verdict = "allow"
    approved = True
    confidence = 0.9

    if normalized_action in {"deploy", "move", "activate", "dose", "release", "calibrate"}:
        risk_tier = "high"
        notes.append("Hardware command can change field state and requires AVANI preflight.")
    if ecological_impact >= 0.5 or reversibility <= 0.5:
        risk_tier = "high"
        notes.append("Ecological impact or reversibility requires heightened review.")
    if trust in {"compromised", "offline"}:
        verdict = "deny"
        approved = False
        confidence = 0.98
        notes.append(f"Device telemetry trust is {trust}; command fails closed.")
    elif trust in {"stale", "drifting", "uncertain"}:
        verdict = "require_approval"
        approved = False
        confidence = 0.75
        notes.append(f"Device telemetry trust is {trust}; human review required.")
    if not rollback_plan and (risk_tier == "high" or reversibility < 0.8):
        verdict = "require_approval"
        approved = False
        notes.append("Rollback plan required before hardware command execution.")
    if not operator_id:
        verdict = "require_approval"
        approved = False
        notes.append("Operator identity is required for device command audit.")
    if not notes:
        notes.append("Device action approved with trusted telemetry and bounded reversibility.")

    return AvaniDeviceReview(
        device_id=device_id,
        action=normalized_action or action,
        operator_id=operator_id or "unknown",
        telemetry_trust=trust,
        verdict=verdict,
        approved=approved,
        risk_tier=risk_tier,
        ecological_risk=round(max(0.0, min(1.0, ecological_impact)), 3),
        reversibility=round(max(0.0, min(1.0, reversibility)), 3),
        human_review=not approved,
        rollback_required=not bool(rollback_plan) and (risk_tier == "high" or reversibility < 0.8),
        confidence=confidence,
        governance_notes=notes,
    )
