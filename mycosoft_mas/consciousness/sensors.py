"""
MYCA World Sensors

Sensors for perceiving the world through various data sources:
- CREPSensor: Real-time global data (flights, ships, satellites, weather)
- Earth2Sensor: Future predictions (weather, climate, spore dispersal)
- NatureOSSensor: Life and ecosystem status
- MINDEXSensor: Knowledge and fungi data with semantic search
- MycoBrainSensor: Device telemetry

Created: Feb 11, 2026
Author: Morgan Rockwell / MYCA
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.world_model import WorldModel

logger = logging.getLogger(__name__)


class BaseSensor:
    """Base class for world sensors."""
    
    def __init__(self, world_model: "WorldModel"):
        self._world_model = world_model
        self._initialized = False
        self._last_data: Optional[Dict[str, Any]] = None
        self._last_update: Optional[datetime] = None
    
    async def initialize(self) -> None:
        """Initialize the sensor."""
        self._initialized = True
    
    async def read(self) -> Optional[Dict[str, Any]]:
        """Read current sensor data."""
        raise NotImplementedError
    
    @property
    def is_available(self) -> bool:
        """Check if sensor is available."""
        return self._initialized


class CREPSensor(BaseSensor):
    """
    CREP (Common Relevant Environmental Picture) Sensor.
    
    Provides real-time data on:
    - Commercial flights
    - Maritime vessels
    - Satellites
    - Weather conditions
    """
    
    def __init__(self, world_model: "WorldModel"):
        super().__init__(world_model)
        self.crep_url = os.environ.get("CREP_API_URL", "http://192.168.0.187:3000/api/crep")
    
    async def read(self) -> Optional[Dict[str, Any]]:
        """Read current CREP data."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.crep_url}/status")
                if response.status_code == 200:
                    self._last_data = response.json()
                    self._last_update = datetime.now(timezone.utc)
                    return self._last_data
        except Exception as e:
            logger.warning(f"CREP sensor read failed: {e}")
        return self._last_data
    
    async def get_flights(self) -> Dict[str, Any]:
        """Get current flight data."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.crep_url}/flights")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"CREP flights fetch failed: {e}")
        return {"count": 0, "flights": []}
    
    async def get_vessels(self) -> Dict[str, Any]:
        """Get current maritime vessel data."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.crep_url}/vessels")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"CREP vessels fetch failed: {e}")
        return {"count": 0, "vessels": []}
    
    async def get_satellites(self) -> Dict[str, Any]:
        """Get current satellite data."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.crep_url}/satellites")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"CREP satellites fetch failed: {e}")
        return {"count": 0, "satellites": []}


class Earth2Sensor(BaseSensor):
    """
    Earth2 Prediction Sensor.
    
    Provides future predictions from NVIDIA Earth2Studio:
    - Weather forecasts
    - Climate projections
    - Spore dispersal predictions
    """
    
    def __init__(self, world_model: "WorldModel"):
        super().__init__(world_model)
        self.earth2_url = os.environ.get("EARTH2_API_URL", "http://192.168.0.187:3000/api/earth2")
    
    async def read(self) -> Optional[Dict[str, Any]]:
        """Read current Earth2 predictions."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.earth2_url}/predictions")
                if response.status_code == 200:
                    self._last_data = response.json()
                    self._last_update = datetime.now(timezone.utc)
                    return self._last_data
        except Exception as e:
            logger.warning(f"Earth2 sensor read failed: {e}")
        return self._last_data
    
    async def get_weather_forecast(self, location: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Get weather forecast."""
        try:
            params = {}
            if location:
                params["lat"] = location.get("lat", 0)
                params["lon"] = location.get("lon", 0)
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.earth2_url}/weather", params=params)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Earth2 weather fetch failed: {e}")
        return {"forecast": "unavailable"}


class NatureOSSensor(BaseSensor):
    """
    NatureOS Ecosystem Sensor.

    Provides ecosystem and life status data:
    - Environment health
    - Species observations
    - Ecological metrics
    - MATLAB integration status
    """

    def __init__(self, world_model: "WorldModel"):
        super().__init__(world_model)
        self.natureos_url = os.environ.get(
            "NATUREOS_API_URL", "http://192.168.0.187:3000/api/natureos"
        ).rstrip("/")

    async def read(self) -> Optional[Dict[str, Any]]:
        """Read current NatureOS status including MATLAB health."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.natureos_url}/status")
                if response.status_code == 200:
                    self._last_data = response.json()
                    self._last_update = datetime.now(timezone.utc)
                    # Include MATLAB health when available
                    try:
                        matlab_base = self.natureos_url.replace(
                            "/api/natureos", ""
                        )
                        mres = await client.get(
                            f"{matlab_base}/api/natureos/matlab/health"
                        )
                        if mres.status_code == 200:
                            self._last_data["matlab"] = mres.json()
                    except Exception:
                        pass
                    return self._last_data
        except Exception as e:
            logger.warning(f"NatureOS sensor read failed: {e}")
        return self._last_data

    async def get_anomaly_scores(
        self, device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get anomaly detection scores from MATLAB endpoint."""
        try:
            matlab_base = self.natureos_url.replace("/api/natureos", "")
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{matlab_base}/api/natureos/matlab/anomaly-detection",
                    json={"deviceId": device_id} if device_id else {},
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"NatureOS anomaly detection failed: {e}")
        return {"anomalies": [], "scores": []}


class MINDEXSensor(BaseSensor):
    """
    MINDEX Knowledge Sensor.
    
    Provides access to Mycosoft's knowledge base:
    - Fungi taxonomy and species data
    - Chemical compounds
    - Research papers
    - Device telemetry history
    - Semantic search capabilities
    """
    
    def __init__(self, world_model: "WorldModel" = None):
        # Allow standalone initialization
        if world_model:
            super().__init__(world_model)
        else:
            self._world_model = None
            self._initialized = False
            self._last_data = None
            self._last_update = None
        
        self.mindex_url = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000")
    
    async def initialize(self) -> None:
        """Initialize the MINDEX sensor and test connection."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.mindex_url}/health")
                if response.status_code == 200:
                    self._initialized = True
                    logger.info("MINDEX sensor initialized")
        except Exception as e:
            logger.warning(f"MINDEX sensor initialization failed: {e}")
            self._initialized = False
    
    async def read(self) -> Optional[Dict[str, Any]]:
        """Read MINDEX status and statistics."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.mindex_url}/knowledge/summary")
                if response.status_code == 200:
                    self._last_data = response.json()
                    self._last_update = datetime.now(timezone.utc)
                    return self._last_data
        except Exception as e:
            logger.warning(f"MINDEX sensor read failed: {e}")
        return self._last_data
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 5,
        collection: str = "fungi"
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search on MINDEX knowledge base.
        
        Args:
            query: Search query text
            limit: Maximum results to return
            collection: Knowledge collection to search (fungi, compounds, devices)
            
        Returns:
            List of relevant documents with content and metadata
        """
        results = []
        
        try:
            # Try Qdrant vector search first
            async with httpx.AsyncClient(timeout=15) as client:
                # Try semantic search endpoint
                response = await client.post(
                    f"{self.mindex_url}/search/semantic",
                    json={
                        "query": query,
                        "limit": limit,
                        "collection": collection
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    logger.info(f"MINDEX semantic search returned {len(results)} results")
                    return results
                
                # Fall back to text search
                response = await client.get(
                    f"{self.mindex_url}/search",
                    params={"q": query, "limit": limit}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
        except Exception as e:
            logger.warning(f"MINDEX semantic search failed: {e}")
        
        # Return empty list if all attempts failed
        return results
    
    async def get_species(self, species_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a species."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.mindex_url}/fungi/species",
                    params={"name": species_name}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"MINDEX species lookup failed: {e}")
        return None
    
    async def get_compounds(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get chemical compound data."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.mindex_url}/compounds",
                    params={"limit": limit}
                )
                if response.status_code == 200:
                    return response.json().get("compounds", [])
        except Exception as e:
            logger.warning(f"MINDEX compounds fetch failed: {e}")
        return []


class MycoBrainSensor(BaseSensor):
    """
    MycoBrain Device Sensor.
    
    Provides telemetry from MycoBrain devices:
    - Environmental sensors (BME688/690)
    - VOC/Gas readings
    - Temperature, humidity, pressure
    - Device health status
    """
    
    def __init__(self, world_model: "WorldModel"):
        super().__init__(world_model)
        self.mycobrain_url = os.environ.get("MYCOBRAIN_API_URL", "http://192.168.0.188:8001/api/devices")
    
    async def read(self) -> Optional[Dict[str, Any]]:
        """Read current device telemetry."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.mycobrain_url}/telemetry/latest")
                if response.status_code == 200:
                    self._last_data = response.json()
                    self._last_update = datetime.now(timezone.utc)
                    return self._last_data
        except Exception as e:
            logger.warning(f"MycoBrain sensor read failed: {e}")
        return self._last_data
    
    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific device."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.mycobrain_url}/{device_id}/status")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"MycoBrain device status fetch failed: {e}")
        return None


# Export all sensors
__all__ = [
    "BaseSensor",
    "CREPSensor",
    "Earth2Sensor",
    "NatureOSSensor",
    "MINDEXSensor",
    "MycoBrainSensor",
]
