"""
CREP Sensor

Reads real-time global data from CREP (Common Relevant Environmental Picture):
- Flights (ADS-B data)
- Marine vessels (AIS data)
- Satellites
- Weather
- Railway
- Carbon emissions
- Space debris

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
import httpx

from mycosoft_mas.consciousness.sensors.base_sensor import BaseSensor, SensorStatus

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.world_model import WorldModel, SensorReading, DataFreshness

logger = logging.getLogger(__name__)


class CREPSensor(BaseSensor):
    """
    Sensor for CREP (Common Relevant Environmental Picture) data.
    
    Connects to the CREP collectors on the website to get real-time
    global situational awareness data.
    """
    
    # API endpoints
    CREP_API_BASE = "http://192.168.0.187:3000/api/crep"
    FALLBACK_API_BASE = "http://localhost:3010/api/crep"
    # Legacy aliases used by tests/older code.
    CREP_API = CREP_API_BASE
    MAS_API = CREP_API_BASE
    
    def __init__(self, world_model: Optional["WorldModel"] = None):
        super().__init__(world_model, "crep")
        self._client: Optional[httpx.AsyncClient] = None
        self._api_base = self.CREP_API_BASE
    
    async def connect(self) -> bool:
        """Connect to the CREP API."""
        try:
            self._client = httpx.AsyncClient(timeout=10.0)
            
            # Try primary endpoint
            try:
                response = await self._client.get(f"{self.CREP_API_BASE}/health")
                if response.status_code == 200:
                    self._api_base = self.CREP_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass
            
            # Try fallback
            try:
                response = await self._client.get(f"{self.FALLBACK_API_BASE}/health")
                if response.status_code == 200:
                    self._api_base = self.FALLBACK_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass
            
            self._mark_error("Could not connect to CREP API")
            return False
            
        except Exception as e:
            self._mark_error(str(e))
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the CREP API."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._mark_disconnected()
    
    async def read(self) -> Optional["SensorReading"]:
        """Read current CREP data."""
        from mycosoft_mas.consciousness.world_model import SensorReading, DataFreshness
        
        if not self._client:
            await self.connect()
        
        if not self.is_connected:
            return None
        
        try:
            data = {}
            
            # Get flight data
            flights = await self._get_flights()
            if flights:
                data["flights"] = flights.get("aircraft", [])
                data["flight_count"] = len(data["flights"])
            
            # Get marine data
            vessels = await self._get_marine()
            if vessels:
                data["vessels"] = vessels.get("vessels", [])
                data["vessel_count"] = len(data["vessels"])
            
            # Get satellite data
            satellites = await self._get_satellites()
            if satellites:
                data["satellites"] = satellites.get("satellites", [])
                data["satellite_count"] = len(data["satellites"])
            
            # Get weather data
            weather = await self._get_weather()
            if weather:
                data["weather"] = weather
            
            reading = SensorReading(
                sensor_type="crep",
                data=data,
                timestamp=datetime.now(timezone.utc),
                freshness=DataFreshness.LIVE if data else DataFreshness.UNAVAILABLE,
                confidence=0.9 if data else 0.0,
                source_url=self._api_base
            )
            
            self._record_reading(reading)
            return reading
            
        except Exception as e:
            self._mark_error(str(e))
            return None
    
    async def _get_flights(self) -> Optional[Dict[str, Any]]:
        """Get flight data."""
        try:
            response = await self._client.get(f"{self._api_base}/flights")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Flight data error: {e}")
        return None
    
    async def _get_marine(self) -> Optional[Dict[str, Any]]:
        """Get marine vessel data."""
        try:
            response = await self._client.get(f"{self._api_base}/marine")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Marine data error: {e}")
        return None
    
    async def _get_satellites(self) -> Optional[Dict[str, Any]]:
        """Get satellite data."""
        try:
            response = await self._client.get(f"{self._api_base}/satellites")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Satellite data error: {e}")
        return None
    
    async def _get_weather(self) -> Optional[Dict[str, Any]]:
        """Get weather data."""
        try:
            response = await self._client.get(f"{self._api_base}/weather")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Weather data error: {e}")
        return None
    
    async def get_region_data(
        self,
        lat: float,
        lon: float,
        radius_km: float = 100
    ) -> Dict[str, Any]:
        """Get CREP data for a specific region."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            params = {"lat": lat, "lon": lon, "radius": radius_km}
            
            data = {}
            
            # Get regional flight data
            response = await self._client.get(
                f"{self._api_base}/flights/region",
                params=params
            )
            if response.status_code == 200:
                data["flights"] = response.json()
            
            # Get regional marine data
            response = await self._client.get(
                f"{self._api_base}/marine/region",
                params=params
            )
            if response.status_code == 200:
                data["vessels"] = response.json()
            
            return data
            
        except Exception as e:
            return {"error": str(e)}
