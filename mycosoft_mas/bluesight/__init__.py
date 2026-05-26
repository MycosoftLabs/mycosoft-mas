"""BlueSight multimodal perception runtime package."""

from mycosoft_mas.bluesight.adapters import SensorAdapterRegistry
from mycosoft_mas.bluesight.fusion import fuse_sensor_detections
from mycosoft_mas.bluesight.providers import ProviderRegistry
from mycosoft_mas.bluesight.service import BlueSightService, get_bluesight_service

__all__ = [
    "SensorAdapterRegistry",
    "ProviderRegistry",
    "fuse_sensor_detections",
    "BlueSightService",
    "get_bluesight_service",
]

