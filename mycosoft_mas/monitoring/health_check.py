"""
Health Check Module - February 6, 2026

Health and readiness checks.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Optional[Dict] = None


class HealthChecker:
    """
    Performs health checks on system components.
    """
    
    def __init__(self):
        self.checks: List[ComponentHealth] = []
        self._db_pool = None
        self._redis = None
    
    async def check_database(self) -> ComponentHealth:
        """Check PostgreSQL connection."""
        import time
        start = time.time()
        
        try:
            import asyncpg
            
            conn_str = os.getenv(
                "DATABASE_URL",
                os.getenv("MINDEX_DATABASE_URL", "postgresql://mindex:mindex@localhost:5432/mindex")
            )
            
            conn = await asyncpg.connect(conn_str, timeout=5)
            await conn.fetchval("SELECT 1")
            await conn.close()
            
            latency = (time.time() - start) * 1000
            
            return ComponentHealth(
                name="postgresql",
                status=HealthStatus.HEALTHY,
                latency_ms=latency
            )
            
        except Exception as e:
            return ComponentHealth(
                name="postgresql",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    
    async def check_redis(self) -> ComponentHealth:
        """Check Redis connection."""
        import time
        start = time.time()
        
        try:
            import redis.asyncio as redis
            
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            r = redis.from_url(redis_url)
            await r.ping()
            await r.close()
            
            latency = (time.time() - start) * 1000
            
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=latency
            )
            
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,  # Redis is optional
                message=str(e)
            )
    
    async def check_collectors(self) -> ComponentHealth:
        """Check collector status."""
        try:
            from mycosoft_mas.collectors import get_orchestrator
            
            orch = get_orchestrator()
            status = orch.get_status()
            
            if not status["running"]:
                return ComponentHealth(
                    name="collectors",
                    status=HealthStatus.DEGRADED,
                    message="Collectors not running"
                )
            
            # Check for failures
            failed = sum(
                1 for c in status["collectors"].values()
                if c["status"] == "error"
            )
            
            if failed > 0:
                return ComponentHealth(
                    name="collectors",
                    status=HealthStatus.DEGRADED,
                    message=f"{failed} collectors in error state",
                    details=status["collectors"]
                )
            
            return ComponentHealth(
                name="collectors",
                status=HealthStatus.HEALTHY,
                details={"count": len(status["collectors"])}
            )
            
        except Exception as e:
            return ComponentHealth(
                name="collectors",
                status=HealthStatus.DEGRADED,
                message=str(e)
            )
    
    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks."""
        checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_collectors(),
            return_exceptions=True
        )
        
        results = []
        for check in checks:
            if isinstance(check, Exception):
                results.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(check)
                ))
            else:
                results.append(check)
        
        # Overall status
        if any(c.status == HealthStatus.UNHEALTHY for c in results):
            overall = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in results):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        
        return {
            "status": overall.value,
            "timestamp": datetime.utcnow().isoformat(),
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                    "details": c.details,
                }
                for c in results
            ]
        }
    
    async def liveness(self) -> Dict[str, Any]:
        """Simple liveness check."""
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def readiness(self) -> Dict[str, Any]:
        """Readiness check - is service ready to accept traffic."""
        db_check = await self.check_database()
        
        return {
            "ready": db_check.status != HealthStatus.UNHEALTHY,
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_check.status.value
        }


# Global checker
_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    global _checker
    if _checker is None:
        _checker = HealthChecker()
    return _checker