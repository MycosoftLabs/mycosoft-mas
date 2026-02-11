"""
Earth-2 Pydantic Data Models
February 4, 2026

Defines all data models for Earth-2 model inputs and outputs.
"""

from enum import Enum
import math
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, model_validator
import uuid


class WeatherVariable(str, Enum):
    """Weather variables supported by Earth-2 Atlas model."""
    T2M = "t2m"  # 2m temperature
    U10 = "u10"  # 10m U wind component
    V10 = "v10"  # 10m V wind component
    SP = "sp"    # Surface pressure
    MSL = "msl"  # Mean sea level pressure
    TCW = "tcw"  # Total column water
    TCWV = "tcwv"  # Total column water vapor
    TP = "tp"    # Total precipitation
    T = "t"      # Temperature (upper air)
    U = "u"      # U wind component
    V = "v"      # V wind component
    Z = "z"      # Geopotential height
    Q = "q"      # Specific humidity
    R = "r"      # Relative humidity
    W = "w"      # Vertical velocity
    WIND_SPEED_10M = "wind_speed_10m"
    WIND_DIRECTION_10M = "wind_direction_10m"
    CAPE = "cape"
    CIN = "cin"
    IR_BRIGHTNESS = "ir_brightness"
    VIS_REFLECTANCE = "vis_reflectance"
    RADAR_REFLECTIVITY = "radar_reflectivity"


class Earth2Model(str, Enum):
    """Available Earth-2 AI weather models."""
    ATLAS_ERA5 = "atlas_era5"
    ATLAS_GFS = "atlas_gfs"
    STORMSCOPE_GOES_MRMS = "stormscope_goes_mrms"
    STORMSCOPE_GOES = "stormscope_goes"
    CORRDIFF = "corrdiff"
    HEALDA = "healda"
    FOURCASTNET = "fourcastnet"
    GRAPHCAST = "graphcast"
    PANGU = "pangu"
    GENCAST = "gencast"


class PressureLevel(int, Enum):
    """Standard pressure levels in hPa."""
    L1000 = 1000
    L925 = 925
    L850 = 850
    L700 = 700
    L500 = 500
    L300 = 300
    L250 = 250
    L200 = 200
    L100 = 100
    L50 = 50


class SpatialExtent(BaseModel):
    """Geographic bounding box for spatial queries."""
    min_lat: float = Field(..., ge=-90, le=90, description="Minimum latitude")
    max_lat: float = Field(..., ge=-90, le=90, description="Maximum latitude")
    min_lon: float = Field(..., ge=-180, le=180, description="Minimum longitude")
    max_lon: float = Field(..., ge=-180, le=180, description="Maximum longitude")
    
    @property
    def center(self) -> Tuple[float, float]:
        return ((self.min_lat + self.max_lat) / 2, (self.min_lon + self.max_lon) / 2)
    
    def to_dict(self) -> Dict[str, float]:
        return {"min_lat": self.min_lat, "max_lat": self.max_lat, "min_lon": self.min_lon, "max_lon": self.max_lon}


class TimeRange(BaseModel):
    """Time range for forecasts."""
    start: datetime = Field(..., description="Start time (UTC)")
    end: datetime = Field(..., description="End time (UTC)")
    step_hours: int = Field(default=6, description="Time step in hours")
    
    @property
    def duration_hours(self) -> int:
        delta = self.end - self.start
        return int(delta.total_seconds() / 3600)
    
    @property
    def num_steps(self) -> int:
        return self.duration_hours // self.step_hours + 1


class ModelProvenance(BaseModel):
    """Provenance tracking for model runs."""
    model_version: str = Field(..., description="Model version string")
    input_data_source: str = Field(..., description="Source of input data")
    input_data_timestamp: datetime
    run_timestamp: datetime = Field(default_factory=datetime.utcnow)
    gpu_device: Optional[str] = None
    compute_time_seconds: Optional[float] = None
    checksum: Optional[str] = None


class ForecastParams(BaseModel):
    """Parameters for medium-range weather forecast (Atlas model)."""
    model: Earth2Model = Field(default=Earth2Model.ATLAS_ERA5)
    spatial_extent: Optional[SpatialExtent] = None
    time_range: Optional[TimeRange] = None
    # Legacy convenience inputs used by the unit tests.
    start_time: Optional[datetime] = None
    forecast_hours: int = Field(default=168, ge=1, le=24 * 15)
    step_hours: int = Field(default=6, ge=1, le=24)
    variables: List[WeatherVariable] = Field(default=[WeatherVariable.T2M, WeatherVariable.U10, WeatherVariable.V10, WeatherVariable.TP])
    pressure_levels: List[PressureLevel] = Field(default=[PressureLevel.L850, PressureLevel.L500])
    ensemble_members: int = Field(default=1, ge=1, le=50)
    resolution: float = Field(default=0.25)
    
    class Config:
        use_enum_values = True

    @model_validator(mode="after")
    def _fill_time_and_extent(self) -> "ForecastParams":
        if self.time_range is None:
            start = self.start_time or datetime.utcnow()
            end = start + timedelta(hours=int(self.forecast_hours))
            self.time_range = TimeRange(start=start, end=end, step_hours=int(self.step_hours))
        if self.spatial_extent is None:
            # Neutral default: global extent.
            self.spatial_extent = SpatialExtent(min_lat=-90, max_lat=90, min_lon=-180, max_lon=180)
        return self


class ForecastOutput(BaseModel):
    """Single forecast output for a variable at a timestep."""
    variable: str
    timestamp: datetime
    pressure_level: Optional[int] = None
    data_shape: Tuple[int, int]
    data_url: str
    min_value: float
    max_value: float
    mean_value: float
    units: str


class ForecastResult(BaseModel):
    """Result of a forecast model run."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = Field(default="completed")
    model: str
    params: ForecastParams
    provenance: ModelProvenance
    outputs: List[ForecastOutput] = Field(default_factory=list)
    ensemble_spread: Optional[Dict[str, float]] = None
    data_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class NowcastParams(BaseModel):
    """Parameters for short-range nowcasting (StormScope model)."""
    model: Earth2Model = Field(default=Earth2Model.STORMSCOPE_GOES_MRMS)
    spatial_extent: Optional[SpatialExtent] = None
    lead_time_hours: Optional[int] = Field(default=None, ge=1, le=24)
    time_step_minutes: Optional[int] = Field(default=None, ge=5, le=60)
    include_satellite: bool = True
    include_radar: bool = True
    # Legacy convenience inputs used by the unit tests.
    center_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    center_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    domain_size_km: int = Field(default=500, ge=10, le=5000)
    forecast_minutes: int = Field(default=180, ge=5, le=24 * 60)
    step_minutes: int = Field(default=10, ge=5, le=60)
    variables: Optional[List[WeatherVariable]] = None
    
    class Config:
        use_enum_values = True

    @model_validator(mode="after")
    def _fill_extent_and_time(self) -> "NowcastParams":
        if self.spatial_extent is None:
            lat = float(self.center_lat or 0.0)
            lon = float(self.center_lon or 0.0)
            half_lat = (self.domain_size_km / 2.0) / 111.0
            # Avoid divide by zero near poles.
            denom = max(0.2, abs(math.cos(lat * math.pi / 180.0)))
            half_lon = (self.domain_size_km / 2.0) / (111.0 * denom)
            self.spatial_extent = SpatialExtent(
                min_lat=lat - half_lat,
                max_lat=lat + half_lat,
                min_lon=lon - half_lon,
                max_lon=lon + half_lon,
            )
        if self.lead_time_hours is None:
            self.lead_time_hours = max(1, int((self.forecast_minutes + 59) // 60))
        if self.time_step_minutes is None:
            self.time_step_minutes = int(self.step_minutes)
        return self


class NowcastOutput(BaseModel):
    """Single nowcast output."""
    product_type: str
    timestamp: datetime
    data_url: str
    confidence: float = Field(ge=0, le=1)
    hazard_flags: List[str] = Field(default_factory=list)


class NowcastResult(BaseModel):
    """Result of a nowcast model run."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = Field(default="completed")
    model: str
    params: NowcastParams
    provenance: ModelProvenance
    outputs: List[NowcastOutput] = Field(default_factory=list)
    hazard_summary: Dict[str, Any] = Field(default_factory=dict)
    data_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class DownscaleParams(BaseModel):
    """Parameters for AI downscaling (CorrDiff model)."""
    model: Earth2Model = Field(default=Earth2Model.CORRDIFF)
    input_resolution: float
    output_resolution: float
    spatial_extent: SpatialExtent
    variables: List[WeatherVariable]
    input_data_path: str
    
    class Config:
        use_enum_values = True


class DownscaleResult(BaseModel):
    """Result of a downscaling model run."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = Field(default="completed")
    model: str
    params: DownscaleParams
    provenance: ModelProvenance
    output_shape: Tuple[int, int]
    speedup_factor: float
    energy_efficiency: float
    data_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class Observation(BaseModel):
    """Single observation for data assimilation."""
    variable: WeatherVariable
    latitude: float
    longitude: float
    value: float
    timestamp: datetime
    uncertainty: float
    source: str
    
    class Config:
        use_enum_values = True


class AssimilationParams(BaseModel):
    """Parameters for data assimilation (HealDA model)."""
    model: Earth2Model = Field(default=Earth2Model.HEALDA)
    observations: List[Observation]
    background_data_path: str
    spatial_extent: Optional[SpatialExtent] = None
    
    class Config:
        use_enum_values = True


class AssimilationResult(BaseModel):
    """Result of data assimilation run."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = Field(default="completed")
    model: str
    params: AssimilationParams
    provenance: ModelProvenance
    observations_assimilated: int
    analysis_increment_rms: Dict[str, float]
    data_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class Earth2ModelRun(BaseModel):
    """Complete model run record for MINDEX storage."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: Earth2Model
    run_type: str
    status: str = Field(default="pending")
    requested_by: str = Field(default="system")
    request_timestamp: datetime = Field(default_factory=datetime.utcnow)
    spatial_extent: Optional[SpatialExtent] = None
    time_range: Optional[TimeRange] = None
    provenance: Optional[ModelProvenance] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    compute_time_seconds: Optional[float] = None
    gpu_memory_peak_mb: Optional[float] = None
    output_size_mb: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
    
    def to_mindex_record(self) -> Dict[str, Any]:
        return {
            "id": self.run_id,
            "entity_type": "earth2_model_run",
            "model": self.model,
            "run_type": self.run_type,
            "status": self.status,
            "requested_by": self.requested_by,
            "request_timestamp": self.request_timestamp.isoformat(),
            "spatial_extent": self.spatial_extent.to_dict() if self.spatial_extent else None,
            "output_path": self.output_path,
            "compute_time_seconds": self.compute_time_seconds,
            "created_at": self.request_timestamp.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SporeDispersalParams(BaseModel):
    """Parameters for spore dispersal forecast combining Earth-2 + MINDEX."""
    spatial_extent: Optional[SpatialExtent] = None
    time_range: Optional[TimeRange] = None
    species_filter: Optional[List[str]] = None
    source_locations: Optional[List[Tuple[float, float]]] = None
    wind_model: Earth2Model = Field(default=Earth2Model.ATLAS_ERA5)
    include_precipitation: bool = True
    include_humidity: bool = True
    # Legacy convenience inputs used by the unit tests.
    species: Optional[str] = None
    origin_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    origin_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    origin_concentration: Optional[float] = Field(default=None, ge=0)
    forecast_hours: int = Field(default=48, ge=1, le=24 * 15)

    @model_validator(mode="after")
    def _fill_derived(self) -> "SporeDispersalParams":
        if self.species and not self.species_filter:
            self.species_filter = [self.species]
        if self.origin_lat is not None and self.origin_lon is not None and not self.source_locations:
            self.source_locations = [(float(self.origin_lat), float(self.origin_lon))]
        if self.spatial_extent is None:
            if self.origin_lat is not None and self.origin_lon is not None:
                lat = float(self.origin_lat)
                lon = float(self.origin_lon)
                self.spatial_extent = SpatialExtent(
                    min_lat=lat - 2.0,
                    max_lat=lat + 2.0,
                    min_lon=lon - 2.0,
                    max_lon=lon + 2.0,
                )
            else:
                self.spatial_extent = SpatialExtent(min_lat=-90, max_lat=90, min_lon=-180, max_lon=180)
        if self.time_range is None:
            start = datetime.utcnow()
            end = start + timedelta(hours=int(self.forecast_hours))
            self.time_range = TimeRange(start=start, end=end, step_hours=6)
        return self


class SporeDispersalResult(BaseModel):
    """Result of spore dispersal forecast."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = Field(default="completed")
    params: SporeDispersalParams
    # Legacy fields expected by tests.
    species: Optional[str] = None
    peak_concentration: Optional[float] = None
    weather_run_id: str
    concentration_map_url: str
    risk_zones: List[Dict[str, Any]] = Field(default_factory=list)
    peak_concentration_time: Optional[datetime] = None
    affected_area_km2: float = 0.0
    mindex_species_matched: List[str] = Field(default_factory=list)
    mindex_observations_used: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
