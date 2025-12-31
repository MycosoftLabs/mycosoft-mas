"""
MycoBrain Telemetry Forwarder Agent

Forwards MycoBrain telemetry data to MINDEX and other systems.
Runs as a background agent in the MAS orchestrator.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus
from mycosoft_mas.integrations import UnifiedIntegrationManager

logger = logging.getLogger(__name__)


@dataclass
class TelemetryEvent:
    """Telemetry event from MycoBrain device."""
    device_id: str
    timestamp: datetime
    data: Dict[str, Any]
    sequence: Optional[int] = None


class MycoBrainTelemetryForwarderAgent(BaseAgent):
    """
    Agent that forwards MycoBrain telemetry to MINDEX and other systems.
    
    Listens for telemetry events and automatically forwards them to:
    - MINDEX (for knowledge base storage)
    - NatureOS (for dashboard display)
    - MAS orchestrator (for workflow triggers)
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        super().__init__(agent_id, name, config)
        
        self.integration_manager: Optional[UnifiedIntegrationManager] = None
        self.forwarding_enabled = config.get("forwarding_enabled", True)
        self.batch_size = config.get("batch_size", 10)
        self.telemetry_queue: asyncio.Queue = asyncio.Queue()
        self.forwarding_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize the agent."""
        await super().initialize()
        
        # Initialize integration manager
        self.integration_manager = UnifiedIntegrationManager()
        await self.integration_manager.initialize()
        
        # Start forwarding task
        if self.forwarding_enabled:
            self.forwarding_task = asyncio.create_task(self._forwarding_loop())
        
        self.status = AgentStatus.ACTIVE
        self.logger.info("MycoBrain Telemetry Forwarder Agent initialized")
    
    async def shutdown(self):
        """Shutdown the agent."""
        if self.forwarding_task:
            self.forwarding_task.cancel()
            try:
                await self.forwarding_task
            except asyncio.CancelledError:
                pass
        
        await super().shutdown()
        self.logger.info("MycoBrain Telemetry Forwarder Agent shutdown")
    
    async def forward_telemetry(
        self,
        device_id: str,
        telemetry_data: Dict[str, Any],
        sequence: Optional[int] = None,
    ) -> bool:
        """
        Forward telemetry data to MINDEX and other systems.
        
        Args:
            device_id: MycoBrain device identifier
            telemetry_data: Telemetry data dictionary
            sequence: Optional sequence number for idempotency
        
        Returns:
            True if forwarded successfully
        """
        if not self.forwarding_enabled:
            return False
        
        event = TelemetryEvent(
            device_id=device_id,
            timestamp=datetime.now(),
            data=telemetry_data,
            sequence=sequence,
        )
        
        await self.telemetry_queue.put(event)
        return True
    
    async def _forwarding_loop(self):
        """Background loop that forwards telemetry events."""
        batch: list[TelemetryEvent] = []
        
        while self.status == AgentStatus.ACTIVE:
            try:
                # Collect events with timeout
                try:
                    event = await asyncio.wait_for(
                        self.telemetry_queue.get(),
                        timeout=1.0
                    )
                    batch.append(event)
                except asyncio.TimeoutError:
                    # Timeout - process batch if we have events
                    if batch:
                        await self._process_batch(batch)
                        batch = []
                    continue
                
                # Process batch when full
                if len(batch) >= self.batch_size:
                    await self._process_batch(batch)
                    batch = []
                    
            except asyncio.CancelledError:
                # Process remaining batch before shutdown
                if batch:
                    await self._process_batch(batch)
                break
            except Exception as e:
                self.logger.error(f"Error in forwarding loop: {e}")
                await asyncio.sleep(1)
    
    async def _process_batch(self, batch: list[TelemetryEvent]):
        """Process a batch of telemetry events."""
        for event in batch:
            try:
                # Forward to MINDEX
                if self.integration_manager:
                    await self.integration_manager.mindex.ingest_mycobrain_telemetry(
                        device_id=event.device_id,
                        telemetry_data={
                            "device_id": event.device_id,
                            "device_type": "mycobrain",
                            "timestamp": event.timestamp.isoformat(),
                            "sequence": event.sequence,
                            **event.data,
                        },
                    )
                
                self.logger.debug(f"Forwarded telemetry for device {event.device_id}")
            except Exception as e:
                self.logger.error(f"Failed to forward telemetry for {event.device_id}: {e}")
        
        batch.clear()







