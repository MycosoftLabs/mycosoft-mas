"""
MINDEX Sensor

Reads knowledge and data availability from MINDEX:
- Fungi knowledge
- Research data
- Telemetry
- FCI (Fungal Computing Interface) data

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import httpx

from mycosoft_mas.consciousness.sensors.base_sensor import BaseSensor, SensorStatus

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.world_model import WorldModel, SensorReading, DataFreshness

logger = logging.getLogger(__name__)


class MINDEXSensor(BaseSensor):
    """
    Sensor for MINDEX knowledge data.
    
    Connects to the MINDEX database API for fungi knowledge,
    research data, and telemetry.
    """
    
    # API endpoints
    MINDEX_API_BASE = "http://192.168.0.189:8000"
    FALLBACK_API_BASE = "http://192.168.0.188:8001/api/mindex"
    
    def __init__(self, world_model: Optional["WorldModel"] = None):
        super().__init__(world_model, "mindex")
        self._client: Optional[httpx.AsyncClient] = None
        self._api_base = self.MINDEX_API_BASE

    async def search(self, query: str) -> Dict[str, Any]:
        """Legacy alias used by unit tests."""
        return await self.query(query)
    
    async def connect(self) -> bool:
        """Connect to the MINDEX API."""
        try:
            self._client = httpx.AsyncClient(timeout=10.0)
            
            # Try primary MINDEX VM
            try:
                response = await self._client.get(f"{self.MINDEX_API_BASE}/health")
                if response.status_code == 200:
                    self._api_base = self.MINDEX_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass
            
            # Try MAS API fallback
            try:
                response = await self._client.get(f"{self.FALLBACK_API_BASE}/health")
                if response.status_code == 200:
                    self._api_base = self.FALLBACK_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass
            
            self._mark_error("Could not connect to MINDEX API")
            return False
            
        except Exception as e:
            self._mark_error(str(e))
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the MINDEX API."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._mark_disconnected()
    
    async def read(self) -> Optional["SensorReading"]:
        """Read MINDEX availability and stats."""
        from mycosoft_mas.consciousness.world_model import SensorReading, DataFreshness
        
        if not self._client:
            await self.connect()
        
        if not self.is_connected:
            return None
        
        try:
            data = {}
            
            # Get database stats
            stats = await self._get_stats()
            if stats:
                data["stats"] = stats
                data["available"] = True
            
            # Get recent telemetry summary
            telemetry = await self._get_telemetry_summary()
            if telemetry:
                data["telemetry"] = telemetry
            
            # Get knowledge categories
            categories = await self._get_categories()
            if categories:
                data["categories"] = categories
            
            reading = SensorReading(
                sensor_type="mindex",
                data=data,
                timestamp=datetime.now(timezone.utc),
                freshness=DataFreshness.LIVE if data.get("available") else DataFreshness.UNAVAILABLE,
                confidence=0.95 if data else 0.0,
                source_url=self._api_base
            )
            
            self._record_reading(reading)
            return reading
            
        except Exception as e:
            self._mark_error(str(e))
            return None
    
    async def _get_stats(self) -> Optional[Dict[str, Any]]:
        """Get database statistics."""
        try:
            response = await self._client.get(f"{self._api_base}/stats")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Stats error: {e}")
        return None
    
    async def _get_telemetry_summary(self) -> Optional[Dict[str, Any]]:
        """Get recent telemetry summary."""
        try:
            response = await self._client.get(f"{self._api_base}/telemetry/summary")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Telemetry summary error: {e}")
        return None
    
    async def _get_categories(self) -> Optional[List[str]]:
        """Get available knowledge categories."""
        try:
            response = await self._client.get(f"{self._api_base}/categories")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Categories error: {e}")
        return None
    
    async def query(self, query_text: str) -> Dict[str, Any]:
        """Query MINDEX for knowledge."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            response = await self._client.post(
                f"{self._api_base}/search",
                json={"query": query_text, "limit": 10}
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 5,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic search over knowledge base."""
        if not self._client or not self.is_connected:
            return []
        
        try:
            params = {"query": query, "limit": limit}
            if category:
                params["category"] = category
            
            response = await self._client.post(
                f"{self._api_base}/semantic-search",
                json=params
            )
            if response.status_code == 200:
                return response.json().get("results", [])
        except Exception as e:
            logger.warning(f"Semantic search error: {e}")
        return []
    
    async def get_fungi_info(self, species: str) -> Dict[str, Any]:
        """Get information about a fungal species."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            response = await self._client.get(
                f"{self._api_base}/fungi/{species}"
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Species not found: {species}"}
        except Exception as e:
            return {"error": str(e)}
