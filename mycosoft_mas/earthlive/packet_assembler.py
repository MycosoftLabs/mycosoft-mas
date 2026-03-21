"""
EarthLIVE Packet Assembler

Assembles unified packet from weather, seismic, satellite collectors.

Created: February 25, 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass
class EarthLIVEPacket:
    """Unified EarthLIVE packet for MYCA Worldview."""

    packet_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    weather: Dict[str, Any] = field(default_factory=dict)
    seismic: Dict[str, Any] = field(default_factory=dict)
    satellite: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": str(self.packet_id),
            "timestamp": self.timestamp.isoformat(),
            "weather": self.weather,
            "seismic": self.seismic,
            "satellite": self.satellite,
            "metadata": self.metadata,
        }


def assemble_packet(
    weather: Optional[Dict[str, Any]] = None,
    seismic: Optional[Dict[str, Any]] = None,
    satellite: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EarthLIVEPacket:
    """Assemble an EarthLIVE packet from collected data."""
    return EarthLIVEPacket(
        weather=weather or {},
        seismic=seismic or {},
        satellite=satellite or {},
        metadata=metadata or {},
    )


async def assemble_from_collectors(
    latitude: float = 47.6062,
    longitude: float = -122.3321,
    seismic_feed: str = "all_day",
    satellite_group: str = "starlink",
) -> EarthLIVEPacket:
    """Run all collectors and assemble unified packet."""
    from mycosoft_mas.earthlive.collectors.satellite import SatelliteCollector
    from mycosoft_mas.earthlive.collectors.seismic import SeismicCollector
    from mycosoft_mas.earthlive.collectors.weather import WeatherCollector

    wc = WeatherCollector(latitude=latitude, longitude=longitude)
    sc = SeismicCollector(feed=seismic_feed)
    satc = SatelliteCollector(group=satellite_group)

    weather_data = await wc.collect()
    seismic_data = await sc.collect()
    satellite_data = await satc.collect()

    return assemble_packet(
        weather=weather_data,
        seismic=seismic_data,
        satellite=satellite_data,
        metadata={
            "latitude": latitude,
            "longitude": longitude,
            "seismic_feed": seismic_feed,
            "satellite_group": satellite_group,
        },
    )
