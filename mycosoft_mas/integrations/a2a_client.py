"""
Outbound A2A client for federating calls to external AI agents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class A2AAgentCard:
    name: str
    version: str
    raw: Dict[str, Any]


class A2AClient:
    """Client for external A2A agents (agent card discovery + message send)."""

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def get_agent_card(self, base_url: str) -> A2AAgentCard:
        base = base_url.rstrip("/")
        candidates = [
            f"{base}/.well-known/agent-card.json",
            f"{base}/a2a/v1/agent-card",
        ]
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            last_error: Optional[Exception] = None
            for url in candidates:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    return A2AAgentCard(
                        name=str(data.get("name", "unknown")),
                        version=str(data.get("version", "unknown")),
                        raw=data,
                    )
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
            if last_error:
                raise last_error
            raise RuntimeError("Unable to fetch A2A agent card")

    async def send_message(
        self,
        base_url: str,
        text: str,
        *,
        context_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        blocking: bool = True,
    ) -> Dict[str, Any]:
        base = base_url.rstrip("/")
        payload = {
            "message": {
                "messageId": metadata.get("message_id") if metadata else "myca-outbound",
                "contextId": context_id,
                "role": "ROLE_USER",
                "parts": [{"text": text, "mediaType": "text/plain"}],
                "metadata": metadata or {},
            },
            "configuration": {
                "blocking": blocking,
                "acceptedOutputModes": ["text/plain"],
            },
            "metadata": metadata or {},
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(f"{base}/a2a/v1/message/send", json=payload)
            resp.raise_for_status()
            return resp.json()
