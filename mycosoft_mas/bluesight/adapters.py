"""Sensor adapter interfaces for BlueSight."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Protocol

from mycosoft_mas.schemas.bluesight import BlueSightSensorPacket


class SensorAdapter(Protocol):
    name: str

    def normalize(self, packet: BlueSightSensorPacket) -> BlueSightSensorPacket:
        ...


@dataclass
class CameraAdapter:
    name: str = "camera_adapter"

    def normalize(self, packet: BlueSightSensorPacket) -> BlueSightSensorPacket:
        packet.metadata.setdefault("sensor_family", "camera")
        packet.metadata.setdefault("resolution", f"{packet.width or 0}x{packet.height or 0}")
        return packet


@dataclass
class LidarAdapter:
    name: str = "lidar_adapter"

    def normalize(self, packet: BlueSightSensorPacket) -> BlueSightSensorPacket:
        packet.metadata.setdefault("sensor_family", "lidar")
        packet.metadata.setdefault("point_cloud", True)
        return packet


@dataclass
class RadarAdapter:
    name: str = "radar_adapter"

    def normalize(self, packet: BlueSightSensorPacket) -> BlueSightSensorPacket:
        packet.metadata.setdefault("sensor_family", "radar")
        packet.metadata.setdefault("velocity_vectors", True)
        return packet


@dataclass
class WifiSenseAdapter:
    name: str = "wifi_sense_adapter"

    def normalize(self, packet: BlueSightSensorPacket) -> BlueSightSensorPacket:
        packet.metadata.setdefault("sensor_family", "wifi_sense")
        packet.metadata.setdefault("occupancy_signal", True)
        return packet


class SensorAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: Dict[str, SensorAdapter] = {
            "camera": CameraAdapter(),
            "microscope": CameraAdapter(),
            "screen_capture": CameraAdapter(),
            "lidar": LidarAdapter(),
            "radar": RadarAdapter(),
            "wifi_sense": WifiSenseAdapter(),
        }

    def normalize(self, packet: BlueSightSensorPacket) -> BlueSightSensorPacket:
        adapter = self._adapters.get(packet.source)
        if adapter is None:
            return packet
        return adapter.normalize(packet)

