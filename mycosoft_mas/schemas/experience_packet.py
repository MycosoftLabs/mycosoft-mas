"""
Experience Packet (EP) schema - the irreducible unit of cognition.

Every input (text/voice/sensor) entering MYCA's pipeline must be wrapped in an EP.
No text or sensor input enters without being wrapped.

Created: February 17, 2026
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ObservationModality(Enum):
    """Input modality types."""

    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    BIOELECTRIC = "bioelectric"
    VOC = "voc"
    SENSOR = "sensor"
    LOG = "log"
    OTHER = "other"


@dataclass
class Geo:
    """Geolocation with accuracy."""

    lat: float
    lon: float
    alt: Optional[float] = None
    accuracy_m: Optional[float] = None


@dataclass
class GroundTruth:
    """Temporal and spatial grounding of the input."""

    monotonic_ts: float = field(default_factory=time.monotonic)
    wall_ts_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    geo: Optional[Geo] = None
    frame: Optional[str] = None
    device_id: Optional[str] = None
    sensor_id: Optional[str] = None
    # Phase 2: H3 index (set by spatial_enrich)
    h3_index: Optional[str] = None


@dataclass
class SelfState:
    """Snapshot of MYCA's internal state at input time."""

    snapshot_ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    services: Dict[str, Any] = field(default_factory=dict)
    agents: Dict[str, Any] = field(default_factory=dict)
    active_plans: List[str] = field(default_factory=list)
    safety_mode: Optional[str] = None
    memory_indices: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldStateRef:
    """Reference to world state snapshot (CREP, Earth2, etc.)."""

    snapshot_ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sources: List[str] = field(default_factory=list)
    freshness: str = "unknown"
    summary: Optional[str] = None
    nlm_prediction: Optional[Dict[str, Any]] = None


@dataclass
class Observation:
    """The raw observation (input signal)."""

    modality: ObservationModality = ObservationModality.TEXT
    raw_payload: Optional[str] = None
    derived_features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Uncertainty:
    """Missingness flags and confidence estimates."""

    missingness: Dict[str, Any] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    sensor_noise: Dict[str, float] = field(default_factory=dict)


@dataclass
class Provenance:
    """Chain-of-custody and cryptographic hash."""

    sha256_hash: Optional[str] = None
    upstream_ids: List[str] = field(default_factory=list)
    signer: Optional[str] = None


@dataclass
class ExperiencePacket:
    """Complete Experience Packet - all inputs wrapped in this."""

    id: str = field(default_factory=lambda: f"ep_{uuid.uuid4().hex[:16]}")
    ground_truth: GroundTruth = field(default_factory=GroundTruth)
    self_state: Optional[SelfState] = None
    world_state: Optional[WorldStateRef] = None
    observation: Observation = field(default_factory=Observation)
    uncertainty: Uncertainty = field(default_factory=Uncertainty)
    provenance: Provenance = field(default_factory=Provenance)
    # Phase 2: Event/episode tracking
    event_boundary: bool = False
    episode_id: Optional[str] = None
