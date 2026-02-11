"""
FCI WebSocket Router - Real-time Signal Streaming

Provides WebSocket endpoints for:
- Real-time FCI signal streaming
- SDR configuration updates
- Stimulation command dispatch
- Pattern detection events

(c) 2026 Mycosoft Labs - February 9, 2026
"""

import asyncio
import json
import logging
import math
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

# Import SDR pipeline
try:
    from mycosoft_mas.bio.sdr_pipeline import (
        SDRPipeline,
        SDRConfig,
        FilterPreset,
        EMFPreset,
        RFPreset,
        create_pipeline_from_preset,
    )
    HAS_SDR = True
except ImportError:
    HAS_SDR = False

logger = logging.getLogger(__name__)

# Import FCI driver for hardware/hybrid mode
try:
    from mycosoft_mas.devices.fci_driver import (
        get_driver,
        FCIDriverMode,
        FCIDriverBase,
        register_hardware_device,
    )
    HAS_FCI_DRIVER = True
except ImportError:
    HAS_FCI_DRIVER = False

router = APIRouter(prefix="/api/fci", tags=["FCI WebSocket"])


# ============================================================================
# CONNECTION MANAGER
# ============================================================================


class ConnectionManager:
    """Manages WebSocket connections for FCI streaming."""
    
    def __init__(self):
        # Map device_id -> set of connected websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # SDR pipelines per connection
        self.pipelines: Dict[WebSocket, SDRPipeline] = {}
        # All connections for global broadcasts (e.g., device discovery)
        self.all_connections: Set[WebSocket] = set()
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        is_first_for_device = False
        async with self._lock:
            if device_id not in self.active_connections:
                self.active_connections[device_id] = set()
                is_first_for_device = True
            self.active_connections[device_id].add(websocket)
            self.all_connections.add(websocket)
            
            # Create SDR pipeline for this connection
            if HAS_SDR:
                self.pipelines[websocket] = create_pipeline_from_preset(FilterPreset.LAB)
        
        logger.info(f"WS connected: device={device_id}, total={len(self.active_connections.get(device_id, set()))}")
        
        # Broadcast device_connected event if this is the first connection for this device
        if is_first_for_device:
            await self.broadcast_all({
                "type": "device_connected",
                "device_id": device_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    async def disconnect(self, websocket: WebSocket, device_id: str):
        is_last_for_device = False
        async with self._lock:
            if device_id in self.active_connections:
                self.active_connections[device_id].discard(websocket)
                if not self.active_connections[device_id]:
                    del self.active_connections[device_id]
                    is_last_for_device = True
            
            self.all_connections.discard(websocket)
            
            if websocket in self.pipelines:
                del self.pipelines[websocket]
        
        logger.info(f"WS disconnected: device={device_id}")
        
        # Broadcast device_disconnected event if this was the last connection for this device
        if is_last_for_device:
            await self.broadcast_all({
                "type": "device_disconnected",
                "device_id": device_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    async def broadcast_to_device(self, device_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections watching a device."""
        async with self._lock:
            connections = self.active_connections.get(device_id, set()).copy()
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WS: {e}")
    
    async def broadcast_all(self, message: Dict[str, Any]):
        """Broadcast a message to ALL connected clients (for device discovery events)."""
        async with self._lock:
            connections = self.all_connections.copy()
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to WS: {e}")
    
    def get_pipeline(self, websocket: WebSocket) -> Optional[SDRPipeline]:
        return self.pipelines.get(websocket)
    
    def update_pipeline_config(self, websocket: WebSocket, config: SDRConfig):
        if websocket in self.pipelines:
            self.pipelines[websocket].update_config(config)
    
    def get_active_devices(self) -> List[str]:
        """Get list of device IDs with active connections."""
        return list(self.active_connections.keys())


manager = ConnectionManager()


# ============================================================================
# SIGNAL GENERATOR (simulated for development)
# ============================================================================


class FCISignalSimulator:
    """
    Simulates FCI signals for development and testing.
    In production, this would be replaced by real device data.
    """
    
    def __init__(self, sample_rate: float = 100.0, channels: int = 4):
        self.sample_rate = sample_rate
        self.channels = channels
        self._phase = [0.0] * channels
        self._time = 0.0
        
        # Pattern parameters
        self._pattern = "baseline"
        self._pattern_freq = 0.3
        self._pattern_amp = 0.5
    
    def set_pattern(self, pattern: str):
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
    
    def generate_sample(self) -> Dict[str, Any]:
        """Generate one sample for all channels."""
        self._time += 1.0 / self.sample_rate
        
        channels = []
        for ch in range(self.channels):
            # Base signal: pattern frequency + noise
            base = self._pattern_amp * math.sin(2 * math.pi * self._pattern_freq * self._time + self._phase[ch])
            
            # Add noise components
            noise = random.gauss(0, 0.1)  # Gaussian noise
            hum_50hz = 0.3 * math.sin(2 * math.pi * 50 * self._time)  # 50Hz hum
            hum_60hz = 0.2 * math.sin(2 * math.pi * 60 * self._time)  # 60Hz hum
            
            value = base + noise + hum_50hz + hum_60hz
            
            # Occasional spike
            if random.random() < 0.005:
                value += random.choice([-1, 1]) * random.uniform(5, 15)
            
            channels.append({
                "channel": ch,
                "value": value,
            })
            
            self._phase[ch] += random.uniform(-0.01, 0.01)  # Slight phase drift
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channels": channels,
        }
    
    def generate_spectrum(self, samples: List[float]) -> Dict[str, Any]:
        """Generate spectrum data from samples."""
        n = len(samples)
        if n < 8:
            return {"frequencies": [], "magnitudes": [], "peak_frequency": 0, "peak_magnitude": 0}
        
        # Simple DFT for demo (use numpy in real implementation)
        magnitudes = []
        frequencies = []
        
        for k in range(n // 2):
            freq = k * self.sample_rate / n
            frequencies.append(freq)
            
            # DFT bin magnitude
            real_sum = 0.0
            imag_sum = 0.0
            for i, sample in enumerate(samples):
                angle = 2 * math.pi * k * i / n
                real_sum += sample * math.cos(angle)
                imag_sum -= sample * math.sin(angle)
            
            mag = math.sqrt(real_sum**2 + imag_sum**2) / n
            magnitudes.append(mag)
        
        # Find peak
        peak_idx = 1  # Skip DC
        for i in range(2, len(magnitudes)):
            if magnitudes[i] > magnitudes[peak_idx]:
                peak_idx = i
        
        return {
            "frequencies": frequencies,
            "magnitudes": magnitudes,
            "peak_frequency": frequencies[peak_idx] if frequencies else 0,
            "peak_magnitude": magnitudes[peak_idx] if magnitudes else 0,
        }


# Device simulators/drivers
_simulators: Dict[str, FCISignalSimulator] = {}


def get_simulator(device_id: str) -> FCISignalSimulator:
    """Get or create a simulator for a device (legacy compatibility)."""
    if device_id not in _simulators:
        _simulators[device_id] = FCISignalSimulator()
    return _simulators[device_id]


def get_signal_source(device_id: str, sample_rate: float = 100.0):
    """
    Get the appropriate signal source for a device.
    
    Returns an FCI driver (hardware/hybrid) if available,
    otherwise falls back to the built-in simulator.
    """
    if HAS_FCI_DRIVER and not device_id.startswith("demo-"):
        # Use the FCI driver system for real/hybrid mode
        driver = get_driver(device_id, mode=FCIDriverMode.HYBRID)
        return driver
    else:
        # Use built-in simulator for demo devices
        return get_simulator(device_id)


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================


@router.websocket("/ws/stream/{device_id}")
async def fci_stream_websocket(
    websocket: WebSocket,
    device_id: str,
    sample_rate: float = Query(default=100.0, ge=10.0, le=1000.0),
):
    """
    WebSocket endpoint for real-time FCI signal streaming.
    
    Messages sent to client:
    - {"type": "sample", "data": {...}}: Raw and filtered sample data
    - {"type": "spectrum", "data": {...}}: FFT spectrum analysis
    - {"type": "pattern", "data": {...}}: Detected GFST pattern
    - {"type": "event", "data": {...}}: Significant event
    
    Messages from client:
    - {"type": "sdr_config", "config": {...}}: Update SDR filter configuration
    - {"type": "stimulate", "command": {...}}: Send stimulation command
    - {"type": "set_pattern", "pattern": "..."}: (dev) Set simulated pattern
    """
    await manager.connect(websocket, device_id)
    
    # Get signal source (hardware driver or simulator based on device ID)
    signal_source = get_signal_source(device_id, sample_rate)
    
    # Set sample rate (compatible with both simulator and driver)
    if hasattr(signal_source, 'sample_rate'):
        signal_source.sample_rate = sample_rate
    
    sample_buffer: List[float] = []
    sample_count = 0
    spectrum_interval = int(sample_rate * 0.5)  # Spectrum every 0.5 seconds
    pattern_interval = int(sample_rate * 1.0)  # Pattern check every 1 second
    
    try:
        # Create receive and send tasks
        send_task = asyncio.create_task(_stream_samples(
            websocket, device_id, signal_source, sample_rate
        ))
        receive_task = asyncio.create_task(_receive_commands(
            websocket, device_id, signal_source
        ))
        
        # Wait for either to complete (disconnect or error)
        done, pending = await asyncio.wait(
            [send_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
        
    except WebSocketDisconnect:
        logger.info(f"WS disconnected: {device_id}")
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        await manager.disconnect(websocket, device_id)


async def _stream_samples(
    websocket: WebSocket,
    device_id: str,
    signal_source: Any,  # FCISignalSimulator or FCIDriverBase
    sample_rate: float,
):
    """Stream samples to the client."""
    sample_buffer: List[float] = []
    sample_count = 0
    spectrum_interval = int(sample_rate * 0.5)
    pattern_interval = int(sample_rate * 1.0)
    
    pipeline = manager.get_pipeline(websocket)
    
    try:
        while True:
            # Generate sample from signal source (simulator or hardware)
            raw_sample = signal_source.generate_sample()
            
            # Process through SDR pipeline
            processed_channels = []
            for ch_data in raw_sample["channels"]:
                if pipeline and HAS_SDR:
                    processed = pipeline.process_sample(
                        ch_data["value"],
                        channel=ch_data["channel"],
                    )
                    processed_channels.append({
                        "channel": ch_data["channel"],
                        "raw": ch_data["value"],
                        "filtered": processed.filtered_value,
                        "is_artifact": processed.is_artifact,
                        "spike": processed.spike_detected,
                        "snr_db": processed.snr_db,
                    })
                else:
                    processed_channels.append({
                        "channel": ch_data["channel"],
                        "raw": ch_data["value"],
                        "filtered": ch_data["value"],
                        "is_artifact": False,
                        "spike": False,
                        "snr_db": 0.0,
                    })
            
            # Send sample
            await websocket.send_json({
                "type": "sample",
                "timestamp": raw_sample["timestamp"],
                "channels": processed_channels,
            })
            
            # Collect for spectrum analysis
            if processed_channels:
                sample_buffer.append(processed_channels[0]["filtered"])
            sample_count += 1
            
            # Send spectrum periodically
            if sample_count % spectrum_interval == 0 and len(sample_buffer) >= 64:
                if pipeline and HAS_SDR:
                    spectrum = pipeline.compute_spectrum(sample_buffer[-256:])
                    await websocket.send_json({
                        "type": "spectrum",
                        "data": {
                            "frequencies": spectrum.frequencies[:64],
                            "magnitudes": spectrum.magnitudes[:64],
                            "peak_frequency": spectrum.peak_frequency,
                            "peak_magnitude": spectrum.peak_magnitude,
                            "band_powers": spectrum.band_powers,
                            "spectral_entropy": spectrum.spectral_entropy,
                        },
                    })
                else:
                    spectrum = simulator.generate_spectrum(sample_buffer[-256:])
                    await websocket.send_json({
                        "type": "spectrum",
                        "data": spectrum,
                    })
            
            # Pattern detection periodically
            if sample_count % pattern_interval == 0 and pipeline and HAS_SDR:
                if len(sample_buffer) >= 64:
                    spectrum = pipeline.compute_spectrum(sample_buffer[-256:])
                    rms = math.sqrt(sum(s**2 for s in sample_buffer[-100:]) / 100)
                    pattern = pipeline.classify_pattern(spectrum, rms)
                    
                    if pattern:
                        await websocket.send_json({
                            "type": "pattern",
                            "data": {
                                "pattern_name": pattern.pattern_name,
                                "category": pattern.category,
                                "confidence": pattern.confidence,
                                "frequency": pattern.frequency,
                                "amplitude": pattern.amplitude,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        })
            
            # Rate limit
            await asyncio.sleep(1.0 / sample_rate)
    
    except asyncio.CancelledError:
        pass


async def _receive_commands(
    websocket: WebSocket,
    device_id: str,
    signal_source: Any,  # FCISignalSimulator or FCIDriverBase
):
    """Receive and handle commands from client."""
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "sdr_config":
                # Update SDR configuration
                config_data = data.get("config", {})
                if HAS_SDR:
                    config = SDRConfig(
                        bandpass_low=config_data.get("bandpass_low", 0.01),
                        bandpass_high=config_data.get("bandpass_high", 50.0),
                        notch_50hz=config_data.get("notch_50hz", True),
                        notch_60hz=config_data.get("notch_60hz", True),
                        notch_q=config_data.get("notch_q", 30.0),
                        adaptive_enabled=config_data.get("adaptive_enabled", True),
                        adaptive_threshold=config_data.get("adaptive_threshold", 3.0),
                        agc_enabled=config_data.get("agc_enabled", True),
                        dc_removal=config_data.get("dc_removal", True),
                    )
                    manager.update_pipeline_config(websocket, config)
                    
                    await websocket.send_json({
                        "type": "config_ack",
                        "status": "updated",
                    })
            
            elif msg_type == "stimulate":
                # Handle stimulation command
                command = data.get("command", {})
                logger.info(f"Stimulation command for {device_id}: {command}")
                
                # Would send to actual device here
                await websocket.send_json({
                    "type": "stimulate_ack",
                    "status": "queued",
                    "command_id": str(uuid4()),
                })
            
            elif msg_type == "set_pattern":
                # Dev mode: set simulated pattern
                pattern = data.get("pattern", "baseline")
                if hasattr(signal_source, 'set_pattern'):
                    signal_source.set_pattern(pattern)
                
                await websocket.send_json({
                    "type": "pattern_set",
                    "pattern": pattern,
                })
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        pass


# ============================================================================
# HTTP ENDPOINTS FOR TESTING AND DEVICE DISCOVERY
# ============================================================================


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status."""
    return {
        "active_devices": manager.get_active_devices(),
        "total_connections": sum(
            len(conns) for conns in manager.active_connections.values()
        ),
        "sdr_available": HAS_SDR,
    }


@router.get("/devices/active")
async def get_active_devices():
    """
    Get list of currently connected FCI devices.
    Use this for device discovery without WebSocket.
    """
    active = manager.get_active_devices()
    return {
        "devices": active,
        "count": len(active),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class DeviceEventNotification(BaseModel):
    device_id: str
    event: str  # "connected" or "disconnected"


@router.post("/devices/notify")
async def notify_device_event(notification: DeviceEventNotification):
    """
    External endpoint for MycoBrain/Mycorrhizae to notify of device events.
    This allows the firmware to report hot-plug events to MAS, which then
    broadcasts to all connected WebSocket clients.
    """
    event_type = f"device_{notification.event}"
    message = {
        "type": event_type,
        "device_id": notification.device_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "firmware",
    }
    
    await manager.broadcast_all(message)
    logger.info(f"Device event broadcast: {event_type} for {notification.device_id}")
    
    return {
        "status": "broadcast",
        "event": event_type,
        "device_id": notification.device_id,
    }
