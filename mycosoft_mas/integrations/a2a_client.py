"""
Outbound A2A client for federating calls to external and internal AI agents.

Supports internal auth via X-Internal-Token for agent delegation within
the Mycosoft network (MAS <-> MINDEX).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from mycosoft_mas.integrations.mindex_internal_auth import get_internal_headers

# Internal network prefixes where internal auth should be injected
_INTERNAL_PREFIXES = (
    "http://192.168.0.188",
    "http://192.168.0.189",
    "http://192.168.0.190",
    "http://192.168.0.191",
)


@dataclass
class A2AAgentCard:
    name: str
    version: str
    raw: Dict[str, Any]


class A2AClient:
    """Client for external and internal A2A agents (agent card discovery + message send).

    Automatically injects ``X-Internal-Token`` when the target URL is on the
    internal Mycosoft network so that MINDEX and other internal services can
    verify the caller is a trusted MAS agent.
    """

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _auth_headers(url: str) -> Dict[str, str]:
        """Return internal auth headers when *url* is on the internal network."""
        for prefix in _INTERNAL_PREFIXES:
            if url.startswith(prefix):
                return get_internal_headers()
        return {}

    async def get_agent_card(self, base_url: str) -> A2AAgentCard:
        base = base_url.rstrip("/")
        candidates = [
            f"{base}/.well-known/agent-card.json",
            f"{base}/a2a/v1/agent-card",
        ]
        headers = self._auth_headers(base)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            last_error: Optional[Exception] = None
            for url in candidates:
                try:
                    resp = await client.get(url, headers=headers)
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
        headers = self._auth_headers(base)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(
                f"{base}/a2a/v1/message/send", json=payload, headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

