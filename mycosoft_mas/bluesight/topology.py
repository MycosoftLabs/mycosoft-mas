"""Runtime topology for BlueSight browser/edge/server execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal

ExecutionLane = Literal["browser", "edge_pi_hailo", "edge_jetson", "server_gpu", "server_cpu"]


@dataclass(frozen=True)
class LaneConfig:
    lane: ExecutionLane
    providers: List[str]
    sensor_sources: List[str]
    notes: str


def default_topology() -> Dict[str, LaneConfig]:
    return {
        "browser": LaneConfig(
            lane="browser",
            providers=["truth_bootstrap"],
            sensor_sources=["screen_capture", "camera"],
            notes="Fast UX feedback for simulator and dashboards.",
        ),
        "edge_pi_hailo": LaneConfig(
            lane="edge_pi_hailo",
            providers=["yolo26_custom", "hailo_hef"],
            sensor_sources=["camera"],
            notes="Low power fixed-class edge lane.",
        ),
        "edge_jetson": LaneConfig(
            lane="edge_jetson",
            providers=["yolo_world", "yoloe_26", "yolo26_custom"],
            sensor_sources=["camera", "lidar", "radar", "wifi_sense"],
            notes="Open vocabulary and heavier multimodal fusion.",
        ),
        "server_gpu": LaneConfig(
            lane="server_gpu",
            providers=["yolo_world", "yoloe_26", "yolo26_custom"],
            sensor_sources=["camera", "lidar", "radar", "wifi_sense", "microscope"],
            notes="Batch, deep scan, and retrospective analysis.",
        ),
        "server_cpu": LaneConfig(
            lane="server_cpu",
            providers=["truth_bootstrap"],
            sensor_sources=["screen_capture", "camera", "wifi_sense"],
            notes="Fallback and validation lane.",
        ),
    }

