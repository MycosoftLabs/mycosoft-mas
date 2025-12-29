"""WiFi Sense Analysis Agent for MAS."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx
import os


class WiFiSenseAnalysisAgent:
    """Agent for analyzing WiFi Sense presence and motion data."""
    
    def __init__(self):
        self.mindex_base_url = os.getenv("MINDEX_API_BASE_URL", "http://localhost:8002")
        self.mindex_api_key = os.getenv("MINDEX_API_KEY", "dev-secret")
    
    async def analyze_presence_patterns(
        self,
        zone_id: str,
        time_range: tuple[datetime, datetime],
    ) -> Dict[str, Any]:
        """
        Analyze presence patterns in a zone over a time range.
        
        Args:
            zone_id: Zone identifier
            time_range: Tuple of (start_time, end_time)
        
        Returns:
            Dictionary with pattern analysis results
        """
        start_time, end_time = time_range
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.mindex_base_url}/wifisense/events",
                headers={"X-API-Key": self.mindex_api_key},
                params={
                    "zone_id": zone_id,
                    "since": start_time.isoformat(),
                },
            )
            response.raise_for_status()
            events = response.json()
        
        # Filter events by time range
        filtered_events = [
            e for e in events
            if start_time <= datetime.fromisoformat(e["timestamp"]) <= end_time
        ]
        
        # Analyze patterns
        occupancy_count = sum(1 for e in filtered_events if e["presence_type"] == "occupancy")
        motion_count = sum(1 for e in filtered_events if e["presence_type"] == "motion")
        activity_count = sum(1 for e in filtered_events if e["presence_type"] == "activity")
        
        # Calculate average confidence
        avg_confidence = (
            sum(e["confidence"] for e in filtered_events) / len(filtered_events)
            if filtered_events else 0.0
        )
        
        return {
            "zone_id": zone_id,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "total_events": len(filtered_events),
            "occupancy_events": occupancy_count,
            "motion_events": motion_count,
            "activity_events": activity_count,
            "average_confidence": avg_confidence,
            "analysis_timestamp": datetime.utcnow().isoformat(),
        }
    
    async def detect_anomalies(self, zone_id: str) -> List[Dict[str, Any]]:
        """
        Detect anomalies in presence patterns.
        
        Args:
            zone_id: Zone identifier
        
        Returns:
            List of detected anomalies
        """
        # Get recent events (last hour)
        since = datetime.utcnow() - timedelta(hours=1)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.mindex_base_url}/wifisense/events",
                headers={"X-API-Key": self.mindex_api_key},
                params={
                    "zone_id": zone_id,
                    "since": since.isoformat(),
                },
            )
            response.raise_for_status()
            events = response.json()
        
        anomalies = []
        
        # Detect unusual patterns
        if len(events) == 0:
            anomalies.append({
                "type": "no_activity",
                "zone_id": zone_id,
                "message": "No presence events detected in the last hour",
                "severity": "low",
            })
        elif len(events) > 100:
            anomalies.append({
                "type": "high_activity",
                "zone_id": zone_id,
                "message": f"Unusually high activity: {len(events)} events in the last hour",
                "severity": "medium",
            })
        
        # Check for low confidence events
        low_confidence_events = [e for e in events if e.get("confidence", 1.0) < 0.5]
        if len(low_confidence_events) > len(events) * 0.3:
            anomalies.append({
                "type": "low_confidence",
                "zone_id": zone_id,
                "message": f"High percentage of low-confidence events: {len(low_confidence_events)}/{len(events)}",
                "severity": "medium",
            })
        
        return anomalies
    
    async def get_zone_status(self, zone_id: str) -> Dict[str, Any]:
        """Get current status of a zone."""
        async with httpx.AsyncClient() as client:
            # Get active tracks
            tracks_response = await client.get(
                f"{self.mindex_base_url}/wifisense/tracks",
                headers={"X-API-Key": self.mindex_api_key},
                params={"zone_id": zone_id, "active": True},
            )
            tracks_response.raise_for_status()
            tracks = tracks_response.json()
            
            # Get recent events
            since = datetime.utcnow() - timedelta(minutes=5)
            events_response = await client.get(
                f"{self.mindex_base_url}/wifisense/events",
                headers={"X-API-Key": self.mindex_api_key},
                params={"zone_id": zone_id, "since": since.isoformat()},
            )
            events_response.raise_for_status()
            events = events_response.json()
        
        return {
            "zone_id": zone_id,
            "active_tracks": len(tracks),
            "recent_events": len(events),
            "tracks": tracks,
            "last_updated": datetime.utcnow().isoformat(),
        }

