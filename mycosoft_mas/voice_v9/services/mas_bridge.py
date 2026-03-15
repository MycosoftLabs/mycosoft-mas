"""
Voice v9 MAS Bridge - March 2, 2026.

Bridges voice to MAS Brain/tools. Stub delegates to existing Brain API.
Provider is read from env VOICE_PROVIDER (default "stub") for future PersonaPlex/Moshi wiring.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


class MASBridge:
    """Bridges v9 voice flow to MAS Brain and tools."""

    async def chat(
        self,
        session_id: str,
        conversation_id: str,
        user_id: str,
        message: str,
        history: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Send message to MAS Brain. Stub; full impl will call
        POST /voice/brain/chat via httpx.
        """
        provider = os.environ.get("VOICE_PROVIDER", "stub")
        return {
            "session_id": session_id,
            "response": "",
            "provider": provider,
            "actions_taken": [],
        }
