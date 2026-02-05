"""
System Registry Service - February 4, 2026

PostgreSQL-backed registry for tracking all systems, APIs, agents,
services, devices, and integrations across the Mycosoft ecosystem.

Provides:
- System registration and discovery
- API endpoint catalog
- Agent and service tracking
- Device management
- Integration mapping
"""

import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger("SystemRegistry")


# ============================================================================
# Models
# ============================================================================

class SystemType(str, Enum):
    """Types of systems in the Mycosoft ecosystem."""
    # Core Systems
    MAS = "mas"
    WEBSITE = "website"
    NATUREOS = "natureos"
    MINDEX = "mindex"
    NLM = "nlm"
    MYCOBRAIN = "mycobrain"
    # Voice Systems
    PERSONAPLEX = "personaplex"
    MOSHI = "moshi"
    # Automation
    N8N = "n8n"
    # Infrastructure
    PROXMOX = "proxmox"
    # Monitoring
    GRAFANA = "grafana"
    PROMETHEUS = "prometheus"
    # Other
    REDIS = "redis"
    POSTGRES = "postgres"
    QDRANT = "qdrant"


class ServiceType(str, Enum):
    """Types of services."""
    API = "api"
    WORKER = "worker"
    SCHEDULER = "scheduler"
    GATEWAY = "gateway"
    DATABASE = "database"


class DeviceType(str, Enum):
    """Types of MycoBrain devices."""
    SPOREBASE = "sporebase"
    MUSHROOM1 = "mushroom1"
    NFC_TAG = "nfc"
    SENSOR = "sensor"
    GATEWAY = "gateway"


class SystemInfo(BaseModel):
    """Information about a system."""
    id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    type: SystemType
    url: Optional[str] = None
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class APIInfo(BaseModel):
    """Information about an API endpoint."""
    id: Optional[UUID] = None
    system_id: Optional[UUID] = None
    path: str
    method: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    auth_required: bool = False
    deprecated: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentInfo(BaseModel):
    """Information about an AI agent."""
    id: Optional[UUID] = None
    name: str
    type: str
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    status: str = "active"
    version: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ServiceInfo(BaseModel):
    """Information about a service."""
    id: Optional[UUID] = None
    name: str
    type: ServiceType
    description: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    status: str = "unknown"
    health_endpoint: Optional[str] = None
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeviceInfo(BaseModel):
    """Information about a MycoBrain device."""
    id: Optional[UUID] = None
    device_id: str
    name: str
    type: DeviceType
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    status: str = "unknown"
    last_seen: Optional[datetime] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    telemetry: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CodeFileInfo(BaseModel):
    """Information about a source code file."""
    id: Optional[UUID] = None
    repository: str
    file_path: str
    file_type: str
    file_hash: Optional[str] = None
    line_count: Optional[int] = None
    exports: List[str] = Field(default_factory=list)
    imports: List[str] = Field(default_factory=list)
    classes: List[str] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    indexed_at: Optional[datetime] = None


# ============================================================================
# System Registry Service
# ============================================================================

class SystemRegistry:
    """
    PostgreSQL-backed system registry for tracking all Mycosoft components.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://mycosoft:mycosoft@postgres:5432/mycosoft"
        )
        self._pool = None
        self._initialized = False
        self._cache: Dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize database connection pool."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=2,
                max_size=10
            )
            self._initialized = True
            logger.info("System registry initialized")
        except Exception as e:
            logger.error(f"Failed to initialize registry: {e}")
            raise
    
    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._initialized = False
    
    # -------------------------------------------------------------------------
    # Systems
    # -------------------------------------------------------------------------
    
    async def register_system(self, system: SystemInfo) -> SystemInfo:
        """Register or update a system."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            if system.id:
                # Update existing
                await conn.execute("""
                    UPDATE registry.systems
                    SET description = $2, type = $3, url = $4, status = $5, 
                        metadata = $6, updated_at = NOW()
                    WHERE id = $1
                """, system.id, system.description, system.type.value,
                    system.url, system.status, str(system.metadata))
            else:
                # Insert new
                import json
                row = await conn.fetchrow("""
                    INSERT INTO registry.systems (name, description, type, url, status, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                    ON CONFLICT (name) DO UPDATE SET
                        description = EXCLUDED.description,
                        url = EXCLUDED.url,
                        status = EXCLUDED.status,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    RETURNING id, created_at, updated_at
                """, system.name, system.description, system.type.value,
                    system.url, system.status, json.dumps(system.metadata))
                
                system.id = row["id"]
                system.created_at = row["created_at"]
                system.updated_at = row["updated_at"]
        
        return system
    
    async def get_system(self, name: str) -> Optional[SystemInfo]:
        """Get a system by name."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, name, description, type, url, status, 
                       metadata, created_at, updated_at
                FROM registry.systems WHERE name = $1
            """, name)
            
            if row:
                import json
                return SystemInfo(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    type=SystemType(row["type"]),
                    url=row["url"],
                    status=row["status"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
        return None
    
    async def list_systems(self, status: Optional[str] = None) -> List[SystemInfo]:
        """List all systems."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            if status:
                rows = await conn.fetch("""
                    SELECT id, name, description, type, url, status, 
                           metadata, created_at, updated_at
                    FROM registry.systems WHERE status = $1
                    ORDER BY name
                """, status)
            else:
                rows = await conn.fetch("""
                    SELECT id, name, description, type, url, status, 
                           metadata, created_at, updated_at
                    FROM registry.systems ORDER BY name
                """)
            
            import json
            return [
                SystemInfo(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    type=SystemType(row["type"]),
                    url=row["url"],
                    status=row["status"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in rows
            ]
    
    # -------------------------------------------------------------------------
    # APIs
    # -------------------------------------------------------------------------
    
    async def register_api(self, api: APIInfo, system_name: str) -> APIInfo:
        """Register an API endpoint."""
        await self.initialize()
        
        # Get system ID
        system = await self.get_system(system_name)
        if not system:
            raise ValueError(f"System not found: {system_name}")
        
        api.system_id = system.id
        
        async with self._pool.acquire() as conn:
            import json
            row = await conn.fetchrow("""
                INSERT INTO registry.apis 
                (system_id, path, method, description, tags, request_schema, 
                 response_schema, auth_required, deprecated, metadata)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, $9, $10::jsonb)
                ON CONFLICT (system_id, path, method) DO UPDATE SET
                    description = EXCLUDED.description,
                    tags = EXCLUDED.tags,
                    request_schema = EXCLUDED.request_schema,
                    response_schema = EXCLUDED.response_schema,
                    auth_required = EXCLUDED.auth_required,
                    deprecated = EXCLUDED.deprecated,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING id, created_at, updated_at
            """, system.id, api.path, api.method, api.description,
                api.tags, json.dumps(api.request_schema) if api.request_schema else None,
                json.dumps(api.response_schema) if api.response_schema else None,
                api.auth_required, api.deprecated, json.dumps(api.metadata))
            
            api.id = row["id"]
        
        return api
    
    async def list_apis(
        self,
        system_name: Optional[str] = None,
        tag: Optional[str] = None,
        include_deprecated: bool = False
    ) -> List[APIInfo]:
        """List APIs with optional filters."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            query = """
                SELECT a.id, a.system_id, a.path, a.method, a.description,
                       a.tags, a.request_schema, a.response_schema,
                       a.auth_required, a.deprecated, a.metadata,
                       s.name as system_name
                FROM registry.apis a
                JOIN registry.systems s ON a.system_id = s.id
                WHERE 1=1
            """
            params = []
            param_idx = 1
            
            if system_name:
                query += f" AND s.name = ${param_idx}"
                params.append(system_name)
                param_idx += 1
            
            if not include_deprecated:
                query += " AND a.deprecated = FALSE"
            
            query += " ORDER BY s.name, a.path, a.method"
            
            rows = await conn.fetch(query, *params)
            
            import json
            apis = []
            for row in rows:
                apis.append(APIInfo(
                    id=row["id"],
                    system_id=row["system_id"],
                    path=row["path"],
                    method=row["method"],
                    description=row["description"],
                    tags=row["tags"] or [],
                    request_schema=json.loads(row["request_schema"]) if row["request_schema"] else None,
                    response_schema=json.loads(row["response_schema"]) if row["response_schema"] else None,
                    auth_required=row["auth_required"],
                    deprecated=row["deprecated"],
                    metadata={**(json.loads(row["metadata"]) if row["metadata"] else {}), "system_name": row["system_name"]}
                ))
            
            return apis
    
    async def get_api_count(self) -> int:
        """Get total count of registered APIs."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM registry.apis WHERE deprecated = FALSE")
    
    # -------------------------------------------------------------------------
    # Agents
    # -------------------------------------------------------------------------
    
    async def register_agent(self, agent: AgentInfo) -> AgentInfo:
        """Register an AI agent."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            row = await conn.fetchrow("""
                INSERT INTO registry.agents 
                (name, type, description, capabilities, status, version, config, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb)
                ON CONFLICT (name) DO UPDATE SET
                    type = EXCLUDED.type,
                    description = EXCLUDED.description,
                    capabilities = EXCLUDED.capabilities,
                    status = EXCLUDED.status,
                    version = EXCLUDED.version,
                    config = EXCLUDED.config,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING id, created_at, updated_at
            """, agent.name, agent.type, agent.description,
                agent.capabilities, agent.status, agent.version,
                json.dumps(agent.config), json.dumps(agent.metadata))
            
            agent.id = row["id"]
        
        return agent
    
    async def list_agents(self, agent_type: Optional[str] = None) -> List[AgentInfo]:
        """List all agents."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            if agent_type:
                rows = await conn.fetch("""
                    SELECT id, name, type, description, capabilities, status,
                           version, config, metadata, created_at, updated_at
                    FROM registry.agents WHERE type = $1
                    ORDER BY name
                """, agent_type)
            else:
                rows = await conn.fetch("""
                    SELECT id, name, type, description, capabilities, status,
                           version, config, metadata, created_at, updated_at
                    FROM registry.agents ORDER BY name
                """)
            
            import json
            return [
                AgentInfo(
                    id=row["id"],
                    name=row["name"],
                    type=row["type"],
                    description=row["description"],
                    capabilities=row["capabilities"] or [],
                    status=row["status"],
                    version=row["version"],
                    config=json.loads(row["config"]) if row["config"] else {},
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                for row in rows
            ]
    
    # -------------------------------------------------------------------------
    # Services
    # -------------------------------------------------------------------------
    
    async def register_service(self, service: ServiceInfo) -> ServiceInfo:
        """Register a service."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            row = await conn.fetchrow("""
                INSERT INTO registry.services 
                (name, type, description, host, port, status, health_endpoint, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                ON CONFLICT (name) DO UPDATE SET
                    type = EXCLUDED.type,
                    description = EXCLUDED.description,
                    host = EXCLUDED.host,
                    port = EXCLUDED.port,
                    status = EXCLUDED.status,
                    health_endpoint = EXCLUDED.health_endpoint,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING id, created_at, updated_at
            """, service.name, service.type.value, service.description,
                service.host, service.port, service.status,
                service.health_endpoint, json.dumps(service.metadata))
            
            service.id = row["id"]
        
        return service
    
    async def update_service_health(self, name: str, status: str) -> None:
        """Update service health status."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            await conn.execute("""
                UPDATE registry.services
                SET status = $2, last_health_check = NOW()
                WHERE name = $1
            """, name, status)
    
    # -------------------------------------------------------------------------
    # Devices
    # -------------------------------------------------------------------------
    
    async def register_device(self, device: DeviceInfo) -> DeviceInfo:
        """Register a MycoBrain device."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            row = await conn.fetchrow("""
                INSERT INTO registry.devices 
                (device_id, name, type, firmware_version, hardware_version,
                 status, config, telemetry, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9::jsonb)
                ON CONFLICT (device_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    type = EXCLUDED.type,
                    firmware_version = EXCLUDED.firmware_version,
                    hardware_version = EXCLUDED.hardware_version,
                    status = EXCLUDED.status,
                    config = EXCLUDED.config,
                    telemetry = EXCLUDED.telemetry,
                    metadata = EXCLUDED.metadata,
                    last_seen = NOW(),
                    updated_at = NOW()
                RETURNING id, created_at, updated_at, last_seen
            """, device.device_id, device.name, device.type.value,
                device.firmware_version, device.hardware_version, device.status,
                json.dumps(device.config), json.dumps(device.telemetry),
                json.dumps(device.metadata))
            
            device.id = row["id"]
            device.last_seen = row["last_seen"]
        
        return device
    
    async def list_devices(self, device_type: Optional[str] = None) -> List[DeviceInfo]:
        """List all devices."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            if device_type:
                rows = await conn.fetch("""
                    SELECT id, device_id, name, type, firmware_version, hardware_version,
                           status, last_seen, config, telemetry, metadata
                    FROM registry.devices WHERE type = $1
                    ORDER BY name
                """, device_type)
            else:
                rows = await conn.fetch("""
                    SELECT id, device_id, name, type, firmware_version, hardware_version,
                           status, last_seen, config, telemetry, metadata
                    FROM registry.devices ORDER BY name
                """)
            
            import json
            return [
                DeviceInfo(
                    id=row["id"],
                    device_id=row["device_id"],
                    name=row["name"],
                    type=DeviceType(row["type"]),
                    firmware_version=row["firmware_version"],
                    hardware_version=row["hardware_version"],
                    status=row["status"],
                    last_seen=row["last_seen"],
                    config=json.loads(row["config"]) if row["config"] else {},
                    telemetry=json.loads(row["telemetry"]) if row["telemetry"] else {},
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                for row in rows
            ]
    
    # -------------------------------------------------------------------------
    # Code Files
    # -------------------------------------------------------------------------
    
    async def register_code_file(self, file_info: CodeFileInfo) -> CodeFileInfo:
        """Register a code file in the registry."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            row = await conn.fetchrow("""
                INSERT INTO registry.code_files 
                (repository, file_path, file_type, file_hash, line_count,
                 exports, imports, classes, functions, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
                ON CONFLICT (repository, file_path) DO UPDATE SET
                    file_type = EXCLUDED.file_type,
                    file_hash = EXCLUDED.file_hash,
                    line_count = EXCLUDED.line_count,
                    exports = EXCLUDED.exports,
                    imports = EXCLUDED.imports,
                    classes = EXCLUDED.classes,
                    functions = EXCLUDED.functions,
                    metadata = EXCLUDED.metadata,
                    indexed_at = NOW()
                RETURNING id, indexed_at
            """, file_info.repository, file_info.file_path, file_info.file_type,
                file_info.file_hash, file_info.line_count, file_info.exports,
                file_info.imports, file_info.classes, file_info.functions,
                json.dumps(file_info.metadata))
            
            file_info.id = row["id"]
            file_info.indexed_at = row["indexed_at"]
        
        return file_info
    
    async def get_code_stats(self) -> Dict[str, Any]:
        """Get code file statistics by repository."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT repository, file_type, 
                       COUNT(*) as file_count,
                       SUM(line_count) as total_lines
                FROM registry.code_files
                GROUP BY repository, file_type
                ORDER BY repository, file_count DESC
            """)
            
            stats = {}
            for row in rows:
                repo = row["repository"]
                if repo not in stats:
                    stats[repo] = {"files": {}, "total_files": 0, "total_lines": 0}
                
                stats[repo]["files"][row["file_type"]] = {
                    "count": row["file_count"],
                    "lines": row["total_lines"] or 0
                }
                stats[repo]["total_files"] += row["file_count"]
                stats[repo]["total_lines"] += row["total_lines"] or 0
            
            return stats
    
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    
    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get overall registry statistics."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            stats = {}
            
            stats["systems"] = await conn.fetchval("SELECT COUNT(*) FROM registry.systems")
            stats["apis"] = await conn.fetchval("SELECT COUNT(*) FROM registry.apis WHERE deprecated = FALSE")
            stats["agents"] = await conn.fetchval("SELECT COUNT(*) FROM registry.agents")
            stats["services"] = await conn.fetchval("SELECT COUNT(*) FROM registry.services")
            stats["devices"] = await conn.fetchval("SELECT COUNT(*) FROM registry.devices")
            stats["code_files"] = await conn.fetchval("SELECT COUNT(*) FROM registry.code_files")
            
            return stats


# Singleton instance
_registry: Optional[SystemRegistry] = None


def get_registry() -> SystemRegistry:
    """Get singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = SystemRegistry()
    return _registry
