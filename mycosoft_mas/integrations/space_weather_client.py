"""
Space Weather Client

Provides access to space weather and astronomical data from:
- NASA DONKI (Space Weather Database)
- NASA NEO (Near Earth Objects)
- NOAA Space Weather Prediction Center
- SOHO/STEREO Solar Observatories
- GOES Satellite Data
- ACE/DSCOVR Real-time Solar Wind

Environment Variables:
    NASA_API_KEY: NASA API key (optional, DEMO_KEY works for testing)
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


class SpaceWeatherClient:
    """
    Client for space weather and astronomical data APIs.
    
    Provides unified access to:
    - Solar activity (flares, CMEs, solar wind)
    - Geomagnetic conditions (Kp index, storms)
    - Near Earth Objects
    - Satellite data (GOES, ACE, DSCOVR)
    - Weather forecasts
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the space weather client."""
        self.config = config or {}
        self.nasa_api_key = self.config.get("nasa_api_key") or os.getenv("NASA_API_KEY", "DEMO_KEY")
        self.timeout = self.config.get("timeout", 30)
        
        # Base URLs
        self.nasa_donki_url = "https://api.nasa.gov/DONKI"
        self.nasa_neo_url = "https://api.nasa.gov/neo/rest/v1"
        self.noaa_swpc_url = "https://services.swpc.noaa.gov"
        self.noaa_weather_url = "https://api.weather.gov"
        
        self._client: Optional[httpx.AsyncClient] = None
        logger.info("Space weather client initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of space weather APIs."""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.noaa_swpc_url}/products/solar-wind/plasma-1-day.json"
            )
            return {
                "status": "ok" if response.status_code == 200 else "degraded",
                "noaa_swpc": response.status_code == 200,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # NASA DONKI APIs
    async def get_cme(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get Coronal Mass Ejection data."""
        client = await self._get_client()
        params = {"api_key": self.nasa_api_key}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        
        response = await client.get(f"{self.nasa_donki_url}/CME", params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_solar_flares(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get solar flare data."""
        client = await self._get_client()
        params = {"api_key": self.nasa_api_key}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        
        response = await client.get(f"{self.nasa_donki_url}/FLR", params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_geomagnetic_storms(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get geomagnetic storm data."""
        client = await self._get_client()
        params = {"api_key": self.nasa_api_key}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        
        response = await client.get(f"{self.nasa_donki_url}/GST", params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_solar_energetic_particles(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get Solar Energetic Particle data."""
        client = await self._get_client()
        params = {"api_key": self.nasa_api_key}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        
        response = await client.get(f"{self.nasa_donki_url}/SEP", params=params)
        response.raise_for_status()
        return response.json()
    
    # NASA NEO APIs
    async def get_neo_feed(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get Near Earth Object feed."""
        client = await self._get_client()
        params = {"api_key": self.nasa_api_key}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        response = await client.get(f"{self.nasa_neo_url}/feed", params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_neo_browse(self) -> Dict[str, Any]:
        """Browse all Near Earth Objects."""
        client = await self._get_client()
        response = await client.get(
            f"{self.nasa_neo_url}/neo/browse",
            params={"api_key": self.nasa_api_key}
        )
        response.raise_for_status()
        return response.json()
    
    # NOAA Space Weather APIs
    async def get_solar_wind(self, period: str = "1-day") -> List[List[Any]]:
        """Get real-time solar wind data."""
        client = await self._get_client()
        response = await client.get(
            f"{self.noaa_swpc_url}/products/solar-wind/plasma-{period}.json"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_kp_index(self) -> List[List[Any]]:
        """Get planetary K-index (geomagnetic activity)."""
        client = await self._get_client()
        response = await client.get(
            f"{self.noaa_swpc_url}/products/noaa-planetary-k-index.json"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_space_weather_alerts(self) -> List[Dict[str, Any]]:
        """Get active space weather alerts."""
        client = await self._get_client()
        response = await client.get(
            f"{self.noaa_swpc_url}/products/alerts.json"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_aurora_forecast(self) -> Dict[str, Any]:
        """Get aurora forecast data."""
        client = await self._get_client()
        response = await client.get(
            f"{self.noaa_swpc_url}/json/ovation_aurora_latest.json"
        )
        response.raise_for_status()
        return response.json()
    
    # GOES Satellite Data
    async def get_xray_flux(self) -> List[List[Any]]:
        """Get GOES X-ray flux data."""
        client = await self._get_client()
        response = await client.get(
            f"{self.noaa_swpc_url}/json/goes/primary/xrays-7-day.json"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_proton_flux(self) -> List[List[Any]]:
        """Get GOES proton flux data."""
        client = await self._get_client()
        response = await client.get(
            f"{self.noaa_swpc_url}/json/goes/primary/integral-protons-7-day.json"
        )
        response.raise_for_status()
        return response.json()
    
    # ACE/DSCOVR Data
    async def get_ace_mag(self, period: str = "1h") -> List[List[Any]]:
        """Get ACE magnetometer data."""
        client = await self._get_client()
        response = await client.get(
            f"{self.noaa_swpc_url}/products/ace/mag_{period}.json"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_dscovr_plasma(self) -> List[List[Any]]:
        """Get DSCOVR plasma data."""
        client = await self._get_client()
        response = await client.get(
            f"{self.noaa_swpc_url}/products/dscovr/plasma-1-day.json"
        )
        response.raise_for_status()
        return response.json()
    
    # Weather API
    async def get_weather_forecast(
        self,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """Get weather forecast for location."""
        client = await self._get_client()
        
        # First get the grid point
        headers = {"User-Agent": "MycoSoft-MAS/1.0"}
        response = await client.get(
            f"{self.noaa_weather_url}/points/{lat},{lon}",
            headers=headers
        )
        response.raise_for_status()
        point_data = response.json()
        
        # Get the forecast
        forecast_url = point_data["properties"]["forecast"]
        response = await client.get(forecast_url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def get_weather_alerts(
        self,
        state: Optional[str] = None,
        active: bool = True
    ) -> Dict[str, Any]:
        """Get weather alerts."""
        client = await self._get_client()
        headers = {"User-Agent": "MycoSoft-MAS/1.0"}
        
        url = f"{self.noaa_weather_url}/alerts"
        if active:
            url += "/active"
        
        params = {}
        if state:
            params["area"] = state
        
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        logger.info("Space weather client closed")
