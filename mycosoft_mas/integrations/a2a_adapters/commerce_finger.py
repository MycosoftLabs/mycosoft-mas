from __future__ import annotations

import os
from typing import Any, Dict, Optional

from mycosoft_mas.integrations.a2a_client import A2AClient


class CommerceFingerAdapter:
    """A2A adapter for commerce-domain external agents."""

    def __init__(self, client: Optional[A2AClient] = None, base_url: Optional[str] = None) -> None:
        self.client = client or A2AClient()
        self.base_url = (base_url or os.getenv("A2A_COMMERCE_URL", "")).rstrip("/")

    async def ask(self, prompt: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("A2A_COMMERCE_URL is not configured")
        return await self.client.send_message(self.base_url, prompt, metadata=metadata or {})

