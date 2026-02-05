"""
Earth-2 Pydantic Data Models
February 4, 2026

Defines all data models for Earth-2 model inputs and outputs.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
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
    time_range: TimeRange
    variables: List[WeatherVariable] = Field(default=[WeatherVariable.T2M, WeatherVariable.U10, WeatherVariable.V10, WeatherVariable.TP])
    pressure_levels: List[PressureLevel] = Field(default=[PressureLevel.L850, PressureLevel.L500])
    ensemble_members: int = Field(default=1, ge=1, le=50)
    resolution: float = Field(default=0.25)
    
    class Config:
        use_enum_values = True


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
    spatial_extent: SpatialExtent
    lead_time_hours: int = Field(default=6, ge=1, le=24)
    time_step_minutes: int = Field(default=10, ge=5, le=60)
    include_satellite: bool = True
    include_radar: bool = True
    
    class Config:
        use_enum_values = True


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
    spatial_extent: SpatialExtent
    time_range: TimeRange
    species_filter: Optional[List[str]] = None
    source_locations: Optional[List[Tuple[float, float]]] = None
    wind_model: Earth2Model = Field(default=Earth2Model.ATLAS_ERA5)
    include_precipitation: bool = True
    include_humidity: bool = True


class SporeDispersalResult(BaseModel):
    """Result of spore dispersal forecast."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = Field(default="completed")
    params: SporeDispersalParams
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
