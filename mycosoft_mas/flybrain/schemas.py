"""FlyBrain module contracts.

Pydantic models shared by the engine, encoders/decoders, plugs, vision,
navigation, the FastAPI router, the agent, and the website BFF.

Honesty rules (mirror ITDX / Fusarium):
- Nothing here is ever fabricated. A missing connectome, a missing detector
  or an unreachable device is reported as ``available=False`` / ``None`` /
  ``NOT_SUPPLIED`` and never painted as a result.
- ``BrainState`` rates are measured from simulated spikes of the FlyWire
  v783 connectome model (Shiu et al. 2024). They are simulation output,
  never a biological measurement, and are labelled ``origin="SIMULATED"``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "flybrain/v1"
ORIGIN_SIMULATED = "SIMULATED"

PlugName = Literal["standalone", "droid", "earthsim", "nlm", "itdx"]
BackendName = Literal["auto", "numpy", "torch"]
ObservationKind = Literal[
    "detections",
    "telemetry",
    "earthsim",
    "nlm",
    "itdx_slice",
    "raw_rates",
]
ChannelStatus = Literal["SCORED", "UNQUALIFIED", "NOT_SUPPLIED"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Atlas
# ---------------------------------------------------------------------------


class NeuronGroup(BaseModel):
    """A named population of FlyWire neurons."""

    name: str
    role: Literal["sensory", "motor", "interneuron", "custom"] = "custom"
    description: str = ""
    flywire_ids: List[int] = Field(default_factory=list)
    indices: List[int] = Field(default_factory=list)
    derived: bool = False
    missing_ids: List[int] = Field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.indices)


class AtlasSummary(BaseModel):
    schema_version: str = "flybrain.atlas/v1"
    source: Dict[str, Any] = Field(default_factory=dict)
    groups: List[Dict[str, Any]] = Field(default_factory=list)
    sensorimotor: Dict[str, Any] = Field(default_factory=dict)
    connectome_loaded: bool = False


# ---------------------------------------------------------------------------
# Stimulation
# ---------------------------------------------------------------------------


class StimulusCommand(BaseModel):
    """Drive (Poisson, ``rate_hz``) or silence a set of neurons."""

    group: Optional[str] = None
    flywire_ids: Optional[List[int]] = None
    rate_hz: float = Field(default=0.0, ge=0.0, le=2000.0)
    mode: Literal["poisson", "silence", "unsilence", "clear"] = "poisson"


# ---------------------------------------------------------------------------
# Observations (inputs)
# ---------------------------------------------------------------------------


class Observation(BaseModel):
    kind: ObservationKind
    payload: Dict[str, Any] = Field(default_factory=dict)
    t_ms: Optional[float] = None
    source: str = "api"


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------


class Taxon(BaseModel):
    taxon_id: Optional[str] = None
    scientific_name: Optional[str] = None
    rank: Optional[str] = None
    source: str = "mindex"
    matched: bool = False
    note: str = ""


class GeoPoint(BaseModel):
    lat: float
    lon: float


class Detection(BaseModel):
    id: str
    cls: str
    conf: float = Field(ge=0.0, le=1.0)
    bbox_xyxy: Tuple[float, float, float, float]
    bbox_norm: Optional[Tuple[float, float, float, float]] = None
    source: str = "image"
    track_id: Optional[str] = None
    category: str = "unknown"
    taxon: Optional[Taxon] = None
    bearing_deg: Optional[float] = None
    range_m: Optional[float] = None
    range_source: Optional[Literal["measured", "estimate"]] = None
    location: Optional[GeoPoint] = None
    perimeter: Optional[List[List[float]]] = None  # [[lon, lat], ...] closed ring
    pathway: Optional[List[List[float]]] = None  # [[lon, lat], ...] track history
    attributes: Dict[str, Any] = Field(default_factory=dict)


class DetectionFrame(BaseModel):
    schema_version: str = "flybrain.detection_frame/v1"
    t_ms: Optional[float] = None
    frame_w: Optional[int] = None
    frame_h: Optional[int] = None
    engine: Optional[str] = None
    model: Optional[str] = None
    device: Optional[str] = None
    sahi: bool = False
    slices: int = 0
    license: Optional[str] = None
    available: bool = True
    detections: List[Detection] = Field(default_factory=list)
    note: str = ""
    source: str = "image"


class VisionHealth(BaseModel):
    available: bool
    engine: Optional[str] = None
    model: Optional[str] = None
    weights_path: Optional[str] = None
    device: Optional[str] = None
    sahi: bool = False
    sahi_impl: Optional[str] = None
    remote_url: Optional[str] = None
    reason: str = ""


# ---------------------------------------------------------------------------
# Brain state and actions (outputs)
# ---------------------------------------------------------------------------


class BrainState(BaseModel):
    schema_version: str = SCHEMA_VERSION
    origin: str = ORIGIN_SIMULATED
    session_id: str
    t_ms: float
    step: int
    n_neurons: int
    n_active: int
    spike_count_window: int
    window_ms: float
    rates_hz: Dict[str, float] = Field(default_factory=dict)
    stimulated_hz: Dict[str, float] = Field(default_factory=dict)
    silenced: List[str] = Field(default_factory=list)
    backend: str
    realtime_ratio: Optional[float] = None
    subgraph: Optional[Dict[str, Any]] = None


class MotorAction(BaseModel):
    kind: Literal["locomotion", "attention", "none"] = "none"
    forward: float = Field(default=0.0, ge=-1.0, le=1.0)
    turn: float = Field(default=0.0, ge=-1.0, le=1.0)  # negative = left
    heading_delta_deg: float = 0.0
    throttle_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    target_bearing_deg: Optional[float] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    note: str = ""


class Waypoint(BaseModel):
    lat: float
    lon: float
    hold_seconds: int = 0
    note: str = ""


class NavPath(BaseModel):
    schema_version: str = "flybrain.nav_path/v1"
    start: Optional[GeoPoint] = None
    goal: Optional[GeoPoint] = None
    waypoints: List[Waypoint] = Field(default_factory=list)
    geojson: Optional[Dict[str, Any]] = None
    blocked_cells: int = 0
    total_cells: int = 0
    cost: Optional[float] = None
    feasible: bool = False
    turn_bias: float = 0.0
    note: str = ""


class ITDXChannelRow(BaseModel):
    """Same shape as ``itdx_api._channel`` rows."""

    status: ChannelStatus = "NOT_SUPPLIED"
    agent_id: Optional[str] = "flybrain"
    p: Optional[float] = None
    uncertainty: Optional[float] = None
    error: Optional[str] = None
    note: str = ""
    live: Dict[str, Any] = Field(default_factory=dict)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    reason: Optional[str] = None
    capability_class: Optional[str] = None
    sample_count: Optional[int] = None


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class SubgraphSpec(BaseModel):
    """Restrict the simulation to neurons near the atlas groups in use."""

    seed_groups: List[str] = Field(default_factory=list)
    hops: int = Field(default=2, ge=0, le=4)
    min_weight: float = Field(default=1.0, ge=0.0)
    max_neurons: int = Field(default=20000, ge=1)


class SessionConfig(BaseModel):
    plug: PlugName = "standalone"
    backend: BackendName = "auto"
    # Minimum 0.01 ms: together with the 5000 ms window ceiling this bounds a
    # single tick to 500_000 engine steps, so a request can never pin a worker
    # thread (and the session lock) for an unbounded number of steps.
    dt_ms: float = Field(default=0.1, ge=0.01, le=1.0)
    window_ms: float = Field(default=50.0, gt=0.0, le=5000.0)
    seed: Optional[int] = None
    subgraph: Optional[SubgraphSpec] = None
    dry_run: bool = True
    record: bool = True
    device_id: Optional[str] = None
    plug_config: Dict[str, Any] = Field(default_factory=dict)
    label: str = ""

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        return (value or "").strip()[:120]


class SessionInfo(BaseModel):
    schema_version: str = SCHEMA_VERSION
    session_id: str = Field(default_factory=lambda: f"fb-{uuid4().hex[:12]}")
    created_at: str = Field(default_factory=utc_now_iso)
    config: SessionConfig
    status: Literal["ready", "running", "stopped", "error"] = "ready"
    backend: str = "numpy"
    n_neurons: int = 0
    n_synapses: int = 0
    subgraph: Optional[Dict[str, Any]] = None
    ticks: int = 0
    t_ms: float = 0.0
    autopilot: bool = False
    error: Optional[str] = None
    plug: Dict[str, Any] = Field(default_factory=dict)


class TickRequest(BaseModel):
    observations: List[Observation] = Field(default_factory=list)
    window_ms: Optional[float] = Field(default=None, gt=0.0, le=5000.0)
    stimuli: List[StimulusCommand] = Field(default_factory=list)
    act: bool = True


class TickResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    origin: str = ORIGIN_SIMULATED
    session_id: str
    tick: int
    t_ms: float
    brain: BrainState
    action: MotorAction
    nav: Optional[NavPath] = None
    detections: Optional[DetectionFrame] = None
    plug: str
    dry_run: bool
    plug_result: Dict[str, Any] = Field(default_factory=dict)
    avani: Optional[Dict[str, Any]] = None
    encoded_rates_hz: Dict[str, float] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)
    wall_ms: float = 0.0


class SpikeRecord(BaseModel):
    session_id: str
    from_ms: float
    to_ms: float
    count: int
    times_ms: List[float] = Field(default_factory=list)
    neuron_indices: List[int] = Field(default_factory=list)
    flywire_ids: List[int] = Field(default_factory=list)
    truncated: bool = False


class ConnectomeManifest(BaseModel):
    loaded: bool = False
    data_dir: Optional[str] = None
    completeness_path: Optional[str] = None
    connectivity_path: Optional[str] = None
    n_neurons: int = 0
    n_synapses: int = 0
    sha256_ok: Optional[bool] = None
    sha256: Dict[str, str] = Field(default_factory=dict)
    version: str = "flywire-783"
    license: str = "FlyWire public release data terms apply; see docs/FLYBRAIN_MODULE_SEP14_2026.md"
    reason: str = ""


class FlyBrainHealth(BaseModel):
    status: Literal["healthy", "degraded", "unavailable"]
    schema_version: str = SCHEMA_VERSION
    connectome: ConnectomeManifest
    vision: VisionHealth
    backend: str
    torch_available: bool = False
    cuda_available: bool = False
    sessions: int = 0
    autopilots: int = 0
    plugs: List[str] = Field(default_factory=list)
    note: str = ""
