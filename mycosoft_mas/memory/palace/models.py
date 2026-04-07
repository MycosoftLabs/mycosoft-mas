"""
Palace Models - Data structures for the Memory Palace.
Created: April 7, 2026

Defines the spatial organization primitives:
- Wing: Top-level domain container (agent category, data source, project)
- Room: Topic within a wing
- Hall: 5 standardized corridors (facts, events, discoveries, preferences, advice)
- Tunnel: Cross-wing connection when a room appears in multiple wings
- Closet: AAAK-compressed summary pointing to original drawers
- Drawer: Verbatim content entry (maps to mindex.memory_entries)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID


class HallType(str, Enum):
    """5 standardized corridors in every wing."""

    FACTS = "facts"  # Decisions, locked-in choices, confirmed knowledge
    EVENTS = "events"  # Sessions, milestones, task completions, errors
    DISCOVERIES = "discoveries"  # Breakthroughs, new insights, learned patterns
    PREFERENCES = "preferences"  # Habits, configuration, user/agent preferences
    ADVICE = "advice"  # Recommendations, solutions, best practices


class SourceType(str, Enum):
    """Types of data sources that map to wings."""

    AGENT = "agent"
    CREP = "crep"
    DEVICE = "device"
    MYCOLOGY = "mycology"
    WEATHER = "weather"
    WORKFLOW = "workflow"
    INFRASTRUCTURE = "infrastructure"
    SCIENCE = "science"
    INTEGRATION = "integration"
    PROJECT = "project"
    CUSTOM = "custom"


@dataclass
class Wing:
    """Top-level container — maps to a domain, agent category, or data source."""

    id: Optional[UUID] = None
    name: str = ""
    description: str = ""
    source_type: SourceType = SourceType.CUSTOM
    properties: Dict[str, Any] = field(default_factory=dict)
    room_count: int = 0
    drawer_count: int = 0
    created_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: Dict) -> "Wing":
        return cls(
            id=row.get("id"),
            name=row["name"],
            description=row.get("description", ""),
            source_type=SourceType(row.get("source_type", "custom")),
            properties=row.get("properties", {}),
            room_count=row.get("room_count", 0),
            drawer_count=row.get("drawer_count", 0),
            created_at=row.get("created_at"),
        )


@dataclass
class Room:
    """Topic within a wing (e.g., wing='mycology', room='species-identification')."""

    id: Optional[UUID] = None
    wing_id: Optional[UUID] = None
    wing_name: str = ""
    name: str = ""
    description: str = ""
    drawer_count: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: Dict) -> "Room":
        return cls(
            id=row.get("id"),
            wing_id=row.get("wing_id"),
            wing_name=row.get("wing_name", ""),
            name=row["name"],
            description=row.get("description", ""),
            drawer_count=row.get("drawer_count", 0),
            properties=row.get("properties", {}),
            created_at=row.get("created_at"),
        )


@dataclass
class Hall:
    """One of the 5 standardized corridors within a wing."""

    hall_type: HallType
    wing_name: str
    room_name: Optional[str] = None
    drawer_count: int = 0


@dataclass
class Tunnel:
    """Cross-wing connection — a room that appears in 2+ wings."""

    id: Optional[UUID] = None
    room_name: str = ""
    wing_a: str = ""
    wing_b: str = ""
    wing_a_id: Optional[UUID] = None
    wing_b_id: Optional[UUID] = None
    strength: float = 1.0
    discovered_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: Dict) -> "Tunnel":
        return cls(
            id=row.get("id"),
            room_name=row["room_name"],
            wing_a=row.get("wing_a_name", ""),
            wing_b=row.get("wing_b_name", ""),
            wing_a_id=row.get("wing_a"),
            wing_b_id=row.get("wing_b"),
            strength=row.get("strength", 1.0),
            discovered_at=row.get("discovered_at"),
        )


@dataclass
class Drawer:
    """Verbatim content entry — maps to a memory entry with palace metadata."""

    id: Optional[UUID] = None
    wing: str = ""
    room: str = ""
    hall: HallType = HallType.FACTS
    content: str = ""
    content_hash: str = ""
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    source_agent: str = ""
    source_file: str = ""
    is_closet: bool = False
    closet_source_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Closet:
    """AAAK-compressed summary pointing to original drawers."""

    id: Optional[UUID] = None
    wing: str = ""
    room: str = ""
    aaak_text: str = ""
    source_drawer_ids: List[UUID] = field(default_factory=list)
    token_count: int = 0
    compression_ratio: float = 1.0
    created_at: Optional[datetime] = None


@dataclass
class PalaceTaxonomy:
    """Full palace structure: wing -> room -> hall hierarchy."""

    wings: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_entry(self, wing: str, room: str, hall: str, count: int = 1):
        if wing not in self.wings:
            self.wings[wing] = {"rooms": {}, "total": 0}
        if room not in self.wings[wing]["rooms"]:
            self.wings[wing]["rooms"][room] = {"halls": {}, "total": 0}
        self.wings[wing]["rooms"][room]["halls"][hall] = (
            self.wings[wing]["rooms"][room]["halls"].get(hall, 0) + count
        )
        self.wings[wing]["rooms"][room]["total"] += count
        self.wings[wing]["total"] += count

    def to_dict(self) -> Dict[str, Any]:
        return self.wings
