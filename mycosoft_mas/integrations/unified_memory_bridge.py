"""
Unified Memory Bridge - February 4, 2026

Provides a unified interface for external systems to access
the MINDEX memory, registry, and graph services.

Designed for:
- NatureOS (.NET Core)
- NLM (Python)
- MycoBrain (C++/Arduino via HTTP)
- External integrations
"""

import os
import logging
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("UnifiedMemoryBridge")


class MemoryScope(str, Enum):
    """Memory scopes available through the bridge."""
    CONVERSATION = "conversation"
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    EPHEMERAL = "ephemeral"
    DEVICE = "device"
    EXPERIMENT = "experiment"
    WORKFLOW = "workflow"


class UnifiedMemoryBridge:
    """
    Bridge class for accessing MINDEX memory services.
    
    Can be used as a library or through the REST API.
    """
    
    def __init__(
        self,
        mindex_url: Optional[str] = None,
        mas_url: Optional[str] = None,
        timeout: float = 30.0
    ):
        self._mindex_url = mindex_url or os.getenv(
            "MINDEX_URL", "http://192.168.0.189:8000"
        )
        self._mas_url = mas_url or os.getenv(
            "MAS_URL", "http://192.168.0.188:8001"
        )
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
    
    # =========================================================================
    # Memory Operations
    # =========================================================================
    
    async def memory_write(
        self,
        scope: MemoryScope,
        namespace: str,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Write to memory with cryptographic integrity."""
        client = await self._get_client()
        
        response = await client.post(
            f"{self._mas_url}/api/memory/write",
            json={
                "scope": scope.value,
                "namespace": namespace,
                "key": key,
                "value": value,
                "metadata": metadata,
                "ttl_seconds": ttl_seconds
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def memory_read(
        self,
        scope: MemoryScope,
        namespace: str,
        key: Optional[str] = None
    ) -> Optional[Any]:
        """Read from memory."""
        client = await self._get_client()
        
        response = await client.post(
            f"{self._mas_url}/api/memory/read",
            json={
                "scope": scope.value,
                "namespace": namespace,
                "key": key
            }
        )
        response.raise_for_status()
        data = response.json()
        return data.get("value")
    
    async def memory_delete(
        self,
        scope: MemoryScope,
        namespace: str,
        key: str
    ) -> bool:
        """Delete from memory."""
        client = await self._get_client()
        
        response = await client.post(
            f"{self._mas_url}/api/memory/delete",
            json={
                "scope": scope.value,
                "namespace": namespace,
                "key": key
            }
        )
        response.raise_for_status()
        return response.json().get("success", False)
    
    async def memory_list_keys(
        self,
        scope: MemoryScope,
        namespace: str
    ) -> List[str]:
        """List keys in a namespace."""
        client = await self._get_client()
        
        response = await client.get(
            f"{self._mas_url}/api/memory/list/{scope.value}/{namespace}"
        )
        response.raise_for_status()
        return response.json().get("keys", [])
    
    # =========================================================================
    # Registry Operations
    # =========================================================================
    
    async def registry_list_systems(self) -> List[Dict[str, Any]]:
        """List all registered systems."""
        client = await self._get_client()
        
        response = await client.get(f"{self._mas_url}/api/registry/systems")
        response.raise_for_status()
        return response.json().get("systems", [])
    
    async def registry_list_apis(
        self,
        system: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List registered APIs."""
        client = await self._get_client()
        
        params = {}
        if system:
            params["system"] = system
        
        response = await client.get(
            f"{self._mas_url}/api/registry/apis",
            params=params
        )
        response.raise_for_status()
        return response.json().get("apis", [])
    
    async def registry_list_devices(
        self,
        device_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List registered devices."""
        client = await self._get_client()
        
        params = {}
        if device_type:
            params["type"] = device_type
        
        response = await client.get(
            f"{self._mas_url}/api/registry/devices",
            params=params
        )
        response.raise_for_status()
        return response.json().get("devices", [])
    
    async def registry_update_device(
        self,
        device_id: str,
        status: str,
        telemetry: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update device status and telemetry."""
        client = await self._get_client()
        
        response = await client.post(
            f"{self._mas_url}/api/registry/devices/{device_id}/status",
            params={"status": status},
            json=telemetry
        )
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Graph Operations
    # =========================================================================
    
    async def graph_list_nodes(
        self,
        node_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List nodes from the knowledge graph."""
        client = await self._get_client()
        
        params = {"limit": limit}
        if node_type:
            params["node_type"] = node_type
        
        response = await client.get(
            f"{self._mas_url}/api/graph/nodes",
            params=params
        )
        response.raise_for_status()
        return response.json().get("nodes", [])
    
    async def graph_find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Find path between two nodes."""
        client = await self._get_client()
        
        response = await client.post(
            f"{self._mas_url}/api/graph/path",
            json={
                "source_id": source_id,
                "target_id": target_id,
                "max_depth": max_depth
            }
        )
        response.raise_for_status()
        data = response.json()
        return data.get("path") if data.get("found") else None
    
    async def graph_get_subgraph(
        self,
        node_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """Get a subgraph centered on a node."""
        client = await self._get_client()
        
        response = await client.get(
            f"{self._mas_url}/api/graph/subgraph/{node_id}",
            params={"depth": depth}
        )
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Ledger Operations
    # =========================================================================
    
    async def ledger_get_stats(self) -> Dict[str, Any]:
        """Get ledger statistics."""
        client = await self._get_client()
        
        response = await client.get(f"{self._mindex_url}/api/ledger/stats")
        response.raise_for_status()
        return response.json()
    
    async def ledger_verify_chain(self) -> Dict[str, Any]:
        """Verify blockchain integrity."""
        client = await self._get_client()
        
        response = await client.post(f"{self._mindex_url}/api/ledger/verify")
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Audit Operations
    # =========================================================================
    
    async def audit_log(
        self,
        user_id: str,
        action: str,
        resource: str,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> Dict[str, Any]:
        """Log an audit entry."""
        client = await self._get_client()
        
        response = await client.post(
            f"{self._mas_url}/api/security/audit/log",
            json={
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "success": success,
                "details": details or {},
                "severity": severity
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def audit_query(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Query audit log."""
        client = await self._get_client()
        
        params = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        if action:
            params["action"] = action
        
        response = await client.get(
            f"{self._mas_url}/api/security/audit/query",
            params=params
        )
        response.raise_for_status()
        return response.json().get("entries", [])
    
    # =========================================================================
    # Health Check
    # =========================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all connected services."""
        client = await self._get_client()
        
        services = {}
        
        # Check MAS
        try:
            response = await client.get(f"{self._mas_url}/health")
            services["mas"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            services["mas"] = f"error: {e}"
        
        # Check MAS Memory
        try:
            response = await client.get(f"{self._mas_url}/api/memory/health")
            services["memory"] = response.json().get("status", "unknown")
        except Exception as e:
            services["memory"] = f"error: {e}"
        
        # Check MINDEX
        try:
            response = await client.get(f"{self._mindex_url}/health")
            services["mindex"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            services["mindex"] = f"error: {e}"
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": services,
            "overall": "healthy" if all(
                v == "healthy" for v in services.values() if isinstance(v, str) and not v.startswith("error")
            ) else "degraded"
        }


# Singleton instance
_bridge: Optional[UnifiedMemoryBridge] = None


def get_memory_bridge() -> UnifiedMemoryBridge:
    """Get singleton bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = UnifiedMemoryBridge()
    return _bridge
