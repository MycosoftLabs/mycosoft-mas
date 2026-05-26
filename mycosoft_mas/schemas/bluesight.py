"""
BlueSight multimodal schema contracts.

These contracts are profile-agnostic first, then extended for Petri and Earth profiles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

SensorSource = Literal[
    "camera",
    "lidar",
    "radar",
    "wifi_sense",
    "screen_capture",
    "microscope",
]
RuntimeTarget = Literal["browser", "raspberry_pi_hailo8", "jetson", "server_gpu", "server_cpu"]
ProfileName = Literal["petri", "earth_globe", "device_scene"]


class BlueSightModelHealth(BaseModel):
    model_name: str
    model_version: str
    runtime: RuntimeTarget
    provider: str
    healthy: bool = True
    fps: Optional[float] = None
    latency_ms: Optional[float] = None
    notes: Optional[str] = None


class BlueSightLinkedEntity(BaseModel):
    type: str
    id: str
    taxon_id: Optional[str] = None


class BlueSightDetection(BaseModel):
    detection_id: str
    class_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    track_id: Optional[str] = None
    bbox_xyxy: Optional[Tuple[float, float, float, float]] = None
    centroid_xy: Optional[Tuple[float, float]] = None
    mask_rle: Optional[str] = None
    linked_entity: Optional[BlueSightLinkedEntity] = None
    visual_label: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class BlueSightTrack(BaseModel):
    track_id: str
    class_name: str
    status: Literal["created", "updated", "lost"] = "updated"
    confidence: float = Field(ge=0.0, le=1.0)
    centroid_xy: Optional[Tuple[float, float]] = None
    last_seen_ts: str


class BlueSightSensorPacket(BaseModel):
    schema: str = "org.mycosoft.bluesight.sensor_packet.v1"
    profile: ProfileName
    run_id: str
    frame_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    source: SensorSource
    width: Optional[int] = None
    height: Optional[int] = None
    frame_ref: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    truth_state: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BlueSightFusionPacket(BaseModel):
    schema: str = "org.mycosoft.bluesight.fusion_packet.v1"
    profile: ProfileName
    run_id: str
    frame_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    detections: List[BlueSightDetection] = Field(default_factory=list)
    tracks: List[BlueSightTrack] = Field(default_factory=list)
    sensor_disagreement_score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BlueSightReconciliation(BaseModel):
    matched_sim_entities: int = 0
    unmatched_visual_entities: int = 0
    visual_truth_disagreement_score: float = 0.0
    sensor_disagreement_score: float = 0.0


class BlueSightObservation(BaseModel):
    schema: str = "org.mycosoft.bluesight.observation.v1"
    profile: ProfileName
    run_id: str
    frame_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    source: SensorSource
    detections: List[BlueSightDetection] = Field(default_factory=list)
    tracks: List[BlueSightTrack] = Field(default_factory=list)
    reconciliation: BlueSightReconciliation = Field(default_factory=BlueSightReconciliation)
    model_health: Optional[BlueSightModelHealth] = None
    truth_state_ref: Optional[str] = None
    scene_summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PetriTruthState(BaseModel):
    run_id: str
    tick: int
    colonies: List[Dict[str, Any]] = Field(default_factory=list)
    spores: List[Dict[str, Any]] = Field(default_factory=list)
    tips: List[Dict[str, Any]] = Field(default_factory=list)
    segments: List[Dict[str, Any]] = Field(default_factory=list)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    chemical_fields_summary: Dict[str, float] = Field(default_factory=dict)
    events_since_last_frame: List[Dict[str, Any]] = Field(default_factory=list)


class PetriVisualObservation(BlueSightObservation):
    schema: str = "org.mycosoft.bluesight.petri.observation.v1"
    profile: ProfileName = "petri"
    dish: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)


class EarthVisualObservation(BlueSightObservation):
    schema: str = "org.mycosoft.bluesight.earth.observation.v1"
    profile: ProfileName = "earth_globe"
    geo_bounds: Optional[Dict[str, float]] = None
    scene_type: Optional[str] = None


class DeviceSceneObservation(BlueSightObservation):
    schema: str = "org.mycosoft.bluesight.device.observation.v1"
    profile: ProfileName = "device_scene"
    device_id: Optional[str] = None
    calibration_id: Optional[str] = None

