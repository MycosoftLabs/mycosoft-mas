from __future__ import annotations

from typing import Optional

import httpx


class JetsonCameraClient:
    def __init__(self, base_url: str = "http://192.168.0.100:8080", timeout_s: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def close(self) -> None:
        await self._client.aclose()

    async def frame(self) -> Optional[bytes]:
        response = await self._client.get(f"{self.base_url}/camera/frame")
        if response.status_code >= 400:
            return None
        return response.content

