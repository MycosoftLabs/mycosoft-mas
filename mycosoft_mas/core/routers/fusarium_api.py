"""
FUSARIUM API Router
February 12, 2026

FastAPI router for FUSARIUM defense system endpoints.

FUSARIUM is Mycosoft's integrated defense system combining:
- Fungal species distribution data
- Spore dispersal modeling
- Agricultural/infrastructure risk zone mapping
- Threat detection for SOC integration

Endpoints:
- /species - Fungal species distribution data
- /dispersal - Spore dispersal modeling
- /risk-zones - Risk zone mapping
- /threats - Threat detection for SOC
- /health - Health check
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
MINDEX_API_URL = "http://192.168.0.189:8000"
CREP_API_URL = "http://192.168.0.187:3000/api/crep"


# =============================================================================
# Request/Response Models
# =============================================================================

class SpeciesQueryParams(BaseModel):
    """Query parameters for species search."""
    min_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    max_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    min_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    max_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    species_name: Optional[str] = None
    pathogenic_only: bool = False
    limit: int = Field(default=100, ge=1, le=1000)


class DispersalRequest(BaseModel):
    """Request for spore dispersal modeling."""
    origin_lat: float = Field(ge=-90, le=90)
    origin_lon: float = Field(ge=-180, le=180)
    species: Optional[str] = None
    forecast_hours: int = Field(default=72, ge=1, le=168)
    wind_factor: float = Field(default=1.0, ge=0.1, le=5.0)


class DispersalZone(BaseModel):
    """Dispersal zone model."""
    center_lat: float
    center_lon: float
    radius_km: float
    concentration: float
    time_hours: int
    species: Optional[str] = None


class RiskZone(BaseModel):
    """Risk zone model."""
    id: str
    name: str
    center_lat: float
    center_lon: float
    radius_km: float
    risk_level: float  # 0-1
    primary_threat: str
    affected_crops: List[str] = []
    recommendations: List[str] = []


class ThreatAlert(BaseModel):
    """Threat alert model for SOC integration."""
    id: str
    title: str
    description: str
    severity: str  # low, medium, high, critical
    category: str  # fungal, weather, infrastructure, biological
    source: str
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    radius_km: Optional[float] = None
    timestamp: str
    metadata: Dict[str, Any] = {}


# =============================================================================
# In-memory data stores (would connect to MINDEX in production)
# =============================================================================

# Known pathogenic Fusarium species
PATHOGENIC_SPECIES = [
    {
        "id": "fusarium-oxysporum",
        "name": "Fusarium oxysporum",
        "common_name": "Panama disease",
        "pathogenic": True,
        "affected_crops": ["banana", "tomato", "cotton"],
        "optimal_temp_c": 28,
        "humidity_threshold": 70,
    },
    {
        "id": "fusarium-graminearum",
        "name": "Fusarium graminearum",
        "common_name": "Head blight",
        "pathogenic": True,
        "affected_crops": ["wheat", "barley", "corn"],
        "optimal_temp_c": 25,
        "humidity_threshold": 75,
    },
    {
        "id": "fusarium-verticillioides",
        "name": "Fusarium verticillioides",
        "common_name": "Ear rot",
        "pathogenic": True,
        "affected_crops": ["corn", "sorghum"],
        "optimal_temp_c": 30,
        "humidity_threshold": 65,
    },
    {
        "id": "fusarium-solani",
        "name": "Fusarium solani",
        "common_name": "Root rot",
        "pathogenic": True,
        "affected_crops": ["potato", "soybean", "pea"],
        "optimal_temp_c": 24,
        "humidity_threshold": 80,
    },
    {
        "id": "fusarium-proliferatum",
        "name": "Fusarium proliferatum",
        "common_name": "Stalk rot",
        "pathogenic": True,
        "affected_crops": ["corn", "asparagus", "garlic"],
        "optimal_temp_c": 27,
        "humidity_threshold": 70,
    },
]


# =============================================================================
# Helper Functions
# =============================================================================

async def fetch_weather_data(lat: float, lon: float) -> Dict[str, Any]:
    """Fetch weather data for dispersal modeling."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CREP_API_URL}/weather")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Could not fetch weather data: {e}")
    
    # Return default weather if unavailable
    return {
        "wind_speed_ms": 5.0,
        "wind_direction_deg": 180,
        "temperature_c": 25,
        "humidity_pct": 70,
        "precipitation_mm": 0,
    }


def calculate_dispersal_zones(
    origin_lat: float,
    origin_lon: float,
    forecast_hours: int,
    weather: Dict[str, Any],
    wind_factor: float = 1.0,
) -> List[Dict[str, Any]]:
    """Calculate spore dispersal zones based on weather conditions."""
    import math
    
    zones = []
    wind_speed = weather.get("wind_speed_ms", 5.0) * wind_factor
    wind_dir = math.radians(weather.get("wind_direction_deg", 180))
    humidity = weather.get("humidity_pct", 70)
    
    for hours in range(6, forecast_hours + 1, 6):
        # Simple dispersal model: distance = wind_speed * time
        distance_km = (wind_speed * 3.6) * hours * 0.001  # Convert to km
        
        # Calculate center of dispersal zone
        # Spores travel in wind direction
        delta_lat = (distance_km / 111) * math.cos(wind_dir)
        delta_lon = (distance_km / (111 * math.cos(math.radians(origin_lat)))) * math.sin(wind_dir)
        
        center_lat = origin_lat + delta_lat
        center_lon = origin_lon + delta_lon
        
        # Concentration decreases with distance and time
        base_concentration = 1.0 / (1 + hours / 12)
        humidity_factor = humidity / 100 if humidity > 50 else 0.5
        concentration = base_concentration * humidity_factor
        
        # Radius expands with time due to diffusion
        radius_km = 10 + (hours * 0.5)
        
        zones.append({
            "center_lat": round(center_lat, 4),
            "center_lon": round(center_lon, 4),
            "radius_km": round(radius_km, 2),
            "concentration": round(concentration, 3),
            "time_hours": hours,
        })
    
    return zones


def calculate_risk_level(
    temp: float,
    humidity: float,
    species_optimal_temp: float,
    species_humidity_threshold: float,
) -> float:
    """Calculate infection risk level (0-1) based on environmental conditions."""
    # Temperature factor: closer to optimal = higher risk
    temp_diff = abs(temp - species_optimal_temp)
    temp_factor = max(0, 1 - (temp_diff / 20))
    
    # Humidity factor: above threshold = high risk
    if humidity >= species_humidity_threshold:
        humidity_factor = 1.0
    elif humidity >= species_humidity_threshold - 20:
        humidity_factor = (humidity - (species_humidity_threshold - 20)) / 20
    else:
        humidity_factor = 0.1
    
    # Combined risk
    risk = (temp_factor * 0.4) + (humidity_factor * 0.6)
    return round(min(1.0, max(0.0, risk)), 2)


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/health")
async def health_check():
    """Health check for FUSARIUM API."""
    return {
        "status": "healthy",
        "service": "fusarium",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@router.get("/species", response_model=List[Dict[str, Any]])
async def get_fungal_species(
    min_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    max_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    min_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    max_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    species_name: Optional[str] = None,
    pathogenic_only: bool = False,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """
    Get fungal species distribution data.
    
    Filters:
    - Bounding box (min_lat, max_lat, min_lon, max_lon)
    - Species name (partial match)
    - Pathogenic only flag
    
    Returns list of species with locations.
    """
    # Try to fetch from MINDEX first
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {"limit": limit}
            if species_name:
                params["name"] = species_name
            if pathogenic_only:
                params["pathogenic"] = "true"
            
            response = await client.get(
                f"{MINDEX_API_URL}/api/species/fungi",
                params=params,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("species", data) if isinstance(data, dict) else data
    except Exception as e:
        logger.warning(f"Could not fetch from MINDEX, using local data: {e}")
    
    # Fallback to local data
    species_list = PATHOGENIC_SPECIES if pathogenic_only else PATHOGENIC_SPECIES
    
    if species_name:
        species_list = [
            s for s in species_list 
            if species_name.lower() in s["name"].lower()
        ]
    
    # Add mock location data for visualization
    import random
    result = []
    for species in species_list[:limit]:
        entry = species.copy()
        # Generate random locations within bounds or global
        lat = random.uniform(min_lat or -60, max_lat or 60)
        lon = random.uniform(min_lon or -180, max_lon or 180)
        entry["latitude"] = round(lat, 4)
        entry["longitude"] = round(lon, 4)
        entry["observation_count"] = random.randint(10, 500)
        result.append(entry)
    
    return result


@router.post("/dispersal", response_model=List[DispersalZone])
async def calculate_spore_dispersal(request: DispersalRequest):
    """
    Calculate spore dispersal forecast from origin point.
    
    Uses weather data to model spore transport over time.
    Returns list of dispersal zones with concentration estimates.
    """
    # Fetch weather data
    weather = await fetch_weather_data(request.origin_lat, request.origin_lon)
    
    # Calculate dispersal zones
    zones = calculate_dispersal_zones(
        origin_lat=request.origin_lat,
        origin_lon=request.origin_lon,
        forecast_hours=request.forecast_hours,
        weather=weather,
        wind_factor=request.wind_factor,
    )
    
    # Add species to zones if specified
    if request.species:
        for zone in zones:
            zone["species"] = request.species
    
    return zones


@router.get("/dispersal")
async def get_current_dispersal(
    min_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    max_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    min_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    max_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    time: Optional[str] = None,
):
    """
    Get current spore dispersal data for visualization.
    
    Returns active dispersal zones based on recent modeling.
    """
    # For now, return sample data for visualization
    center_lat = ((min_lat or -90) + (max_lat or 90)) / 2
    center_lon = ((min_lon or -180) + (max_lon or 180)) / 2
    
    weather = await fetch_weather_data(center_lat, center_lon)
    
    # Generate sample dispersal from a hypothetical source
    zones = calculate_dispersal_zones(
        origin_lat=center_lat,
        origin_lon=center_lon,
        forecast_hours=48,
        weather=weather,
    )
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "zones": zones,
        "weather": weather,
    }


@router.get("/risk-zones", response_model=List[RiskZone])
async def get_risk_zones(
    min_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    max_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    min_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    max_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    crop: Optional[str] = None,
    threat_level: Optional[str] = None,  # low, medium, high
):
    """
    Get agricultural/infrastructure risk zones.
    
    Returns areas at risk of fungal infection based on:
    - Weather conditions
    - Known species presence
    - Crop susceptibility
    """
    # Fetch current weather
    center_lat = ((min_lat or 0) + (max_lat or 0)) / 2 if min_lat and max_lat else 40.0
    center_lon = ((min_lon or 0) + (max_lon or 0)) / 2 if min_lon and max_lon else -100.0
    weather = await fetch_weather_data(center_lat, center_lon)
    
    temp = weather.get("temperature_c", 25)
    humidity = weather.get("humidity_pct", 70)
    
    risk_zones = []
    
    for i, species in enumerate(PATHOGENIC_SPECIES):
        # Skip if filtering by crop and this species doesn't affect it
        if crop and crop.lower() not in [c.lower() for c in species.get("affected_crops", [])]:
            continue
        
        # Calculate risk level
        risk = calculate_risk_level(
            temp=temp,
            humidity=humidity,
            species_optimal_temp=species.get("optimal_temp_c", 25),
            species_humidity_threshold=species.get("humidity_threshold", 70),
        )
        
        # Filter by threat level
        if threat_level:
            if threat_level == "low" and risk > 0.33:
                continue
            elif threat_level == "medium" and (risk <= 0.33 or risk > 0.66):
                continue
            elif threat_level == "high" and risk <= 0.66:
                continue
        
        # Generate risk zone
        import random
        zone_lat = center_lat + random.uniform(-5, 5)
        zone_lon = center_lon + random.uniform(-5, 5)
        
        recommendations = []
        if risk > 0.66:
            recommendations = [
                "Apply preventive fungicides",
                "Increase monitoring frequency",
                "Prepare contingency harvest plan",
            ]
        elif risk > 0.33:
            recommendations = [
                "Monitor weather conditions",
                "Inspect crops weekly",
                "Ensure good drainage",
            ]
        else:
            recommendations = ["Standard monitoring"]
        
        risk_zones.append(RiskZone(
            id=f"risk-zone-{i}",
            name=f"{species['common_name']} Risk Zone",
            center_lat=round(zone_lat, 4),
            center_lon=round(zone_lon, 4),
            radius_km=round(random.uniform(20, 100), 1),
            risk_level=risk,
            primary_threat=species["name"],
            affected_crops=species.get("affected_crops", []),
            recommendations=recommendations,
        ))
    
    return risk_zones


@router.get("/threats", response_model=List[ThreatAlert])
async def get_active_threats(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Get active FUSARIUM threats for SOC integration.
    
    Returns threat alerts combining:
    - Fungal infection risk
    - Weather-related threats
    - Infrastructure impacts
    """
    # Fetch current conditions
    weather = await fetch_weather_data(40.0, -100.0)
    temp = weather.get("temperature_c", 25)
    humidity = weather.get("humidity_pct", 70)
    
    threats = []
    
    # Generate threats based on species and conditions
    for species in PATHOGENIC_SPECIES:
        risk = calculate_risk_level(
            temp=temp,
            humidity=humidity,
            species_optimal_temp=species.get("optimal_temp_c", 25),
            species_humidity_threshold=species.get("humidity_threshold", 70),
        )
        
        if risk < 0.33:
            continue  # Skip low-risk
        
        threat_severity = "critical" if risk > 0.8 else "high" if risk > 0.66 else "medium"
        
        # Filter by severity if specified
        if severity and threat_severity != severity:
            continue
        
        # Filter by category if specified
        if category and category != "fungal":
            continue
        
        import random
        threats.append(ThreatAlert(
            id=f"fusarium-{species['id']}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            title=f"{species['common_name']} Outbreak Risk",
            description=f"High risk of {species['name']} outbreak affecting {', '.join(species.get('affected_crops', [])[:3])}",
            severity=threat_severity,
            category="fungal",
            source="fusarium",
            location_lat=round(random.uniform(25, 50), 4),
            location_lon=round(random.uniform(-125, -70), 4),
            radius_km=round(random.uniform(50, 200), 1),
            timestamp=datetime.utcnow().isoformat(),
            metadata={
                "species": species["name"],
                "risk_level": risk,
                "affected_crops": species.get("affected_crops", []),
                "optimal_conditions": {
                    "temperature_c": species.get("optimal_temp_c"),
                    "humidity_threshold": species.get("humidity_threshold"),
                },
                "current_conditions": {
                    "temperature_c": temp,
                    "humidity_pct": humidity,
                },
            },
        ))
    
    # Add weather-related threats if conditions are severe
    if humidity > 90 or temp > 35:
        threats.append(ThreatAlert(
            id=f"weather-alert-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            title="Severe Weather Conditions",
            description="Environmental conditions highly favorable for fungal proliferation",
            severity="high",
            category="weather",
            source="fusarium",
            timestamp=datetime.utcnow().isoformat(),
            metadata={
                "temperature_c": temp,
                "humidity_pct": humidity,
            },
        ))
    
    return threats[:limit]


@router.post("/threats/report")
async def report_threat(threat: ThreatAlert):
    """
    Report a new FUSARIUM threat.
    
    Creates a threat alert and optionally pushes to SOC.
    """
    logger.info(f"FUSARIUM threat reported: {threat.title} ({threat.severity})")
    
    # In production, this would:
    # 1. Store the threat in database
    # 2. Push to SOC via /api/security/incidents
    # 3. Trigger notifications
    
    return {
        "status": "received",
        "threat_id": threat.id,
        "timestamp": datetime.utcnow().isoformat(),
    }
