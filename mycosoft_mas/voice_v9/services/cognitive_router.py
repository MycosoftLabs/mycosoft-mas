"""
Voice v9 Cognitive Router - March 2, 2026.

Routes turns to MAS bridge or local LLM. Stub for Phase 1.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from mycosoft_mas.voice_v9.services.local_llama_adapter import LocalLlamaAdapter


class CognitiveRouter:
    """Routes conversational turns to MAS or local Llama."""

    def __init__(self) -> None:
        self._local_llama = LocalLlamaAdapter()
        self._prefer_local_llama = os.getenv("VOICE_V9_USE_LOCAL_LLAMA", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    async def route(
        self,
        session_id: str,
        user_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Decide target (mas_bridge vs local_llama) and delegate.
        """
        context = context or {}
        if context.get("force_target") in {"local_llama", "mas_bridge"}:
            target = context["force_target"]
        elif self._prefer_local_llama:
            target = "local_llama"
        else:
            target = "mas_bridge"

        if target == "local_llama":
            system_prompt = context.get(
                "system_prompt",
                "You are MYCA. Respond concisely, clearly, and maintain MYCA identity.",
            )
            response = await self._local_llama.generate(user_text, system_prompt=system_prompt)
            return {
                "target": "local_llama",
                "session_id": session_id,
                "deferred": False,
                "response": response,
                "provider": "local_llama",
            }

        return {
            "target": "mas_bridge",
            "session_id": session_id,
            "deferred": False,
            "response": "",
            "provider": "mas_bridge",
        }
