"""
Earth-2 API Router
February 4, 2026

FastAPI router for Earth-2 AI weather model endpoints.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ForecastRequest(BaseModel):
    """Request for medium-range forecast."""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    forecast_hours: Optional[int] = Field(default=None, ge=1, le=24 * 15)
    forecast_days: Optional[int] = Field(default=None, ge=1, le=15)
    step_hours: int = Field(default=6, ge=1, le=24)
    variables: List[str] = Field(default=["t2m", "u10", "v10", "tp"])
    pressure_levels: List[int] = Field(default=[850, 500])
    ensemble_members: int = Field(default=1, ge=1, le=50)
    resolution: float = Field(default=0.25)
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lon: Optional[float] = None
    max_lon: Optional[float] = None


class NowcastRequest(BaseModel):
    """Request for short-range nowcast."""
    # Bounding box (preferred when available)
    min_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    max_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    min_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    max_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    # Legacy center-point schema used in unit tests
    center_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    center_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    domain_size_km: int = Field(default=500, ge=10, le=5000)
    forecast_minutes: int = Field(default=180, ge=5, le=24 * 60)
    step_minutes: int = Field(default=10, ge=5, le=60)
    variables: List[str] = Field(default=["radar_reflectivity"])

    lead_time_hours: int = Field(default=6, ge=1, le=24)
    time_step_minutes: int = Field(default=10, ge=5, le=60)
    include_satellite: bool = True
    include_radar: bool = True


class DownscaleRequest(BaseModel):
    """Request for AI downscaling."""
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    input_resolution: float
    output_resolution: float
    input_data_path: str
    variables: List[str]


class SporeDispersalRequest(BaseModel):
    """Request for spore dispersal forecast."""
    # Bounding box (preferred when available)
    min_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    max_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    min_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    max_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    forecast_hours: Optional[int] = Field(default=None, ge=1, le=24 * 15)
    # Legacy origin schema used in unit tests
    species: Optional[str] = None
    origin_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    origin_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    origin_concentration: Optional[float] = Field(default=None, ge=0)
    species_filter: Optional[List[str]] = None
    include_precipitation: bool = True
    include_humidity: bool = True


class ModelRunResponse(BaseModel):
    """Response for model run submission."""
    run_id: str
    status: str
    model: str
    message: str = ""


class RunStatusResponse(BaseModel):
    """Response for run status query."""
    run_id: str
    status: str
    model: str
    run_type: str
    requested_by: str
    request_timestamp: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    compute_time_seconds: Optional[float] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None


# ============================================================================
# Health and Status Endpoints
# ============================================================================

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check Earth-2 service health."""
    try:
        from mycosoft_mas.earth2 import get_earth2_service
        service = get_earth2_service()
        status = await service.get_status()
        return {
            "status": "healthy",
            "service": "earth2",
            "available": status["available"],
            "models_available": status["available"],
            "gpu_device": status["gpu_device"],
            "active_runs": status["active_runs"],
            "loaded_models": status["loaded_models"],
        }
    except Exception as e:
        logger.error(f"Earth-2 health check failed: {e}")
        return {
            "status": "degraded",
            "service": "earth2",
            "error": str(e),
        }


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get detailed Earth-2 service status."""
    from mycosoft_mas.earth2 import get_earth2_service
    service = get_earth2_service()
    return await service.get_status()


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """List available Earth-2 models."""
    return {
        "models": [
            {
                "id": "atlas_era5",
                "name": "Atlas ERA5",
                "type": "forecast",
                "description": "Medium-range global forecast (0-15 days)",
                "variables": 75,
                "resolution": 0.25,
            },
            {
                "id": "atlas_gfs",
                "name": "Atlas GFS",
                "type": "forecast",
                "description": "Medium-range forecast with GFS initialization",
                "variables": 75,
                "resolution": 0.25,
            },
            {
                "id": "stormscope_goes_mrms",
                "name": "StormScope GOES-MRMS",
                "type": "nowcast",
                "description": "Short-range hazardous weather nowcast (0-6 hours)",
                "resolution": 0.0125,
            },
            {
                "id": "corrdiff",
                "name": "CorrDiff",
                "type": "downscale",
                "description": "AI downscaling (500x faster than physics)",
            },
            {
                "id": "healda",
                "name": "HealDA",
                "type": "assimilation",
                "description": "Global data assimilation in seconds",
            },
        ]
    }


# ============================================================================
# Forecast Endpoints
# ============================================================================

@router.post("/forecast", response_model=ModelRunResponse)
async def submit_forecast(
    request: ForecastRequest,
    background_tasks: BackgroundTasks,
) -> ModelRunResponse:
    """
    Submit a medium-range weather forecast request.
    
    Uses the Atlas model to generate global or regional forecasts
    for up to 15 days in advance.
    """
    from mycosoft_mas.earth2 import (
        get_earth2_service, ForecastParams, TimeRange, SpatialExtent
    )
    
    service = get_earth2_service()
    
    # Parse time range
    start = datetime.fromisoformat(request.start_time) if request.start_time else datetime.utcnow()
    if request.end_time:
        end = datetime.fromisoformat(request.end_time)
    elif request.forecast_hours:
        end = start + timedelta(hours=int(request.forecast_hours))
    elif request.forecast_days:
        end = start + timedelta(days=int(request.forecast_days))
    else:
        end = start + timedelta(days=7)
    
    time_range = TimeRange(start=start, end=end, step_hours=request.step_hours)
    
    # Parse spatial extent
    spatial_extent = None
    if all([request.min_lat, request.max_lat, request.min_lon, request.max_lon]):
        spatial_extent = SpatialExtent(
            min_lat=request.min_lat,
            max_lat=request.max_lat,
            min_lon=request.min_lon,
            max_lon=request.max_lon,
        )
    
    params = ForecastParams(
        time_range=time_range,
        spatial_extent=spatial_extent,
        ensemble_members=request.ensemble_members,
        resolution=request.resolution,
    )
    
    # Run forecast
    result = await service.run_forecast(params)
    
    return ModelRunResponse(
        run_id=result.run_id,
        status=result.status,
        model=result.model,
        message=f"Forecast completed with {len(result.outputs)} outputs",
    )


@router.get("/forecast/{run_id}")
async def get_forecast_status(run_id: str) -> RunStatusResponse:
    """Get status of a forecast run."""
    from mycosoft_mas.earth2 import get_earth2_service
    
    service = get_earth2_service()
    run = await service.get_run_status(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return RunStatusResponse(
        run_id=run.run_id,
        status=run.status,
        model=str(run.model),
        run_type=run.run_type,
        requested_by=run.requested_by,
        request_timestamp=run.request_timestamp.isoformat(),
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        compute_time_seconds=run.compute_time_seconds,
        output_path=run.output_path,
        error_message=run.error_message,
    )


# ============================================================================
# Nowcast Endpoints
# ============================================================================

@router.post("/nowcast", response_model=ModelRunResponse)
async def submit_nowcast(request: NowcastRequest) -> ModelRunResponse:
    """
    Submit a short-range nowcast request.
    
    Uses the StormScope model to generate high-resolution
    radar and satellite predictions for 0-6 hours.
    """
    from mycosoft_mas.earth2 import get_earth2_service, NowcastParams, SpatialExtent
    
    service = get_earth2_service()
    
    if all(v is not None for v in [request.min_lat, request.max_lat, request.min_lon, request.max_lon]):
        spatial_extent = SpatialExtent(
            min_lat=float(request.min_lat),
            max_lat=float(request.max_lat),
            min_lon=float(request.min_lon),
            max_lon=float(request.max_lon),
        )
    else:
        center_lat = float(request.center_lat or 0.0)
        center_lon = float(request.center_lon or 0.0)
        half_lat = (float(request.domain_size_km) / 2.0) / 111.0
        spatial_extent = SpatialExtent(
            min_lat=center_lat - half_lat,
            max_lat=center_lat + half_lat,
            min_lon=center_lon - half_lat,
            max_lon=center_lon + half_lat,
        )
    
    lead_time_hours = max(1, int((request.forecast_minutes + 59) // 60))
    params = NowcastParams(
        spatial_extent=spatial_extent,
        lead_time_hours=lead_time_hours,
        time_step_minutes=request.step_minutes,
        include_satellite=request.include_satellite,
        include_radar=request.include_radar,
    )
    
    result = await service.run_nowcast(params)
    
    return ModelRunResponse(
        run_id=result.run_id,
        status=result.status,
        model=result.model,
        message=f"Nowcast completed with {len(result.outputs)} outputs",
    )


# ============================================================================
# Downscale Endpoints
# ============================================================================

@router.post("/downscale", response_model=ModelRunResponse)
async def submit_downscale(request: DownscaleRequest) -> ModelRunResponse:
    """
    Submit an AI downscaling request.
    
    Uses the CorrDiff model to convert coarse forecasts
    into high-resolution regional products (500x faster).
    """
    from mycosoft_mas.earth2 import (
        get_earth2_service, DownscaleParams, SpatialExtent, WeatherVariable
    )
    
    service = get_earth2_service()
    
    spatial_extent = SpatialExtent(
        min_lat=request.min_lat,
        max_lat=request.max_lat,
        min_lon=request.min_lon,
        max_lon=request.max_lon,
    )
    
    # Parse variables
    variables = [WeatherVariable(v) for v in request.variables]
    
    params = DownscaleParams(
        spatial_extent=spatial_extent,
        input_resolution=request.input_resolution,
        output_resolution=request.output_resolution,
        input_data_path=request.input_data_path,
        variables=variables,
    )
    
    result = await service.run_downscale(params)
    
    return ModelRunResponse(
        run_id=result.run_id,
        status=result.status,
        model=result.model,
        message=f"Downscaling completed ({result.speedup_factor}x speedup)",
    )


# ============================================================================
# Spore Dispersal Endpoints
# ============================================================================

@router.post("/spore-dispersal", response_model=ModelRunResponse)
async def submit_spore_dispersal(request: SporeDispersalRequest) -> ModelRunResponse:
    """
    Submit a spore dispersal forecast request.
    
    Combines Earth-2 weather forecasts with MINDEX spore data
    to generate dispersion forecasts and risk zones.
    """
    from mycosoft_mas.earth2 import (
        get_earth2_service, SporeDispersalParams, SpatialExtent, TimeRange
    )
    
    service = get_earth2_service()
    
    if all(v is not None for v in [request.min_lat, request.max_lat, request.min_lon, request.max_lon]):
        spatial_extent = SpatialExtent(
            min_lat=float(request.min_lat),
            max_lat=float(request.max_lat),
            min_lon=float(request.min_lon),
            max_lon=float(request.max_lon),
        )
    elif request.origin_lat is not None and request.origin_lon is not None:
        spatial_extent = SpatialExtent(
            min_lat=float(request.origin_lat) - 2.0,
            max_lat=float(request.origin_lat) + 2.0,
            min_lon=float(request.origin_lon) - 2.0,
            max_lon=float(request.origin_lon) + 2.0,
        )
    else:
        spatial_extent = SpatialExtent(min_lat=-90, max_lat=90, min_lon=-180, max_lon=180)
    
    start = datetime.fromisoformat(request.start_time) if request.start_time else datetime.utcnow()
    if request.end_time:
        end = datetime.fromisoformat(request.end_time)
    elif request.forecast_hours:
        end = start + timedelta(hours=int(request.forecast_hours))
    else:
        end = start + timedelta(days=3)
    
    time_range = TimeRange(start=start, end=end)
    
    params = SporeDispersalParams(
        spatial_extent=spatial_extent,
        time_range=time_range,
        species_filter=request.species_filter or ([request.species] if request.species else None),
        origin_lat=request.origin_lat,
        origin_lon=request.origin_lon,
        origin_concentration=request.origin_concentration,
        include_precipitation=request.include_precipitation,
        include_humidity=request.include_humidity,
    )
    
    result = await service.run_spore_dispersal(params)
    
    return ModelRunResponse(
        run_id=result.run_id,
        status=result.status,
        model="spore_dispersal",
        message=f"Dispersal forecast completed, {len(result.risk_zones)} risk zones identified",
    )


# ============================================================================
# Run Management Endpoints
# ============================================================================

@router.get("/runs")
async def list_runs(
    run_type: Optional[str] = Query(None, description="Filter by run type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
) -> Dict[str, Any]:
    """List model runs with optional filtering."""
    from mycosoft_mas.earth2 import get_earth2_service
    
    service = get_earth2_service()
    runs = await service.list_runs(run_type=run_type, status=status, limit=limit)
    
    return {
        "runs": [r.to_mindex_record() for r in runs],
        "count": len(runs),
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> RunStatusResponse:
    """Get status of any model run."""
    from mycosoft_mas.earth2 import get_earth2_service
    
    service = get_earth2_service()
    run = await service.get_run_status(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return RunStatusResponse(
        run_id=run.run_id,
        status=run.status,
        model=str(run.model),
        run_type=run.run_type,
        requested_by=run.requested_by,
        request_timestamp=run.request_timestamp.isoformat(),
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        compute_time_seconds=run.compute_time_seconds,
        output_path=run.output_path,
        error_message=run.error_message,
    )


@router.get("/runs/{run_id}/output")
async def get_run_output(run_id: str) -> Dict[str, Any]:
    """Get output data from a completed model run."""
    from mycosoft_mas.earth2 import get_earth2_service
    
    service = get_earth2_service()
    run = await service.get_run_status(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status != "completed":
        raise HTTPException(status_code=400, detail=f"Run is {run.status}, not completed")
    
    return {
        "run_id": run_id,
        "output_path": run.output_path,
        "message": "Output data available at the specified path",
    }


# ============================================================================
# Visualization Layer Endpoints
# ============================================================================

@router.get("/layers")
async def list_layers() -> Dict[str, Any]:
    """List available visualization layers for CREP/Earth Simulator."""
    return {
        "layers": [
            {
                "id": "earth2_temperature",
                "name": "Temperature (2m)",
                "type": "forecast",
                "variable": "t2m",
                "colormap": "temperature",
            },
            {
                "id": "earth2_wind",
                "name": "Wind Speed (10m)",
                "type": "forecast",
                "variable": "wind_speed_10m",
                "colormap": "wind",
            },
            {
                "id": "earth2_precipitation",
                "name": "Precipitation",
                "type": "forecast",
                "variable": "tp",
                "colormap": "precipitation",
            },
            {
                "id": "earth2_radar",
                "name": "Radar Reflectivity",
                "type": "nowcast",
                "variable": "radar_reflectivity",
                "colormap": "radar",
            },
            {
                "id": "earth2_spore",
                "name": "Spore Concentration",
                "type": "spore_dispersal",
                "colormap": "spore",
            },
        ]
    }
