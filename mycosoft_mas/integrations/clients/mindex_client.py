import aiohttp
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MindexClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
        return self.session

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        session = await self._get_session()
        async with session.get(f"{self.base_url}/market/{symbol}") as resp:
            resp.raise_for_status()
            return await resp.json()

    async def close(self):
        if self.session:
            await self.session.close()
