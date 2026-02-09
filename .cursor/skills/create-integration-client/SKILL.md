---
name: create-integration-client
description: Create a new integration client module for the MAS system. Use when adding a new external service integration, API client, or third-party connector.
---

# Create an Integration Client

## Pattern

Integration clients live in `mycosoft_mas/integrations/` and follow a consistent async HTTP pattern.

## Steps

```
Integration Client Progress:
- [ ] Step 1: Create client file
- [ ] Step 2: Update __init__.py
- [ ] Step 3: Register with integration manager
- [ ] Step 4: Test the client
```

### Step 1: Create the client file

Create `mycosoft_mas/integrations/your_client.py`:

```python
"""Your Service Client - Integration with external service."""

import httpx
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class YourServiceClient:
    """Client for communicating with Your Service API."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        """Check if the external service is reachable."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            response.raise_for_status()
            return {"status": "healthy", "service": "your-service"}
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}

    async def get_data(self, endpoint: str) -> Dict[str, Any]:
        """Fetch data from the service."""
        client = await self._get_client()
        response = await client.get(endpoint)
        response.raise_for_status()
        return response.json()

    async def post_data(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to the service."""
        client = await self._get_client()
        response = await client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
```

### Step 2: Update __init__.py

Add to `mycosoft_mas/integrations/__init__.py`:

```python
from .your_client import YourServiceClient

__all__ = [
    # ... existing clients ...
    'YourServiceClient',
]
```

### Step 3: Register with integration manager

The integration manager at `mycosoft_mas/integrations/integration_manager.py` coordinates all clients.

### Step 4: Test

```python
import pytest
from mycosoft_mas.integrations.your_client import YourServiceClient

@pytest.mark.asyncio
async def test_client_health():
    client = YourServiceClient(base_url="http://service-url")
    result = await client.health_check()
    assert result["status"] in ("healthy", "unhealthy")
    await client.close()
```

## Key Rules

- Always use async httpx (not requests)
- Include health_check method
- Include proper timeout (30s default)
- Include close/cleanup method
- Handle errors with logging, not silent failures
- No mock data -- connect to real service URLs
