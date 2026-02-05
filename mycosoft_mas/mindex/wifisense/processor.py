"""
WiFiSense CSI Processor
Phase 0: RSSI-based presence detection
Phase 1: CSI amplitude variance for motion detection

This processor analyzes WiFi signal data from MycoBrain devices
to detect presence, motion, and environmental changes.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import statistics
import math

from .models import (
    CSIReading,
    PresenceEvent,
    MotionEvent,
    ZoneConfig,
    PresenceState,
    MotionLevel,
    WiFiSenseStatus,
)


class RSSIBuffer:
    """Circular buffer for RSSI readings with statistics"""
    
    def __init__(self, max_size: int = 100, window_seconds: int = 30):
        self.readings: deque = deque(maxlen=max_size)
        self.window_seconds = window_seconds
    
    def add(self, rssi: float, timestamp: datetime = None):
        if timestamp is None:
            timestamp = datetime.utcnow()
        self.readings.append((timestamp, rssi))
        self._cleanup()
    
    def _cleanup(self):
        """Remove old readings outside the window"""
        cutoff = datetime.utcnow() - timedelta(seconds=self.window_seconds)
        while self.readings and self.readings[0][0] < cutoff:
            self.readings.popleft()
    
    def get_stats(self) -> Dict:
        """Get statistics for current readings"""
        self._cleanup()
        if not self.readings:
            return {"count": 0, "mean": None, "std": None, "min": None, "max": None}
        
        values = [r[1] for r in self.readings]
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "variance": statistics.variance(values) if len(values) > 1 else 0,
        }
    
    def get_trend(self) -> str:
        """Detect trend in RSSI (approaching/leaving/stable)"""
        self._cleanup()
        if len(self.readings) < 5:
            return "unknown"
        
        # Compare first and last quartile means
        n = len(self.readings)
        q1_values = [r[1] for r in list(self.readings)[:n//4+1]]
        q4_values = [r[1] for r in list(self.readings)[-n//4-1:]]
        
        if not q1_values or not q4_values:
            return "stable"
        
        q1_mean = statistics.mean(q1_values)
        q4_mean = statistics.mean(q4_values)
        
        diff = q4_mean - q1_mean
        if diff > 3:  # 3 dB increase = approaching
            return "approaching"
        elif diff < -3:  # 3 dB decrease = leaving
            return "leaving"
        return "stable"


class WiFiSenseProcessor:
    """
    WiFi CSI/RSSI processor for presence and motion detection
    
    Phase 0: Uses RSSI patterns for presence detection
    - Threshold-based presence detection
    - RSSI variance for motion indication
    - Trend analysis for entering/leaving detection
    
    Phase 1 (future): CSI amplitude variance for motion
    Phase 2 (future): CSI phase for pose estimation
    """
    
    def __init__(self):
        self.zones: Dict[str, ZoneConfig] = {}
        self.device_buffers: Dict[str, RSSIBuffer] = {}
        self.zone_states: Dict[str, PresenceState] = {}
        self.last_events: Dict[str, datetime] = {}
        self.enabled = True
        self.processing_mode = "phase0"
    
    def configure_zone(self, zone: ZoneConfig):
        """Add or update a zone configuration"""
        self.zones[zone.zone_id] = zone
        self.zone_states[zone.zone_id] = PresenceState.UNKNOWN
    
    def remove_zone(self, zone_id: str):
        """Remove a zone configuration"""
        self.zones.pop(zone_id, None)
        self.zone_states.pop(zone_id, None)
    
    def process_reading(self, reading: CSIReading) -> List:
        """
        Process a CSI/RSSI reading and return any events
        Returns list of PresenceEvent and/or MotionEvent
        """
        if not self.enabled:
            return []
        
        events = []
        device_id = reading.device_id
        
        # Get or create buffer for this device
        if device_id not in self.device_buffers:
            self.device_buffers[device_id] = RSSIBuffer()
        
        buffer = self.device_buffers[device_id]
        buffer.add(reading.rssi, reading.timestamp)
        
        # Find zones this device belongs to
        for zone_id, zone in self.zones.items():
            if not zone.enabled:
                continue
            if device_id not in zone.devices:
                continue
            
            # Process presence for this zone
            presence_event = self._detect_presence(zone, buffer)
            if presence_event:
                events.append(presence_event)
            
            # Process motion for this zone
            motion_event = self._detect_motion(zone, buffer)
            if motion_event:
                events.append(motion_event)
        
        return events
    
    def _detect_presence(self, zone: ZoneConfig, buffer: RSSIBuffer) -> Optional[PresenceEvent]:
        """Detect presence based on RSSI threshold and trend"""
        stats = buffer.get_stats()
        
        if stats["count"] < 3:
            return None
        
        mean_rssi = stats["mean"]
        trend = buffer.get_trend()
        
        # Determine presence state
        old_state = self.zone_states.get(zone.zone_id, PresenceState.UNKNOWN)
        
        if mean_rssi > zone.presence_threshold:
            if trend == "approaching" and old_state in [PresenceState.ABSENT, PresenceState.UNKNOWN]:
                new_state = PresenceState.ENTERING
            elif old_state == PresenceState.ENTERING:
                new_state = PresenceState.PRESENT
            else:
                new_state = PresenceState.PRESENT
        else:
            if trend == "leaving" and old_state == PresenceState.PRESENT:
                new_state = PresenceState.LEAVING
            elif old_state == PresenceState.LEAVING:
                new_state = PresenceState.ABSENT
            else:
                new_state = PresenceState.ABSENT
        
        # Only emit event on state change
        if new_state != old_state:
            self.zone_states[zone.zone_id] = new_state
            
            # Calculate confidence based on how far above/below threshold
            distance_from_threshold = abs(mean_rssi - zone.presence_threshold)
            confidence = min(1.0, 0.5 + (distance_from_threshold / 20))
            
            return PresenceEvent(
                zone_id=zone.zone_id,
                state=new_state,
                confidence=confidence,
                device_ids=zone.devices,
                rssi_avg=mean_rssi,
            )
        
        return None
    
    def _detect_motion(self, zone: ZoneConfig, buffer: RSSIBuffer) -> Optional[MotionEvent]:
        """Detect motion based on RSSI variance (Phase 0) or CSI variance (Phase 1)"""
        stats = buffer.get_stats()
        
        if stats["count"] < 10:
            return None
        
        variance = stats.get("variance", 0)
        
        # Thresholds scaled by sensitivity
        base_threshold = 2.0  # dB^2
        sensitivity = zone.motion_sensitivity
        
        high_threshold = base_threshold / (sensitivity + 0.1) * 4
        medium_threshold = base_threshold / (sensitivity + 0.1) * 2
        low_threshold = base_threshold / (sensitivity + 0.1)
        
        if variance > high_threshold:
            motion_level = MotionLevel.HIGH
        elif variance > medium_threshold:
            motion_level = MotionLevel.MEDIUM
        elif variance > low_threshold:
            motion_level = MotionLevel.LOW
        else:
            motion_level = MotionLevel.NONE
        
        # Only emit if significant motion
        if motion_level == MotionLevel.NONE:
            return None
        
        # Rate limit motion events (max 1 per 5 seconds)
        last_event = self.last_events.get(f"motion:{zone.zone_id}")
        if last_event and (datetime.utcnow() - last_event).total_seconds() < 5:
            return None
        
        self.last_events[f"motion:{zone.zone_id}"] = datetime.utcnow()
        
        return MotionEvent(
            zone_id=zone.zone_id,
            motion_level=motion_level,
            confidence=min(1.0, variance / high_threshold),
            variance=variance,
        )
    
    def get_zone_status(self, zone_id: str) -> Dict:
        """Get current status for a zone"""
        if zone_id not in self.zones:
            return {"error": "Zone not found"}
        
        zone = self.zones[zone_id]
        state = self.zone_states.get(zone_id, PresenceState.UNKNOWN)
        
        # Aggregate stats from all devices in zone
        all_stats = []
        for device_id in zone.devices:
            if device_id in self.device_buffers:
                all_stats.append(self.device_buffers[device_id].get_stats())
        
        return {
            "zone_id": zone_id,
            "name": zone.name,
            "presence_state": state.value,
            "devices": zone.devices,
            "device_stats": all_stats,
            "enabled": zone.enabled,
        }
    
    def get_status(self) -> WiFiSenseStatus:
        """Get overall system status"""
        devices_online = len([d for d in self.device_buffers.values() if d.get_stats()["count"] > 0])
        
        return WiFiSenseStatus(
            enabled=self.enabled,
            zones=list(self.zones.values()),
            devices_online=devices_online,
            devices_total=len(self.device_buffers),
            processing_mode=self.processing_mode,
        )


# Global processor instance
_processor: Optional[WiFiSenseProcessor] = None


def get_processor() -> WiFiSenseProcessor:
    """Get or create the global WiFiSense processor"""
    global _processor
    if _processor is None:
        _processor = WiFiSenseProcessor()
    return _processor
