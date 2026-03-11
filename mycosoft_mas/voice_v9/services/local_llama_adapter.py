"""
Voice v9 Local Llama Adapter - March 11, 2026.

Calls an Ollama-compatible endpoint for low-latency local responses.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx


class LocalLlamaAdapter:
    """Thin adapter for local/remote Ollama-compatible LLM endpoints."""

    def __init__(self) -> None:
        self.base_url = os.getenv("VOICE_V9_LOCAL_LLAMA_URL", "http://192.168.0.188:11434").rstrip("/")
        self.model = os.getenv("VOICE_V9_LOCAL_LLAMA_MODEL", "llama3.1:8b")
        self.timeout_sec = float(os.getenv("VOICE_V9_LOCAL_LLAMA_TIMEOUT", "12"))

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a single non-streaming response."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return (data.get("response") or "").strip()
