"""Detection provider interfaces for BlueSight."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Protocol

from mycosoft_mas.schemas.bluesight import BlueSightDetection, BlueSightSensorPacket


class DetectionProvider(Protocol):
    name: str

    def detect(self, packet: BlueSightSensorPacket) -> List[BlueSightDetection]:
        ...


@dataclass
class TruthBootstrapProvider:
    """Derives detections from profile truth state if available."""

    name: str = "truth_bootstrap"

    def detect(self, packet: BlueSightSensorPacket) -> List[BlueSightDetection]:
        detections: List[BlueSightDetection] = []
        truth = packet.truth_state or {}
        for entity_type in ("colonies", "spores", "tips", "segments", "nodes"):
            entities = truth.get(entity_type, [])
            for index, entity in enumerate(entities):
                x = float(entity.get("x", 0.0))
                y = float(entity.get("y", 0.0))
                w = float(entity.get("w", 4.0))
                h = float(entity.get("h", 4.0))
                entity_id = str(entity.get("id", f"{entity_type}_{index}"))
                detections.append(
                    BlueSightDetection(
                        detection_id=f"{packet.frame_id}:{entity_type}:{entity_id}",
                        class_name=entity.get("class_name", entity_type.rstrip("s")),
                        confidence=1.0,
                        centroid_xy=(x, y),
                        bbox_xyxy=(x - w / 2.0, y - h / 2.0, x + w / 2.0, y + h / 2.0),
                        linked_entity={"type": entity_type.rstrip("s"), "id": entity_id},
                        visual_label=str(entity.get("label", entity_type.rstrip("s"))),
                    )
                )
        return detections


@dataclass
class EmptyProvider:
    name: str

    def detect(self, packet: BlueSightSensorPacket) -> List[BlueSightDetection]:
        return []


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, DetectionProvider] = {
            "truth_bootstrap": TruthBootstrapProvider(),
            "yolo_world": EmptyProvider("yolo_world"),
            "yoloe_26": EmptyProvider("yoloe_26"),
            "yolo26_custom": EmptyProvider("yolo26_custom"),
            "hailo_hef": EmptyProvider("hailo_hef"),
            "lidar_cluster_detector": EmptyProvider("lidar_cluster_detector"),
            "wifi_presence_detector": EmptyProvider("wifi_presence_detector"),
        }

    def provider(self, name: str) -> DetectionProvider:
        return self._providers.get(name, self._providers["truth_bootstrap"])

