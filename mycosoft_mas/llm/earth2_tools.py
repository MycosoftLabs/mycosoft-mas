"""
Earth-2 Tool Definitions for MYCA Tool Pipeline
February 4, 2026

Provides Earth-2 weather model tools for mid-conversation tool calls.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_earth2_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get Earth-2 tool definitions for registration with ToolRegistry.
    
    Returns list of tool definition dicts.
    """
    return [
        {
            "name": "earth2_forecast",
            "description": "Get AI weather forecast for a location and time range using NVIDIA Earth-2 Atlas model. Returns temperature, wind, precipitation predictions for up to 15 days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "object",
                        "description": "Location for forecast",
                        "properties": {
                            "lat": {"type": "number", "description": "Latitude"},
                            "lon": {"type": "number", "description": "Longitude"}
                        },
                        "required": ["lat", "lon"]
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to forecast (1-15)",
                        "default": 7,
                        "minimum": 1,
                        "maximum": 15
                    },
                    "variables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Weather variables (t2m, tp, u10, v10)",
                        "default": ["t2m", "tp"]
                    }
                },
                "required": ["location"]
            }
        },
        {
            "name": "earth2_nowcast",
            "description": "Get short-term weather nowcast (0-6 hours) using NVIDIA Earth-2 StormScope model. Predicts radar reflectivity and severe weather hazards.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "object",
                        "description": "Geographic region for nowcast",
                        "properties": {
                            "min_lat": {"type": "number"},
                            "max_lat": {"type": "number"},
                            "min_lon": {"type": "number"},
                            "max_lon": {"type": "number"}
                        },
                        "required": ["min_lat", "max_lat", "min_lon", "max_lon"]
                    },
                    "lead_time_hours": {
                        "type": "integer",
                        "description": "Forecast lead time (1-6 hours)",
                        "default": 6,
                        "minimum": 1,
                        "maximum": 6
                    }
                },
                "required": ["region"]
            }
        },
        {
            "name": "earth2_spore_dispersal",
            "description": "Get spore dispersal forecast combining Earth-2 weather with MINDEX fungal data. Identifies risk zones for spore concentration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "object",
                        "description": "Geographic region",
                        "properties": {
                            "min_lat": {"type": "number"},
                            "max_lat": {"type": "number"},
                            "min_lon": {"type": "number"},
                            "max_lon": {"type": "number"}
                        },
                        "required": ["min_lat", "max_lat", "min_lon", "max_lon"]
                    },
                    "species_filter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by fungal species"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Forecast days (1-7)",
                        "default": 3
                    }
                },
                "required": ["region"]
            }
        },
        {
            "name": "earth2_model_status",
            "description": "Check Earth-2 model service status and GPU availability.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    ]


async def execute_earth2_forecast(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Earth-2 forecast tool."""
    from mycosoft_mas.earth2 import (
        get_earth2_service, ForecastParams, TimeRange, SpatialExtent
    )
    
    service = get_earth2_service()
    
    # Accept multiple legacy schemas (tests pass `location` as a string and
    # provide `latitude`/`longitude` + `forecast_days`).
    location = args.get("location", {})
    if isinstance(location, dict):
        lat = location.get("lat")
        lon = location.get("lon")
    else:
        lat = None
        lon = None
    lat = float(args.get("latitude", lat if lat is not None else 47.6))
    lon = float(args.get("longitude", lon if lon is not None else -122.3))
    days = int(args.get("forecast_days", args.get("days", 7)))
    
    # Create small extent around point
    extent = SpatialExtent(
        min_lat=lat - 1,
        max_lat=lat + 1,
        min_lon=lon - 1,
        max_lon=lon + 1,
    )
    
    time_range = TimeRange(
        start=datetime.utcnow(),
        end=datetime.utcnow() + timedelta(days=days),
    )
    
    params = ForecastParams(spatial_extent=extent, time_range=time_range)
    
    result = await service.run_forecast(params)
    
    # Extract point forecast
    forecast_points = []
    for output in result.outputs[:10]:  # Limit for response size
        forecast_points.append({
            "time": output.timestamp.isoformat(),
            "variable": output.variable,
            "value": output.mean_value,
            "units": output.units,
        })
    
    return {
        "run_id": result.run_id,
        "location": {"lat": lat, "lon": lon},
        "forecast": forecast_points,
        "model": result.model,
    }


async def execute_earth2_nowcast(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Earth-2 nowcast tool."""
    from mycosoft_mas.earth2 import get_earth2_service, NowcastParams, SpatialExtent
    
    service = get_earth2_service()
    
    region = args.get("region", {})
    if not isinstance(region, dict):
        region = {}

    # Tests pass a center point + forecast_hours. Build a small domain.
    center_lat = float(args.get("latitude", region.get("center_lat", 39.0)))
    center_lon = float(args.get("longitude", region.get("center_lon", -98.0)))
    domain_km = float(args.get("domain_size_km", region.get("domain_size_km", 500)))
    half_lat = (domain_km / 2.0) / 111.0
    extent = SpatialExtent(
        min_lat=center_lat - half_lat,
        max_lat=center_lat + half_lat,
        min_lon=center_lon - half_lat,
        max_lon=center_lon + half_lat,
    )
    
    lead_time_hours = int(args.get("forecast_hours", args.get("lead_time_hours", 6)))
    params = NowcastParams(spatial_extent=extent, lead_time_hours=lead_time_hours)
    
    result = await service.run_nowcast(params)
    
    return {
        "run_id": result.run_id,
        "hazard_summary": result.hazard_summary,
        "outputs": len(result.outputs),
        "model": result.model,
    }


async def execute_earth2_spore_dispersal(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Earth-2 spore dispersal tool."""
    from mycosoft_mas.earth2 import (
        get_earth2_service, SporeDispersalParams, SpatialExtent, TimeRange
    )
    
    service = get_earth2_service()
    
    region = args.get("region", {})
    if not isinstance(region, dict):
        region = {}

    origin_lat = float(args.get("origin_lat", args.get("latitude", 41.5)))
    origin_lon = float(args.get("origin_lon", args.get("longitude", -93.0)))
    extent = SpatialExtent(
        min_lat=region.get("min_lat", origin_lat - 2.0),
        max_lat=region.get("max_lat", origin_lat + 2.0),
        min_lon=region.get("min_lon", origin_lon - 2.0),
        max_lon=region.get("max_lon", origin_lon + 2.0),
    )

    days = int(args.get("days", max(1, int(float(args.get("forecast_hours", 72)) / 24.0))))
    time_range = TimeRange(
        start=datetime.utcnow(),
        end=datetime.utcnow() + timedelta(days=days),
    )
    
    species = args.get("species")
    params = SporeDispersalParams(
        spatial_extent=extent,
        time_range=time_range,
        species_filter=args.get("species_filter") or ([species] if isinstance(species, str) and species else None),
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        origin_concentration=float(args.get("origin_concentration", args.get("concentration", 0)) or 0),
    )
    
    result = await service.run_spore_dispersal(params)
    
    return {
        "run_id": result.run_id,
        "risk_zones": result.risk_zones,
        "affected_area_km2": result.affected_area_km2,
        "species_matched": result.mindex_species_matched,
    }


async def execute_earth2_model_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Earth-2 model status tool."""
    from mycosoft_mas.earth2 import get_earth2_service
    
    service = get_earth2_service()
    status = await service.get_status()
    
    return {
        "available": status["available"],
        "gpu_device": status["gpu_device"],
        "active_runs": status["active_runs"],
        "loaded_models": status["loaded_models"],
    }


# Tool handler mapping
EARTH2_TOOL_HANDLERS = {
    "earth2_forecast": execute_earth2_forecast,
    "earth2_nowcast": execute_earth2_nowcast,
    "earth2_spore_dispersal": execute_earth2_spore_dispersal,
    "earth2_model_status": execute_earth2_model_status,
}


def register_earth2_tools(registry) -> None:
    """
    Register Earth-2 tools with an existing ToolRegistry.
    
    Args:
        registry: ToolRegistry instance to register tools with
    """
    from mycosoft_mas.llm.tool_pipeline import ToolDefinition
    
    for tool_def in get_earth2_tool_definitions():
        registry.register(ToolDefinition(
            name=tool_def["name"],
            description=tool_def["description"],
            parameters=tool_def["parameters"],
            handler=EARTH2_TOOL_HANDLERS.get(tool_def["name"]),
        ))
    
    logger.info(f"Registered {len(EARTH2_TOOL_HANDLERS)} Earth-2 tools")
