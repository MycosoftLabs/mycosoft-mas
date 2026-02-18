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
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness
    from mycosoft_mas.consciousness.attention import AttentionFocus

logger = logging.getLogger(__name__)


class WriteBehindQueue:
    """Non-blocking write-behind queue for low-priority persistence."""

    def __init__(self):
        self._queue: asyncio.Queue[Callable[[], Awaitable[None]]] = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._shutdown = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._shutdown.clear()
        self._task = asyncio.create_task(self._process_loop())

    async def stop(self) -> None:
        self._shutdown.set()
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    def enqueue(self, write_fn: Callable[[], Awaitable[None]]) -> None:
        try:
            self._queue.put_nowait(write_fn)
        except asyncio.QueueFull:
            pass

    async def _process_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                write_fn = await self._queue.get()
                await write_fn()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"Write-behind failed: {exc}")


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
    crep_data: Dict[str, Any] = field(default_factory=dict)
    crep_freshness: DataFreshness = DataFreshness.UNAVAILABLE
    
    # Earth2 predictions
    predictions: Dict[str, Any] = field(default_factory=dict)
    predictions_freshness: DataFreshness = DataFreshness.UNAVAILABLE
    
    # NatureOS status
    ecosystem_status: Dict[str, Any] = field(default_factory=dict)
    ecosystem_freshness: DataFreshness = DataFreshness.UNAVAILABLE
    
    # MINDEX knowledge
    knowledge_available: bool = False
    knowledge_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Device telemetry
    device_telemetry: Dict[str, Any] = field(default_factory=dict)
    device_freshness: DataFreshness = DataFreshness.UNAVAILABLE
    
    # Aggregated metrics
    total_flights: int = 0
    total_vessels: int = 0
    total_satellites: int = 0
    active_devices: int = 0
    pending_alerts: int = 0

    # Legacy field names used by the unit tests
    @property
    def earth2_data(self) -> Dict[str, Any]:
        return self.predictions or {}

    @property
    def natureos_data(self) -> Dict[str, Any]:
        return self.ecosystem_status or {}

    @property
    def mindex_data(self) -> Dict[str, Any]:
        return self.knowledge_stats or {}

    @property
    def mycobrain_data(self) -> Dict[str, Any]:
        return self.device_telemetry or {}
    
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
    
    def __init__(self, consciousness: Optional["MYCAConsciousness"] = None):
        self._consciousness = consciousness
        self._current_state = WorldState()
        self._history: List[WorldState] = []
        self._max_history = 100
        self._cache_updated: datetime = datetime.now(timezone.utc)
        self._write_queue = WriteBehindQueue()

        # Legacy/test compatibility: simple sensor registry.
        self._sensors: Dict[str, Any] = {}
        try:
            from mycosoft_mas.consciousness.sensors import (
                CREPSensor, Earth2Sensor, NatureOSSensor, MINDEXSensor, MycoBrainSensor
            )
            self._sensors = {
                "crep": CREPSensor(self),
                "earth2": Earth2Sensor(self),
                "natureos": NatureOSSensor(self),
                "mindex": MINDEXSensor(self),
                "mycobrain": MycoBrainSensor(self),
            }
        except Exception:
            self._sensors = {}
        
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

    async def initialize(self) -> None:
        """Legacy init: connect all sensors."""
        for sensor in self._sensors.values():
            connect = getattr(sensor, "connect", None)
            if asyncio.iscoroutinefunction(connect):
                await connect()  # type: ignore[misc]

    async def update_all(self) -> None:
        """Legacy update: read from all sensors and update state."""
        for name, sensor in self._sensors.items():
            read = getattr(sensor, "read", None)
            if not asyncio.iscoroutinefunction(read):
                continue
            reading = await read()  # type: ignore[misc]
            data: Dict[str, Any] = {}
            if isinstance(reading, SensorReading):
                data = reading.data
            elif isinstance(reading, dict):
                data = reading
            if name == "crep":
                self._current_state.crep_data = data
            elif name == "earth2":
                self._current_state.predictions = data
            elif name == "natureos":
                self._current_state.ecosystem_status = data
            elif name == "mindex":
                self._current_state.knowledge_stats = data
            elif name == "mycobrain":
                self._current_state.device_telemetry = data

    def get_current_state(self) -> WorldState:
        """Legacy getter for tests."""
        return self._current_state

    @property
    def sensor_status(self) -> Dict[str, Any]:
        """Legacy sensor status map used by tests."""
        out: Dict[str, Any] = {}
        for name, sensor in self._sensors.items():
            out[name] = getattr(sensor, "status", None)
        return out
    
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
            self._cache_updated = now
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
    
    def get_cached_context(self) -> Dict[str, Any]:
        """
        Get a fast cached version of world context without any async operations.
        Used as fallback when get_relevant_context times out.
        """
        age_seconds = max((datetime.now(timezone.utc) - self._cache_updated).total_seconds(), 0.0)
        return {
            "timestamp": self._current_state.timestamp.isoformat(),
            "summary": self._current_state.to_summary(),
            "age_seconds": age_seconds,
            "data": {
                "crep": self._current_state.crep_data,
                "predictions": self._current_state.predictions,
                "ecosystem": self._current_state.ecosystem_status,
                "devices": self._current_state.device_telemetry,
            },
            "cached": True,
        }
    
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
            "cache_age_seconds": max((datetime.now(timezone.utc) - self._cache_updated).total_seconds(), 0.0),
        }

    def enqueue_write(self, write_fn: Callable[[], Awaitable[None]]) -> None:
        """Queue a non-blocking write-behind operation."""
        self._write_queue.enqueue(write_fn)

    def start_write_queue(self) -> None:
        """Start write-behind processor loop."""
        self._write_queue.start()

    async def shutdown(self) -> None:
        """Shutdown background write queue."""
        await self._write_queue.stop()
    
    async def get_state(self) -> Dict[str, Any]:
        """Get current world state as a dictionary."""
        return {
            "timestamp": self._current_state.timestamp.isoformat(),
            "sensors": {
                "crep": {
                    "data": self._current_state.crep_data,
                    "freshness": self._current_state.crep_freshness.value,
                    "flights": {"count": self._current_state.total_flights},
                    "vessels": {"count": self._current_state.total_vessels},
                    "satellites": {"count": self._current_state.total_satellites},
                },
                "earth2": {
                    "data": self._current_state.predictions,
                    "freshness": self._current_state.predictions_freshness.value,
                    "models": "Multiple prediction models available",
                },
                "natureos": {
                    "data": self._current_state.ecosystem_status,
                    "freshness": self._current_state.ecosystem_freshness.value,
                },
                "mindex": {
                    "available": self._current_state.knowledge_available,
                    "stats": self._current_state.knowledge_stats,
                },
                "mycobrain": {
                    "data": self._current_state.device_telemetry,
                    "freshness": self._current_state.device_freshness.value,
                    "active_devices": self._current_state.active_devices,
                },
            },
            "alerts": self._current_state.pending_alerts,
            "summary": self._current_state.to_summary(),
        }


class StandaloneWorldModel:
    """Standalone world model for use without full consciousness."""
    
    def __init__(self):
        self._current_state = WorldState()
    
    async def get_state(self) -> Dict[str, Any]:
        """Get current world state."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensors": {
                "crep": {"status": "not_connected"},
                "earth2": {"status": "not_connected"},
                "natureos": {"status": "not_connected"},
                "mindex": {"status": "not_connected"},
                "mycobrain": {"status": "not_connected"},
            },
            "summary": "Standalone world model - sensors not initialized",
        }


# Singleton instance for standalone use
_world_model: Optional[StandaloneWorldModel] = None


def get_world_model() -> StandaloneWorldModel:
    """Get or create the standalone world model singleton."""
    global _world_model
    if _world_model is None:
        _world_model = StandaloneWorldModel()
    return _world_model
