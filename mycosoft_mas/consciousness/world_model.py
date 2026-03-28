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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.attention import AttentionFocus
    from mycosoft_mas.consciousness.core import MYCAConsciousness

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

    LIVE = "live"  # Updated within seconds
    RECENT = "recent"  # Updated within minutes
    STALE = "stale"  # Updated within hours
    OUTDATED = "outdated"  # Older than hours
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

    # NLM insights and predictions (Nature Learning Model)
    nlm_insights: Dict[str, Any] = field(default_factory=dict)
    nlm_freshness: DataFreshness = DataFreshness.UNAVAILABLE

    # EarthLIVE packetized environmental data (weather, seismic, satellite)
    earthlive_packet: Dict[str, Any] = field(default_factory=dict)
    earthlive_freshness: DataFreshness = DataFreshness.UNAVAILABLE

    # Presence data (live users, sessions, staff)
    presence_data: Dict[str, Any] = field(default_factory=dict)
    presence_freshness: DataFreshness = DataFreshness.UNAVAILABLE
    online_users: int = 0
    active_sessions: int = 0
    staff_online: int = 0
    superuser_online: bool = False

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
            parts.append(
                f"Tracking {self.total_flights} flights, {self.total_vessels} vessels, {self.total_satellites} satellites"
            )

        if self.predictions:
            weather = self.predictions.get("weather", {})
            if weather:
                parts.append(f"Weather: {weather.get('summary', 'Unknown')}")

        if self.ecosystem_status:
            status = self.ecosystem_status.get("overall", "Unknown")
            parts.append(f"Ecosystem: {status}")

        if self.nlm_insights:
            insights = self.nlm_insights.get("insights", [])
            if insights:
                parts.append(
                    f"NLM: {insights[0]}"
                    if len(insights) == 1
                    else f"NLM: {len(insights)} insights"
                )

        if self.earthlive_packet:
            w = self.earthlive_packet.get("weather", {})
            s = self.earthlive_packet.get("seismic", {})
            if w or s:
                parts.append("EarthLIVE: weather + seismic")

        if self.active_devices > 0:
            parts.append(f"{self.active_devices} devices online")

        if self.online_users > 0:
            parts.append(f"{self.online_users} users online ({self.staff_online} staff)")

        if self.pending_alerts > 0:
            parts.append(f"{self.pending_alerts} pending alerts")

        return "; ".join(parts) if parts else "World state: limited data available"


class _NullSensor:
    """Stub sensor used when a real sensor fails to import."""

    status = "unavailable"

    async def connect(self) -> bool:
        return False

    async def read(self) -> Dict[str, Any]:
        return {}

    async def disconnect(self) -> None:
        pass


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
    NLM_UPDATE_INTERVAL = 60
    MINDEX_UPDATE_INTERVAL = 60
    EARTHLIVE_UPDATE_INTERVAL = 120
    PRESENCE_UPDATE_INTERVAL = 5

    # All sensor keys in canonical order
    _SENSOR_KEYS = (
        "crep",
        "earth2",
        "natureos",
        "mindex",
        "mycobrain",
        "nlm",
        "earthlive",
        "presence",
        "workspace",
    )

    def __init__(self, consciousness: Optional["MYCAConsciousness"] = None):
        self._consciousness = consciousness
        self._current_state = WorldState()
        self._history: List[WorldState] = []
        self._max_history = 100
        self._cache_updated: datetime = datetime.now(timezone.utc)
        self._write_queue = WriteBehindQueue()

        # Build the unified sensor registry (per-sensor error isolation)
        self._sensors: Dict[str, Any] = self._build_sensor_registry()

        # Named refs populated from the same _sensors dict
        self._crep_sensor = self._sensors.get("crep")
        self._earth2_sensor = self._sensors.get("earth2")
        self._natureos_sensor = self._sensors.get("natureos")
        self._mindex_sensor = self._sensors.get("mindex")
        self._mycobrain_sensor = self._sensors.get("mycobrain")
        self._nlm_sensor = self._sensors.get("nlm")
        self._earthlive_sensor = self._sensors.get("earthlive")
        self._presence_sensor = self._sensors.get("presence")
        self._workspace_sensor = self._sensors.get("workspace")

        # Timestamps for throttling
        self._last_crep_update: Optional[datetime] = None
        self._last_prediction_update: Optional[datetime] = None
        self._last_ecosystem_update: Optional[datetime] = None
        self._last_device_update: Optional[datetime] = None
        self._last_nlm_update: Optional[datetime] = None
        self._last_mindex_update: Optional[datetime] = None
        self._last_earthlive_update: Optional[datetime] = None
        self._last_presence_update: Optional[datetime] = None

        self._lock = asyncio.Lock()
        self._sensors_initialized = False

    def _build_sensor_registry(self) -> Dict[str, Any]:
        """Build sensor registry with per-sensor error isolation.

        Each sensor is constructed inside its own try/except so one
        missing or broken module does not collapse all sensors.
        """
        from mycosoft_mas.consciousness.sensors import (
            CREPSensor,
            Earth2Sensor,
            EarthLIVESensor,
            MINDEXSensor,
            MycoBrainSensor,
            NatureOSSensor,
            NLMSensor,
            PresenceSensor,
            WorkspaceSensor,
        )

        sensor_classes = {
            "crep": CREPSensor,
            "earth2": Earth2Sensor,
            "natureos": NatureOSSensor,
            "mindex": MINDEXSensor,
            "mycobrain": MycoBrainSensor,
            "nlm": NLMSensor,
            "earthlive": EarthLIVESensor,
            "presence": PresenceSensor,
            "workspace": WorkspaceSensor,
        }

        registry: Dict[str, Any] = {}
        for name, cls in sensor_classes.items():
            try:
                if cls is not None:
                    registry[name] = cls(self)
                else:
                    logger.warning("Sensor class %s is None (import failed), using NullSensor", name)
                    registry[name] = _NullSensor()
            except Exception as exc:
                logger.warning("Failed to construct sensor %s: %s", name, exc)
                registry[name] = _NullSensor()
        return registry

    async def initialize_sensors(self) -> None:
        """Initialize all world sensors (idempotent).

        Rebuilds the sensor registry and syncs named refs.
        Safe to call multiple times.
        """
        if self._sensors_initialized:
            return

        # Rebuild registry so sensors constructed after __init__ pick up
        # any newly available modules.
        self._sensors = self._build_sensor_registry()

        # Sync named refs from the same dict
        self._crep_sensor = self._sensors.get("crep")
        self._earth2_sensor = self._sensors.get("earth2")
        self._natureos_sensor = self._sensors.get("natureos")
        self._mindex_sensor = self._sensors.get("mindex")
        self._mycobrain_sensor = self._sensors.get("mycobrain")
        self._nlm_sensor = self._sensors.get("nlm")
        self._earthlive_sensor = self._sensors.get("earthlive")
        self._presence_sensor = self._sensors.get("presence")
        self._workspace_sensor = self._sensors.get("workspace")

        self._sensors_initialized = True
        logger.info("World sensors initialized (%d sensors)", len(self._sensors))

    @property
    def is_degraded(self) -> bool:
        """True when more than half of sensors are NullSensor stubs."""
        null_count = sum(1 for s in self._sensors.values() if isinstance(s, _NullSensor))
        return null_count > len(self._sensors) // 2

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
            elif name == "nlm":
                self._current_state.nlm_insights = data
            elif name == "earthlive":
                self._current_state.earthlive_packet = data
                self._current_state.earthlive_freshness = (
                    DataFreshness.LIVE if data else DataFreshness.UNAVAILABLE
                )
            elif name == "presence":
                if isinstance(data, dict):
                    self._current_state.presence_data = data
                    self._current_state.online_users = data.get("online_count", 0)
                    self._current_state.active_sessions = data.get("sessions_count", 0)
                    self._current_state.staff_online = data.get("staff_count", 0)
                    self._current_state.superuser_online = data.get("superuser_online", False)

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

            # Update NLM
            if self._should_update(self._last_nlm_update, self.NLM_UPDATE_INTERVAL):
                await self._update_nlm()
                self._last_nlm_update = now

            # Update MINDEX
            if self._should_update(self._last_mindex_update, self.MINDEX_UPDATE_INTERVAL):
                await self._update_mindex()
                self._last_mindex_update = now

            # Update EarthLIVE
            if self._should_update(self._last_earthlive_update, self.EARTHLIVE_UPDATE_INTERVAL):
                await self._update_earthlive()
                self._last_earthlive_update = now

            # Update presence
            if self._should_update(self._last_presence_update, self.PRESENCE_UPDATE_INTERVAL):
                await self._update_presence()
                self._last_presence_update = now

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

    async def _update_nlm(self) -> None:
        """Update NLM insights and predictions."""
        if self._nlm_sensor:
            try:
                reading = await self._nlm_sensor.read()
                if reading:
                    self._current_state.nlm_insights = reading.data
                    self._current_state.nlm_freshness = reading.freshness
            except Exception as e:
                logger.warning(f"NLM update error: {e}")
                self._current_state.nlm_freshness = DataFreshness.UNAVAILABLE

    async def _update_mindex(self) -> None:
        """Update MINDEX knowledge stats and availability."""
        sensor = self._mindex_sensor or self._sensors.get("mindex")
        if not sensor:
            return
        try:
            reading = await sensor.read()
            if reading:
                data = (
                    reading.data
                    if isinstance(reading, SensorReading)
                    else (reading if isinstance(reading, dict) else {})
                )
                self._current_state.knowledge_stats = data
                self._current_state.knowledge_available = bool(
                    data.get("available") or data.get("stats")
                )
        except Exception as e:
            logger.warning(f"MINDEX update error: {e}")
            self._current_state.knowledge_available = False

    async def _update_earthlive(self) -> None:
        """Update EarthLIVE packetized environmental data."""
        if self._earthlive_sensor:
            try:
                reading = await self._earthlive_sensor.read()
                if reading:
                    self._current_state.earthlive_packet = reading.data
                    self._current_state.earthlive_freshness = reading.freshness
            except Exception as e:
                logger.warning(f"EarthLIVE update error: {e}")
                self._current_state.earthlive_freshness = DataFreshness.UNAVAILABLE

    async def _update_presence(self) -> None:
        """Update presence data (online users, sessions, staff)."""
        if self._presence_sensor:
            try:
                data = await self._presence_sensor.read()
                if data and isinstance(data, dict):
                    self._current_state.presence_data = data
                    self._current_state.online_users = data.get("online_count", 0)
                    self._current_state.active_sessions = data.get("sessions_count", 0)
                    self._current_state.staff_online = data.get("staff_count", 0)
                    self._current_state.superuser_online = data.get("superuser_online", False)
                    self._current_state.presence_freshness = DataFreshness.LIVE
            except Exception as e:
                logger.warning(f"Presence update error: {e}")
                self._current_state.presence_freshness = DataFreshness.UNAVAILABLE

    def _archive_state(self) -> None:
        """Archive the current state to history."""
        self._history.append(self._current_state)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

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
                "nlm": self._current_state.nlm_insights,
                "mindex": self._current_state.knowledge_stats,
                "presence": self._current_state.presence_data,
            },
            "cached": True,
        }

    async def get_relevant_context(self, focus: "AttentionFocus") -> Dict[str, Any]:
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
        focus.related_entities if focus else []
        focus_content = focus.content.lower() if focus else ""

        # CREP data for world-related queries
        if any(
            word in focus_content for word in ["flight", "ship", "satellite", "weather", "world"]
        ):
            if self._current_state.crep_data:
                context["crep"] = {
                    "flights": self._current_state.total_flights,
                    "vessels": self._current_state.total_vessels,
                    "satellites": self._current_state.total_satellites,
                    "freshness": self._current_state.crep_freshness.value,
                }

        # Predictions for future-related queries
        if any(
            word in focus_content
            for word in ["predict", "forecast", "tomorrow", "future", "weather"]
        ):
            if self._current_state.predictions:
                context["predictions"] = self._current_state.predictions

        # Ecosystem for nature-related queries
        if any(
            word in focus_content
            for word in ["nature", "ecosystem", "life", "environment", "fungi"]
        ):
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

        # Presence for user/session-related queries
        if any(
            word in focus_content
            for word in ["who", "user", "online", "staff", "presence", "session"]
        ):
            if self._current_state.presence_data:
                context["presence"] = self._current_state.presence_data

        # Workspace state for task/work/team/schedule queries
        workspace_keywords = [
            "task",
            "work",
            "email",
            "schedule",
            "team",
            "morgan",
            "rj",
            "garret",
            "slack",
            "discord",
            "send",
            "asana",
            "status",
            "briefing",
            "daily",
            "doing",
            "busy",
            "plan",
            "todo",
            "message",
            "notify",
            "check",
            "meeting",
        ]
        if any(word in focus_content for word in workspace_keywords):
            workspace_sensor = getattr(self, "_workspace_sensor", None)
            if workspace_sensor:
                try:
                    reading = await workspace_sensor.read()
                    if reading:
                        context["workspace"] = reading.data
                except Exception as e:
                    logger.debug("Workspace sensor read failed: %s", e)

        return context

    async def query(
        self, query_type: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
            return {
                "data": self._current_state.crep_data,
                "freshness": self._current_state.crep_freshness.value,
            }

        elif query_type == "predictions":
            return {
                "data": self._current_state.predictions,
                "freshness": self._current_state.predictions_freshness.value,
            }

        elif query_type == "ecosystem":
            return {
                "data": self._current_state.ecosystem_status,
                "freshness": self._current_state.ecosystem_freshness.value,
            }

        elif query_type == "devices":
            return {
                "data": self._current_state.device_telemetry,
                "active": self._current_state.active_devices,
            }

        elif query_type == "telemetry":
            return await self.get_current_telemetry(params.get("device_id"))

        elif query_type == "knowledge":
            if self._mindex_sensor:
                return await self._mindex_sensor.query(params.get("query", ""))
            return {"error": "MINDEX sensor not available"}

        elif query_type == "summary":
            return {"summary": self._current_state.to_summary()}

        else:
            return {"error": f"Unknown query type: {query_type}"}

    async def get_current_telemetry(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current device telemetry. Supports "what's the temperature at mushroom1?" queries.
        Returns cached telemetry from world state; if device_id given and not in cache,
        fetches live from MycoBrain sensor.
        """
        data = self._current_state.device_telemetry or {}
        if device_id:
            device_id_lower = device_id.lower().replace(" ", "-")
            devices_list = data.get("devices", []) if isinstance(data, dict) else []
            sensor_readings = data.get("sensor_readings", {}) if isinstance(data, dict) else {}
            for d in devices_list:
                if not isinstance(d, dict):
                    continue
                did = d.get("device_id") or d.get("id") or ""
                if device_id_lower in str(did).lower() or str(did).lower() in device_id_lower:
                    telemetry = (
                        sensor_readings.get(did, d) if isinstance(sensor_readings, dict) else d
                    )
                    return {
                        "device_id": did,
                        "telemetry": telemetry,
                        "freshness": self._current_state.device_freshness.value,
                    }
            if self._mycobrain_sensor and hasattr(self._mycobrain_sensor, "get_device_telemetry"):
                try:
                    live = await self._mycobrain_sensor.get_device_telemetry(device_id)
                    if live and "error" not in live:
                        t = live.get("telemetry", live)
                        return {"device_id": device_id, "telemetry": t, "freshness": "live"}
                except Exception as e:
                    logger.debug("Live telemetry fetch failed: %s", e)
            return {"device_id": device_id, "telemetry": {}, "error": "Device not found or offline"}
        return {
            "devices": data,
            "active": self._current_state.active_devices,
            "freshness": self._current_state.device_freshness.value,
        }

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
            "cache_age_seconds": max(
                (datetime.now(timezone.utc) - self._cache_updated).total_seconds(), 0.0
            ),
        }

    def enqueue_write(self, write_fn: Callable[[], Awaitable[None]]) -> None:
        """Queue a non-blocking write-behind operation."""
        self._write_queue.enqueue(write_fn)

    def start_write_queue(self) -> None:
        """Start write-behind processor loop."""
        self._write_queue.start()

    async def disconnect_all(self) -> None:
        """Disconnect all sensors that support it."""
        for name, sensor in self._sensors.items():
            disconnect = getattr(sensor, "disconnect", None)
            if asyncio.iscoroutinefunction(disconnect):
                try:
                    await disconnect()
                except Exception as exc:
                    logger.debug("Error disconnecting sensor %s: %s", name, exc)

    async def shutdown(self) -> None:
        """Shutdown background write queue and disconnect sensors."""
        await self.disconnect_all()
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
