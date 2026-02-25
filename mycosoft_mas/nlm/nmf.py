"""
NLM Nature Message Frame (NMF)

Packetized output format for NLM translation layer. Combines bio-tokens,
structured semantic data, and telemetry envelopes into a unified frame.

Created: February 25, 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from mycosoft_mas.nlm.telemetry_envelopes import TelemetryEnvelope


@dataclass
class NatureMessageFrame:
    """
    Nature Message Frame (NMF) - packetized output for NLM worldview.

    Combines:
    - bio_tokens: Micro-speak tokens from translation
    - structured_output: Normalized semantic data
    - envelopes: Associated telemetry envelopes (ETA, ESI, BAR, RER, EEW)
    """

    frame_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    bio_tokens: List[str] = field(default_factory=list)
    structured_output: Dict[str, Any] = field(default_factory=dict)
    envelopes: List[Any] = field(default_factory=list)  # List[TelemetryEnvelope]
    context: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (envelopes serialized via to_dict)."""
        return {
            "frame_id": str(self.frame_id),
            "timestamp": self.timestamp.isoformat(),
            "bio_tokens": self.bio_tokens,
            "structured_output": self.structured_output,
            "envelopes": [
                e.to_dict() if hasattr(e, "to_dict") else e for e in self.envelopes
            ],
            "context": self.context,
            "confidence": self.confidence,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NatureMessageFrame":
        """Create from dictionary."""
        from mycosoft_mas.nlm.telemetry_envelopes import TelemetryEnvelope

        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        elif ts is None:
            ts = datetime.now(timezone.utc)
        fid = data.get("frame_id")
        if isinstance(fid, str):
            fid = UUID(fid)
        elif fid is None:
            fid = uuid4()
        envelopes = data.get("envelopes", [])
        parsed = []
        for e in envelopes:
            if isinstance(e, dict):
                parsed.append(TelemetryEnvelope.from_dict(e))
            else:
                parsed.append(e)
        return cls(
            frame_id=fid,
            timestamp=ts,
            bio_tokens=data.get("bio_tokens", []),
            structured_output=data.get("structured_output", {}),
            envelopes=parsed,
            context=data.get("context", {}),
            confidence=float(data.get("confidence", 1.0)),
            source_id=data.get("source_id", ""),
        )
