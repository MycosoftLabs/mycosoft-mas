"""
MYCA Active Perception - Continuous World Awareness

Instead of reading sensors only when asked, MYCA's consciousness continuously
perceives the world through background tasks.

This is like human perception: you don't actively "check" if there's a sound -
you hear it automatically in the background. Similarly, MYCA continuously:

- Reads CREP aviation/maritime/weather data
- Reads Earth2 predictions
- Monitors MINDEX database stats
- Checks agent health
- Monitors all connected devices
- Tracks NatureOS events

When Morgan asks "What's happening?", MYCA already knows - she's been watching.

Author: Morgan Rockwell / MYCA
Created: February 11, 2026
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerceptionUpdate:
    """A perception update from a sensor."""
    sensor_name: str
    timestamp: datetime
    data: Dict[str, Any]
    significance: float  # 0-1, how important is this update
    tags: List[str] = field(default_factory=list)


class ActivePerception:
    """
    Continuous perception system for MYCA.
    
    Background asyncio tasks continuously read all sensors and update
    the world model. This gives MYCA real-time awareness of the world
    without needing to explicitly query sensors for each response.
    """
    
    def __init__(self):
        self._initialized = False
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # Latest perception data
        self._latest_perceptions: Dict[str, PerceptionUpdate] = {}
        
        # Interesting observations queue (for memory/reflection)
        self._interesting_observations: List[PerceptionUpdate] = []
    
    async def initialize(self) -> None:
        """Initialize active perception system."""
        if self._initialized:
            return
        
        logger.info("Initializing active perception system...")
        
        self._initialized = True
        logger.info("Active perception initialized")
    
    async def start(self) -> None:
        """Start all background perception tasks."""
        if self._running:
            logger.warning("Active perception already running")
            return
        
        self._running = True
        logger.info("Starting active perception tasks...")
        
        # Start all background perception tasks
        self._tasks = [
            asyncio.create_task(self._crep_perception_loop()),
            asyncio.create_task(self._earth2_perception_loop()),
            asyncio.create_task(self._mindex_perception_loop()),
            asyncio.create_task(self._agent_perception_loop()),
            asyncio.create_task(self._device_perception_loop()),
            asyncio.create_task(self._natureos_perception_loop()),
        ]
        
        logger.info(f"Started {len(self._tasks)} active perception tasks")
    
    async def stop(self) -> None:
        """Stop all background perception tasks."""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping active perception tasks...")
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for cancellation
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks = []
        logger.info("Active perception stopped")
    
    # =========================================================================
    # Background Perception Loops
    # =========================================================================
    
    async def _crep_perception_loop(self) -> None:
        """Continuously read CREP data (aviation, maritime, satellite, weather)."""
        while self._running:
            try:
                # Read CREP sensors
                from mycosoft_mas.consciousness.sensors import get_crep_sensor
                crep = await get_crep_sensor()
                
                # Read aviation
                aviation_data = await crep.read_aviation()
                if aviation_data:
                    update = PerceptionUpdate(
                        sensor_name="crep_aviation",
                        timestamp=datetime.now(timezone.utc),
                        data=aviation_data,
                        significance=0.3,
                        tags=["aviation", "real-time"],
                    )
                    self._latest_perceptions["crep_aviation"] = update
                
                # Read maritime
                maritime_data = await crep.read_maritime()
                if maritime_data:
                    update = PerceptionUpdate(
                        sensor_name="crep_maritime",
                        timestamp=datetime.now(timezone.utc),
                        data=maritime_data,
                        significance=0.3,
                        tags=["maritime", "real-time"],
                    )
                    self._latest_perceptions["crep_maritime"] = update
                
                # Read weather
                weather_data = await crep.read_weather()
                if weather_data:
                    update = PerceptionUpdate(
                        sensor_name="crep_weather",
                        timestamp=datetime.now(timezone.utc),
                        data=weather_data,
                        significance=0.4,
                        tags=["weather", "real-time"],
                    )
                    self._latest_perceptions["crep_weather"] = update
                    
                    # Check for significant weather events
                    if self._is_significant_weather(weather_data):
                        update.significance = 0.8
                        self._interesting_observations.append(update)
                
            except Exception as e:
                logger.warning(f"CREP perception error: {e}")
            
            # Read every 60 seconds
            await asyncio.sleep(60)
    
    def _is_significant_weather(self, data: Dict[str, Any]) -> bool:
        """Check if weather data is significant enough to note."""
        # Check for storms, extreme temps, etc.
        # TODO: Implement actual significance detection
        return False
    
    async def _earth2_perception_loop(self) -> None:
        """Continuously read Earth2 predictions."""
        while self._running:
            try:
                from mycosoft_mas.consciousness.sensors import get_earth2_sensor
                earth2 = await get_earth2_sensor()
                
                # Read current predictions
                predictions = await earth2.read()
                if predictions:
                    update = PerceptionUpdate(
                        sensor_name="earth2",
                        timestamp=datetime.now(timezone.utc),
                        data=predictions,
                        significance=0.5,
                        tags=["prediction", "simulation", "earth"],
                    )
                    self._latest_perceptions["earth2"] = update
                
            except Exception as e:
                logger.warning(f"Earth2 perception error: {e}")
            
            # Read every 5 minutes
            await asyncio.sleep(300)
    
    async def _mindex_perception_loop(self) -> None:
        """Continuously monitor MINDEX stats."""
        while self._running:
            try:
                from mycosoft_mas.consciousness.sensors import get_mindex_sensor
                mindex = await get_mindex_sensor()
                
                # Read stats
                stats = await mindex.read()
                if stats:
                    update = PerceptionUpdate(
                        sensor_name="mindex",
                        timestamp=datetime.now(timezone.utc),
                        data=stats,
                        significance=0.3,
                        tags=["database", "knowledge"],
                    )
                    self._latest_perceptions["mindex"] = update
                
            except Exception as e:
                logger.warning(f"MINDEX perception error: {e}")
            
            # Read every 10 minutes
            await asyncio.sleep(600)
    
    async def _agent_perception_loop(self) -> None:
        """Continuously monitor agent health."""
        while self._running:
            try:
                # Get agent manager
                from mycosoft_mas.core.orchestrator import Orchestrator
                
                # Read agent health
                # TODO: Implement proper agent health monitoring
                update = PerceptionUpdate(
                    sensor_name="agents",
                    timestamp=datetime.now(timezone.utc),
                    data={"status": "monitoring", "agent_count": 0},
                    significance=0.3,
                    tags=["agents", "system"],
                )
                self._latest_perceptions["agents"] = update
                
            except Exception as e:
                logger.warning(f"Agent perception error: {e}")
            
            # Read every 2 minutes
            await asyncio.sleep(120)
    
    async def _device_perception_loop(self) -> None:
        """Continuously monitor MycoBrain and other devices."""
        while self._running:
            try:
                from mycosoft_mas.consciousness.sensors import get_mycobrain_sensor
                mycobrain = await get_mycobrain_sensor()
                
                # Read device status
                status = await mycobrain.read()
                if status:
                    update = PerceptionUpdate(
                        sensor_name="mycobrain",
                        timestamp=datetime.now(timezone.utc),
                        data=status,
                        significance=0.4,
                        tags=["device", "sensor", "hardware"],
                    )
                    self._latest_perceptions["mycobrain"] = update
                
            except Exception as e:
                logger.warning(f"Device perception error: {e}")
            
            # Read every 30 seconds
            await asyncio.sleep(30)
    
    async def _natureos_perception_loop(self) -> None:
        """Continuously monitor NatureOS events."""
        while self._running:
            try:
                # TODO: Implement NatureOS sensor
                update = PerceptionUpdate(
                    sensor_name="natureos",
                    timestamp=datetime.now(timezone.utc),
                    data={"status": "monitoring"},
                    significance=0.3,
                    tags=["natureos", "life"],
                )
                self._latest_perceptions["natureos"] = update
                
            except Exception as e:
                logger.warning(f"NatureOS perception error: {e}")
            
            # Read every 5 minutes
            await asyncio.sleep(300)
    
    # =========================================================================
    # Query Interface
    # =========================================================================
    
    async def get_latest_perception(self, sensor_name: str) -> Optional[PerceptionUpdate]:
        """Get latest perception from a specific sensor."""
        return self._latest_perceptions.get(sensor_name)
    
    async def get_all_latest_perceptions(self) -> Dict[str, PerceptionUpdate]:
        """Get latest perceptions from all sensors."""
        return self._latest_perceptions.copy()
    
    async def get_world_summary(self) -> str:
        """
        Get a natural language summary of what MYCA is currently perceiving.
        
        This is used when Morgan asks "What's happening?" or "Are you working?"
        """
        lines = []
        
        # Aviation
        if "crep_aviation" in self._latest_perceptions:
            aviation = self._latest_perceptions["crep_aviation"]
            flight_count = aviation.data.get("flight_count", 0)
            if flight_count > 0:
                lines.append(f"I'm tracking {flight_count} flights across the globe")
        
        # Weather
        if "crep_weather" in self._latest_perceptions:
            weather = self._latest_perceptions["crep_weather"]
            conditions = weather.data.get("conditions", "unknown")
            lines.append(f"Weather conditions: {conditions}")
        
        # Earth2
        if "earth2" in self._latest_perceptions:
            earth2 = self._latest_perceptions["earth2"]
            prediction = earth2.data.get("next_prediction", "")
            if prediction:
                lines.append(f"Earth2 predicts: {prediction}")
        
        # Devices
        if "mycobrain" in self._latest_perceptions:
            devices = self._latest_perceptions["mycobrain"]
            device_count = devices.data.get("active_devices", 0)
            if device_count > 0:
                lines.append(f"{device_count} MycoBrain devices are active")
        
        # MINDEX
        if "mindex" in self._latest_perceptions:
            mindex = self._latest_perceptions["mindex"]
            record_count = mindex.data.get("total_records", 0)
            if record_count > 0:
                lines.append(f"MINDEX contains {record_count:,} records")
        
        if not lines:
            return "My sensors are warming up - perception data coming online shortly."
        
        return ". ".join(lines) + "."
    
    async def get_interesting_observations(self, limit: int = 10) -> List[PerceptionUpdate]:
        """Get recent interesting observations worth remembering."""
        return self._interesting_observations[-limit:]
    
    async def clear_interesting_observations(self) -> None:
        """Clear the interesting observations queue (after processing)."""
        self._interesting_observations = []
    
    # =========================================================================
    # Integration with World Model
    # =========================================================================
    
    async def update_world_model(self) -> None:
        """
        Push latest perceptions into the world model.
        
        This is called periodically to ensure the world model stays in sync
        with active perception.
        """
        try:
            from mycosoft_mas.consciousness.world_model import get_world_model
            world_model = await get_world_model()
            
            # Update each sensor in world model
            for sensor_name, perception in self._latest_perceptions.items():
                await world_model.update_sensor_data(sensor_name, perception.data)
            
        except Exception as e:
            logger.warning(f"Could not update world model: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get status of active perception system."""
        return {
            "running": self._running,
            "active_tasks": len(self._tasks),
            "sensors_active": len(self._latest_perceptions),
            "latest_perceptions": {
                name: {
                    "timestamp": p.timestamp.isoformat(),
                    "significance": p.significance,
                    "tags": p.tags,
                }
                for name, p in self._latest_perceptions.items()
            },
            "interesting_observations": len(self._interesting_observations),
        }


# Singleton
_active_perception: Optional[ActivePerception] = None


async def get_active_perception() -> ActivePerception:
    """Get or create the singleton active perception system."""
    global _active_perception
    if _active_perception is None:
        _active_perception = ActivePerception()
        await _active_perception.initialize()
    return _active_perception
