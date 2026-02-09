"""
Earth-2 Forecaster - February 6, 2026

Integration with NVIDIA Earth-2 / Earth2Studio for weather forecasts.
Provides weather, storm, wildfire, and environmental predictions.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .prediction_types import (
    EntityType,
    GeoPoint,
    PredictedPosition,
    PredictionSource,
)

logger = logging.getLogger("Earth2Forecaster")


class Earth2Forecaster:
    """
    Integration with Earth-2 AI weather models.
    
    Supports:
    - Weather forecasts (temperature, precipitation, wind)
    - Storm track predictions
    - Wildfire spread modeling
    - Air quality forecasts
    """
    
    model_version = "1.0.0"
    
    # Forecast types
    FORECAST_WEATHER = "weather"
    FORECAST_STORM = "storm"
    FORECAST_WILDFIRE = "wildfire"
    FORECAST_AIR_QUALITY = "air_quality"
    
    # Available models
    MODELS = {
        "fcn": {
            "name": "FourCastNet",
            "resolution_km": 25,
            "max_horizon_hours": 240,
        },
        "pangu": {
            "name": "Pangu-Weather",
            "resolution_km": 25,
            "max_horizon_hours": 168,
        },
        "graphcast": {
            "name": "GraphCast",
            "resolution_km": 28,
            "max_horizon_hours": 240,
        },
    }
    
    def __init__(self, gpu_gateway_url: Optional[str] = None):
        self.gpu_gateway_url = gpu_gateway_url or os.getenv(
            "GPU_GATEWAY_URL", "http://localhost:8100"
        )
        self._earth2_available = False
        self._model_cache: Dict[str, Any] = {}
    
    async def initialize(self):
        """Check Earth-2 availability and warm up models."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.gpu_gateway_url}/health",
                    timeout=5.0
                )
                if response.status_code == 200:
                    self._earth2_available = True
                    logger.info("Earth-2 GPU gateway available")
        except Exception as e:
            logger.warning(f"Earth-2 not available: {e}")
            self._earth2_available = False
    
    async def get_weather_forecast(
        self,
        location: GeoPoint,
        from_time: datetime,
        to_time: datetime,
        resolution_hours: int = 1,
        model: str = "fcn"
    ) -> List[Dict[str, Any]]:
        """
        Get weather forecast for a location.
        
        Returns list of forecast points with temperature, precipitation,
        wind speed/direction, humidity, etc.
        """
        forecasts = []
        
        if self._earth2_available:
            forecasts = await self._fetch_earth2_forecast(
                location, from_time, to_time, resolution_hours, model, "weather"
            )
        else:
            # Generate synthetic forecast for development
            forecasts = self._generate_synthetic_weather(
                location, from_time, to_time, resolution_hours
            )
        
        return forecasts
    
    async def get_storm_tracks(
        self,
        region_bounds: Tuple[float, float, float, float],  # min_lat, min_lng, max_lat, max_lng
        from_time: datetime,
        to_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get storm track predictions for a region.
        
        Returns list of storms with predicted paths.
        """
        if self._earth2_available:
            return await self._fetch_storm_tracks(region_bounds, from_time, to_time)
        
        # Return empty for now without real data
        return []
    
    async def get_wildfire_spread(
        self,
        fire_location: GeoPoint,
        wind_speed: float,
        wind_direction: float,
        fuel_moisture: float = 0.3,
        hours_ahead: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Predict wildfire spread based on conditions.
        
        Returns contours of predicted fire perimeter at different times.
        """
        predictions = []
        
        # Simple spread model
        # In production, would use Earth-2 coupled with fire models
        
        base_spread_rate = 0.5  # km/h base rate
        wind_factor = 1 + (wind_speed / 20)  # Faster with wind
        moisture_factor = 1 - fuel_moisture  # Faster with dry fuel
        
        spread_rate = base_spread_rate * wind_factor * moisture_factor
        
        for hour in range(1, hours_ahead + 1):
            # Calculate radius in direction of wind
            downwind_radius = spread_rate * hour * 1.5  # Faster downwind
            crosswind_radius = spread_rate * hour * 0.5  # Slower crosswind
            upwind_radius = spread_rate * hour * 0.2  # Much slower upwind
            
            predictions.append({
                "hour": hour,
                "timestamp": (datetime.now(timezone.utc) + timedelta(hours=hour)).isoformat(),
                "center": fire_location.to_dict(),
                "radii": {
                    "downwind_km": downwind_radius,
                    "crosswind_km": crosswind_radius,
                    "upwind_km": upwind_radius,
                },
                "wind_direction": wind_direction,
                "area_km2": 3.14159 * downwind_radius * crosswind_radius,
            })
        
        return predictions
    
    async def get_forecast_tiles(
        self,
        variable: str,  # "temperature", "precipitation", "wind", etc.
        time: datetime,
        zoom: int,
        tile_x: int,
        tile_y: int,
        model: str = "fcn"
    ) -> Optional[bytes]:
        """
        Get map tile for forecast visualization.
        
        Returns PNG tile data for overlay on map.
        """
        if not self._earth2_available:
            return None
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.gpu_gateway_url}/forecast/tiles/{model}/{variable}",
                    params={
                        "time": time.isoformat(),
                        "z": zoom,
                        "x": tile_x,
                        "y": tile_y,
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.content
        except Exception as e:
            logger.error(f"Failed to fetch forecast tile: {e}")
        
        return None
    
    async def _fetch_earth2_forecast(
        self,
        location: GeoPoint,
        from_time: datetime,
        to_time: datetime,
        resolution_hours: int,
        model: str,
        forecast_type: str
    ) -> List[Dict[str, Any]]:
        """Fetch forecast from Earth-2 GPU gateway."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gpu_gateway_url}/forecast/point",
                    json={
                        "lat": location.lat,
                        "lng": location.lng,
                        "from_time": from_time.isoformat(),
                        "to_time": to_time.isoformat(),
                        "resolution_hours": resolution_hours,
                        "model": model,
                        "type": forecast_type,
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    return response.json().get("forecasts", [])
        except Exception as e:
            logger.error(f"Failed to fetch Earth-2 forecast: {e}")
        
        return []
    
    async def _fetch_storm_tracks(
        self,
        bounds: Tuple[float, float, float, float],
        from_time: datetime,
        to_time: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch storm tracks from Earth-2."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gpu_gateway_url}/forecast/storms",
                    json={
                        "bounds": {
                            "min_lat": bounds[0],
                            "min_lng": bounds[1],
                            "max_lat": bounds[2],
                            "max_lng": bounds[3],
                        },
                        "from_time": from_time.isoformat(),
                        "to_time": to_time.isoformat(),
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    return response.json().get("storms", [])
        except Exception as e:
            logger.error(f"Failed to fetch storm tracks: {e}")
        
        return []
    
    def _generate_synthetic_weather(
        self,
        location: GeoPoint,
        from_time: datetime,
        to_time: datetime,
        resolution_hours: int
    ) -> List[Dict[str, Any]]:
        """Generate synthetic weather data for testing."""
        import math
        import random
        
        forecasts = []
        current_time = from_time
        
        # Base conditions vary by latitude
        base_temp = 15 + 20 * math.cos(math.radians(location.lat))  # Warmer near equator
        
        while current_time <= to_time:
            # Daily temperature cycle
            hour = current_time.hour
            temp_variation = 5 * math.sin(math.radians((hour - 6) * 15))  # Peak at 2pm
            
            # Random weather variability
            random_var = random.gauss(0, 2)
            
            temperature = base_temp + temp_variation + random_var
            
            # Simple precipitation probability
            precip_prob = 0.1 + 0.2 * random.random()
            precipitation = precip_prob * random.uniform(0, 10) if random.random() < precip_prob else 0
            
            # Wind
            wind_speed = 5 + random.uniform(0, 15)
            wind_direction = random.uniform(0, 360)
            
            forecasts.append({
                "timestamp": current_time.isoformat(),
                "location": location.to_dict(),
                "temperature_c": round(temperature, 1),
                "feels_like_c": round(temperature - wind_speed * 0.2, 1),
                "humidity_percent": round(50 + random.uniform(-20, 30)),
                "precipitation_mm": round(precipitation, 1),
                "precipitation_probability": round(precip_prob, 2),
                "wind_speed_kmh": round(wind_speed, 1),
                "wind_direction_deg": round(wind_direction),
                "cloud_cover_percent": round(random.uniform(0, 100)),
                "uv_index": max(0, round(8 * math.sin(math.radians(hour * 7.5)) + random.uniform(-1, 1))),
                "model": "synthetic",
                "source": "development",
            })
            
            current_time += timedelta(hours=resolution_hours)
        
        return forecasts


# Singleton instance
_forecaster: Optional[Earth2Forecaster] = None


async def get_earth2_forecaster() -> Earth2Forecaster:
    """Get singleton Earth2Forecaster instance."""
    global _forecaster
    if _forecaster is None:
        _forecaster = Earth2Forecaster()
        await _forecaster.initialize()
    return _forecaster