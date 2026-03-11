"""
Voice v9 Memory Bridge - March 2, 2026.

Bridges voice to memory/context. Stub for Phase 1.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class MemoryBridge:
    """Bridges v9 voice to memory recall and storage."""

    async def recall(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Recall memory context for a turn. Stub returns empty."""
        return {
            "memories": [],
            "episodes": [],
            "user_profile": None,
        }

    async def store(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store a turn in memory. Stub returns True."""
        return True
