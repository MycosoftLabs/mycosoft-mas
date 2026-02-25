"""
EarthLIVE Sensor

Feeds the world model with packetized environmental live data:
- Weather (OpenMeteo)
- Seismic (USGS)
- Satellite (Celestrak)

Integrates EarthLIVE framework into World Model.

Created: February 25, 2026
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from mycosoft_mas.consciousness.sensors.base_sensor import BaseSensor, SensorStatus
from mycosoft_mas.earthlive.packet_assembler import assemble_from_collectors

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.world_model import WorldModel, SensorReading, DataFreshness

logger = logging.getLogger(__name__)


class EarthLIVESensor(BaseSensor):
    """
    Sensor for EarthLIVE packetized environmental data.

    Collects weather, seismic, and satellite data and returns
    a unified EarthLIVE packet to the world model.
    """

    def __init__(
        self,
        world_model: Optional["WorldModel"] = None,
        latitude: float = 47.6062,
        longitude: float = -122.3321,
    ):
        super().__init__(world_model, "earthlive")
        self._latitude = latitude
        self._longitude = longitude

    async def connect(self) -> bool:
        """EarthLIVE uses stateless HTTP - always ready."""
        self._mark_connected()
        return True

    async def disconnect(self) -> None:
        """No persistent connection to close."""
        self._mark_disconnected()

    async def read(self) -> Optional["SensorReading"]:
        """Read EarthLIVE packet from collectors."""
        from mycosoft_mas.consciousness.world_model import SensorReading, DataFreshness

        if not self.is_connected:
            await self.connect()

        try:
            packet = await assemble_from_collectors(
                latitude=self._latitude,
                longitude=self._longitude,
            )
            data = packet.to_dict()

            reading = SensorReading(
                sensor_type="earthlive",
                data=data,
                timestamp=datetime.now(timezone.utc),
                freshness=DataFreshness.LIVE if data.get("weather") or data.get("seismic") else DataFreshness.RECENT,
                confidence=1.0,
                source_url="earthlive",
            )

            self._record_reading(reading)
            return reading

        except Exception as e:
            self._mark_error(str(e))
            return None
