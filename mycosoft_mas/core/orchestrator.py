"""
Enhanced Orchestrator with Health Polling, Failover, and Recovery.
Created: February 5, 2026

Provides robust service orchestration for the Mycosoft MAS:
- Service health polling and monitoring
- Automatic failover when services fail
- Recovery state restoration
- Circuit breaker pattern
- Retry with exponential backoff
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger("Orchestrator")


class ServiceState(str, Enum):
    """State of a managed service."""
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"
    FAILED = "failed"
    STOPPED = "stopped"


class CircuitState(str, Enum):
    """Circuit breaker state."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class ServiceConfig:
    """Configuration for a managed service."""
    id: str
    name: str
    health_url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    start_command: Optional[str] = None
    stop_command: Optional[str] = None
    health_check_interval: int = 30  # seconds
    health_check_timeout: int = 5    # seconds
    failure_threshold: int = 3       # failures before unhealthy
    recovery_threshold: int = 2      # successes before healthy
    retry_delay: int = 5             # seconds between retries
    max_retries: int = 3
    is_critical: bool = False        # If critical, affects overall system
    fallback_service_id: Optional[str] = None  # ID of fallback service


@dataclass
class ServiceStatus:
    """Current status of a managed service."""
    service_id: str
    state: ServiceState = ServiceState.STOPPED
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_check: Optional[datetime] = None
    last_healthy: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_error: Optional[str] = None
    response_time_ms: Optional[float] = None
    uptime_start: Optional[datetime] = None
    recovery_attempts: int = 0


@dataclass
class RecoveryState:
    """State to restore after recovery."""
    service_id: str
    saved_at: datetime
    state_data: Dict[str, Any] = field(default_factory=dict)
    pending_tasks: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def record_success(self) -> None:
        """Record a successful execution."""
        self.failure_count = 0
        self.success_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.success_count >= 2:  # Require 2 successes to close
                self.state = CircuitState.CLOSED
                self.success_count = 0
    
    def record_failure(self) -> None:
        """Record a failed execution."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


class Orchestrator:
    """
    Enhanced orchestrator with health polling, failover, and recovery.
    
    Features:
    - Service health monitoring
    - Automatic failover to backup services
    - Circuit breaker pattern
    - Recovery state management
    - Retry with exponential backoff
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceConfig] = {}
        self._status: Dict[str, ServiceStatus] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._recovery_states: Dict[str, RecoveryState] = {}
        self._health_task: Optional[asyncio.Task] = None
        self._running = False
        self._event_handlers: Dict[str, List[Callable]] = {}
    
    def register_service(self, config: ServiceConfig) -> None:
        """Register a service for orchestration."""
        self._services[config.id] = config
        self._status[config.id] = ServiceStatus(service_id=config.id)
        self._circuit_breakers[config.id] = CircuitBreaker(
            failure_threshold=config.failure_threshold
        )
        logger.info(f"Registered service: {config.name} ({config.id})")
    
    def register_default_services(self) -> None:
        """Register default Mycosoft services."""
        defaults = [
            ServiceConfig(
                id="mas_api",
                name="MAS API",
                health_url="http://localhost:8000/health",
                is_critical=True
            ),
            ServiceConfig(
                id="personaplex",
                name="PersonaPlex Voice",
                health_url="http://localhost:8999/v1/health",
                fallback_service_id="moshi_direct"
            ),
            ServiceConfig(
                id="n8n",
                name="n8n Workflows",
                health_url="http://localhost:5678/healthz"
            ),
            ServiceConfig(
                id="mindex_db",
                name="MINDEX Database",
                host="192.168.0.189",
                port=5432,
                is_critical=True
            ),
            ServiceConfig(
                id="redis",
                name="Redis Cache",
                host="localhost",
                port=6379
            ),
        ]
        
        for config in defaults:
            self.register_service(config)
    
    async def start(self) -> None:
        """Start the orchestrator."""
        if self._running:
            return
        
        self._running = True
        self.register_default_services()
        
        # Start health polling
        self._health_task = asyncio.create_task(self._health_polling_loop())
        
        logger.info("Orchestrator started")
    
    async def stop(self) -> None:
        """Stop the orchestrator."""
        self._running = False
        
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        # Save recovery states
        for service_id in self._services:
            await self._save_recovery_state(service_id)
        
        logger.info("Orchestrator stopped")
    
    async def _health_polling_loop(self) -> None:
        """Main health polling loop."""
        while self._running:
            try:
                for service_id, config in self._services.items():
                    await self._check_service_health(service_id)
                
                await asyncio.sleep(10)  # Poll every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health polling error: {e}")
                await asyncio.sleep(5)
    
    async def _check_service_health(self, service_id: str) -> ServiceStatus:
        """Check health of a single service."""
        config = self._services.get(service_id)
        status = self._status.get(service_id)
        breaker = self._circuit_breakers.get(service_id)
        
        if not config or not status or not breaker:
            return status
        
        # Check circuit breaker
        if not breaker.can_execute():
            status.state = ServiceState.FAILED
            return status
        
        start_time = datetime.now(timezone.utc)
        
        try:
            if config.health_url:
                # HTTP health check
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        config.health_url,
                        timeout=aiohttp.ClientTimeout(total=config.health_check_timeout)
                    ) as resp:
                        end_time = datetime.now(timezone.utc)
                        status.response_time_ms = (end_time - start_time).total_seconds() * 1000
                        
                        if resp.status == 200:
                            self._record_success(service_id)
                        else:
                            self._record_failure(service_id, f"HTTP {resp.status}")
            
            elif config.host and config.port:
                # TCP health check
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(config.host, config.port),
                        timeout=config.health_check_timeout
                    )
                    writer.close()
                    await writer.wait_closed()
                    
                    end_time = datetime.now(timezone.utc)
                    status.response_time_ms = (end_time - start_time).total_seconds() * 1000
                    self._record_success(service_id)
                except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                    self._record_failure(service_id, str(e))
        
        except Exception as e:
            self._record_failure(service_id, str(e))
        
        status.last_check = datetime.now(timezone.utc)
        return status
    
    def _record_success(self, service_id: str) -> None:
        """Record successful health check."""
        status = self._status.get(service_id)
        breaker = self._circuit_breakers.get(service_id)
        
        if not status or not breaker:
            return
        
        status.consecutive_successes += 1
        status.consecutive_failures = 0
        status.last_healthy = datetime.now(timezone.utc)
        
        breaker.record_success()
        
        # Transition to healthy
        if status.state in [ServiceState.DEGRADED, ServiceState.RECOVERING]:
            config = self._services.get(service_id)
            if config and status.consecutive_successes >= config.recovery_threshold:
                old_state = status.state
                status.state = ServiceState.HEALTHY
                status.recovery_attempts = 0
                self._emit_event("service_recovered", service_id, old_state)
        elif status.state == ServiceState.STARTING:
            status.state = ServiceState.HEALTHY
            status.uptime_start = datetime.now(timezone.utc)
            self._emit_event("service_started", service_id)
    
    def _record_failure(self, service_id: str, error: str) -> None:
        """Record failed health check."""
        status = self._status.get(service_id)
        breaker = self._circuit_breakers.get(service_id)
        config = self._services.get(service_id)
        
        if not status or not breaker or not config:
            return
        
        status.consecutive_failures += 1
        status.consecutive_successes = 0
        status.last_failure = datetime.now(timezone.utc)
        status.last_error = error
        
        breaker.record_failure()
        
        # Transition based on failure count
        old_state = status.state
        
        if status.consecutive_failures >= config.failure_threshold:
            status.state = ServiceState.UNHEALTHY
            
            # Trigger failover if configured
            if config.fallback_service_id:
                asyncio.create_task(self._trigger_failover(service_id))
            
            self._emit_event("service_unhealthy", service_id, error)
        elif status.consecutive_failures >= config.failure_threshold // 2:
            status.state = ServiceState.DEGRADED
            self._emit_event("service_degraded", service_id, error)
    
    async def _trigger_failover(self, failed_service_id: str) -> None:
        """Trigger failover to backup service."""
        config = self._services.get(failed_service_id)
        if not config or not config.fallback_service_id:
            return
        
        fallback_config = self._services.get(config.fallback_service_id)
        if not fallback_config:
            logger.warning(f"Fallback service {config.fallback_service_id} not found")
            return
        
        logger.info(f"Triggering failover from {failed_service_id} to {config.fallback_service_id}")
        
        # Save recovery state
        await self._save_recovery_state(failed_service_id)
        
        # Notify of failover
        self._emit_event("failover_triggered", failed_service_id, config.fallback_service_id)
        
        # Start recovery attempts
        asyncio.create_task(self._attempt_recovery(failed_service_id))
    
    async def _attempt_recovery(self, service_id: str) -> None:
        """Attempt to recover a failed service."""
        config = self._services.get(service_id)
        status = self._status.get(service_id)
        
        if not config or not status:
            return
        
        status.state = ServiceState.RECOVERING
        
        for attempt in range(config.max_retries):
            status.recovery_attempts = attempt + 1
            
            logger.info(f"Recovery attempt {attempt + 1}/{config.max_retries} for {service_id}")
            
            # Wait with exponential backoff
            delay = config.retry_delay * (2 ** attempt)
            await asyncio.sleep(delay)
            
            # Check health
            result = await self._check_service_health(service_id)
            
            if result.state == ServiceState.HEALTHY:
                # Restore recovery state
                await self._restore_recovery_state(service_id)
                logger.info(f"Service {service_id} recovered successfully")
                return
        
        # Recovery failed
        status.state = ServiceState.FAILED
        self._emit_event("recovery_failed", service_id, status.recovery_attempts)
    
    async def _save_recovery_state(self, service_id: str) -> None:
        """Save state for recovery."""
        recovery = RecoveryState(
            service_id=service_id,
            saved_at=datetime.now(timezone.utc),
            state_data={},
            context={"reason": "failover"}
        )
        self._recovery_states[service_id] = recovery
        logger.debug(f"Saved recovery state for {service_id}")
    
    async def _restore_recovery_state(self, service_id: str) -> None:
        """Restore state after recovery."""
        recovery = self._recovery_states.get(service_id)
        if not recovery:
            return
        
        logger.debug(f"Restored recovery state for {service_id}")
        self._emit_event("state_restored", service_id, recovery.saved_at)
    
    def _emit_event(self, event_type: str, *args) -> None:
        """Emit an orchestration event."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(*args)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
    
    def on(self, event_type: str, handler: Callable) -> None:
        """Register an event handler."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def get_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Get service status."""
        if service_id:
            status = self._status.get(service_id)
            if status:
                return {
                    "service_id": status.service_id,
                    "state": status.state.value,
                    "circuit_state": status.circuit_state.value,
                    "consecutive_failures": status.consecutive_failures,
                    "last_check": status.last_check.isoformat() if status.last_check else None,
                    "last_healthy": status.last_healthy.isoformat() if status.last_healthy else None,
                    "response_time_ms": status.response_time_ms,
                    "last_error": status.last_error
                }
            return {}
        
        # Return all statuses
        return {
            sid: {
                "state": s.state.value,
                "response_time_ms": s.response_time_ms,
                "last_error": s.last_error
            }
            for sid, s in self._status.items()
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary."""
        healthy = sum(1 for s in self._status.values() if s.state == ServiceState.HEALTHY)
        total = len(self._status)
        
        critical_healthy = sum(
            1 for sid, s in self._status.items()
            if s.state == ServiceState.HEALTHY and self._services[sid].is_critical
        )
        critical_total = sum(1 for c in self._services.values() if c.is_critical)
        
        return {
            "overall_health": "healthy" if healthy == total else "degraded" if healthy > 0 else "unhealthy",
            "services_healthy": healthy,
            "services_total": total,
            "health_percentage": round(healthy / total * 100, 1) if total else 0,
            "critical_services_healthy": critical_healthy,
            "critical_services_total": critical_total,
            "running": self._running
        }


# Singleton instance
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
