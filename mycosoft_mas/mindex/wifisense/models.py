"""
WiFiSense Data Models
Pydantic models for CSI data and sensing results
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum


class PresenceState(str, Enum):
    """Presence detection states"""
    ABSENT = "absent"
    PRESENT = "present"
    ENTERING = "entering"
    LEAVING = "leaving"
    UNKNOWN = "unknown"


class MotionLevel(str, Enum):
    """Motion activity levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CSIReading(BaseModel):
    """Raw CSI data from ESP32/WiFi device"""
    device_id: str = Field(..., description="Source device ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    rssi: float = Field(..., description="Received Signal Strength Indicator (dBm)")
    
    # CSI amplitude/phase data (if available from ESP32-CSI firmware)
    csi_amplitude: Optional[List[float]] = Field(None, description="CSI amplitude per subcarrier")
    csi_phase: Optional[List[float]] = Field(None, description="CSI phase per subcarrier")
    
    # Additional metadata
    mac_tx: Optional[str] = Field(None, description="Transmitter MAC address")
    mac_rx: Optional[str] = Field(None, description="Receiver MAC address")
    channel: Optional[int] = Field(None, description="WiFi channel")
    bandwidth: Optional[int] = Field(20, description="Channel bandwidth (MHz)")


class PresenceEvent(BaseModel):
    """Presence detection result"""
    zone_id: str = Field(..., description="Zone or room identifier")
    state: PresenceState = Field(..., description="Current presence state")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    device_ids: List[str] = Field(default_factory=list, description="Contributing devices")
    rssi_avg: Optional[float] = Field(None, description="Average RSSI in zone")
    occupancy_count: Optional[int] = Field(None, description="Estimated occupancy count")


class MotionEvent(BaseModel):
    """Motion detection result"""
    zone_id: str = Field(..., description="Zone or room identifier")
    motion_level: MotionLevel = Field(..., description="Motion activity level")
    velocity_estimate: Optional[float] = Field(None, description="Estimated velocity (m/s)")
    direction: Optional[str] = Field(None, description="Motion direction estimate")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    variance: Optional[float] = Field(None, description="CSI amplitude variance")


class ZoneConfig(BaseModel):
    """WiFiSense zone configuration"""
    zone_id: str = Field(..., description="Unique zone identifier")
    name: str = Field(..., description="Human-readable zone name")
    devices: List[str] = Field(default_factory=list, description="Device IDs covering this zone")
    presence_threshold: float = Field(-70.0, description="RSSI threshold for presence (dBm)")
    motion_sensitivity: float = Field(0.5, ge=0.0, le=1.0, description="Motion detection sensitivity")
    enabled: bool = Field(True, description="Whether zone sensing is enabled")


class WiFiSenseStatus(BaseModel):
    """Overall WiFiSense system status"""
    enabled: bool = Field(True)
    zones: List[ZoneConfig] = Field(default_factory=list)
    devices_online: int = Field(0)
    devices_total: int = Field(0)
    last_reading: Optional[datetime] = None
    processing_mode: Literal["phase0", "phase1", "phase2"] = "phase0"
