"""
Palace Navigator - Spatial Organization Layer for MYCA Memory.
Created: April 7, 2026

Manages the palace topology: wings, rooms, halls, tunnels, drawers, closets.
This is a metadata overlay on top of existing mindex.memory_entries — it classifies
and organizes memories spatially without duplicating storage.

The palace metaphor (from mempalace project):
- Wings = top-level domains (agent categories, data sources)
- Rooms = topics within wings
- Halls = 5 standardized corridors: facts, events, discoveries, preferences, advice
- Tunnels = cross-wing connections (rooms appearing in multiple wings)
- Closets = AAAK-compressed summaries
- Drawers = verbatim content entries
"""

import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from mycosoft_mas.memory.palace.models import (
    Closet,
    Drawer,
    Hall,
    HallType,
    PalaceTaxonomy,
    Room,
    SourceType,
    Tunnel,
    Wing,
)

logger = logging.getLogger("PalaceNavigator")

# Default wing definitions for auto-registration
DEFAULT_WINGS: List[Dict[str, Any]] = [
    {"name": "crep", "description": "Common Relevant Environmental Picture data", "source_type": "crep"},
    {"name": "devices", "description": "MycoBrain, FCI, and IoT device data", "source_type": "device"},
    {"name": "mycology", "description": "Species, compounds, habitats from MINDEX", "source_type": "mycology"},
    {"name": "weather", "description": "Earth2 climate and weather simulations", "source_type": "weather"},
    {"name": "agents", "description": "Agent state, decisions, and learning", "source_type": "agent"},
    {"name": "workflows", "description": "n8n workflow execution history", "source_type": "workflow"},
    {"name": "infrastructure", "description": "VMs, Docker, networking, services", "source_type": "infrastructure"},
    {"name": "science", "description": "NLM, bio, DNA storage, experiments", "source_type": "science"},
    {"name": "integrations", "description": "Notion, Slack, GitHub, Stripe, etc.", "source_type": "integration"},
]

# Hall classification keywords
HALL_KEYWORDS: Dict[HallType, List[str]] = {
    HallType.FACTS: [
        "decided", "confirmed", "is", "equals", "defined", "set to",
        "configured", "identified", "fact", "conclusion", "determination",
    ],
    HallType.EVENTS: [
        "completed", "started", "failed", "deployed", "created", "deleted",
        "migrated", "updated", "error", "timeout", "milestone", "session",
    ],
    HallType.DISCOVERIES: [
        "discovered", "found", "breakthrough", "realized", "learned",
        "insight", "novel", "unexpected", "new pattern", "correlation",
    ],
    HallType.PREFERENCES: [
        "prefers", "likes", "configured", "setting", "default", "habit",
        "preference", "style", "mode", "threshold", "parameter",
    ],
    HallType.ADVICE: [
        "recommend", "should", "best practice", "solution", "workaround",
        "tip", "suggestion", "approach", "strategy", "guideline",
    ],
}

# Room classification keywords by wing
ROOM_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "crep": {
        "flights": ["flight", "aircraft", "adsb", "aviation", "altitude"],
        "marine": ["vessel", "ship", "ais", "maritime", "port"],
        "satellites": ["satellite", "orbit", "space", "tle", "tracking"],
        "weather": ["weather", "temperature", "humidity", "pressure", "wind"],
        "fungal": ["fungal", "mushroom", "mycelium", "spore", "fruiting"],
    },
    "devices": {
        "bme688": ["bme688", "gas", "voc", "air quality"],
        "bme690": ["bme690", "environmental"],
        "lora": ["lora", "lorawan", "gateway", "radio"],
        "electrode": ["electrode", "fci", "signal", "neural"],
        "mycobrain": ["mycobrain", "esp32", "firmware", "telemetry"],
    },
    "mycology": {
        "species": ["species", "taxonomy", "genus", "family", "identification"],
        "compounds": ["compound", "chemical", "molecule", "alkaloid", "terpene"],
        "habitats": ["habitat", "ecosystem", "substrate", "environment", "biome"],
        "genetics": ["gene", "dna", "rna", "genome", "sequence", "genetic"],
        "observations": ["observation", "sighting", "collection", "sample"],
    },
    "infrastructure": {
        "vms": ["vm", "proxmox", "virtual", "192.168"],
        "docker": ["docker", "container", "image", "compose", "dockerfile"],
        "networking": ["network", "firewall", "port", "dns", "cloudflare"],
        "databases": ["postgres", "redis", "qdrant", "database", "migration"],
        "services": ["service", "api", "endpoint", "health", "deploy"],
    },
}


class PalaceNavigator:
    """
    Manages the spatial organization of MYCA's memory palace.

    Provides wing/room/hall/tunnel management, drawer filing with
    auto-classification, tunnel detection, and taxonomy queries.
    """

    def __init__(self):
        self._pool = None
        self._initialized = False
        self._wing_cache: Dict[str, Wing] = {}
        self._room_cache: Dict[str, Dict[str, Room]] = {}

    async def initialize(self) -> None:
        """Initialize navigator with shared pool and ensure default wings exist."""
        if self._initialized:
            return

        from mycosoft_mas.memory.palace.db_pool import get_shared_pool

        self._pool = await get_shared_pool()
        await self._ensure_schema()
        await self._ensure_default_wings()
        await self._load_wing_cache()
        self._initialized = True
        logger.info(f"PalaceNavigator initialized with {len(self._wing_cache)} wings")

    async def _ensure_schema(self) -> None:
        """Ensure palace tables exist (idempotent)."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS mindex.palace_wings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    source_type TEXT DEFAULT 'custom',
                    properties JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT now()
                );

                CREATE TABLE IF NOT EXISTS mindex.palace_rooms (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    wing_id UUID REFERENCES mindex.palace_wings(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    drawer_count INTEGER DEFAULT 0,
                    properties JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT now(),
                    UNIQUE(wing_id, name)
                );

                CREATE TABLE IF NOT EXISTS mindex.palace_tunnels (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    room_name TEXT NOT NULL,
                    wing_a UUID REFERENCES mindex.palace_wings(id) ON DELETE CASCADE,
                    wing_b UUID REFERENCES mindex.palace_wings(id) ON DELETE CASCADE,
                    strength FLOAT DEFAULT 1.0,
                    discovered_at TIMESTAMPTZ DEFAULT now(),
                    UNIQUE(room_name, wing_a, wing_b)
                );
            """)

            # Add palace columns to memory_entries if not present
            # Using DO block for idempotent ALTER
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'mindex' AND table_name = 'memory_entries'
                        AND column_name = 'wing'
                    ) THEN
                        ALTER TABLE mindex.memory_entries
                            ADD COLUMN wing TEXT,
                            ADD COLUMN room TEXT,
                            ADD COLUMN hall TEXT,
                            ADD COLUMN is_closet BOOLEAN DEFAULT false,
                            ADD COLUMN closet_source_id UUID;
                    END IF;
                END $$;
            """)

            # Create indexes if not exists
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_wing_room
                    ON mindex.memory_entries(wing, room);
                CREATE INDEX IF NOT EXISTS idx_memory_hall
                    ON mindex.memory_entries(hall);
                CREATE INDEX IF NOT EXISTS idx_memory_is_closet
                    ON mindex.memory_entries(is_closet) WHERE is_closet = true;
            """)

    async def _ensure_default_wings(self) -> None:
        """Create default wings if they don't exist."""
        async with self._pool.acquire() as conn:
            for wing_def in DEFAULT_WINGS:
                await conn.execute(
                    """
                    INSERT INTO mindex.palace_wings (name, description, source_type)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    wing_def["name"],
                    wing_def["description"],
                    wing_def["source_type"],
                )

    async def _load_wing_cache(self) -> None:
        """Load wings into memory cache."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM mindex.palace_wings")
            self._wing_cache = {}
            for row in rows:
                wing = Wing.from_db_row(dict(row))
                self._wing_cache[wing.name] = wing

    # =========================================================================
    # Wing Operations
    # =========================================================================

    async def create_wing(
        self,
        name: str,
        description: str = "",
        source_type: str = "custom",
        properties: Optional[Dict[str, Any]] = None,
    ) -> Wing:
        """Create a new wing in the palace."""
        await self.initialize()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO mindex.palace_wings (name, description, source_type, properties)
                VALUES ($1, $2, $3, $4::jsonb)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    source_type = EXCLUDED.source_type,
                    properties = EXCLUDED.properties
                RETURNING *
                """,
                name,
                description,
                source_type,
                json.dumps(properties or {}),
            )
            wing = Wing.from_db_row(dict(row))
            self._wing_cache[name] = wing
            return wing

    async def list_wings(self) -> List[Wing]:
        """List all wings with drawer counts."""
        await self.initialize()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT w.*,
                    COALESCE(r.room_count, 0) as room_count,
                    COALESCE(m.drawer_count, 0) as drawer_count
                FROM mindex.palace_wings w
                LEFT JOIN (
                    SELECT wing_id, COUNT(*) as room_count
                    FROM mindex.palace_rooms GROUP BY wing_id
                ) r ON r.wing_id = w.id
                LEFT JOIN (
                    SELECT wing, COUNT(*) as drawer_count
                    FROM mindex.memory_entries WHERE wing IS NOT NULL GROUP BY wing
                ) m ON m.wing = w.name
                ORDER BY w.name
            """)
            return [Wing.from_db_row(dict(row)) for row in rows]

    async def get_wing(self, name: str) -> Optional[Wing]:
        """Get a wing by name."""
        if name in self._wing_cache:
            return self._wing_cache[name]
        await self.initialize()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mindex.palace_wings WHERE name = $1", name
            )
            if row:
                wing = Wing.from_db_row(dict(row))
                self._wing_cache[name] = wing
                return wing
        return None

    # =========================================================================
    # Room Operations
    # =========================================================================

    async def create_room(
        self,
        wing_name: str,
        room_name: str,
        description: str = "",
        properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[Room]:
        """Create a room within a wing."""
        await self.initialize()
        wing = await self.get_wing(wing_name)
        if not wing or not wing.id:
            logger.warning(f"Wing '{wing_name}' not found")
            return None

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO mindex.palace_rooms (wing_id, name, description, properties)
                VALUES ($1, $2, $3, $4::jsonb)
                ON CONFLICT (wing_id, name) DO UPDATE SET
                    description = EXCLUDED.description,
                    properties = EXCLUDED.properties
                RETURNING *
                """,
                wing.id,
                room_name,
                description,
                json.dumps(properties or {}),
            )
            room = Room.from_db_row(dict(row))
            room.wing_name = wing_name
            return room

    async def list_rooms(self, wing_name: Optional[str] = None) -> List[Room]:
        """List rooms, optionally filtered by wing."""
        await self.initialize()

        async with self._pool.acquire() as conn:
            if wing_name:
                rows = await conn.fetch(
                    """
                    SELECT r.*, w.name as wing_name
                    FROM mindex.palace_rooms r
                    JOIN mindex.palace_wings w ON w.id = r.wing_id
                    WHERE w.name = $1
                    ORDER BY r.name
                    """,
                    wing_name,
                )
            else:
                rows = await conn.fetch("""
                    SELECT r.*, w.name as wing_name
                    FROM mindex.palace_rooms r
                    JOIN mindex.palace_wings w ON w.id = r.wing_id
                    ORDER BY w.name, r.name
                """)
            return [Room.from_db_row(dict(row)) for row in rows]

    # =========================================================================
    # Drawer Operations (Filing and Retrieval)
    # =========================================================================

    async def file_drawer(
        self,
        content: str,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        hall: Optional[str] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        agent_id: str = "",
        source_file: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[UUID]:
        """
        File a new drawer (memory entry) with palace spatial metadata.

        Auto-classifies wing/room/hall if not provided.
        Returns the memory entry UUID.
        """
        await self.initialize()

        # Auto-classify if not provided
        if not wing:
            wing = self._classify_wing(content, tags or [], agent_id)
        if not room:
            room = self._classify_room(content, wing, tags or [])
        if not hall:
            hall = self._classify_hall(content).value

        # Ensure wing exists
        if wing not in self._wing_cache:
            await self.create_wing(wing, source_type="custom")

        # Ensure room exists
        await self.create_room(wing, room)

        # Compute content hash for deduplication
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Store in memory_entries with palace metadata
        entry_id = uuid4()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.memory_entries (
                    id, scope, layer, key, value, importance,
                    wing, room, hall, is_closet, created_at
                ) VALUES (
                    $1, 'AGENT', 'semantic', $2, $3::jsonb, $4,
                    $5, $6, $7, false, now()
                )
                ON CONFLICT (id) DO NOTHING
                """,
                entry_id,
                f"drawer:{content_hash}",
                json.dumps({
                    "text": content,
                    "agent_id": agent_id,
                    "source_file": source_file,
                    "tags": tags or [],
                    **(metadata or {}),
                }),
                importance,
                wing,
                room,
                hall,
            )

            # Update room drawer count
            await conn.execute(
                """
                UPDATE mindex.palace_rooms SET drawer_count = drawer_count + 1
                WHERE wing_id = (SELECT id FROM mindex.palace_wings WHERE name = $1)
                AND name = $2
                """,
                wing,
                room,
            )

        logger.debug(f"Filed drawer in {wing}/{room}/{hall}: {content[:80]}...")
        return entry_id

    async def search_drawers(
        self,
        query: Optional[str] = None,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        hall: Optional[str] = None,
        limit: int = 20,
        min_importance: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search drawers with optional palace filters."""
        await self.initialize()

        conditions = ["wing IS NOT NULL"]
        params = []
        idx = 1

        if wing:
            conditions.append(f"wing = ${idx}")
            params.append(wing)
            idx += 1
        if room:
            conditions.append(f"room = ${idx}")
            params.append(room)
            idx += 1
        if hall:
            conditions.append(f"hall = ${idx}")
            params.append(hall)
            idx += 1
        if min_importance > 0:
            conditions.append(f"importance >= ${idx}")
            params.append(min_importance)
            idx += 1
        if query:
            conditions.append(f"value::text ILIKE ${idx}")
            params.append(f"%{query}%")
            idx += 1

        where = " AND ".join(conditions)
        params.append(limit)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, wing, room, hall, value, importance, is_closet, created_at
                FROM mindex.memory_entries
                WHERE {where}
                ORDER BY importance DESC, created_at DESC
                LIMIT ${idx}
                """,
                *params,
            )

            return [
                {
                    "id": str(row["id"]),
                    "wing": row["wing"],
                    "room": row["room"],
                    "hall": row["hall"],
                    "content": row["value"],
                    "importance": row["importance"],
                    "is_closet": row["is_closet"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
                for row in rows
            ]

    async def check_duplicate(
        self, content: str, threshold: float = 0.9
    ) -> Optional[Dict[str, Any]]:
        """Check if similar content already exists (text-based dedup)."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, wing, room, hall, value, importance
                FROM mindex.memory_entries
                WHERE key = $1 AND wing IS NOT NULL
                LIMIT 1
                """,
                f"drawer:{content_hash}",
            )
            if row:
                return {
                    "id": str(row["id"]),
                    "wing": row["wing"],
                    "room": row["room"],
                    "duplicate": True,
                }
        return None

    # =========================================================================
    # Tunnel Operations (Cross-Wing Connections)
    # =========================================================================

    async def detect_tunnels(self) -> List[Tunnel]:
        """
        Detect cross-wing tunnels — rooms that appear in 2+ wings.
        Auto-discovers and persists tunnel connections.
        """
        await self.initialize()

        async with self._pool.acquire() as conn:
            # Find rooms appearing in multiple wings
            rows = await conn.fetch("""
                SELECT room, array_agg(DISTINCT wing) as wings
                FROM mindex.memory_entries
                WHERE wing IS NOT NULL AND room IS NOT NULL
                GROUP BY room
                HAVING COUNT(DISTINCT wing) >= 2
            """)

            tunnels = []
            for row in rows:
                room_name = row["room"]
                wings = row["wings"]

                # Create tunnels for each wing pair
                for i in range(len(wings)):
                    for j in range(i + 1, len(wings)):
                        wing_a = await self.get_wing(wings[i])
                        wing_b = await self.get_wing(wings[j])
                        if wing_a and wing_b and wing_a.id and wing_b.id:
                            tunnel_row = await conn.fetchrow(
                                """
                                INSERT INTO mindex.palace_tunnels (room_name, wing_a, wing_b)
                                VALUES ($1, $2, $3)
                                ON CONFLICT (room_name, wing_a, wing_b) DO UPDATE SET
                                    strength = mindex.palace_tunnels.strength + 0.1
                                RETURNING *
                                """,
                                room_name,
                                wing_a.id,
                                wing_b.id,
                            )
                            tunnel = Tunnel(
                                id=tunnel_row["id"],
                                room_name=room_name,
                                wing_a=wings[i],
                                wing_b=wings[j],
                                strength=tunnel_row["strength"],
                            )
                            tunnels.append(tunnel)

            logger.info(f"Detected {len(tunnels)} tunnels")
            return tunnels

    async def find_tunnels(
        self, wing_a: str, wing_b: Optional[str] = None
    ) -> List[Tunnel]:
        """Find tunnels connecting two wings (or all tunnels from a wing)."""
        await self.initialize()

        async with self._pool.acquire() as conn:
            if wing_b:
                rows = await conn.fetch(
                    """
                    SELECT t.*, wa.name as wing_a_name, wb.name as wing_b_name
                    FROM mindex.palace_tunnels t
                    JOIN mindex.palace_wings wa ON wa.id = t.wing_a
                    JOIN mindex.palace_wings wb ON wb.id = t.wing_b
                    WHERE (wa.name = $1 AND wb.name = $2)
                       OR (wa.name = $2 AND wb.name = $1)
                    ORDER BY t.strength DESC
                    """,
                    wing_a,
                    wing_b,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT t.*, wa.name as wing_a_name, wb.name as wing_b_name
                    FROM mindex.palace_tunnels t
                    JOIN mindex.palace_wings wa ON wa.id = t.wing_a
                    JOIN mindex.palace_wings wb ON wb.id = t.wing_b
                    WHERE wa.name = $1 OR wb.name = $1
                    ORDER BY t.strength DESC
                    """,
                    wing_a,
                )
            return [Tunnel.from_db_row(dict(row)) for row in rows]

    # =========================================================================
    # Taxonomy
    # =========================================================================

    async def get_taxonomy(self) -> PalaceTaxonomy:
        """Get full palace taxonomy: wing -> room -> hall -> count."""
        await self.initialize()

        taxonomy = PalaceTaxonomy()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT wing, room, hall, COUNT(*) as cnt
                FROM mindex.memory_entries
                WHERE wing IS NOT NULL
                GROUP BY wing, room, hall
                ORDER BY wing, room, hall
            """)

            for row in rows:
                taxonomy.add_entry(
                    wing=row["wing"] or "unknown",
                    room=row["room"] or "general",
                    hall=row["hall"] or "facts",
                    count=row["cnt"],
                )

        return taxonomy

    async def get_status(self) -> Dict[str, Any]:
        """Get palace status overview."""
        await self.initialize()

        async with self._pool.acquire() as conn:
            wing_count = await conn.fetchval(
                "SELECT COUNT(*) FROM mindex.palace_wings"
            )
            room_count = await conn.fetchval(
                "SELECT COUNT(*) FROM mindex.palace_rooms"
            )
            drawer_count = await conn.fetchval(
                "SELECT COUNT(*) FROM mindex.memory_entries WHERE wing IS NOT NULL"
            )
            closet_count = await conn.fetchval(
                "SELECT COUNT(*) FROM mindex.memory_entries WHERE is_closet = true"
            )
            tunnel_count = await conn.fetchval(
                "SELECT COUNT(*) FROM mindex.palace_tunnels"
            )

        return {
            "wings": wing_count,
            "rooms": room_count,
            "drawers": drawer_count,
            "closets": closet_count,
            "tunnels": tunnel_count,
            "initialized": self._initialized,
        }

    # =========================================================================
    # Auto-Classification
    # =========================================================================

    def _classify_wing(
        self, content: str, tags: List[str], agent_id: str
    ) -> str:
        """Auto-classify content into a wing based on keywords and context."""
        content_lower = content.lower()
        tag_str = " ".join(tags).lower()
        combined = f"{content_lower} {tag_str} {agent_id.lower()}"

        scores: Dict[str, int] = defaultdict(int)

        # Check agent-based classification
        if "crep" in combined or "flight" in combined or "marine" in combined:
            scores["crep"] += 5
        if "device" in combined or "mycobrain" in combined or "fci" in combined:
            scores["devices"] += 5
        if "species" in combined or "fungal" in combined or "mycol" in combined:
            scores["mycology"] += 5
        if "weather" in combined or "earth2" in combined or "climate" in combined:
            scores["weather"] += 5
        if "workflow" in combined or "n8n" in combined:
            scores["workflows"] += 5
        if "docker" in combined or "vm" in combined or "deploy" in combined:
            scores["infrastructure"] += 5
        if "nlm" in combined or "experiment" in combined or "dna" in combined:
            scores["science"] += 5
        if "notion" in combined or "slack" in combined or "github" in combined:
            scores["integrations"] += 5

        # Default to agents wing if agent context is strong
        if agent_id and not scores:
            scores["agents"] += 1

        if scores:
            return max(scores, key=scores.get)
        return "agents"

    def _classify_room(
        self, content: str, wing: str, tags: List[str]
    ) -> str:
        """Auto-classify content into a room within a wing."""
        content_lower = content.lower()

        if wing in ROOM_KEYWORDS:
            scores: Dict[str, int] = defaultdict(int)
            for room_name, keywords in ROOM_KEYWORDS[wing].items():
                for kw in keywords:
                    if kw in content_lower:
                        scores[room_name] += 1

            if scores:
                return max(scores, key=scores.get)

        return "general"

    def _classify_hall(self, content: str) -> HallType:
        """Auto-classify content into one of the 5 standardized halls."""
        content_lower = content.lower()
        scores: Dict[HallType, int] = defaultdict(int)

        for hall_type, keywords in HALL_KEYWORDS.items():
            for kw in keywords:
                if kw in content_lower:
                    scores[hall_type] += 1

        if scores:
            return max(scores, key=scores.get)
        return HallType.FACTS


# Singleton
_navigator: Optional[PalaceNavigator] = None


async def get_palace_navigator() -> PalaceNavigator:
    """Get or create the singleton PalaceNavigator."""
    global _navigator
    if _navigator is None:
        _navigator = PalaceNavigator()
        await _navigator.initialize()
    return _navigator
