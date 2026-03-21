"""
OpenClaw integration for edge operator execution.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class OpenClawClient:
    def __init__(self, base_url: str, timeout_seconds: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)

    async def health(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def run_task(self, task: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/tasks", json=task, headers=headers)
            response.raise_for_status()
            return response.json()
