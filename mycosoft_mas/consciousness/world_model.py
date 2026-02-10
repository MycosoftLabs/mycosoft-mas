"""
MYCA World Model

A unified perception of the world that integrates:
- CREP: Real-time global data (flights, ships, satellites, weather)
- Earth2: Future predictions (weather, spore dispersal)
- NatureOS: Life and ecosystem status
- MINDEX: Knowledge and fungi data
- MycoBrain: Device telemetry

This gives MYCA continuous awareness of the world state.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness
    from mycosoft_mas.consciousness.attention import AttentionFocus

logger = logging.getLogger(__name__)


class DataFreshness(Enum):
    """How fresh the data is."""
    LIVE = "live"           # Updated within seconds
    RECENT = "recent"       # Updated within minutes
    STALE = "stale"         # Updated within hours
    OUTDATED = "outdated"   # Older than hours
    UNAVAILABLE = "unavailable"


@dataclass
class SensorReading:
    """A reading from a world sensor."""
    sensor_type: str
    data: Dict[str, Any]
    timestamp: datetime
    freshness: DataFreshness
    confidence: float = 1.0
    source_url: Optional[str] = None
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds()


@dataclass
class WorldState:
    """Complete snapshot of MYCA's world perception."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # CREP data
    crep_data: Optional[Dict[str, Any]] = None
    crep_freshness: DataFreshness = DataFreshness.UNAVAILABLE
    
    # Earth2 predictions
    predictions: Optional[Dict[str, Any]] = None
    predictions_freshness: DataFreshness = DataFreshness.UNAVAILABLE
    
    # NatureOS status
    ecosystem_status: Optional[Dict[str, Any]] = None
    ecosystem_freshness: DataFreshness = DataFreshness.UNAVAILABLE
    
    # MINDEX knowledge
    knowledge_available: bool = False
    knowledge_stats: Optional[Dict[str, Any]] = None
    
    # Device telemetry
    device_telemetry: Optional[Dict[str, Any]] = None
    device_freshness: DataFreshness = DataFreshness.UNAVAILABLE
    
    # Aggregated metrics
    total_flights: int = 0
    total_vessels: int = 0
    total_satellites: int = 0
    active_devices: int = 0
    pending_alerts: int = 0
    
    def to_summary(self) -> str:
        """Generate a natural language summary of world state."""
        parts = []
        
        if self.crep_data:
            parts.append(f"Tracking {self.total_flights} flights, {self.total_vessels} vessels, {self.total_satellites} satellites")
        
        if self.predictions:
            weather = self.predictions.get("weather", {})
            if weather:
                parts.append(f"Weather: {weather.get('summary', 'Unknown')}")
        
        if self.ecosystem_status:
            status = self.ecosystem_status.get("overall", "Unknown")
            parts.append(f"Ecosystem: {status}")
        
        if self.active_devices > 0:
            parts.append(f"{self.active_devices} devices online")
        
        if self.pending_alerts > 0:
            parts.append(f"{self.pending_alerts} pending alerts")
        
        return "; ".join(parts) if parts else "World state: limited data available"


class WorldModel:
    """
    MYCA's unified world perception.
    
    This integrates data from multiple sensors into a coherent
    world model that MYCA can query and reason about.
    """
    
    # Update intervals (seconds)
    CREP_UPDATE_INTERVAL = 30
    PREDICTION_UPDATE_INTERVAL = 300
    ECOSYSTEM_UPDATE_INTERVAL = 60
    DEVICE_UPDATE_INTERVAL = 10
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        self._consciousness = consciousness
        self._current_state = WorldState()
        self._history: List[WorldState] = []
        self._max_history = 100
        
        # Sensors (lazy-loaded)
        self._crep_sensor: Optional["CREPSensor"] = None
        self._earth2_sensor: Optional["Earth2Sensor"] = None
        self._natureos_sensor: Optional["NatureOSSensor"] = None
        self._mindex_sensor: Optional["MINDEXSensor"] = None
        self._mycobrain_sensor: Optional["MycoBrainSensor"] = None
        
        # Timestamps for throttling
        self._last_crep_update: Optional[datetime] = None
        self._last_prediction_update: Optional[datetime] = None
        self._last_ecosystem_update: Optional[datetime] = None
        self._last_device_update: Optional[datetime] = None
        
        self._lock = asyncio.Lock()
    
    async def initialize_sensors(self) -> None:
        """Initialize all world sensors."""
        try:
            from mycosoft_mas.consciousness.sensors import (
                CREPSensor, Earth2Sensor, NatureOSSensor, 
                MINDEXSensor, MycoBrainSensor
            )
            
            self._crep_sensor = CREPSensor(self)
            self._earth2_sensor = Earth2Sensor(self)
            self._natureos_sensor = NatureOSSensor(self)
            self._mindex_sensor = MINDEXSensor(self)
            self._mycobrain_sensor = MycoBrainSensor(self)
            
            logger.info("World sensors initialized")
        except ImportError as e:
            logger.warning(f"Could not initialize some sensors: {e}")
    
    async def update(self) -> None:
        """Update the world model from all sensors."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            
            # Update CREP
            if self._should_update(self._last_crep_update, self.CREP_UPDATE_INTERVAL):
                await self._update_crep()
                self._last_crep_update = now
            
            # Update predictions
            if self._should_update(self._last_prediction_update, self.PREDICTION_UPDATE_INTERVAL):
                await self._update_predictions()
                self._last_prediction_update = now
            
            # Update ecosystem
            if self._should_update(self._last_ecosystem_update, self.ECOSYSTEM_UPDATE_INTERVAL):
                await self._update_ecosystem()
                self._last_ecosystem_update = now
            
            # Update devices
            if self._should_update(self._last_device_update, self.DEVICE_UPDATE_INTERVAL):
                await self._update_devices()
                self._last_device_update = now
            
            # Update timestamp and archive
            self._current_state.timestamp = now
            self._archive_state()
    
    def _should_update(self, last_update: Optional[datetime], interval: int) -> bool:
        """Check if enough time has passed to update."""
        if last_update is None:
            return True
        return (datetime.now(timezone.utc) - last_update).total_seconds() >= interval
    
    async def _update_crep(self) -> None:
        """Update CREP data."""
        if self._crep_sensor:
            try:
                reading = await self._crep_sensor.read()
                if reading:
                    self._current_state.crep_data = reading.data
                    self._current_state.crep_freshness = reading.freshness
                    
                    # Extract metrics
                    self._current_state.total_flights = reading.data.get("flight_count", 0)
                    self._current_state.total_vessels = reading.data.get("vessel_count", 0)
                    self._current_state.total_satellites = reading.data.get("satellite_count", 0)
            except Exception as e:
                logger.warning(f"CREP update error: {e}")
                self._current_state.crep_freshness = DataFreshness.UNAVAILABLE
    
    async def _update_predictions(self) -> None:
        """Update Earth2 predictions."""
        if self._earth2_sensor:
            try:
                reading = await self._earth2_sensor.read()
                if reading:
                    self._current_state.predictions = reading.data
                    self._current_state.predictions_freshness = reading.freshness
            except Exception as e:
                logger.warning(f"Prediction update error: {e}")
                self._current_state.predictions_freshness = DataFreshness.UNAVAILABLE
    
    async def _update_ecosystem(self) -> None:
        """Update NatureOS ecosystem status."""
        if self._natureos_sensor:
            try:
                reading = await self._natureos_sensor.read()
                if reading:
                    self._current_state.ecosystem_status = reading.data
                    self._current_state.ecosystem_freshness = reading.freshness
            except Exception as e:
                logger.warning(f"Ecosystem update error: {e}")
                self._current_state.ecosystem_freshness = DataFreshness.UNAVAILABLE
    
    async def _update_devices(self) -> None:
        """Update MycoBrain device telemetry."""
        if self._mycobrain_sensor:
            try:
                reading = await self._mycobrain_sensor.read()
                if reading:
                    self._current_state.device_telemetry = reading.data
                    self._current_state.device_freshness = reading.freshness
                    self._current_state.active_devices = reading.data.get("active_count", 0)
            except Exception as e:
                logger.warning(f"Device update error: {e}")
                self._current_state.device_freshness = DataFreshness.UNAVAILABLE
    
    def _archive_state(self) -> None:
        """Archive the current state to history."""
        self._history.append(self._current_state)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_current_state(self) -> WorldState:
        """Get the current world state."""
        return self._current_state
    
    async def get_summary(self) -> str:
        """Get a natural language summary of world state."""
        return self._current_state.to_summary()
    
    async def get_relevant_context(
        self,
        focus: "AttentionFocus"
    ) -> Dict[str, Any]:
        """
        Get world context relevant to the current focus.
        
        This filters the world state to what's most relevant
        to what MYCA is currently thinking about.
        """
        context = {
            "timestamp": self._current_state.timestamp.isoformat(),
            "summary": self._current_state.to_summary(),
        }
        
        # Add relevant data based on focus category
        focus_entities = focus.related_entities if focus else []
        focus_content = focus.content.lower() if focus else ""
        
        # CREP data for world-related queries
        if any(word in focus_content for word in ["flight", "ship", "satellite", "weather", "world"]):
            if self._current_state.crep_data:
                context["crep"] = {
                    "flights": self._current_state.total_flights,
                    "vessels": self._current_state.total_vessels,
                    "satellites": self._current_state.total_satellites,
                    "freshness": self._current_state.crep_freshness.value,
                }
        
        # Predictions for future-related queries
        if any(word in focus_content for word in ["predict", "forecast", "tomorrow", "future", "weather"]):
            if self._current_state.predictions:
                context["predictions"] = self._current_state.predictions
        
        # Ecosystem for nature-related queries
        if any(word in focus_content for word in ["nature", "ecosystem", "life", "environment", "fungi"]):
            if self._current_state.ecosystem_status:
                context["ecosystem"] = self._current_state.ecosystem_status
        
        # Device info for device-related queries
        if any(word in focus_content for word in ["device", "sensor", "mycobrain", "telemetry"]):
            if self._current_state.device_telemetry:
                context["devices"] = {
                    "active_count": self._current_state.active_devices,
                    "telemetry": self._current_state.device_telemetry,
                    "freshness": self._current_state.device_freshness.value,
                }
        
        return context
    
    async def query(self, query_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Query specific world data.
        
        Args:
            query_type: Type of query (crep, predictions, ecosystem, devices, knowledge)
            params: Query parameters
        
        Returns:
            Query results
        """
        params = params or {}
        
        if query_type == "crep":
            return {"data": self._current_state.crep_data, "freshness": self._current_state.crep_freshness.value}
        
        elif query_type == "predictions":
            return {"data": self._current_state.predictions, "freshness": self._current_state.predictions_freshness.value}
        
        elif query_type == "ecosystem":
            return {"data": self._current_state.ecosystem_status, "freshness": self._current_state.ecosystem_freshness.value}
        
        elif query_type == "devices":
            return {"data": self._current_state.device_telemetry, "active": self._current_state.active_devices}
        
        elif query_type == "knowledge":
            if self._mindex_sensor:
                return await self._mindex_sensor.query(params.get("query", ""))
            return {"error": "MINDEX sensor not available"}
        
        elif query_type == "summary":
            return {"summary": self._current_state.to_summary()}
        
        else:
            return {"error": f"Unknown query type: {query_type}"}
    
    def get_history(self, limit: int = 10) -> List[WorldState]:
        """Get recent world state history."""
        return self._history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get world model statistics."""
        return {
            "current_timestamp": self._current_state.timestamp.isoformat(),
            "crep_freshness": self._current_state.crep_freshness.value,
            "prediction_freshness": self._current_state.predictions_freshness.value,
            "ecosystem_freshness": self._current_state.ecosystem_freshness.value,
            "device_freshness": self._current_state.device_freshness.value,
            "total_flights": self._current_state.total_flights,
            "total_vessels": self._current_state.total_vessels,
            "total_satellites": self._current_state.total_satellites,
            "active_devices": self._current_state.active_devices,
            "history_size": len(self._history),
        }
