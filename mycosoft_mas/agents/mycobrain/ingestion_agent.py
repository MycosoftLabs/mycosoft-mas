"""
MycoBrain Ingestion Agent

This agent handles telemetry ingestion from MycoBrain devices to MINDEX.
It subscribes to telemetry from device agents, validates data, and pushes
it to MINDEX with proper schema mapping and idempotency handling.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus
from mycosoft_mas.integrations.unified_integration_manager import UnifiedIntegrationManager
from mycosoft_mas.protocols.mdp_v1 import MDPTelemetry

logger = logging.getLogger(__name__)


class MycoBrainIngestionAgent(BaseAgent):
    """
    Agent for ingesting MycoBrain telemetry into MINDEX.
    
    Responsibilities:
    - Subscribe to telemetry from MycoBrain device agents
    - Map telemetry fields to MINDEX schema
    - Ensure idempotent inserts using sequence numbers
    - Handle authentication with API keys
    - Batch inserts for efficiency
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the ingestion agent."""
        super().__init__(agent_id, name, config)
        
        # Integration manager
        self.integration_manager: Optional[UnifiedIntegrationManager] = None
        
        # Device tracking
        self.device_api_keys: Dict[str, str] = config.get("device_api_keys", {})
        self.device_locations: Dict[str, Dict[str, float]] = config.get("device_locations", {})
        
        # Batch processing
        self.batch_size = config.get("batch_size", 10)
        self.batch_timeout = config.get("batch_timeout", 5.0)
        self.telemetry_queue: asyncio.Queue = asyncio.Queue()
        self.batch_buffer: List[Dict[str, Any]] = []
        
        # Idempotency tracking
        self.processed_sequences: Dict[str, set] = {}  # device_id -> set of sequences
        
        # Data directory
        self.data_dir = Path(config.get("data_dir", "data/mycobrain/ingestion"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Metrics
        self.metrics.update({
            "telemetry_received": 0,
            "telemetry_ingested": 0,
            "telemetry_failed": 0,
            "duplicate_sequences": 0,
            "batches_processed": 0,
        })
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            self.status = AgentStatus.INITIALIZING
            self.logger.info(f"Initializing MycoBrain ingestion agent {self.name}")
            
            # Initialize integration manager
            self.integration_manager = UnifiedIntegrationManager()
            await self.integration_manager.initialize()
            
            # Start background tasks
            self.background_tasks.extend([
                asyncio.create_task(self._process_telemetry_queue()),
                asyncio.create_task(self._process_batch_buffer()),
            ])
            
            self.status = AgentStatus.ACTIVE
            self.is_running = True
            self.metrics["start_time"] = datetime.now()
            
            self.logger.info(f"MycoBrain ingestion agent {self.name} initialized successfully")
            return True
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to initialize ingestion agent {self.name}: {str(e)}")
            return False
    
    async def stop(self) -> bool:
        """Stop the agent."""
        try:
            self.logger.info(f"Stopping MycoBrain ingestion agent {self.name}")
            self.is_running = False
            
            # Process remaining batch
            if self.batch_buffer:
                await self._ingest_batch()
            
            # Close integration manager
            if self.integration_manager:
                await self.integration_manager.close()
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            self.status = AgentStatus.STOPPED
            self.logger.info(f"MycoBrain ingestion agent {self.name} stopped")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping agent: {str(e)}")
            return False
    
    async def ingest_telemetry(
        self,
        device_id: str,
        telemetry: MDPTelemetry,
        sequence: int,
        timestamp: datetime
    ) -> bool:
        """
        Queue telemetry for ingestion.
        
        Args:
            device_id: Device identifier
            telemetry: Telemetry data
            sequence: MDP sequence number
            timestamp: Timestamp of telemetry
        
        Returns:
            True if queued successfully
        """
        # Check for duplicate sequence
        if device_id not in self.processed_sequences:
            self.processed_sequences[device_id] = set()
        
        if sequence in self.processed_sequences[device_id]:
            self.metrics["duplicate_sequences"] += 1
            self.logger.debug(f"Duplicate sequence {sequence} for device {device_id}")
            return False
        
        # Add to queue
        await self.telemetry_queue.put({
            "device_id": device_id,
            "telemetry": telemetry,
            "sequence": sequence,
            "timestamp": timestamp
        })
        
        self.metrics["telemetry_received"] += 1
        return True
    
    async def _process_telemetry_queue(self) -> None:
        """Process telemetry from queue and add to batch buffer."""
        while self.is_running:
            try:
                # Get telemetry with timeout
                telemetry_data = await asyncio.wait_for(
                    self.telemetry_queue.get(),
                    timeout=self.batch_timeout
                )
                
                # Add to batch buffer
                self.batch_buffer.append(telemetry_data)
                
                # Trigger batch processing if buffer is full
                if len(self.batch_buffer) >= self.batch_size:
                    asyncio.create_task(self._ingest_batch())
                
            except asyncio.TimeoutError:
                # Timeout - process batch if not empty
                if self.batch_buffer:
                    asyncio.create_task(self._ingest_batch())
            except Exception as e:
                self.logger.error(f"Error processing telemetry queue: {str(e)}")
    
    async def _process_batch_buffer(self) -> None:
        """Periodically process batch buffer."""
        while self.is_running:
            try:
                await asyncio.sleep(self.batch_timeout)
                if self.batch_buffer:
                    await self._ingest_batch()
            except Exception as e:
                self.logger.error(f"Error in batch processor: {str(e)}")
    
    async def _ingest_batch(self) -> None:
        """Ingest a batch of telemetry to MINDEX."""
        if not self.batch_buffer:
            return
        
        batch = self.batch_buffer.copy()
        self.batch_buffer.clear()
        
        self.logger.debug(f"Ingesting batch of {len(batch)} telemetry records")
        
        ingested = 0
        failed = 0
        
        for telemetry_data in batch:
            try:
                success = await self._ingest_single_telemetry(telemetry_data)
                if success:
                    ingested += 1
                    # Mark sequence as processed
                    device_id = telemetry_data["device_id"]
                    sequence = telemetry_data["sequence"]
                    if device_id not in self.processed_sequences:
                        self.processed_sequences[device_id] = set()
                    self.processed_sequences[device_id].add(sequence)
                    
                    # Keep only last 10000 sequences per device
                    if len(self.processed_sequences[device_id]) > 10000:
                        # Remove oldest sequences (simple approach: clear if too large)
                        self.processed_sequences[device_id] = set(
                            list(self.processed_sequences[device_id])[-5000:]
                        )
                else:
                    failed += 1
            except Exception as e:
                self.logger.error(f"Error ingesting telemetry: {str(e)}")
                failed += 1
        
        self.metrics["telemetry_ingested"] += ingested
        self.metrics["telemetry_failed"] += failed
        self.metrics["batches_processed"] += 1
        
        self.logger.info(f"Batch ingested: {ingested} succeeded, {failed} failed")
    
    async def _ingest_single_telemetry(self, telemetry_data: Dict[str, Any]) -> bool:
        """Ingest a single telemetry record to MINDEX."""
        device_id = telemetry_data["device_id"]
        telemetry = telemetry_data["telemetry"]
        sequence = telemetry_data["sequence"]
        timestamp = telemetry_data["timestamp"]
        
        try:
            # Map telemetry to MINDEX schema
            mindex_data = self._map_telemetry_to_mindex(device_id, telemetry, sequence, timestamp)
            
            # Get API key for device
            api_key = self.device_api_keys.get(device_id)
            if not api_key:
                self.logger.warning(f"No API key configured for device {device_id}")
                # Use default MINDEX client (may have global API key)
                api_key = None
            
            # Ingest to MINDEX
            # Note: This assumes MINDEX client has a method for ingesting MycoBrain telemetry
            # We'll need to add this method to MINDEXClient
            result = await self.integration_manager.mindex.ingest_mycobrain_telemetry(
                device_id=device_id,
                telemetry_data=mindex_data,
                api_key=api_key
            )
            
            return result.get("success", False)
            
        except Exception as e:
            self.logger.error(f"Error ingesting telemetry for device {device_id}: {str(e)}")
            return False
    
    def _map_telemetry_to_mindex(
        self,
        device_id: str,
        telemetry: MDPTelemetry,
        sequence: int,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Map MycoBrain telemetry to MINDEX schema.
        
        Returns:
            Dictionary with MINDEX-compatible fields
        """
        # Get device location if available
        location = self.device_locations.get(device_id, {})
        
        # Build MINDEX telemetry record
        mindex_record = {
            "device_id": device_id,
            "device_type": "mycobrain",
            "timestamp": timestamp.isoformat(),
            "sequence": sequence,
            
            # Analog inputs
            "analog_inputs": {
                "ai1_voltage": telemetry.ai1_voltage,
                "ai2_voltage": telemetry.ai2_voltage,
                "ai3_voltage": telemetry.ai3_voltage,
                "ai4_voltage": telemetry.ai4_voltage,
            },
            
            # Environmental sensors (BME688)
            "environmental": {}
        }
        
        if telemetry.temperature is not None:
            mindex_record["environmental"]["temperature"] = telemetry.temperature
        if telemetry.humidity is not None:
            mindex_record["environmental"]["humidity"] = telemetry.humidity
        if telemetry.pressure is not None:
            mindex_record["environmental"]["pressure"] = telemetry.pressure
        if telemetry.gas_resistance is not None:
            mindex_record["environmental"]["gas_resistance"] = telemetry.gas_resistance
        
        # MOSFET states
        mindex_record["mosfet_states"] = {
            f"mosfet_{i}": state for i, state in enumerate(telemetry.mosfet_states)
        }
        
        # I²C addresses
        mindex_record["i2c_sensors"] = {
            "detected_addresses": telemetry.i2c_addresses
        }
        
        # Power status
        mindex_record["power"] = telemetry.power_status
        
        # Device metadata
        mindex_record["device_metadata"] = {
            "firmware_version": telemetry.firmware_version,
            "uptime_seconds": telemetry.uptime_seconds,
        }
        
        # Location (if available)
        if location:
            mindex_record["location"] = location
        
        return mindex_record
