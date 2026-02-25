"""
NLM Telemetry Envelopes - ETA, ESI, BAR, RER, EEW

Unified packetized telemetry envelope types for the MYCA Worldview.
Each envelope carries typed environmental, seismic, biological, resource,
and early-warning data from NLM and connected systems.

Created: February 25, 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class EnvelopeType(str, Enum):
    """NLM telemetry envelope types."""

    ETA = "ETA"  # Environmental Telemetry Aggregate
    ESI = "ESI"  # Earth Seismic Intelligence
    BAR = "BAR"  # Biological Activity Response
    RER = "RER"  # Resource Exchange Response
    EEW = "EEW"  # Earth Early Warning


DEFAULT_TTL_SECONDS = 3600


@dataclass
class TelemetryEnvelope:
    """
    Base telemetry envelope for NLM worldview data.

    All envelope types (ETA, ESI, BAR, RER, EEW) share this structure.
    """

    envelope_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    envelope_id: UUID = field(default_factory=uuid4)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "envelope_id": str(self.envelope_id),
            "envelope_type": self.envelope_type,
            "timestamp": self.timestamp.isoformat(),
            "source_id": self.source_id,
            "payload": self.payload,
            "confidence": self.confidence,
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelemetryEnvelope":
        """Create from dictionary."""
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        elif ts is None:
            ts = datetime.now(timezone.utc)
        eid = data.get("envelope_id")
        if isinstance(eid, str):
            eid = UUID(eid)
        elif eid is None:
            eid = uuid4()
        return cls(
            envelope_type=data.get("envelope_type", "ETA"),
            timestamp=ts,
            source_id=data.get("source_id", ""),
            payload=data.get("payload", {}),
            confidence=float(data.get("confidence", 1.0)),
            ttl_seconds=int(data.get("ttl_seconds", DEFAULT_TTL_SECONDS)),
            envelope_id=eid,
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# ETA - Environmental Telemetry Aggregate
# ---------------------------------------------------------------------------


def create_eta_envelope(
    source_id: str,
    temperature_c: Optional[float] = None,
    humidity_pct: Optional[float] = None,
    pressure_hpa: Optional[float] = None,
    co2_ppm: Optional[float] = None,
    voc_ppb: Optional[float] = None,
    light_lux: Optional[float] = None,
    location: Optional[Dict[str, float]] = None,
    confidence: float = 1.0,
) -> TelemetryEnvelope:
    """Create an ETA (Environmental Telemetry Aggregate) envelope."""
    payload: Dict[str, Any] = {}
    if temperature_c is not None:
        payload["temperature_c"] = temperature_c
    if humidity_pct is not None:
        payload["humidity_pct"] = humidity_pct
    if pressure_hpa is not None:
        payload["pressure_hpa"] = pressure_hpa
    if co2_ppm is not None:
        payload["co2_ppm"] = co2_ppm
    if voc_ppb is not None:
        payload["voc_ppb"] = voc_ppb
    if light_lux is not None:
        payload["light_lux"] = light_lux
    if location:
        payload["location"] = location
    return TelemetryEnvelope(
        envelope_type=EnvelopeType.ETA.value,
        source_id=source_id,
        payload=payload,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# ESI - Earth Seismic Intelligence
# ---------------------------------------------------------------------------


def create_esi_envelope(
    source_id: str,
    magnitude: Optional[float] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    depth_km: Optional[float] = None,
    event_time: Optional[datetime] = None,
    event_id: Optional[str] = None,
    usgs_data: Optional[Dict[str, Any]] = None,
    mwave_data: Optional[Dict[str, Any]] = None,
    confidence: float = 1.0,
) -> TelemetryEnvelope:
    """Create an ESI (Earth Seismic Intelligence) envelope."""
    payload: Dict[str, Any] = {}
    if magnitude is not None:
        payload["magnitude"] = magnitude
    if latitude is not None:
        payload["latitude"] = latitude
    if longitude is not None:
        payload["longitude"] = longitude
    if depth_km is not None:
        payload["depth_km"] = depth_km
    if event_time is not None:
        payload["event_time"] = event_time.isoformat()
    if event_id:
        payload["event_id"] = event_id
    if usgs_data:
        payload["usgs"] = usgs_data
    if mwave_data:
        payload["mwave"] = mwave_data
    return TelemetryEnvelope(
        envelope_type=EnvelopeType.ESI.value,
        source_id=source_id,
        payload=payload,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# BAR - Biological Activity Response
# ---------------------------------------------------------------------------


def create_bar_envelope(
    source_id: str,
    pattern_name: str,
    category: str = "",
    confidence: float = 1.0,
    bioelectric_channels: Optional[List[Dict[str, Any]]] = None,
    gfst_interpretation: Optional[Dict[str, Any]] = None,
    device_id: Optional[str] = None,
) -> TelemetryEnvelope:
    """Create a BAR (Biological Activity Response) envelope for FCI/GFST patterns."""
    payload: Dict[str, Any] = {
        "pattern_name": pattern_name,
        "category": category,
    }
    if bioelectric_channels:
        payload["bioelectric_channels"] = bioelectric_channels
    if gfst_interpretation:
        payload["gfst_interpretation"] = gfst_interpretation
    if device_id:
        payload["device_id"] = device_id
    return TelemetryEnvelope(
        envelope_type=EnvelopeType.BAR.value,
        source_id=source_id,
        payload=payload,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# RER - Resource Exchange Response
# ---------------------------------------------------------------------------


def create_rer_envelope(
    source_id: str,
    nutrient_flow: Optional[Dict[str, Any]] = None,
    substrate_conditions: Optional[Dict[str, Any]] = None,
    moisture_pct: Optional[float] = None,
    ph: Optional[float] = None,
    conductivity_us_cm: Optional[float] = None,
    confidence: float = 1.0,
) -> TelemetryEnvelope:
    """Create an RER (Resource Exchange Response) envelope."""
    payload: Dict[str, Any] = {}
    if nutrient_flow:
        payload["nutrient_flow"] = nutrient_flow
    if substrate_conditions:
        payload["substrate_conditions"] = substrate_conditions
    if moisture_pct is not None:
        payload["moisture_pct"] = moisture_pct
    if ph is not None:
        payload["ph"] = ph
    if conductivity_us_cm is not None:
        payload["conductivity_us_cm"] = conductivity_us_cm
    return TelemetryEnvelope(
        envelope_type=EnvelopeType.RER.value,
        source_id=source_id,
        payload=payload,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# EEW - Earth Early Warning
# ---------------------------------------------------------------------------


def create_eew_envelope(
    source_id: str,
    alert_type: str,
    severity: str = "moderate",
    message: str = "",
    predicted_time: Optional[datetime] = None,
    location: Optional[Dict[str, float]] = None,
    seismic_risk: Optional[Dict[str, Any]] = None,
    weather_risk: Optional[Dict[str, Any]] = None,
    spore_dispersal: Optional[Dict[str, Any]] = None,
    confidence: float = 1.0,
) -> TelemetryEnvelope:
    """Create an EEW (Earth Early Warning) envelope for predictive alerts."""
    payload: Dict[str, Any] = {
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
    }
    if predicted_time is not None:
        payload["predicted_time"] = predicted_time.isoformat()
    if location:
        payload["location"] = location
    if seismic_risk:
        payload["seismic_risk"] = seismic_risk
    if weather_risk:
        payload["weather_risk"] = weather_risk
    if spore_dispersal:
        payload["spore_dispersal"] = spore_dispersal
    return TelemetryEnvelope(
        envelope_type=EnvelopeType.EEW.value,
        source_id=source_id,
        payload=payload,
        confidence=confidence,
        ttl_seconds=300,  # Early warnings expire sooner
    )
