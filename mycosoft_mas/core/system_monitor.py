"""
System Monitor for MYCA Awareness.
Created: February 5, 2026

Provides comprehensive monitoring for MYCA to track:
- All systems (MAS, Website, MINDEX, PersonaPlex, n8n, etc.)
- APIs (health, latency, error rates)
- Agents (status, workload, errors)
- Containers (Docker status, resource usage)
- Health metrics (uptime, response times, error rates)

Enables MYCA to understand the current state of the entire Mycosoft ecosystem.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger("SystemMonitor")


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    OFFLINE = "offline"


class ComponentType(str, Enum):
    """Types of monitored components."""
    SYSTEM = "system"
    API = "api"
    AGENT = "agent"
    CONTAINER = "container"
    SERVICE = "service"
    DATABASE = "database"
    DEVICE = "device"


@dataclass
class HealthCheck:
    """Result of a health check."""
    component_id: str
    component_type: ComponentType
    status: HealthStatus
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """Metrics for a monitored system."""
    system_id: str
    uptime_seconds: Optional[float] = None
    request_count: int = 0
    error_count: int = 0
    avg_response_time_ms: float = 0.0
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MonitoredComponent:
    """A component being monitored."""
    id: str
    name: str
    component_type: ComponentType
    url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    health_endpoint: Optional[str] = None
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: Optional[HealthCheck] = None
    metrics: Optional[SystemMetrics] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SystemMonitor:
    """
    Comprehensive system monitoring for MYCA.
    
    Provides:
    - Health checking for all registered systems
    - Metric collection and aggregation
    - Status dashboard data
    - Alert generation for issues
    - Historical health tracking
    """
    
    # Default monitored systems
    DEFAULT_SYSTEMS = [
        {"id": "mas", "name": "MAS", "type": "system", "url": "http://localhost:8000", "health": "/health"},
        {"id": "website", "name": "Website", "type": "system", "url": "http://192.168.0.187:3000", "health": "/api/health"},
        {"id": "mindex", "name": "MINDEX", "type": "database", "host": "192.168.0.189", "port": 5432},
        {"id": "personaplex", "name": "PersonaPlex", "type": "service", "url": "http://localhost:8999", "health": "/v1/health"},
        {"id": "n8n", "name": "n8n", "type": "service", "url": "http://localhost:5678", "health": "/healthz"},
        {"id": "grafana", "name": "Grafana", "type": "service", "url": "http://localhost:3001", "health": "/api/health"},
        {"id": "prometheus", "name": "Prometheus", "type": "service", "url": "http://localhost:9090", "health": "/-/healthy"},
        {"id": "redis", "name": "Redis", "type": "database", "host": "localhost", "port": 6379},
    ]
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
            "MINDEX_DATABASE_URL",
            "postgresql://mycosoft:Mushroom1!Mushroom1!@192.168.0.189:5432/mindex"
        )
        self._pool = None
        self._components: Dict[str, MonitoredComponent] = {}
        self._health_history: List[HealthCheck] = []
        self._initialized = False
        self._check_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize the monitor."""
        if self._initialized:
            return
        
        # Register default systems
        for sys in self.DEFAULT_SYSTEMS:
            component = MonitoredComponent(
                id=sys["id"],
                name=sys["name"],
                component_type=ComponentType(sys["type"]),
                url=sys.get("url"),
                host=sys.get("host"),
                port=sys.get("port"),
                health_endpoint=sys.get("health")
            )
            self._components[sys["id"]] = component
        
        # Load from registry
        await self._load_from_registry()
        
        # Connect to database
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=3
            )
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
        
        self._initialized = True
        logger.info(f"System monitor initialized with {len(self._components)} components")
    
    async def _load_from_registry(self) -> None:
        """Load additional systems from registry."""
        try:
            import asyncpg
            pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=2
            )
            
            async with pool.acquire() as conn:
                # Load systems
                rows = await conn.fetch("SELECT * FROM registry.systems")
                for row in rows:
                    component = MonitoredComponent(
                        id=row["name"].lower().replace(" ", "_"),
                        name=row["name"],
                        component_type=ComponentType.SYSTEM,
                        url=row.get("url"),
                        metadata={"registry": "systems"}
                    )
                    if component.id not in self._components:
                        self._components[component.id] = component
                
                # Load from agents (just count for now)
                agent_count = await conn.fetchval("SELECT COUNT(*) FROM registry.agents")
                logger.info(f"Registry contains {agent_count} agents")
                
                # Load from devices
                device_count = await conn.fetchval("SELECT COUNT(*) FROM registry.devices")
                logger.info(f"Registry contains {device_count} devices")
            
            await pool.close()
        except Exception as e:
            logger.warning(f"Failed to load from registry: {e}")
    
    async def check_health(self, component_id: str) -> Optional[HealthCheck]:
        """Check health of a specific component."""
        component = self._components.get(component_id)
        if not component:
            return None
        
        check = HealthCheck(
            component_id=component_id,
            component_type=component.component_type
        )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            if component.url and component.health_endpoint:
                # HTTP health check
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    url = f"{component.url}{component.health_endpoint}"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        end_time = datetime.now(timezone.utc)
                        check.response_time_ms = (end_time - start_time).total_seconds() * 1000
                        
                        if resp.status == 200:
                            check.status = HealthStatus.HEALTHY
                            try:
                                check.details = await resp.json()
                            except:
                                check.details = {"body": await resp.text()}
                        elif resp.status < 500:
                            check.status = HealthStatus.DEGRADED
                        else:
                            check.status = HealthStatus.UNHEALTHY
                            check.error_message = f"HTTP {resp.status}"
            
            elif component.host and component.port:
                # TCP port check
                import asyncio
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(component.host, component.port),
                        timeout=5.0
                    )
                    writer.close()
                    await writer.wait_closed()
                    
                    end_time = datetime.now(timezone.utc)
                    check.response_time_ms = (end_time - start_time).total_seconds() * 1000
                    check.status = HealthStatus.HEALTHY
                except asyncio.TimeoutError:
                    check.status = HealthStatus.UNHEALTHY
                    check.error_message = "Connection timeout"
                except ConnectionRefusedError:
                    check.status = HealthStatus.OFFLINE
                    check.error_message = "Connection refused"
            
            else:
                check.status = HealthStatus.UNKNOWN
                check.error_message = "No health check configured"
        
        except Exception as e:
            check.status = HealthStatus.UNHEALTHY
            check.error_message = str(e)
        
        # Update component status
        component.status = check.status
        component.last_check = check
        
        # Store in history
        self._health_history.append(check)
        if len(self._health_history) > 1000:
            self._health_history = self._health_history[-500:]
        
        return check
    
    async def check_all(self) -> Dict[str, HealthCheck]:
        """Check health of all components."""
        await self.initialize()
        
        results = {}
        
        # Check in parallel
        tasks = []
        for component_id in self._components:
            tasks.append(self.check_health(component_id))
        
        checks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for check in checks:
            if isinstance(check, HealthCheck):
                results[check.component_id] = check
        
        return results
    
    async def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard data for MYCA."""
        await self.initialize()
        
        # Run health checks
        checks = await self.check_all()
        
        # Aggregate stats
        healthy = sum(1 for c in checks.values() if c.status == HealthStatus.HEALTHY)
        degraded = sum(1 for c in checks.values() if c.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for c in checks.values() if c.status == HealthStatus.UNHEALTHY)
        offline = sum(1 for c in checks.values() if c.status == HealthStatus.OFFLINE)
        unknown = sum(1 for c in checks.values() if c.status == HealthStatus.UNKNOWN)
        
        # Response time stats
        response_times = [c.response_time_ms for c in checks.values() if c.response_time_ms]
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_components": len(checks),
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
                "offline": offline,
                "unknown": unknown,
                "health_percentage": round(healthy / len(checks) * 100, 1) if checks else 0
            },
            "performance": {
                "avg_response_time_ms": round(avg_response, 2),
                "max_response_time_ms": round(max(response_times), 2) if response_times else 0,
                "min_response_time_ms": round(min(response_times), 2) if response_times else 0
            },
            "components": {
                cid: {
                    "name": self._components[cid].name,
                    "type": self._components[cid].component_type.value,
                    "status": check.status.value,
                    "response_time_ms": check.response_time_ms,
                    "error": check.error_message
                }
                for cid, check in checks.items()
            },
            "issues": [
                {
                    "component": cid,
                    "name": self._components[cid].name,
                    "status": check.status.value,
                    "error": check.error_message
                }
                for cid, check in checks.items()
                if check.status in [HealthStatus.UNHEALTHY, HealthStatus.OFFLINE]
            ]
        }
    
    async def get_component_history(
        self,
        component_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get health history for a component."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        history = [
            {
                "status": h.status.value,
                "response_time_ms": h.response_time_ms,
                "checked_at": h.checked_at.isoformat(),
                "error": h.error_message
            }
            for h in self._health_history
            if h.component_id == component_id and h.checked_at >= cutoff
        ]
        
        return history
    
    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start continuous health monitoring."""
        await self.initialize()
        
        async def monitor_loop():
            while True:
                try:
                    await self.check_all()
                    logger.debug("Health check cycle complete")
                except Exception as e:
                    logger.error(f"Health check failed: {e}")
                
                await asyncio.sleep(interval_seconds)
        
        self._check_task = asyncio.create_task(monitor_loop())
        logger.info(f"Started continuous monitoring (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
            self._check_task = None
    
    def register_component(
        self,
        component_id: str,
        name: str,
        component_type: ComponentType,
        url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        health_endpoint: Optional[str] = None
    ) -> MonitoredComponent:
        """Register a new component for monitoring."""
        component = MonitoredComponent(
            id=component_id,
            name=name,
            component_type=component_type,
            url=url,
            host=host,
            port=port,
            health_endpoint=health_endpoint
        )
        self._components[component_id] = component
        return component
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return {
            "components_count": len(self._components),
            "history_entries": len(self._health_history),
            "monitoring_active": self._check_task is not None,
            "database_connected": self._pool is not None,
            "initialized": self._initialized
        }


# Singleton instance
_system_monitor: Optional[SystemMonitor] = None


async def get_system_monitor() -> SystemMonitor:
    """Get or create the singleton system monitor instance."""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
        await _system_monitor.initialize()
    return _system_monitor
