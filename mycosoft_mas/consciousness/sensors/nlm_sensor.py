"""
NLM Sensor

Feeds the world model with Nature Learning Model outputs:
- Environmental data processing (temperature, humidity, CO2, etc.)
- Ecological insights and predictions
- Species growth forecasts and recommendations

Connects to NLM API and uses device telemetry from MycoBrain as input.
Part of the "Opposable Thumb" architecture - NLM as the biosphere-grounded core.

Author: MYCA
Created: February 23, 2026
"""

import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

import httpx

from mycosoft_mas.consciousness.sensors.base_sensor import BaseSensor

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.world_model import SensorReading, WorldModel

logger = logging.getLogger(__name__)

# NLM API base URL - MAS VM or local
NLM_API_BASE = os.getenv("NLM_API_URL", "http://192.168.0.188:8200")
LOCAL_NLM = "http://localhost:8200"

# MycoBrain for env data input
MYCOBRAIN_API = "http://192.168.0.188:8001/api/mycobrain"
MYCOBRAIN_LOCAL = "http://localhost:8003"


class NLMSensor(BaseSensor):
    """
    Sensor for Nature Learning Model outputs.

    Aggregates environmental telemetry from MycoBrain (or world model),
    sends to NLM for processing, and returns insights and predictions
    to feed the consciousness world model.
    """

    def __init__(self, world_model: Optional["WorldModel"] = None):
        super().__init__(world_model, "nlm")
        self._client: Optional[httpx.AsyncClient] = None
        self._nlm_base = NLM_API_BASE
        self._mycobrain_base = MYCOBRAIN_API

    async def connect(self) -> bool:
        """Connect to NLM API."""
        try:
            self._client = httpx.AsyncClient(timeout=10.0)

            # Try MAS NLM endpoint
            try:
                response = await self._client.get(f"{NLM_API_BASE}/health")
                if response.status_code == 200:
                    self._nlm_base = NLM_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass

            # Try local NLM
            try:
                response = await self._client.get(f"{LOCAL_NLM}/health")
                if response.status_code == 200:
                    self._nlm_base = LOCAL_NLM
                    self._mark_connected()
                    return True
            except Exception:
                pass

            self._mark_error("Could not connect to NLM API")
            return False

        except Exception as e:
            self._mark_error(str(e))
            return False

    async def disconnect(self) -> None:
        """Disconnect from NLM API."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._mark_disconnected()

    def _get_env_from_world_model(self) -> Dict[str, Any]:
        """Extract environmental data from world model device telemetry."""
        env: Dict[str, Any] = {}
        if self._world_model:
            state = self._world_model.get_current_state()
            telemetry = state.device_telemetry or {}
            sensor_readings = telemetry.get("sensor_readings") or telemetry
            if isinstance(sensor_readings, dict):
                env["temperature"] = sensor_readings.get("temperature")
                env["humidity"] = sensor_readings.get("humidity")
                env["pressure"] = sensor_readings.get("pressure")
                env["co2"] = sensor_readings.get("co2") or sensor_readings.get("gas_resistance")
            if isinstance(sensor_readings, list) and sensor_readings:
                latest = sensor_readings[0] if isinstance(sensor_readings[0], dict) else {}
                env["temperature"] = env.get("temperature") or latest.get("temperature")
                env["humidity"] = env.get("humidity") or latest.get("humidity")
        return env

    async def _fetch_mycobrain_env(self) -> Dict[str, Any]:
        """Fetch environmental data from MycoBrain API."""
        env: Dict[str, Any] = {}
        if not self._client:
            return env
        for base in [self._mycobrain_base, MYCOBRAIN_LOCAL]:
            try:
                response = await self._client.get(f"{base}/environment")
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict):
                        env["temperature"] = data.get("temperature")
                        env["humidity"] = data.get("humidity")
                        env["pressure"] = data.get("pressure")
                        env["co2"] = data.get("co2")
                    break
            except Exception:
                continue
        return env

    async def read(self) -> Optional["SensorReading"]:
        """Read NLM-processed environmental insights and predictions."""
        from mycosoft_mas.consciousness.world_model import DataFreshness, SensorReading

        if not self._client:
            await self.connect()

        if not self.is_connected:
            return None

        try:
            # Gather environmental input
            env = self._get_env_from_world_model()
            if not env:
                env = await self._fetch_mycobrain_env()

            # Default fallback for testing
            temperature = env.get("temperature")
            humidity = env.get("humidity")
            if temperature is None:
                temperature = 22.0
            if humidity is None:
                humidity = 55.0

            # Call NLM process_environmental_data API
            result = await self._call_nlm_process(
                temperature=float(temperature),
                humidity=float(humidity),
                co2=env.get("co2"),
                pressure=env.get("pressure"),
                **{
                    k: v
                    for k, v in env.items()
                    if k not in ("temperature", "humidity", "co2", "pressure")
                },
            )

            reading = SensorReading(
                sensor_type="nlm",
                data=result,
                timestamp=datetime.now(timezone.utc),
                freshness=(
                    DataFreshness.LIVE
                    if result.get("insights") or result.get("predictions")
                    else DataFreshness.RECENT
                ),
                confidence=result.get("confidence", 0.7),
                source_url=self._nlm_base,
            )

            self._record_reading(reading)
            return reading

        except Exception as e:
            self._mark_error(str(e))
            return None

    async def _call_nlm_process(
        self,
        temperature: float,
        humidity: float,
        co2: Optional[float] = None,
        pressure: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Call NLM API process_environmental_data endpoint."""
        if not self._client:
            return self._fallback_result(temperature, humidity, co2, pressure)

        try:
            payload = {
                "temperature": temperature,
                "humidity": humidity,
                "co2": co2,
                "pressure": pressure,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **kwargs,
            }
            response = await self._client.post(
                f"{self._nlm_base}/api/environmental/process",
                json=payload,
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"NLM process call failed: {e}")

        return self._fallback_result(temperature, humidity, co2, pressure)

    def _fallback_result(
        self,
        temperature: float,
        humidity: float,
        co2: Optional[float],
        pressure: Optional[float],
    ) -> Dict[str, Any]:
        """Return minimal result when NLM API is unavailable."""
        insights = []
        if 18 <= temperature <= 28 and 40 <= humidity <= 70:
            insights.append("Environmental conditions within typical fungal growth range")
        if co2 and co2 > 1000:
            insights.append("Elevated CO2 may affect sensor readings")
        return {
            "status": "processed",
            "temperature": temperature,
            "humidity": humidity,
            "co2": co2,
            "pressure": pressure,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "insights": insights,
            "predictions": [],
            "confidence": 0.5,
        }
