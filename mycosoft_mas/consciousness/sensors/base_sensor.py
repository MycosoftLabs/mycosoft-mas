"""
Base Sensor Class

Abstract base for all world sensors.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional
from dataclasses import dataclass

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.world_model import WorldModel, SensorReading, DataFreshness

logger = logging.getLogger(__name__)


class SensorStatus(Enum):
    """Status of a sensor."""
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


class BaseSensor(ABC):
    """
    Abstract base class for world sensors.
    
    All sensors must implement:
    - read(): Get a reading from the sensor
    - connect(): Establish connection to data source
    - disconnect(): Close connection
    """
    
    def __init__(self, world_model: "WorldModel", name: str):
        self._world_model = world_model
        self._name = name
        self._status = SensorStatus.INITIALIZING
        self._last_reading: Optional["SensorReading"] = None
        self._last_error: Optional[str] = None
        self._read_count = 0
        self._error_count = 0
        self._connected_at: Optional[datetime] = None
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def status(self) -> SensorStatus:
        return self._status
    
    @property
    def is_connected(self) -> bool:
        return self._status == SensorStatus.CONNECTED
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the data source.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the data source."""
        pass
    
    @abstractmethod
    async def read(self) -> Optional["SensorReading"]:
        """
        Read data from the sensor.
        
        Returns:
            SensorReading with data, or None if unavailable
        """
        pass
    
    def _mark_connected(self) -> None:
        """Mark sensor as connected."""
        self._status = SensorStatus.CONNECTED
        self._connected_at = datetime.now(timezone.utc)
        logger.info(f"Sensor {self._name} connected")
    
    def _mark_disconnected(self) -> None:
        """Mark sensor as disconnected."""
        self._status = SensorStatus.DISCONNECTED
        logger.info(f"Sensor {self._name} disconnected")
    
    def _mark_error(self, error: str) -> None:
        """Mark sensor as having an error."""
        self._status = SensorStatus.ERROR
        self._last_error = error
        self._error_count += 1
        logger.warning(f"Sensor {self._name} error: {error}")
    
    def _record_reading(self, reading: "SensorReading") -> None:
        """Record a successful reading."""
        self._last_reading = reading
        self._read_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sensor statistics."""
        return {
            "name": self._name,
            "status": self._status.value,
            "read_count": self._read_count,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "connected_at": self._connected_at.isoformat() if self._connected_at else None,
            "last_reading_age": self._last_reading.age_seconds if self._last_reading else None,
        }
