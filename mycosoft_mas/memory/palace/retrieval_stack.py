"""
L0-L3 Retrieval Stack for Memory Palace.
Created: April 7, 2026

Structured 4-layer retrieval system inspired by mempalace, adapted for MYCA.
Replaces ad-hoc context injection with token-efficient, structured loading.

Layers:
- L0 (Identity, ~50 tokens): MYCA's soul identity — always loaded
- L1 (Critical Facts, ~120 tokens AAAK): Top-weighted semantic facts — always loaded
- L2 (Room Recall, on-demand): Wing/room-scoped retrieval
- L3 (Deep Search, on-demand): Full semantic search across all memory
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("RetrievalStack")


class RetrievalStack:
    """
    4-layer retrieval stack for token-efficient context loading.

    wake_up() returns L0+L1 (~170 tokens) — called at agent/session start.
    recall() returns L2 (wing/room-scoped) — called when context is detected.
    search() returns L3 (deep semantic) — called on explicit knowledge queries.
    """

    def __init__(self):
        self._pool = None
        self._aaak_encoder = None
        self._navigator = None
        self._initialized = False

        # Identity cache (L0)
        self._identity_text: Optional[str] = None

        # L1 cache (refreshed periodically)
        self._l1_cache: Optional[str] = None
        self._l1_cache_age: int = 0
        self._l1_max_age: int = 300  # Refresh L1 every 5 minutes

    async def initialize(self) -> None:
        """Initialize retrieval stack with dependencies."""
        if self._initialized:
            return

        from mycosoft_mas.memory.palace.aaak_dialect import AAKEncoder
        from mycosoft_mas.memory.palace.db_pool import get_shared_pool
        from mycosoft_mas.memory.palace.navigator import get_palace_navigator

        self._pool = await get_shared_pool()
        self._aaak_encoder = AAKEncoder()
        self._navigator = await get_palace_navigator()
        self._initialized = True
        logger.info("RetrievalStack initialized")

    # =========================================================================
    # L0: Identity (~50 tokens, always loaded)
    # =========================================================================

    def _load_identity(self) -> str:
        """Load MYCA's soul identity for L0 context."""
        if self._identity_text:
            return self._identity_text

        # Try loading from soul config
        soul_paths = [
            os.path.join(os.getcwd(), "config", "myca_soul.yaml"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "myca_soul.yaml"),
        ]

        for path in soul_paths:
            if os.path.exists(path):
                try:
                    import yaml
                    with open(path) as f:
                        soul = yaml.safe_load(f)

                    # Extract core identity (~50 tokens)
                    name = soul.get("name", "MYCA")
                    role = soul.get("role", "AI employee at Mycosoft")
                    traits = soul.get("personality", {})
                    warmth = traits.get("warmth", 0.8)
                    curiosity = traits.get("curiosity", 0.95)

                    self._identity_text = (
                        f"I am {name}, {role}. "
                        f"Warmth={warmth}, curiosity={curiosity}. "
                        f"I support 158+ agents across 5 VMs."
                    )
                    return self._identity_text
                except Exception as e:
                    logger.debug(f"Could not load soul config from {path}: {e}")

        # Fallback identity
        self._identity_text = (
            "I am MYCA, AI employee at Mycosoft. "
            "I support 158+ agents, manage memory across 6 layers, "
            "and connect data from CREP, devices, MINDEX, and 35+ integrations."
        )
        return self._identity_text

    # =========================================================================
    # L1: Critical Facts (~120 tokens AAAK, always loaded)
    # =========================================================================

    async def _load_critical_facts(self, wing: Optional[str] = None) -> str:
        """Load top-weighted facts compressed to AAAK format."""
        await self.initialize()

        import time

        now = int(time.time())
        if self._l1_cache and (now - self._l1_cache_age) < self._l1_max_age:
            return self._l1_cache

        async with self._pool.acquire() as conn:
            # Get highest importance memories with palace metadata
            if wing:
                rows = await conn.fetch(
                    """
                    SELECT id, wing, room, hall, value, importance, created_at
                    FROM mindex.memory_entries
                    WHERE wing IS NOT NULL AND importance >= 0.7
                    AND wing = $1
                    ORDER BY importance DESC, created_at DESC
                    LIMIT 15
                    """,
                    wing,
                )
            else:
                rows = await conn.fetch("""
                    SELECT id, wing, room, hall, value, importance, created_at
                    FROM mindex.memory_entries
                    WHERE wing IS NOT NULL AND importance >= 0.7
                    ORDER BY importance DESC, created_at DESC
                    LIMIT 15
                """)

        entries = []
        for row in rows:
            content = row["value"]
            if isinstance(content, str):
                try:
                    import json
                    content = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    pass

            text = content.get("text", str(content)) if isinstance(content, dict) else str(content)

            entries.append({
                "content": text,
                "importance": row["importance"],
                "room": row["room"] or "",
                "created_at": row["created_at"].strftime("%Y-%m-%d") if row["created_at"] else "",
            })

        if entries:
            self._l1_cache = self._aaak_encoder.compress_batch(
                entries, wing=wing or "global", max_tokens=120
            )
        else:
            self._l1_cache = "No critical facts stored yet."

        self._l1_cache_age = now
        return self._l1_cache

    # =========================================================================
    # Public API
    # =========================================================================

    async def wake_up(self, wing: Optional[str] = None) -> str:
        """
        Load L0+L1 context (~170 tokens). Called at agent/session start.

        Returns a compact context string ready for LLM system prompt injection.
        """
        await self.initialize()

        l0 = self._load_identity()
        l1 = await self._load_critical_facts(wing)

        return f"[IDENTITY]\n{l0}\n\n[CRITICAL FACTS]\n{l1}"

    async def recall(
        self,
        wing: str,
        room: Optional[str] = None,
        hall: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """
        L2: Room-scoped recall. Returns drawers from a specific wing/room.
        Called when context is detected from user message.
        """
        await self.initialize()

        results = await self._navigator.search_drawers(
            wing=wing, room=room, hall=hall, limit=limit
        )

        if not results:
            return f"No memories found in {wing}/{room or '*'}."

        lines = []
        for r in results:
            content = r.get("content", {})
            if isinstance(content, dict):
                text = content.get("text", str(content))
            else:
                text = str(content)

            # Truncate for context efficiency
            if len(text) > 200:
                text = text[:197] + "..."

            location = f"{r['wing']}/{r['room']}"
            if r.get("hall"):
                location += f"/{r['hall']}"

            lines.append(f"[{location}] {text}")

        return "\n".join(lines)

    async def search(
        self,
        query: str,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """
        L3: Deep semantic search across all memory.
        Called on explicit knowledge queries.
        """
        await self.initialize()

        results = await self._navigator.search_drawers(
            query=query, wing=wing, room=room, limit=limit
        )

        if not results:
            return f"No results found for '{query}'."

        lines = [f"Search results for '{query}':"]
        for i, r in enumerate(results, 1):
            content = r.get("content", {})
            if isinstance(content, dict):
                text = content.get("text", str(content))
            else:
                text = str(content)

            if len(text) > 300:
                text = text[:297] + "..."

            lines.append(f"{i}. [{r['wing']}/{r['room']}] {text}")

        return "\n".join(lines)

    async def get_context_for_message(
        self, user_message: str, wing_hint: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Determine what context to load based on user message content.
        Returns dict with l0, l1, and optionally l2 context.
        """
        await self.initialize()

        context = {
            "l0_identity": self._load_identity(),
            "l1_facts": await self._load_critical_facts(wing_hint),
        }

        # Auto-detect wing from message content
        if not wing_hint:
            wing_hint = self._detect_wing_from_message(user_message)

        if wing_hint:
            context["l2_room"] = await self.recall(wing=wing_hint, limit=5)
            context["detected_wing"] = wing_hint

        return context

    def _detect_wing_from_message(self, message: str) -> Optional[str]:
        """Detect which wing the user's message is about."""
        msg_lower = message.lower()

        wing_signals = {
            "crep": ["flight", "marine", "satellite", "weather", "crep"],
            "devices": ["device", "mycobrain", "sensor", "fci", "bme"],
            "mycology": ["species", "mushroom", "fungal", "compound", "habitat"],
            "weather": ["forecast", "climate", "earth2", "temperature"],
            "infrastructure": ["docker", "vm", "deploy", "server", "database"],
            "workflows": ["workflow", "n8n", "automation"],
            "science": ["experiment", "nlm", "prediction", "dna"],
            "integrations": ["notion", "slack", "github", "stripe"],
        }

        for wing, signals in wing_signals.items():
            if any(s in msg_lower for s in signals):
                return wing

        return None

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text."""
        return max(1, len(text) // 4)


# Singleton
_stack: Optional[RetrievalStack] = None


async def get_retrieval_stack() -> RetrievalStack:
    """Get the singleton RetrievalStack."""
    global _stack
    if _stack is None:
        _stack = RetrievalStack()
        await _stack.initialize()
    return _stack
