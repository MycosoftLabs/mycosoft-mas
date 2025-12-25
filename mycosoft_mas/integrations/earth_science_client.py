"""
Earth Science Client

Provides access to earth science and geophysics data from:
- USGS Earthquake API
- NOAA Tides & Currents
- NDBC Buoy Data
- USACE Water Management (Levees/Dams)
- NWS Flood Data
- USGS Water Services
- IRIS Seismic Data
- Marine/Port AIS Data

No API keys required for most services (public data).
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


class EarthScienceClient:
    """
    Client for earth science and geophysics data APIs.
    
    Provides unified access to:
    - Earthquakes and seismic events
    - Tides and ocean currents
    - Buoy observations
    - River levels and flood data
    - Levee/dam status
    - Marine traffic (AIS)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the earth science client."""
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)
        
        # API Keys (mostly optional for public APIs)
        self.marine_traffic_key = self.config.get("marine_traffic_key") or os.getenv("MARINE_TRAFFIC_API_KEY", "")
        
        self._client: Optional[httpx.AsyncClient] = None
        logger.info("Earth science client initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of earth science APIs."""
        try:
            client = await self._get_client()
            response = await client.get(
                "https://earthquake.usgs.gov/fdsnws/event/1/count",
                params={"format": "text", "starttime": "2024-01-01"}
            )
            return {
                "status": "ok" if response.status_code == 200 else "degraded",
                "usgs_earthquake": response.status_code == 200,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # USGS Earthquake APIs
    async def get_earthquakes(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        min_magnitude: float = 2.5,
        max_magnitude: Optional[float] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get earthquake data from USGS."""
        client = await self._get_client()
        params = {
            "format": "geojson",
            "minmagnitude": min_magnitude,
            "limit": limit
        }
        if start_time:
            params["starttime"] = start_time
        if end_time:
            params["endtime"] = end_time
        if max_magnitude:
            params["maxmagnitude"] = max_magnitude
        if lat and lon:
            params["latitude"] = lat
            params["longitude"] = lon
            if radius_km:
                params["maxradiuskm"] = radius_km
        
        response = await client.get(
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    async def get_earthquake_count(
        self,
        start_time: Optional[str] = None,
        min_magnitude: float = 2.5
    ) -> int:
        """Get count of earthquakes matching criteria."""
        client = await self._get_client()
        params = {
            "format": "text",
            "minmagnitude": min_magnitude
        }
        if start_time:
            params["starttime"] = start_time
        
        response = await client.get(
            "https://earthquake.usgs.gov/fdsnws/event/1/count",
            params=params
        )
        response.raise_for_status()
        return int(response.text.strip())
    
    # NOAA Tides & Currents
    async def get_tide_predictions(
        self,
        station_id: str,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None,
        datum: str = "MLLW"
    ) -> Dict[str, Any]:
        """Get tide predictions for a station."""
        client = await self._get_client()
        params = {
            "product": "predictions",
            "application": "MycoSoft_MAS",
            "station": station_id,
            "datum": datum,
            "units": "metric",
            "time_zone": "gmt",
            "format": "json"
        }
        if begin_date:
            params["begin_date"] = begin_date
        if end_date:
            params["end_date"] = end_date
        
        response = await client.get(
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    async def get_water_levels(
        self,
        station_id: str,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get observed water levels for a station."""
        client = await self._get_client()
        params = {
            "product": "water_level",
            "application": "MycoSoft_MAS",
            "station": station_id,
            "datum": "MLLW",
            "units": "metric",
            "time_zone": "gmt",
            "format": "json"
        }
        if begin_date:
            params["begin_date"] = begin_date
        if end_date:
            params["end_date"] = end_date
        
        response = await client.get(
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    async def get_tide_stations(
        self,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of tide stations."""
        client = await self._get_client()
        params = {"type": "tidepredictions", "units": "metric"}
        
        response = await client.get(
            "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        if state and "stations" in data:
            data["stations"] = [
                s for s in data["stations"] 
                if s.get("state", "").upper() == state.upper()
            ]
        
        return data
    
    # NDBC Buoy Data
    async def get_buoy_data(
        self,
        station_id: str,
        data_type: str = "txt"
    ) -> str:
        """Get real-time buoy data from NDBC."""
        client = await self._get_client()
        response = await client.get(
            f"https://www.ndbc.noaa.gov/data/realtime2/{station_id}.{data_type}"
        )
        response.raise_for_status()
        return response.text
    
    async def get_buoy_stations(self) -> str:
        """Get list of active buoy stations."""
        client = await self._get_client()
        response = await client.get(
            "https://www.ndbc.noaa.gov/activestations.xml"
        )
        response.raise_for_status()
        return response.text
    
    # USGS Water Services
    async def get_streamflow(
        self,
        site_id: Optional[str] = None,
        state: Optional[str] = None,
        period: str = "P7D"
    ) -> Dict[str, Any]:
        """Get streamflow (discharge) data from USGS."""
        client = await self._get_client()
        params = {
            "format": "json",
            "parameterCd": "00060",  # Discharge
            "period": period
        }
        if site_id:
            params["sites"] = site_id
        if state:
            params["stateCd"] = state
        
        response = await client.get(
            "https://waterservices.usgs.gov/nwis/iv/",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    async def get_water_levels_usgs(
        self,
        site_id: Optional[str] = None,
        state: Optional[str] = None,
        period: str = "P7D"
    ) -> Dict[str, Any]:
        """Get gage height data from USGS."""
        client = await self._get_client()
        params = {
            "format": "json",
            "parameterCd": "00065",  # Gage height
            "period": period
        }
        if site_id:
            params["sites"] = site_id
        if state:
            params["stateCd"] = state
        
        response = await client.get(
            "https://waterservices.usgs.gov/nwis/iv/",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    # NWS Flood Data
    async def get_flood_status(
        self,
        gage_id: str
    ) -> Dict[str, Any]:
        """Get flood status for a river gage."""
        client = await self._get_client()
        response = await client.get(
            f"https://water.weather.gov/ahps2/hydrograph_to_xml.php",
            params={"gage": gage_id, "output": "xml"}
        )
        response.raise_for_status()
        return {"raw_data": response.text, "gage_id": gage_id}
    
    # USACE Water Management
    async def get_reservoir_levels(
        self,
        office: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get reservoir/dam levels from USACE CWMS."""
        client = await self._get_client()
        params = {"format": "json"}
        if office:
            params["office"] = office
        if location:
            params["name"] = location
        
        response = await client.get(
            "https://cwms-data.usace.army.mil/cwms-data/levels",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    # IRIS Seismic Data
    async def get_seismic_events(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        min_magnitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """Get seismic events from IRIS."""
        client = await self._get_client()
        params = {"format": "text"}
        if start_time:
            params["starttime"] = start_time
        if end_time:
            params["endtime"] = end_time
        if min_magnitude:
            params["minmagnitude"] = min_magnitude
        
        response = await client.get(
            "https://service.iris.edu/fdsnws/event/1/query",
            params=params
        )
        response.raise_for_status()
        return {"events": response.text}
    
    # Tsunami Warnings
    async def get_tsunami_alerts(self) -> Dict[str, Any]:
        """Get active tsunami warnings from NOAA."""
        client = await self._get_client()
        response = await client.get(
            "https://www.tsunami.gov/events/xml/PAAQAtom.xml"
        )
        response.raise_for_status()
        return {"raw_data": response.text, "type": "tsunami_alerts"}
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        logger.info("Earth science client closed")
