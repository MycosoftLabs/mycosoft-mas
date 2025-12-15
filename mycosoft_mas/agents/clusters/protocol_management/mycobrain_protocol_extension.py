"""
MycoBrain Protocol Extension for Mycorrhizae Protocol Agent

This module extends the Mycorrhizae Protocol Agent with MycoBrain-specific
functionality for device telemetry, commands, and environmental monitoring.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from mycosoft_mas.agents.clusters.protocol_management.mycorrhizae_protocol_agent import (
    MycorrhizaeProtocolAgent,
    ProtocolExecution,
    ProtocolStep,
    ProtocolStatus,
)
from mycosoft_mas.protocols.mdp_v1 import MDPTelemetry

logger = logging.getLogger(__name__)


class MycoBrainProtocolExtension:
    """
    Extension methods for Mycorrhizae Protocol Agent to support MycoBrain devices.
    
    This extension allows protocols to:
    - Subscribe to MycoBrain telemetry
    - Send commands to MycoBrain devices
    - Use environmental data from MycoBrain in protocol steps
    - Monitor device state during protocol execution
    """
    
    def __init__(self, protocol_agent: MycorrhizaeProtocolAgent):
        """Initialize the extension with a protocol agent."""
        self.protocol_agent = protocol_agent
        self.logger = logging.getLogger(__name__)
        
        # Device subscriptions
        self.device_subscriptions: Dict[str, List[str]] = {}  # device_id -> [protocol_ids]
        self.telemetry_cache: Dict[str, MDPTelemetry] = {}  # device_id -> latest telemetry
    
    async def subscribe_device_to_protocol(
        self,
        device_id: str,
        protocol_id: str
    ) -> bool:
        """
        Subscribe a MycoBrain device to a protocol execution.
        
        Args:
            device_id: MycoBrain device identifier
            protocol_id: Protocol identifier
        
        Returns:
            True if subscription successful
        """
        if device_id not in self.device_subscriptions:
            self.device_subscriptions[device_id] = []
        
        if protocol_id not in self.device_subscriptions[device_id]:
            self.device_subscriptions[device_id].append(protocol_id)
            self.logger.info(f"Subscribed device {device_id} to protocol {protocol_id}")
            return True
        
        return False
    
    async def unsubscribe_device_from_protocol(
        self,
        device_id: str,
        protocol_id: str
    ) -> bool:
        """Unsubscribe a device from a protocol."""
        if device_id in self.device_subscriptions:
            if protocol_id in self.device_subscriptions[device_id]:
                self.device_subscriptions[device_id].remove(protocol_id)
                self.logger.info(f"Unsubscribed device {device_id} from protocol {protocol_id}")
                return True
        
        return False
    
    async def handle_mycobrain_telemetry(
        self,
        device_id: str,
        telemetry: MDPTelemetry
    ) -> None:
        """
        Handle incoming MycoBrain telemetry.
        
        Updates telemetry cache and notifies subscribed protocols.
        """
        # Update cache
        self.telemetry_cache[device_id] = telemetry
        
        # Notify subscribed protocols
        protocol_ids = self.device_subscriptions.get(device_id, [])
        for protocol_id in protocol_ids:
            await self._notify_protocol_telemetry(protocol_id, device_id, telemetry)
    
    async def _notify_protocol_telemetry(
        self,
        protocol_id: str,
        device_id: str,
        telemetry: MDPTelemetry
    ) -> None:
        """Notify a protocol about device telemetry."""
        # Find active execution for this protocol
        execution = self._find_active_execution(protocol_id)
        if not execution:
            return
        
        # Check if current step requires environmental monitoring
        if execution.current_step:
            step = self._get_protocol_step(protocol_id, execution.current_step)
            if step:
                await self._check_step_conditions(execution, step, device_id, telemetry)
    
    def _find_active_execution(self, protocol_id: str) -> Optional[ProtocolExecution]:
        """Find active execution for a protocol."""
        for execution in self.protocol_agent.executions.values():
            if execution.protocol_id != protocol_id:
                continue

            if execution.status in (ProtocolStatus.IN_PROGRESS, ProtocolStatus.SCHEDULED):
                return execution
        return None
    
    def _get_protocol_step(
        self,
        protocol_id: str,
        step_id: str
    ) -> Optional[ProtocolStep]:
        """Get a protocol step by ID."""
        protocol = self.protocol_agent.protocols.get(protocol_id)
        if protocol:
            for step in protocol.steps:
                if step.step_id == step_id:
                    return step
        return None
    
    async def _check_step_conditions(
        self,
        execution: ProtocolExecution,
        step: ProtocolStep,
        device_id: str,
        telemetry: MDPTelemetry
    ) -> None:
        """Check if step conditions are met based on telemetry."""
        conditions_met = True
        
        # Check temperature
        if step.temperature is not None and telemetry.temperature is not None:
            temp_diff = abs(telemetry.temperature - step.temperature)
            if temp_diff > 2.0:  # 2°C tolerance
                conditions_met = False
                self.logger.warning(
                    f"Temperature mismatch: expected {step.temperature}°C, "
                    f"got {telemetry.temperature}°C"
                )
        
        # Check humidity
        if step.humidity is not None and telemetry.humidity is not None:
            humidity_diff = abs(telemetry.humidity - step.humidity)
            if humidity_diff > 5.0:  # 5% tolerance
                conditions_met = False
                self.logger.warning(
                    f"Humidity mismatch: expected {step.humidity}%, "
                    f"got {telemetry.humidity}%"
                )
        
        # Store telemetry in execution metadata
        if "device_telemetry" not in execution.metadata:
            execution.metadata["device_telemetry"] = {}
        execution.metadata["device_telemetry"][device_id] = {
            "temperature": telemetry.temperature,
            "humidity": telemetry.humidity,
            "pressure": telemetry.pressure,
            "gas_resistance": telemetry.gas_resistance,
            "timestamp": datetime.now().isoformat()
        }
    
    async def send_protocol_command(
        self,
        device_id: str,
        command_type: str,
        parameters: Dict[str, Any],
        protocol_id: Optional[str] = None
    ) -> bool:
        """
        Send a command to a MycoBrain device as part of protocol execution.
        
        Args:
            device_id: Device identifier
            command_type: Command type (e.g., "set_mosfet", "set_telemetry_interval")
            parameters: Command parameters
            protocol_id: Optional protocol ID for tracking
        
        Returns:
            True if command sent successfully
        """
        # This would integrate with MycoBrainDeviceAgent
        # For now, log the command
        self.logger.info(
            f"Sending command {command_type} to device {device_id} "
            f"(protocol: {protocol_id})"
        )
        
        # In a full implementation, this would call:
        # device_agent = await get_device_agent(device_id)
        # return await device_agent.send_command(command_type, parameters)
        
        return True
    
    def get_device_telemetry(self, device_id: str) -> Optional[MDPTelemetry]:
        """Get latest telemetry for a device."""
        return self.telemetry_cache.get(device_id)
    
    def map_telemetry_to_protocol_fields(
        self,
        telemetry: MDPTelemetry
    ) -> Dict[str, Any]:
        """
        Map MycoBrain telemetry to Mycorrhizae Protocol fields.
        
        Returns:
            Dictionary with protocol-compatible fields
        """
        return {
            "temperature": telemetry.temperature,
            "humidity": telemetry.humidity,
            "pressure": telemetry.pressure,
            "gas_resistance": telemetry.gas_resistance,
            "analog_inputs": {
                "ai1": telemetry.ai1_voltage,
                "ai2": telemetry.ai2_voltage,
                "ai3": telemetry.ai3_voltage,
                "ai4": telemetry.ai4_voltage,
            },
            "mosfet_states": telemetry.mosfet_states,
            "i2c_sensors": telemetry.i2c_addresses,
        }
    
    async def create_mycobrain_protocol_step(
        self,
        step_name: str,
        description: str,
        device_id: str,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        mosfet_actions: Optional[Dict[int, bool]] = None,
        telemetry_interval: Optional[int] = None,
        duration: int = 60
    ) -> ProtocolStep:
        """
        Create a protocol step that interacts with MycoBrain device.
        
        Args:
            step_name: Step name
            description: Step description
            device_id: MycoBrain device identifier
            temperature: Target temperature (°C)
            humidity: Target humidity (%)
            mosfet_actions: Dict mapping MOSFET index to desired state
            telemetry_interval: Telemetry interval in seconds
            duration: Step duration in minutes
        
        Returns:
            ProtocolStep with MycoBrain-specific metadata
        """
        metadata = {
            "device_id": device_id,
            "device_type": "mycobrain",
        }
        
        if mosfet_actions:
            metadata["mosfet_actions"] = mosfet_actions
        if telemetry_interval:
            metadata["telemetry_interval"] = telemetry_interval
        
        step = ProtocolStep(
            step_id=f"step_{datetime.now().timestamp()}",
            name=step_name,
            description=description,
            duration=duration,
            temperature=temperature,
            humidity=humidity,
            metadata=metadata
        )
        
        return step
