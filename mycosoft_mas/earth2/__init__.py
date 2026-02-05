"""
NVIDIA Earth-2 Integration Module
February 4, 2026

This module provides integration with NVIDIA Earth-2 AI weather models:
- Atlas (Medium-range forecasting, 0-15 days)
- StormScope (Nowcasting, 0-6 hours)
- CorrDiff (Downscaling)
- HealDA (Data Assimilation)

Components:
- earth2_service: Earth2Studio wrapper service
- models: Pydantic data models for I/O
"""

from .models import (
    ForecastParams,
    ForecastResult,
    NowcastParams,
    NowcastResult,
    DownscaleParams,
    DownscaleResult,
    AssimilationParams,
    AssimilationResult,
    Earth2ModelRun,
    WeatherVariable,
    Earth2Model,
    SpatialExtent,
    TimeRange,
    SporeDispersalParams,
    SporeDispersalResult,
)

from .earth2_service import (
    Earth2StudioService,
    get_earth2_service,
)

__all__ = [
    # Models
    "ForecastParams",
    "ForecastResult",
    "NowcastParams",
    "NowcastResult",
    "DownscaleParams",
    "DownscaleResult",
    "AssimilationParams",
    "AssimilationResult",
    "Earth2ModelRun",
    "WeatherVariable",
    "Earth2Model",
    "SpatialExtent",
    "TimeRange",
    "SporeDispersalParams",
    "SporeDispersalResult",
    # Service
    "Earth2StudioService",
    "get_earth2_service",
]