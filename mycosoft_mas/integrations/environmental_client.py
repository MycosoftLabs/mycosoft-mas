"""
Environmental Data Client

Provides access to environmental sensor data from:
- OpenAQ (Air Quality)
- EPA AirNow
- PurpleAir Sensors
- IQAir
- Safecast (Radiation)
- BreezoMeter
- Ambee (Multi-environmental)

Environment Variables:
    OPENAQ_API_KEY: OpenAQ API key
    EPA_AIRNOW_API_KEY: EPA AirNow API key
    PURPLEAIR_API_KEY: PurpleAir API key
    IQAIR_API_KEY: IQAir API key
    SAFECAST_API_KEY: Safecast API key (optional)
    BREEZOMETER_API_KEY: BreezoMeter API key
    AMBEE_API_KEY: Ambee API key
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class EnvironmentalClient:
    """
    Client for environmental sensor data APIs.
    
    Provides unified access to:
    - Air quality (PM2.5, PM10, O3, NO2, CO, SO2)
    - Radiation levels
    - Pollen counts
    - Fire/smoke data
    - VOC/CO2 levels
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the environmental client."""
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)
        
        # API Keys
        self.openaq_key = self.config.get("openaq_api_key") or os.getenv("OPENAQ_API_KEY", "")
        self.airnow_key = self.config.get("airnow_api_key") or os.getenv("EPA_AIRNOW_API_KEY", "")
        self.purpleair_key = self.config.get("purpleair_api_key") or os.getenv("PURPLEAIR_API_KEY", "")
        self.iqair_key = self.config.get("iqair_api_key") or os.getenv("IQAIR_API_KEY", "")
        self.safecast_key = self.config.get("safecast_api_key") or os.getenv("SAFECAST_API_KEY", "")
        self.breezometer_key = self.config.get("breezometer_api_key") or os.getenv("BREEZOMETER_API_KEY", "")
        self.ambee_key = self.config.get("ambee_api_key") or os.getenv("AMBEE_API_KEY", "")
        
        self._client: Optional[httpx.AsyncClient] = None
        logger.info("Environmental client initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of environmental APIs."""
        try:
            client = await self._get_client()
            # Check OpenAQ
            response = await client.get(
                "https://api.openaq.org/v2/countries",
                params={"limit": 1},
                headers={"X-API-Key": self.openaq_key} if self.openaq_key else {}
            )
            return {
                "status": "ok" if response.status_code == 200 else "degraded",
                "openaq": response.status_code == 200,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # OpenAQ APIs
    async def get_air_quality_measurements(
        self,
        country: Optional[str] = None,
        city: Optional[str] = None,
        location_id: Optional[int] = None,
        parameter: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get air quality measurements from OpenAQ."""
        client = await self._get_client()
        params = {"limit": limit}
        if country:
            params["country"] = country
        if city:
            params["city"] = city
        if location_id:
            params["location_id"] = location_id
        if parameter:
            params["parameter"] = parameter
        
        headers = {"X-API-Key": self.openaq_key} if self.openaq_key else {}
        response = await client.get(
            "https://api.openaq.org/v2/measurements",
            params=params,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_openaq_locations(
        self,
        country: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get monitoring locations from OpenAQ."""
        client = await self._get_client()
        params = {"limit": limit}
        if country:
            params["country"] = country
        if city:
            params["city"] = city
        
        headers = {"X-API-Key": self.openaq_key} if self.openaq_key else {}
        response = await client.get(
            "https://api.openaq.org/v2/locations",
            params=params,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    # EPA AirNow APIs
    async def get_airnow_current(
        self,
        zip_code: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        distance: int = 25
    ) -> List[Dict[str, Any]]:
        """Get current air quality from EPA AirNow."""
        if not self.airnow_key:
            raise ValueError("EPA_AIRNOW_API_KEY is required")
        
        client = await self._get_client()
        params = {
            "format": "application/json",
            "API_KEY": self.airnow_key,
            "distance": distance
        }
        
        if zip_code:
            url = "https://www.airnowapi.org/aq/observation/zipCode/current/"
            params["zipCode"] = zip_code
        elif lat and lon:
            url = "https://www.airnowapi.org/aq/observation/latLong/current/"
            params["latitude"] = lat
            params["longitude"] = lon
        else:
            raise ValueError("Either zip_code or lat/lon required")
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_airnow_forecast(
        self,
        zip_code: str,
        date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get air quality forecast from EPA AirNow."""
        if not self.airnow_key:
            raise ValueError("EPA_AIRNOW_API_KEY is required")
        
        client = await self._get_client()
        params = {
            "format": "application/json",
            "API_KEY": self.airnow_key,
            "zipCode": zip_code
        }
        if date:
            params["date"] = date
        
        response = await client.get(
            "https://www.airnowapi.org/aq/forecast/zipCode/",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    # PurpleAir APIs
    async def get_purpleair_sensors(
        self,
        nw_lat: Optional[float] = None,
        nw_lng: Optional[float] = None,
        se_lat: Optional[float] = None,
        se_lng: Optional[float] = None,
        fields: str = "pm2.5,pm10,temperature,humidity"
    ) -> Dict[str, Any]:
        """Get PurpleAir sensor data."""
        if not self.purpleair_key:
            raise ValueError("PURPLEAIR_API_KEY is required")
        
        client = await self._get_client()
        params = {"fields": fields}
        if all([nw_lat, nw_lng, se_lat, se_lng]):
            params["nwlat"] = nw_lat
            params["nwlng"] = nw_lng
            params["selat"] = se_lat
            params["selng"] = se_lng
        
        response = await client.get(
            "https://api.purpleair.com/v1/sensors",
            params=params,
            headers={"X-API-Key": self.purpleair_key}
        )
        response.raise_for_status()
        return response.json()
    
    # IQAir APIs
    async def get_iqair_nearest(
        self,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """Get air quality from nearest IQAir station."""
        if not self.iqair_key:
            raise ValueError("IQAIR_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://api.airvisual.com/v2/nearest_city",
            params={"lat": lat, "lon": lon, "key": self.iqair_key}
        )
        response.raise_for_status()
        return response.json()
    
    # Safecast Radiation APIs
    async def get_radiation_measurements(
        self,
        lat: float,
        lon: float,
        distance: int = 10000
    ) -> List[Dict[str, Any]]:
        """Get radiation measurements from Safecast."""
        client = await self._get_client()
        params = {
            "latitude": lat,
            "longitude": lon,
            "distance": distance
        }
        if self.safecast_key:
            params["api_key"] = self.safecast_key
        
        response = await client.get(
            "https://api.safecast.org/measurements.json",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    # BreezoMeter APIs
    async def get_breezometer_air_quality(
        self,
        lat: float,
        lon: float,
        features: str = "breezometer_aqi,local_aqi,health_recommendations,pollutants_concentrations"
    ) -> Dict[str, Any]:
        """Get air quality from BreezoMeter."""
        if not self.breezometer_key:
            raise ValueError("BREEZOMETER_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://api.breezometer.com/air-quality/v2/current-conditions",
            params={
                "lat": lat,
                "lon": lon,
                "key": self.breezometer_key,
                "features": features
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_breezometer_pollen(
        self,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """Get pollen data from BreezoMeter."""
        if not self.breezometer_key:
            raise ValueError("BREEZOMETER_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://api.breezometer.com/pollen/v2/forecast/daily",
            params={
                "lat": lat,
                "lon": lon,
                "key": self.breezometer_key,
                "days": 3
            }
        )
        response.raise_for_status()
        return response.json()
    
    # Ambee APIs
    async def get_ambee_air_quality(
        self,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """Get air quality from Ambee."""
        if not self.ambee_key:
            raise ValueError("AMBEE_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://api.ambeedata.com/latest/by-lat-lng",
            params={"lat": lat, "lng": lon},
            headers={"x-api-key": self.ambee_key}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_ambee_fire(
        self,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """Get fire/smoke data from Ambee."""
        if not self.ambee_key:
            raise ValueError("AMBEE_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://api.ambeedata.com/fire/latest/by-lat-lng",
            params={"lat": lat, "lng": lon},
            headers={"x-api-key": self.ambee_key}
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        logger.info("Environmental client closed")
