"""
PSILO — application-layer neuroplasticity protocol (Mar 17, 2026).

Carried over Mycorrhizae-style JSON channels; normalized into ExperiencePacket extensions.
Does not alter MDP/MMP/HPL transport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class PsiloEventType(str, Enum):
    SESSION_START = "psilo.session.start"
    SESSION_TICK = "psilo.session.tick"
    EDGE_ADD = "psilo.edge.add"
    EDGE_EXPIRE = "psilo.edge.expire"
    SYNESTHESIA_INJECT = "psilo.synesthesia.inject"
    METRICS = "psilo.metrics"
    INTEGRATION_REPORT = "psilo.integration.report"
    SESSION_STOP = "psilo.session.stop"


@dataclass
class PsiloEnvelope:
    """
    Application envelope for PSILO events (Mycorrhizae-compatible metadata).
    """

    event_type: str
    session_id: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol": "psilo",
            "version": 1,
            "event_type": self.event_type,
            "session_id": self.session_id,
            "ts": self.ts,
            "trace_id": self.trace_id,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Optional["PsiloEnvelope"]:
        if d.get("protocol") != "psilo" or not d.get("event_type") or not d.get("session_id"):
            return None
        return cls(
            event_type=str(d["event_type"]),
            session_id=str(d["session_id"]),
            ts=str(d.get("ts") or datetime.now(timezone.utc).isoformat()),
            trace_id=d.get("trace_id"),
            payload=dict(d.get("payload") or {}),
        )


def psilo_payload_for_experience_packet(envelope: PsiloEnvelope) -> Dict[str, Any]:
    """Slice of cognition state to merge into ExperiencePacket.metadata or world_state."""
    return {
        "psilo": {
            "event_type": envelope.event_type,
            "session_id": envelope.session_id,
            "payload": envelope.payload,
        }
    }


def merge_psilo_into_packet_metadata(
    existing: Optional[Dict[str, Any]], envelope: PsiloEnvelope
) -> Dict[str, Any]:
    out = dict(existing or {})
    pl = out.get("plasticity") if isinstance(out.get("plasticity"), dict) else {}
    psilo_list = list(pl.get("psilo_events") or [])
    psilo_list.append(envelope.to_dict())
    pl = {**pl, "psilo_events": psilo_list[-50:]}
    out["plasticity"] = pl
    return out
