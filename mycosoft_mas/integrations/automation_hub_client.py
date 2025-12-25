"""
Automation Hub Client

Provides access to automation platforms:
- Zapier (Webhooks)
- IFTTT (Maker Webhooks)
- Make (Integromat)
- Pipedream
- Activepieces

Environment Variables:
    ZAPIER_WEBHOOK_URL: Zapier catch webhook URL
    IFTTT_WEBHOOK_KEY: IFTTT Maker webhook key
    MAKE_WEBHOOK_URL: Make (Integromat) webhook URL
    PIPEDREAM_API_KEY: Pipedream API key
    PIPEDREAM_ENDPOINT: Pipedream endpoint ID
    ACTIVEPIECES_WEBHOOK_URL: Activepieces webhook URL
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class AutomationHubClient:
    """
    Client for automation platform webhooks and APIs.
    
    Provides unified access to trigger automations on:
    - Zapier
    - IFTTT
    - Make (Integromat)
    - Pipedream
    - Activepieces
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the automation hub client."""
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)
        
        # Webhook URLs and Keys
        self.zapier_url = self.config.get("zapier_url") or os.getenv("ZAPIER_WEBHOOK_URL", "")
        self.ifttt_key = self.config.get("ifttt_key") or os.getenv("IFTTT_WEBHOOK_KEY", "")
        self.make_url = self.config.get("make_url") or os.getenv("MAKE_WEBHOOK_URL", "")
        self.pipedream_key = self.config.get("pipedream_key") or os.getenv("PIPEDREAM_API_KEY", "")
        self.pipedream_endpoint = self.config.get("pipedream_endpoint") or os.getenv("PIPEDREAM_ENDPOINT", "")
        self.activepieces_url = self.config.get("activepieces_url") or os.getenv("ACTIVEPIECES_WEBHOOK_URL", "")
        
        self._client: Optional[httpx.AsyncClient] = None
        logger.info("Automation hub client initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of automation platform connections."""
        configured = []
        if self.zapier_url:
            configured.append("zapier")
        if self.ifttt_key:
            configured.append("ifttt")
        if self.make_url:
            configured.append("make")
        if self.pipedream_key:
            configured.append("pipedream")
        if self.activepieces_url:
            configured.append("activepieces")
        
        return {
            "status": "ok" if configured else "not_configured",
            "configured_platforms": configured,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Zapier
    async def trigger_zapier(
        self,
        event: str,
        data: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger a Zapier webhook."""
        url = webhook_url or self.zapier_url
        if not url:
            raise ValueError("ZAPIER_WEBHOOK_URL is required")
        
        client = await self._get_client()
        payload = {
            "event": event,
            "data": data,
            "source": "myca_mas",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = await client.post(url, json=payload)
        response.raise_for_status()
        
        return {
            "success": True,
            "platform": "zapier",
            "event": event,
            "status_code": response.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # IFTTT
    async def trigger_ifttt(
        self,
        event_name: str,
        value1: Optional[str] = None,
        value2: Optional[str] = None,
        value3: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger an IFTTT Maker webhook."""
        if not self.ifttt_key:
            raise ValueError("IFTTT_WEBHOOK_KEY is required")
        
        client = await self._get_client()
        url = f"https://maker.ifttt.com/trigger/{event_name}/with/key/{self.ifttt_key}"
        payload = {}
        if value1:
            payload["value1"] = value1
        if value2:
            payload["value2"] = value2
        if value3:
            payload["value3"] = value3
        
        response = await client.post(url, json=payload)
        response.raise_for_status()
        
        return {
            "success": True,
            "platform": "ifttt",
            "event": event_name,
            "status_code": response.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Make (Integromat)
    async def trigger_make(
        self,
        event: str,
        data: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger a Make (Integromat) webhook."""
        url = webhook_url or self.make_url
        if not url:
            raise ValueError("MAKE_WEBHOOK_URL is required")
        
        client = await self._get_client()
        payload = {
            "event": event,
            "data": data,
            "source": "myca_mas",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = await client.post(url, json=payload)
        response.raise_for_status()
        
        return {
            "success": True,
            "platform": "make",
            "event": event,
            "status_code": response.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Pipedream
    async def trigger_pipedream(
        self,
        event: str,
        data: Dict[str, Any],
        endpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger a Pipedream workflow."""
        ep = endpoint or self.pipedream_endpoint
        if not ep:
            raise ValueError("PIPEDREAM_ENDPOINT is required")
        
        client = await self._get_client()
        url = f"https://{ep}.m.pipedream.net"
        headers = {}
        if self.pipedream_key:
            headers["Authorization"] = f"Bearer {self.pipedream_key}"
        
        payload = {
            "event": event,
            "data": data,
            "source": "myca_mas",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        return {
            "success": True,
            "platform": "pipedream",
            "event": event,
            "status_code": response.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Activepieces
    async def trigger_activepieces(
        self,
        event: str,
        data: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger an Activepieces webhook."""
        url = webhook_url or self.activepieces_url
        if not url:
            raise ValueError("ACTIVEPIECES_WEBHOOK_URL is required")
        
        client = await self._get_client()
        payload = {
            "event": event,
            "data": data,
            "source": "myca_mas",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = await client.post(url, json=payload)
        response.raise_for_status()
        
        return {
            "success": True,
            "platform": "activepieces",
            "event": event,
            "status_code": response.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Unified trigger method
    async def trigger(
        self,
        platform: str,
        event: str,
        data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Trigger an automation on any configured platform.
        
        Args:
            platform: Platform name (zapier, ifttt, make, pipedream, activepieces)
            event: Event name to trigger
            data: Data payload
            **kwargs: Platform-specific arguments
        
        Returns:
            Result of the trigger operation
        """
        platform = platform.lower()
        
        if platform == "zapier":
            return await self.trigger_zapier(event, data, kwargs.get("webhook_url"))
        elif platform == "ifttt":
            return await self.trigger_ifttt(
                event,
                data.get("value1"),
                data.get("value2"),
                data.get("value3")
            )
        elif platform == "make":
            return await self.trigger_make(event, data, kwargs.get("webhook_url"))
        elif platform == "pipedream":
            return await self.trigger_pipedream(event, data, kwargs.get("endpoint"))
        elif platform == "activepieces":
            return await self.trigger_activepieces(event, data, kwargs.get("webhook_url"))
        else:
            raise ValueError(f"Unknown platform: {platform}")
    
    async def broadcast(
        self,
        event: str,
        data: Dict[str, Any],
        platforms: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Broadcast an event to multiple automation platforms.
        
        Args:
            event: Event name to trigger
            data: Data payload
            platforms: List of platforms to trigger (None = all configured)
        
        Returns:
            Results from all platforms
        """
        results = {}
        errors = {}
        
        # Determine which platforms to trigger
        if platforms is None:
            platforms = []
            if self.zapier_url:
                platforms.append("zapier")
            if self.ifttt_key:
                platforms.append("ifttt")
            if self.make_url:
                platforms.append("make")
            if self.pipedream_endpoint:
                platforms.append("pipedream")
            if self.activepieces_url:
                platforms.append("activepieces")
        
        for platform in platforms:
            try:
                result = await self.trigger(platform, event, data)
                results[platform] = result
            except Exception as e:
                errors[platform] = str(e)
                logger.error(f"Failed to trigger {platform}: {e}")
        
        return {
            "event": event,
            "results": results,
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        logger.info("Automation hub client closed")
