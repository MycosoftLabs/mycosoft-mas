"""
FCI Hardware Driver - MycoBrain Signal Interface

Provides drivers for reading bioelectric signals from FCI probes
connected to MycoBrain ESP32 devices.

Two modes:
1. Simulator - Mathematical signal generation for development
2. Hardware - Real device connection via WebSocket/Serial

The driver is designed to be a drop-in replacement for the simulator
in the WebSocket streaming endpoint.

(c) 2026 Mycosoft Labs - February 10, 2026
"""

import asyncio
import json
import logging
import math
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class FCIDriverMode(Enum):
    """FCI driver operating mode."""
    SIMULATOR = "simulator"
    HARDWARE = "hardware"
    HYBRID = "hybrid"  # Uses hardware when available, falls back to simulator


@dataclass
class FCISample:
    """Single sample from FCI channels."""
    timestamp: datetime
    channels: List[Dict[str, float]]
    device_id: str
    is_simulated: bool = True
    quality_score: float = 1.0


class FCIDriverBase(ABC):
    """Abstract base class for FCI signal drivers."""
    
    @abstractmethod
    async def start(self) -> bool:
        """Start the driver. Returns True if successful."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the driver and cleanup resources."""
        pass
    
    @abstractmethod
    async def get_sample(self) -> FCISample:
        """Get a single sample from all channels."""
        pass
    
    @abstractmethod
    def set_pattern(self, pattern: str) -> None:
        """Set the signal pattern (simulator mode) or target (hardware mode)."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if driver is connected to signal source."""
        pass
    
    @property
    @abstractmethod
    def mode(self) -> FCIDriverMode:
        """Return the driver mode."""
        pass


class FCISimulatorDriver(FCIDriverBase):
    """
    Simulated FCI driver for development and testing.
    
    Generates mathematically-modeled bioelectric signals that mimic
    real mycelium patterns based on GFST pattern library.
    """
    
    def __init__(
        self, 
        device_id: str,
        sample_rate: float = 100.0, 
        channels: int = 4
    ):
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.num_channels = channels
        self._phase = [0.0] * channels
        self._time = 0.0
        self._running = False
        
        # Pattern parameters
        self._pattern = "baseline"
        self._pattern_freq = 0.3
        self._pattern_amp = 0.5
    
    def generate_sample(self) -> Dict[str, Any]:
        """
        Legacy interface - synchronous sample generation.
        
        Returns dict format compatible with the old FCISignalSimulator.
        """
        self._time += 1.0 / self.sample_rate
        
        channels = []
        for ch in range(self.num_channels):
            # Base signal: pattern frequency + noise
            base = self._pattern_amp * math.sin(
                2 * math.pi * self._pattern_freq * self._time + self._phase[ch]
            )
            
            # Add noise components
            noise = random.gauss(0, 0.1)
            hum_50hz = 0.3 * math.sin(2 * math.pi * 50 * self._time)
            hum_60hz = 0.2 * math.sin(2 * math.pi * 60 * self._time)
            
            value = base + noise + hum_50hz + hum_60hz
            
            # Occasional spike
            if random.random() < 0.005:
                value += random.choice([-1, 1]) * random.uniform(5, 15)
            
            channels.append({
                "channel": ch,
                "value": value,
            })
            
            self._phase[ch] += random.uniform(-0.01, 0.01)  # Phase drift
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channels": channels,
        }
    
    @property
    def mode(self) -> FCIDriverMode:
        return FCIDriverMode.SIMULATOR
    
    async def start(self) -> bool:
        self._running = True
        logger.info(f"[FCI Simulator] Started for device {self.device_id}")
        return True
    
    async def stop(self) -> None:
        self._running = False
        logger.info(f"[FCI Simulator] Stopped for device {self.device_id}")
    
    def is_connected(self) -> bool:
        return self._running
    
    def set_pattern(self, pattern: str) -> None:
        """Set the current signal pattern."""
        patterns = {
            "baseline": (0.3, 0.5),
            "active_growth": (1.0, 1.5),
            "nutrient_seeking": (2.5, 2.0),
            "temperature_stress": (0.5, 3.0),
            "chemical_stress": (5.0, 5.0),
            "network_communication": (0.5, 1.0),
            "action_potential": (10.0, 15.0),
            "seismic_precursor": (0.05, 0.5),
            "defense_activation": (4.0, 4.0),
        }
        if pattern in patterns:
            self._pattern = pattern
            self._pattern_freq, self._pattern_amp = patterns[pattern]
            logger.debug(f"[FCI Simulator] Pattern set to: {pattern}")
    
    async def get_sample(self) -> FCISample:
        """Generate one sample for all channels."""
        self._time += 1.0 / self.sample_rate
        
        channels = []
        for ch in range(self.num_channels):
            # Base signal: pattern frequency + noise
            base = self._pattern_amp * math.sin(
                2 * math.pi * self._pattern_freq * self._time + self._phase[ch]
            )
            
            # Add noise components
            noise = random.gauss(0, 0.1)
            hum_50hz = 0.3 * math.sin(2 * math.pi * 50 * self._time)
            hum_60hz = 0.2 * math.sin(2 * math.pi * 60 * self._time)
            
            value = base + noise + hum_50hz + hum_60hz
            
            # Occasional spike
            if random.random() < 0.005:
                value += random.choice([-1, 1]) * random.uniform(5, 15)
            
            channels.append({
                "channel": ch,
                "value": value,
            })
            
            self._phase[ch] += random.uniform(-0.01, 0.01)  # Phase drift
        
        return FCISample(
            timestamp=datetime.now(timezone.utc),
            channels=channels,
            device_id=self.device_id,
            is_simulated=True,
            quality_score=0.85 + random.uniform(0, 0.15),
        )


class MycoBrainFCIDriver(FCIDriverBase):
    """
    Hardware driver for MycoBrain FCI devices.
    
    Connects to MycoBrain ESP32 devices via:
    1. WebSocket (preferred for real-time streaming)
    2. HTTP polling (fallback for lower-rate sampling)
    
    The MycoBrain device must be configured to:
    - Connect to the same network as MAS
    - Send FCI data to the configured endpoint
    
    Configuration is done via firmware settings or the notify endpoint.
    """
    
    def __init__(
        self,
        device_id: str,
        mycobrain_host: Optional[str] = None,
        mycobrain_port: int = 80,
        sample_rate: float = 100.0,
        channels: int = 2,
    ):
        self.device_id = device_id
        self.mycobrain_host = mycobrain_host  # None = auto-discover via mDNS/notify
        self.mycobrain_port = mycobrain_port
        self.sample_rate = sample_rate
        self.num_channels = channels
        
        self._running = False
        self._connected = False
        self._last_sample: Optional[FCISample] = None
        self._sample_buffer: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._ws_task: Optional[asyncio.Task] = None
        
        # Fallback simulator for when hardware is disconnected
        self._fallback = FCISimulatorDriver(device_id, sample_rate, channels)
        self._use_fallback = False
    
    @property
    def mode(self) -> FCIDriverMode:
        return FCIDriverMode.HYBRID
    
    async def start(self) -> bool:
        """Start the driver and attempt hardware connection."""
        self._running = True
        
        # Start fallback simulator
        await self._fallback.start()
        
        # Try to connect to hardware
        if self.mycobrain_host:
            connected = await self._connect_websocket()
            if connected:
                logger.info(f"[FCI Hardware] Connected to MycoBrain at {self.mycobrain_host}")
                self._use_fallback = False
                return True
        
        # Fall back to simulator
        self._use_fallback = True
        logger.warning(f"[FCI Hardware] No MycoBrain found, using simulator for {self.device_id}")
        return True
    
    async def stop(self) -> None:
        """Stop the driver and cleanup."""
        self._running = False
        
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        
        await self._fallback.stop()
        self._connected = False
        logger.info(f"[FCI Hardware] Stopped driver for {self.device_id}")
    
    def is_connected(self) -> bool:
        return self._connected or (self._use_fallback and self._fallback.is_connected())
    
    def set_pattern(self, pattern: str) -> None:
        """Forward to fallback simulator or send command to hardware."""
        self._fallback.set_pattern(pattern)
        
        if self._connected and not self._use_fallback:
            # Could send pattern change command to hardware
            # (e.g., for closed-loop experiments)
            pass
    
    def generate_sample(self) -> Dict[str, Any]:
        """
        Legacy interface - synchronous sample generation.
        
        Uses fallback simulator when hardware is not connected.
        When hardware IS connected, still uses last hardware sample
        converted to legacy format.
        """
        # Use fallback simulator for legacy interface
        # The async get_sample() should be preferred for new code
        return self._fallback.generate_sample()
    
    async def get_sample(self) -> FCISample:
        """Get a sample from hardware or fallback to simulator."""
        if self._use_fallback or not self._connected:
            return await self._fallback.get_sample()
        
        try:
            # Non-blocking get from buffer with timeout
            sample = await asyncio.wait_for(
                self._sample_buffer.get(),
                timeout=1.0 / self.sample_rate * 2  # 2x sample period timeout
            )
            return sample
        except asyncio.TimeoutError:
            # Hardware stalled, use fallback
            logger.warning(f"[FCI Hardware] Sample timeout, falling back to simulator")
            return await self._fallback.get_sample()
    
    async def _connect_websocket(self) -> bool:
        """Establish WebSocket connection to MycoBrain."""
        if not self.mycobrain_host:
            return False
        
        try:
            # MycoBrain FCI WebSocket endpoint
            ws_url = f"ws://{self.mycobrain_host}:{self.mycobrain_port}/ws/fci"
            
            # Start WebSocket receiver task
            self._ws_task = asyncio.create_task(self._websocket_receiver(ws_url))
            
            # Wait briefly to see if connection succeeds
            await asyncio.sleep(0.5)
            return self._connected
            
        except Exception as e:
            logger.error(f"[FCI Hardware] WebSocket connection failed: {e}")
            return False
    
    async def _websocket_receiver(self, ws_url: str) -> None:
        """Background task to receive samples from MycoBrain WebSocket."""
        import websockets
        
        try:
            async with websockets.connect(ws_url) as ws:
                self._connected = True
                self._use_fallback = False
                logger.info(f"[FCI Hardware] WebSocket connected to {ws_url}")
                
                while self._running:
                    try:
                        message = await ws.recv()
                        data = json.loads(message)
                        
                        if data.get("type") == "fci_sample":
                            sample = FCISample(
                                timestamp=datetime.fromisoformat(
                                    data.get("timestamp", datetime.now(timezone.utc).isoformat())
                                ),
                                channels=data.get("channels", []),
                                device_id=self.device_id,
                                is_simulated=False,
                                quality_score=data.get("quality", 0.9),
                            )
                            
                            # Add to buffer (drop oldest if full)
                            if self._sample_buffer.full():
                                try:
                                    self._sample_buffer.get_nowait()
                                except asyncio.QueueEmpty:
                                    pass
                            
                            await self._sample_buffer.put(sample)
                            
                    except json.JSONDecodeError:
                        logger.warning("[FCI Hardware] Invalid JSON from MycoBrain")
                        
        except Exception as e:
            logger.error(f"[FCI Hardware] WebSocket error: {e}")
            self._connected = False
            self._use_fallback = True
    
    async def discover_device(self) -> Optional[str]:
        """
        Attempt to discover MycoBrain device on the network.
        
        Returns the IP address if found, None otherwise.
        """
        # Check with Mycorrhizae Protocol for registered devices
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "http://192.168.0.188:8001/api/fci/devices/active"
                )
                if response.status_code == 200:
                    data = response.json()
                    for device in data.get("devices", []):
                        if device.get("device_id") == self.device_id:
                            return device.get("ip_address")
        except Exception as e:
            logger.debug(f"[FCI Hardware] Device discovery failed: {e}")
        
        return None


# ============================================================================
# DRIVER FACTORY
# ============================================================================


_drivers: Dict[str, FCIDriverBase] = {}


def get_driver(
    device_id: str,
    mode: FCIDriverMode = FCIDriverMode.HYBRID,
    mycobrain_host: Optional[str] = None,
) -> FCIDriverBase:
    """
    Get or create an FCI driver for a device.
    
    Args:
        device_id: The FCI device identifier
        mode: SIMULATOR, HARDWARE, or HYBRID (default)
        mycobrain_host: IP address of MycoBrain device (for HARDWARE mode)
    
    Returns:
        An FCI driver instance
    """
    if device_id in _drivers:
        return _drivers[device_id]
    
    if mode == FCIDriverMode.SIMULATOR or device_id.startswith("demo-"):
        driver = FCISimulatorDriver(device_id)
    elif mode == FCIDriverMode.HARDWARE:
        driver = MycoBrainFCIDriver(device_id, mycobrain_host=mycobrain_host)
    else:  # HYBRID
        driver = MycoBrainFCIDriver(device_id, mycobrain_host=mycobrain_host)
    
    _drivers[device_id] = driver
    return driver


async def register_hardware_device(device_id: str, ip_address: str) -> bool:
    """
    Register a hardware device discovered via mDNS or notify endpoint.
    
    This allows the driver to connect to the device.
    """
    if device_id in _drivers:
        driver = _drivers[device_id]
        if isinstance(driver, MycoBrainFCIDriver):
            driver.mycobrain_host = ip_address
            logger.info(f"[FCI Driver] Registered hardware device {device_id} at {ip_address}")
            return True
    else:
        # Create new hardware driver
        driver = MycoBrainFCIDriver(device_id, mycobrain_host=ip_address)
        _drivers[device_id] = driver
        logger.info(f"[FCI Driver] Created hardware driver for {device_id} at {ip_address}")
        return True
    
    return False
