"""
NatureOS Client

Client stub for NatureOS API integration.
NatureOS is a biological systems and environmental monitoring platform.
"""

import logging
import os
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from mycosoft_mas.clients.base import BaseClient, ClientConfig, ClientError

logger = logging.getLogger(__name__)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class Sensor(BaseModel):
    """A sensor in the NatureOS network."""
    id: str
    name: str
    type: str
    location: dict[str, float] = Field(default_factory=dict)  # lat, lon, alt
    status: str = "unknown"
    last_reading: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SensorReading(BaseModel):
    """A sensor reading."""
    sensor_id: str
    timestamp: str
    values: dict[str, float] = Field(default_factory=dict)
    quality: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class BiologicalSample(BaseModel):
    """A biological sample record."""
    id: str
    sample_type: str
    species: Optional[str] = None
    location: dict[str, float] = Field(default_factory=dict)
    collected_at: str
    properties: dict[str, Any] = Field(default_factory=dict)
    analysis_results: dict[str, Any] = Field(default_factory=dict)


class EnvironmentalReport(BaseModel):
    """Environmental monitoring report."""
    id: str
    report_type: str
    location: dict[str, float] = Field(default_factory=dict)
    period_start: str
    period_end: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    alerts: list[dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# CLIENT
# =============================================================================

class NatureOSClient(BaseClient):
    """
    Client for NatureOS API.
    
    Provides methods for:
    - Sensor data retrieval
    - Biological sample management
    - Environmental monitoring
    - Alert management
    
    Usage:
        client = NatureOSClient.from_env()
        
        # Get sensor readings
        readings = await client.get_sensor_readings(
            sensor_id="sensor_123",
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-02T00:00:00Z",
        )
        
        # Submit sample
        sample = await client.submit_sample(
            sample_type="soil",
            location={"lat": 37.7749, "lon": -122.4194},
        )
    """
    
    @classmethod
    def from_env(cls) -> "NatureOSClient":
        """Create client from environment variables."""
        config = ClientConfig(
            base_url=os.getenv("NATUREOS_BASE_URL", "https://api.natureos.io"),
            api_key=os.getenv("NATUREOS_API_KEY", ""),
            timeout=30,
            max_retries=3,
        )
        return cls(config)
    
    # =========================================================================
    # SENSORS
    # =========================================================================
    
    async def list_sensors(
        self,
        location: Optional[dict[str, float]] = None,
        radius_km: float = 10.0,
        sensor_type: Optional[str] = None,
        correlation_id: Optional[UUID] = None,
    ) -> list[Sensor]:
        """
        List available sensors.
        
        Args:
            location: Center point for geographic filter
            radius_km: Radius in kilometers
            sensor_type: Filter by sensor type
            correlation_id: Correlation ID for tracing
            
        Returns:
            List of Sensor objects
        """
        params = {}
        
        if location:
            params["lat"] = location.get("lat")
            params["lon"] = location.get("lon")
            params["radius"] = radius_km
        
        if sensor_type:
            params["type"] = sensor_type
        
        response = await self.get(
            "/v1/sensors",
            params=params,
            correlation_id=correlation_id,
        )
        return [Sensor(**s) for s in response.get("sensors", [])]
    
    async def get_sensor(
        self,
        sensor_id: str,
        correlation_id: Optional[UUID] = None,
    ) -> Optional[Sensor]:
        """
        Get a sensor by ID.
        
        Args:
            sensor_id: Sensor ID
            correlation_id: Correlation ID for tracing
            
        Returns:
            Sensor or None if not found
        """
        try:
            response = await self.get(
                f"/v1/sensors/{sensor_id}",
                correlation_id=correlation_id,
            )
            return Sensor(**response)
        except ClientError as e:
            if e.status_code == 404:
                return None
            raise
    
    async def get_sensor_readings(
        self,
        sensor_id: str,
        start_time: str,
        end_time: str,
        interval: str = "1h",
        correlation_id: Optional[UUID] = None,
    ) -> list[SensorReading]:
        """
        Get sensor readings for a time range.
        
        Args:
            sensor_id: Sensor ID
            start_time: Start time (ISO 8601)
            end_time: End time (ISO 8601)
            interval: Aggregation interval (e.g., "1m", "1h", "1d")
            correlation_id: Correlation ID for tracing
            
        Returns:
            List of SensorReading objects
        """
        params = {
            "start": start_time,
            "end": end_time,
            "interval": interval,
        }
        
        response = await self.get(
            f"/v1/sensors/{sensor_id}/readings",
            params=params,
            correlation_id=correlation_id,
        )
        return [SensorReading(**r) for r in response.get("readings", [])]
    
    # =========================================================================
    # BIOLOGICAL SAMPLES
    # =========================================================================
    
    async def submit_sample(
        self,
        sample_type: str,
        location: dict[str, float],
        species: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
        correlation_id: Optional[UUID] = None,
    ) -> BiologicalSample:
        """
        Submit a biological sample for analysis.
        
        Args:
            sample_type: Type of sample (e.g., "soil", "water", "tissue")
            location: Collection location
            species: Optional species identification
            properties: Sample properties
            correlation_id: Correlation ID for tracing
            
        Returns:
            Created BiologicalSample
        """
        data = {
            "sample_type": sample_type,
            "location": location,
            "properties": properties or {},
        }
        
        if species:
            data["species"] = species
        
        response = await self.post(
            "/v1/samples",
            data=data,
            correlation_id=correlation_id,
        )
        return BiologicalSample(**response)
    
    async def get_sample(
        self,
        sample_id: str,
        correlation_id: Optional[UUID] = None,
    ) -> Optional[BiologicalSample]:
        """
        Get a sample by ID.
        
        Args:
            sample_id: Sample ID
            correlation_id: Correlation ID for tracing
            
        Returns:
            BiologicalSample or None if not found
        """
        try:
            response = await self.get(
                f"/v1/samples/{sample_id}",
                correlation_id=correlation_id,
            )
            return BiologicalSample(**response)
        except ClientError as e:
            if e.status_code == 404:
                return None
            raise
    
    async def list_samples(
        self,
        sample_type: Optional[str] = None,
        species: Optional[str] = None,
        location: Optional[dict[str, float]] = None,
        radius_km: float = 10.0,
        limit: int = 100,
        correlation_id: Optional[UUID] = None,
    ) -> list[BiologicalSample]:
        """
        List biological samples with filters.
        
        Args:
            sample_type: Filter by sample type
            species: Filter by species
            location: Center point for geographic filter
            radius_km: Radius in kilometers
            limit: Maximum results
            correlation_id: Correlation ID for tracing
            
        Returns:
            List of BiologicalSample objects
        """
        params = {"limit": limit}
        
        if sample_type:
            params["type"] = sample_type
        if species:
            params["species"] = species
        if location:
            params["lat"] = location.get("lat")
            params["lon"] = location.get("lon")
            params["radius"] = radius_km
        
        response = await self.get(
            "/v1/samples",
            params=params,
            correlation_id=correlation_id,
        )
        return [BiologicalSample(**s) for s in response.get("samples", [])]
    
    # =========================================================================
    # ENVIRONMENTAL REPORTS
    # =========================================================================
    
    async def get_environmental_report(
        self,
        location: dict[str, float],
        period_start: str,
        period_end: str,
        report_type: str = "summary",
        correlation_id: Optional[UUID] = None,
    ) -> EnvironmentalReport:
        """
        Get an environmental report for a location and time period.
        
        Args:
            location: Location coordinates
            period_start: Report period start (ISO 8601)
            period_end: Report period end (ISO 8601)
            report_type: Type of report
            correlation_id: Correlation ID for tracing
            
        Returns:
            EnvironmentalReport
        """
        params = {
            "lat": location.get("lat"),
            "lon": location.get("lon"),
            "start": period_start,
            "end": period_end,
            "type": report_type,
        }
        
        response = await self.get(
            "/v1/reports/environmental",
            params=params,
            correlation_id=correlation_id,
        )
        return EnvironmentalReport(**response)
    
    async def subscribe_alerts(
        self,
        location: dict[str, float],
        radius_km: float,
        alert_types: list[str],
        webhook_url: str,
        correlation_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """
        Subscribe to environmental alerts.
        
        Args:
            location: Center point for alert area
            radius_km: Alert radius
            alert_types: Types of alerts to receive
            webhook_url: URL to receive alerts
            correlation_id: Correlation ID for tracing
            
        Returns:
            Subscription details
        """
        data = {
            "location": location,
            "radius_km": radius_km,
            "alert_types": alert_types,
            "webhook_url": webhook_url,
        }
        
        return await self.post(
            "/v1/alerts/subscriptions",
            data=data,
            correlation_id=correlation_id,
        )
