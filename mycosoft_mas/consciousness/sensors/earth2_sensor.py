"""
Earth2 Sensor

Reads predictions from the Earth2 simulation system:
- Weather forecasts
- Climate predictions
- Spore dispersal models
- Environmental predictions

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


class Earth2Sensor(BaseSensor):
    """
    Sensor for Earth2 prediction data.
    
    Connects to the Earth2 service (NVIDIA Earth2Studio) for
    weather forecasting, climate predictions, and spore dispersal models.
    """
    
    # API endpoints
    EARTH2_API_BASE = "http://192.168.0.188:8001/api/earth2"
    LOCAL_API_BASE = "http://localhost:8220"  # Local GPU service
    
    def __init__(self, world_model: "WorldModel"):
        super().__init__(world_model, "earth2")
        self._client: Optional[httpx.AsyncClient] = None
        self._api_base = self.EARTH2_API_BASE
    
    async def connect(self) -> bool:
        """Connect to the Earth2 API."""
        try:
            self._client = httpx.AsyncClient(timeout=30.0)  # Longer timeout for predictions
            
            # Try MAS API endpoint
            try:
                response = await self._client.get(f"{self.EARTH2_API_BASE}/health")
                if response.status_code == 200:
                    self._api_base = self.EARTH2_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass
            
            # Try local GPU service
            try:
                response = await self._client.get(f"{self.LOCAL_API_BASE}/health")
                if response.status_code == 200:
                    self._api_base = self.LOCAL_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass
            
            self._mark_error("Could not connect to Earth2 API")
            return False
            
        except Exception as e:
            self._mark_error(str(e))
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the Earth2 API."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._mark_disconnected()
    
    async def read(self) -> Optional["SensorReading"]:
        """Read current predictions."""
        from mycosoft_mas.consciousness.world_model import SensorReading, DataFreshness
        
        if not self._client:
            await self.connect()
        
        if not self.is_connected:
            return None
        
        try:
            data = {}
            
            # Get weather forecast
            forecast = await self._get_forecast()
            if forecast:
                data["weather"] = forecast
            
            # Get current predictions summary
            predictions = await self._get_predictions_summary()
            if predictions:
                data["predictions"] = predictions
            
            reading = SensorReading(
                sensor_type="earth2",
                data=data,
                timestamp=datetime.now(timezone.utc),
                freshness=DataFreshness.RECENT if data else DataFreshness.UNAVAILABLE,
                confidence=0.8 if data else 0.0,
                source_url=self._api_base
            )
            
            self._record_reading(reading)
            return reading
            
        except Exception as e:
            self._mark_error(str(e))
            return None
    
    async def _get_forecast(self) -> Optional[Dict[str, Any]]:
        """Get weather forecast."""
        try:
            response = await self._client.get(f"{self._api_base}/forecast")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Forecast error: {e}")
        return None
    
    async def _get_predictions_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of current predictions."""
        try:
            response = await self._client.get(f"{self._api_base}/predictions/summary")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Predictions error: {e}")
        return None
    
    async def forecast_weather(
        self,
        lat: float,
        lon: float,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get weather forecast for a specific location."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            response = await self._client.post(
                f"{self._api_base}/forecast/location",
                json={"lat": lat, "lon": lon, "hours": hours}
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def predict_spore_dispersal(
        self,
        lat: float,
        lon: float,
        species: str = "generic"
    ) -> Dict[str, Any]:
        """Predict spore dispersal for a fungal species."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            response = await self._client.post(
                f"{self._api_base}/spore-dispersal",
                json={"lat": lat, "lon": lon, "species": species}
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def nowcast(
        self,
        lat: float,
        lon: float,
        minutes: int = 60
    ) -> Dict[str, Any]:
        """Get short-term nowcast predictions."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            response = await self._client.post(
                f"{self._api_base}/nowcast",
                json={"lat": lat, "lon": lon, "minutes": minutes}
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
