"""
Ingestion Orchestrator - February 6, 2026

Manages and coordinates all data collectors.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .base_collector import BaseCollector, CollectorStatus

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Blocking calls
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_requests: int = 3


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_successes = 0
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                self.half_open_successes = 0
            else:
                raise CircuitOpenError(f"Circuit {self.name} is open")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_recovery(self) -> bool:
        if self.last_failure_time is None:
            return True
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout
    
    def _on_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.config.half_open_requests:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit {self.name} closed (recovered)")
        else:
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} reopened")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} opened after {self.failure_count} failures")


class CircuitOpenError(Exception):
    pass


@dataclass
class AuditLogEntry:
    timestamp: datetime
    collector: str
    action: str
    details: Dict[str, Any]
    success: bool


class AuditLogger:
    """Logs all collector actions for audit trail."""
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.entries: List[AuditLogEntry] = []
    
    def log(
        self,
        collector: str,
        action: str,
        details: Dict[str, Any],
        success: bool = True
    ) -> None:
        entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            collector=collector,
            action=action,
            details=details,
            success=success
        )
        
        self.entries.append(entry)
        
        # Trim if too long
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
    
    def get_entries(
        self,
        collector: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        entries = self.entries
        
        if collector:
            entries = [e for e in entries if e.collector == collector]
        
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "collector": e.collector,
                "action": e.action,
                "details": e.details,
                "success": e.success,
            }
            for e in entries[-limit:]
        ]


class IngestionOrchestrator:
    """
    Orchestrates all data collectors.
    """
    
    def __init__(self):
        self.collectors: Dict[str, BaseCollector] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.audit_logger = AuditLogger()
        self._running = False
    
    def register(self, collector: BaseCollector) -> None:
        """Register a collector."""
        self.collectors[collector.name] = collector
        self.circuit_breakers[collector.name] = CircuitBreaker(collector.name)
        logger.info(f"Registered collector: {collector.name}")
    
    async def start(self) -> None:
        """Start all registered collectors."""
        self._running = True
        
        for name, collector in self.collectors.items():
            await collector.initialize()
            task = asyncio.create_task(self._run_collector(name))
            self.tasks[name] = task
            logger.info(f"Started collector: {name}")
        
        self.audit_logger.log("orchestrator", "start", {"collectors": list(self.collectors.keys())})
    
    async def stop(self) -> None:
        """Stop all collectors."""
        self._running = False
        
        for name, collector in self.collectors.items():
            collector.stop()
        
        # Wait for all tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        
        # Cleanup
        for collector in self.collectors.values():
            await collector.cleanup()
        
        self.tasks.clear()
        self.audit_logger.log("orchestrator", "stop", {})
        logger.info("All collectors stopped")
    
    async def _run_collector(self, name: str) -> None:
        """Run a collector with circuit breaker protection."""
        collector = self.collectors[name]
        breaker = self.circuit_breakers[name]
        
        while self._running and not collector._stop_event.is_set():
            try:
                events = await breaker.call(collector.run_once)
                
                self.audit_logger.log(
                    name,
                    "fetch",
                    {"events": len(events)},
                    success=True
                )
                
            except CircuitOpenError:
                await asyncio.sleep(10)
                continue
                
            except Exception as e:
                self.audit_logger.log(
                    name,
                    "fetch",
                    {"error": str(e)},
                    success=False
                )
            
            # Wait for next poll
            try:
                await asyncio.wait_for(
                    collector._stop_event.wait(),
                    timeout=collector.poll_interval_seconds
                )
            except asyncio.TimeoutError:
                pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all collectors."""
        return {
            "running": self._running,
            "collectors": {
                name: {
                    **collector.get_status(),
                    "circuit_state": self.circuit_breakers[name].state.value,
                }
                for name, collector in self.collectors.items()
            }
        }
    
    async def trigger_fetch(self, collector_name: str) -> Dict[str, Any]:
        """Trigger immediate fetch for a collector."""
        if collector_name not in self.collectors:
            return {"error": f"Unknown collector: {collector_name}"}
        
        collector = self.collectors[collector_name]
        
        try:
            events = await collector.run_once()
            self.audit_logger.log(
                collector_name,
                "manual_fetch",
                {"events": len(events)},
                success=True
            )
            return {"success": True, "events": len(events)}
        except Exception as e:
            self.audit_logger.log(
                collector_name,
                "manual_fetch",
                {"error": str(e)},
                success=False
            )
            return {"success": False, "error": str(e)}
    
    def get_audit_log(
        self,
        collector: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get audit log entries."""
        return self.audit_logger.get_entries(collector, since, limit)


# Global orchestrator
_orchestrator: Optional[IngestionOrchestrator] = None


def get_orchestrator() -> IngestionOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = IngestionOrchestrator()
    return _orchestrator


async def start_default_collectors() -> None:
    """Start orchestrator with default collectors."""
    from .opensky_collector import OpenSkyCollector
    from .usgs_collector import USGSCollector
    from .norad_collector import NORADCollector
    from .ais_collector import AISCollector
    from .noaa_collector import NOAACollector
    
    orch = get_orchestrator()
    
    orch.register(OpenSkyCollector())
    orch.register(USGSCollector())
    orch.register(NORADCollector())
    orch.register(AISCollector())
    orch.register(NOAACollector())
    
    await orch.start()
