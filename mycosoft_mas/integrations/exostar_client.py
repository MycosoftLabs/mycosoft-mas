"""
Exostar Compliance Integration Client.

Identity federation, supply chain risk management, CMMC compliance tracking.
Requires Exostar partnership/account - API access is not public.

Environment Variables:
    EXOSTAR_API_URL: Exostar API base URL (provided upon partnership)
    EXOSTAR_API_KEY: Exostar API key or token
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class ExostarClient:
    """Client for Exostar compliance and identity federation APIs."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_url = (self.config.get("api_url") or os.environ.get("EXOSTAR_API_URL", "")).rstrip(
            "/"
        )
        self.api_key = self.config.get("api_key") or os.environ.get("EXOSTAR_API_KEY", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _is_configured(self) -> bool:
        return bool(self.api_url and self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _not_configured_response(self, operation: str) -> Dict[str, Any]:
        return {
            "status": "not_configured",
            "operation": operation,
            "message": "Exostar API requires partnership. Set EXOSTAR_API_URL and EXOSTAR_API_KEY.",
        }

    async def check_compliance_status(self, entity_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check CMMC/compliance status for an entity or organization.
        entity_id: Optional Exostar entity identifier.
        """
        if not self._is_configured():
            return self._not_configured_response("check_compliance_status")
        try:
            client = await self._get_client()
            path = "/compliance/status" if not entity_id else f"/compliance/status/{entity_id}"
            r = await client.get(path)
            if r.is_success:
                return {"status": "success", "data": r.json()}
            return {"status": "error", "status_code": r.status_code, "detail": r.text}
        except Exception as e:
            logger.warning("Exostar check_compliance_status failed: %s", e)
            return {"status": "error", "error": str(e)}

    async def get_supply_chain_risk(self, supplier_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get supply chain risk assessment data.
        supplier_id: Optional supplier/vendor identifier.
        """
        if not self._is_configured():
            return self._not_configured_response("get_supply_chain_risk")
        try:
            client = await self._get_client()
            path = "/supply-chain/risk" if not supplier_id else f"/supply-chain/risk/{supplier_id}"
            r = await client.get(path)
            if r.is_success:
                return {"status": "success", "data": r.json()}
            return {"status": "error", "status_code": r.status_code, "detail": r.text}
        except Exception as e:
            logger.warning("Exostar get_supply_chain_risk failed: %s", e)
            return {"status": "error", "error": str(e)}

    async def get_identity_federation_status(self) -> Dict[str, Any]:
        """Get identity federation and access gateway status."""
        if not self._is_configured():
            return self._not_configured_response("get_identity_federation_status")
        try:
            client = await self._get_client()
            r = await client.get("/identity/federation/status")
            if r.is_success:
                return {"status": "success", "data": r.json()}
            return {"status": "error", "status_code": r.status_code, "detail": r.text}
        except Exception as e:
            logger.warning("Exostar get_identity_federation_status failed: %s", e)
            return {"status": "error", "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check Exostar API availability and configuration."""
        if not self._is_configured():
            return {
                "status": "not_configured",
                "service": "exostar",
                "message": "Set EXOSTAR_API_URL and EXOSTAR_API_KEY for Exostar partnership access.",
            }
        try:
            client = await self._get_client()
            r = await client.get("/health")
            ok = r.is_success
            return {
                "status": "healthy" if ok else "unhealthy",
                "service": "exostar",
                "configured": True,
                "api_reachable": ok,
            }
        except Exception as e:
            logger.warning("Exostar health_check failed: %s", e)
            return {
                "status": "unhealthy",
                "service": "exostar",
                "configured": True,
                "error": str(e),
            }
