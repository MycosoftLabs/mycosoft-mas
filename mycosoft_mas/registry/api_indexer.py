"""
API Indexer - February 4, 2026

Automatically discovers and indexes all FastAPI routes across
the Mycosoft Multi-Agent System, creating a comprehensive API catalog.

Features:
- FastAPI route introspection
- OpenAPI schema extraction
- Cross-system API discovery
- Tag-based categorization
"""

import os
import logging
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

from mycosoft_mas.registry.system_registry import (
    get_registry, SystemRegistry, APIInfo, SystemInfo, SystemType
)

logger = logging.getLogger("APIIndexer")


# ============================================================================
# System Configuration
# ============================================================================

# Known systems and their OpenAPI endpoints
SYSTEM_CONFIGS = {
    "MAS": {
        "type": SystemType.MAS,
        "url": os.getenv("MAS_URL", "http://192.168.0.188:8001"),
        "openapi_path": "/openapi.json",
        "description": "Mycosoft Multi-Agent System Orchestrator"
    },
    "Website": {
        "type": SystemType.WEBSITE,
        "url": os.getenv("WEBSITE_URL", "http://192.168.0.187:3000"),
        "openapi_path": None,  # Next.js API routes
        "description": "Mycosoft Website and Dashboard"
    },
    "MINDEX": {
        "type": SystemType.MINDEX,
        "url": os.getenv("MINDEX_URL", "http://192.168.0.189:8000"),
        "openapi_path": "/openapi.json",
        "description": "Memory Index and Knowledge Graph Service"
    },
    "NatureOS": {
        "type": SystemType.NATUREOS,
        "url": os.getenv("NATUREOS_URL", "http://192.168.0.188:5000"),
        "openapi_path": "/swagger/v1/swagger.json",  # .NET Core Swagger
        "description": "Nature Operating System Backend"
    },
    "NLM": {
        "type": SystemType.NLM,
        "url": os.getenv("NLM_URL", "http://192.168.0.188:8200"),
        "openapi_path": "/openapi.json",
        "description": "Nature Learning Model Service"
    }
}


class APIIndexer:
    """
    Discovers and indexes APIs across all Mycosoft systems.
    """
    
    def __init__(self, registry: Optional[SystemRegistry] = None):
        self._registry = registry or get_registry()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._indexed_apis: Set[str] = set()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
    
    async def index_all_systems(self) -> Dict[str, Any]:
        """Index APIs from all known systems."""
        results = {
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "systems": {},
            "total_apis": 0,
            "errors": []
        }
        
        for system_name, config in SYSTEM_CONFIGS.items():
            try:
                # Register/update system
                system = SystemInfo(
                    name=system_name,
                    type=config["type"],
                    url=config["url"],
                    description=config["description"],
                    status="active"
                )
                await self._registry.register_system(system)
                
                # Index APIs
                if config.get("openapi_path"):
                    api_count = await self._index_openapi_system(
                        system_name, config["url"], config["openapi_path"]
                    )
                else:
                    # Manual API discovery for non-OpenAPI systems
                    api_count = await self._index_manual_apis(system_name, config)
                
                results["systems"][system_name] = {
                    "url": config["url"],
                    "api_count": api_count,
                    "status": "indexed"
                }
                results["total_apis"] += api_count
                
            except Exception as e:
                logger.error(f"Failed to index {system_name}: {e}")
                results["errors"].append({
                    "system": system_name,
                    "error": str(e)
                })
                results["systems"][system_name] = {
                    "url": config["url"],
                    "api_count": 0,
                    "status": "error"
                }
        
        return results
    
    async def _index_openapi_system(
        self,
        system_name: str,
        base_url: str,
        openapi_path: str
    ) -> int:
        """Index a system using its OpenAPI specification."""
        client = await self._get_client()
        openapi_url = urljoin(base_url, openapi_path)
        
        try:
            response = await client.get(openapi_url)
            response.raise_for_status()
            spec = response.json()
        except Exception as e:
            logger.warning(f"Could not fetch OpenAPI spec from {openapi_url}: {e}")
            # Fall back to known routes
            return await self._index_known_routes(system_name, base_url)
        
        api_count = 0
        paths = spec.get("paths", {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    api = APIInfo(
                        path=path,
                        method=method.upper(),
                        description=details.get("summary") or details.get("description"),
                        tags=details.get("tags", []),
                        request_schema=details.get("requestBody", {}).get("content", {}).get(
                            "application/json", {}
                        ).get("schema"),
                        response_schema=self._extract_response_schema(details),
                        auth_required="security" in details or "security" in spec,
                        deprecated=details.get("deprecated", False),
                        metadata={
                            "operation_id": details.get("operationId"),
                            "indexed_from": "openapi"
                        }
                    )
                    
                    await self._registry.register_api(api, system_name)
                    api_count += 1
        
        logger.info(f"Indexed {api_count} APIs from {system_name}")
        return api_count
    
    def _extract_response_schema(self, details: Dict) -> Optional[Dict]:
        """Extract response schema from OpenAPI operation."""
        responses = details.get("responses", {})
        for status_code in ["200", "201", "202"]:
            if status_code in responses:
                content = responses[status_code].get("content", {})
                if "application/json" in content:
                    return content["application/json"].get("schema")
        return None
    
    async def _index_known_routes(self, system_name: str, base_url: str) -> int:
        """Index known routes for a system without OpenAPI."""
        # Known MAS routes
        known_routes = {
            "MAS": [
                ("/health", "GET", "Health check endpoint"),
                ("/api/agents", "GET", "List all agents"),
                ("/api/agents/{agent_id}", "GET", "Get agent by ID"),
                ("/api/tasks", "GET", "List tasks"),
                ("/api/tasks", "POST", "Create task"),
                ("/api/memory/health", "GET", "Memory system health"),
                ("/api/memory/write", "POST", "Write to memory"),
                ("/api/memory/read", "POST", "Read from memory"),
                ("/api/memory/delete", "POST", "Delete from memory"),
                ("/api/memory/list/{scope}/{namespace}", "GET", "List memory keys"),
                ("/api/memory/audit", "GET", "Get memory audit log"),
                ("/api/security/audit/log", "POST", "Log security audit entry"),
                ("/api/security/audit/query", "GET", "Query security audit log"),
                ("/api/security/audit/stats", "GET", "Get audit statistics"),
                ("/api/security/health", "GET", "Security service health"),
                ("/api/voice/session", "POST", "Create voice session"),
                ("/api/voice/health", "GET", "Voice service health"),
                ("/api/mindex/query", "POST", "Query MINDEX"),
                ("/api/mindex/health", "GET", "MINDEX health"),
                ("/api/natureos/telemetry", "POST", "NatureOS telemetry"),
                ("/api/natureos/health", "GET", "NatureOS health"),
                ("/api/workflow/trigger", "POST", "Trigger workflow"),
                ("/api/workflow/status/{execution_id}", "GET", "Get workflow status"),
            ],
            "MINDEX": [
                ("/health", "GET", "Health check"),
                ("/api/memory/health", "GET", "Memory health"),
                ("/api/memory/write", "POST", "Write memory"),
                ("/api/memory/read", "POST", "Read memory"),
                ("/api/ledger/stats", "GET", "Ledger statistics"),
                ("/api/ledger/verify", "POST", "Verify chain integrity"),
                ("/api/registry/systems", "GET", "List systems"),
                ("/api/registry/apis", "GET", "List APIs"),
                ("/api/registry/agents", "GET", "List agents"),
                ("/api/graph/nodes", "GET", "List graph nodes"),
                ("/api/graph/edges", "GET", "List graph edges"),
            ]
        }
        
        routes = known_routes.get(system_name, [])
        api_count = 0
        
        for path, method, description in routes:
            api = APIInfo(
                path=path,
                method=method,
                description=description,
                tags=[system_name.lower()],
                metadata={"indexed_from": "known_routes"}
            )
            await self._registry.register_api(api, system_name)
            api_count += 1
        
        return api_count
    
    async def _index_manual_apis(
        self,
        system_name: str,
        config: Dict[str, Any]
    ) -> int:
        """Manually index APIs for systems without OpenAPI."""
        # Website Next.js API routes
        if system_name == "Website":
            return await self._index_nextjs_routes(config["url"])
        
        return await self._index_known_routes(system_name, config["url"])
    
    async def _index_nextjs_routes(self, base_url: str) -> int:
        """Index Next.js API routes (known routes)."""
        routes = [
            ("/api/agents", "GET", "Agent management API"),
            ("/api/agents", "POST", "Create agent"),
            ("/api/topology", "GET", "Get agent topology"),
            ("/api/memory", "GET", "Memory API gateway"),
            ("/api/memory", "POST", "Memory write proxy"),
            ("/api/voice/tts", "POST", "Text-to-speech"),
            ("/api/voice/stt", "POST", "Speech-to-text"),
            ("/api/voice/session", "POST", "Voice session"),
            ("/api/natureos/devices", "GET", "List NatureOS devices"),
            ("/api/natureos/telemetry", "POST", "Device telemetry"),
            ("/api/scientific/experiments", "GET", "List experiments"),
            ("/api/scientific/experiments", "POST", "Create experiment"),
            ("/api/bio/sensors", "GET", "Biosensor data"),
        ]
        
        api_count = 0
        for path, method, description in routes:
            api = APIInfo(
                path=path,
                method=method,
                description=description,
                tags=["website", "nextjs"],
                metadata={"indexed_from": "manual", "framework": "nextjs"}
            )
            await self._registry.register_api(api, "Website")
            api_count += 1
        
        return api_count
    
    async def discover_live_endpoints(self, system_name: str) -> List[str]:
        """Probe common endpoints to discover live APIs."""
        config = SYSTEM_CONFIGS.get(system_name)
        if not config:
            return []
        
        base_url = config["url"]
        client = await self._get_client()
        
        common_paths = [
            "/health", "/api/health", "/status",
            "/api", "/api/v1", "/api/v2",
            "/docs", "/redoc", "/openapi.json", "/swagger.json"
        ]
        
        live_endpoints = []
        for path in common_paths:
            try:
                url = urljoin(base_url, path)
                response = await client.get(url, timeout=5.0)
                if response.status_code < 500:
                    live_endpoints.append(path)
            except Exception:
                pass
        
        return live_endpoints


# Singleton
_indexer: Optional[APIIndexer] = None


def get_api_indexer() -> APIIndexer:
    """Get singleton indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = APIIndexer()
    return _indexer


async def index_all_apis() -> Dict[str, Any]:
    """Convenience function to index all APIs."""
    indexer = get_api_indexer()
    return await indexer.index_all_systems()
