"""
Growth Simulator Agent for Mycology BioAgent System

This agent manages mushroom growth models, processes environmental factors,
coordinates with device data, and updates growth parameters.
"""

import asyncio
import logging
import json
import os
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class GrowthPhase(Enum):
    """Growth phases in mushroom development"""
    SPORE = auto()
    GERMINATION = auto()
    MYCELIUM = auto()
    PRIMORDIA = auto()
    PINNING = auto()
    FRUITING = auto()
    MATURATION = auto()
    SPORULATION = auto()

class SubstrateType(Enum):
    """Types of growth substrates"""
    WOOD = auto()
    STRAW = auto()
    COMPOST = auto()
    GRAIN = auto()
    SAWDUST = auto()
    SOIL = auto()
    CUSTOM = auto()

class EnvironmentalFactor(Enum):
    """Enumeration of environmental factors."""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    CO2 = "co2"
    LIGHT = "light"
    AIRFLOW = "airflow"
    NUTRIENTS = "nutrients"
    PH = "ph"

@dataclass
class EnvironmentalConditions:
    """Environmental conditions for growth"""
    temperature: float  # in Celsius
    humidity: float  # relative humidity percentage
    co2_level: float  # in ppm
    light_intensity: float  # in lux
    air_flow: float  # in m/s
    ph: float  # pH level
    substrate_moisture: float  # percentage
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class GrowthParameters:
    """Parameters for growth simulation"""
    species_id: str
    substrate_type: SubstrateType
    initial_mass: float  # in grams
    optimal_conditions: EnvironmentalConditions
    tolerance_ranges: Dict[str, tuple]  # min/max ranges for each parameter
    growth_rate: float  # in mm/day
    colonization_rate: float  # in mm/day
    fruiting_probability: float  # 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SimulationResult:
    """Results of a growth simulation"""
    simulation_id: str
    species_id: str
    parameters: GrowthParameters
    current_phase: GrowthPhase
    biomass: float  # in grams
    colony_size: float  # in mm
    fruiting_bodies: int
    environmental_history: List[EnvironmentalConditions]
    phase_transitions: Dict[GrowthPhase, datetime]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

class GrowthSimulatorAgent(BaseAgent):
    """Agent for simulating mushroom growth"""
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the GrowthSimulatorAgent."""
        super().__init__(agent_id, name, config)
        
        # Initialize storage
        self.growth_parameters: Dict[str, GrowthParameters] = {}
        self.active_simulations: Dict[str, SimulationResult] = {}
        self.simulation_queue: asyncio.Queue = asyncio.Queue()
        
        # Initialize directories
        self.data_dir = Path(config.get('data_dir', 'data/growth_simulation'))
        
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics
        self.metrics.update({
            "simulations_started": 0,
            "simulations_completed": 0,
            "simulations_failed": 0,
            "parameters_updated": 0,
            "simulation_errors": 0
        })

    async def initialize(self) -> bool:
        """Initialize the agent and its services."""
        try:
            self.status = AgentStatus.INITIALIZING
            self.logger.info(f"Initializing GrowthSimulatorAgent {self.name}")
            
            # Load existing parameters
            await self._load_parameters()
            
            # Start background tasks
            self.background_tasks.extend([
                asyncio.create_task(self._process_simulation_queue())
            ])
            
            self.status = AgentStatus.ACTIVE
            self.is_running = True
            self.metrics["start_time"] = datetime.now()
            
            self.logger.info(f"GrowthSimulatorAgent {self.name} initialized successfully")
            return True
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to initialize GrowthSimulatorAgent {self.name}: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop the agent and cleanup resources."""
        try:
            self.logger.info(f"Stopping GrowthSimulatorAgent {self.name}")
            self.is_running = False
            
            # Save parameters
            await self._save_parameters()
            
            # Cancel background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self.background_tasks = []
            self.status = AgentStatus.STOPPED
            
            self.logger.info(f"GrowthSimulatorAgent {self.name} stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping GrowthSimulatorAgent {self.name}: {str(e)}")
            return False

    async def register_growth_parameters(
        self,
        species_id: str,
        substrate_type: SubstrateType,
        initial_mass: float,
        optimal_conditions: EnvironmentalConditions,
        tolerance_ranges: Dict[str, tuple],
        growth_rate: float,
        colonization_rate: float,
        fruiting_probability: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register growth parameters for a species"""
        parameters = GrowthParameters(
            species_id=species_id,
            substrate_type=substrate_type,
            initial_mass=initial_mass,
            optimal_conditions=optimal_conditions,
            tolerance_ranges=tolerance_ranges,
            growth_rate=growth_rate,
            colonization_rate=colonization_rate,
            fruiting_probability=fruiting_probability,
            metadata=metadata or {}
        )
        
        self.growth_parameters[species_id] = parameters
        await self._save_parameters()
        
        return species_id

    async def start_simulation(
        self,
        species_id: str,
        environmental_conditions: EnvironmentalConditions,
        custom_parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new growth simulation"""
        if species_id not in self.growth_parameters:
            raise ValueError(f"No growth parameters registered for species {species_id}")
        
        simulation_id = f"sim_{len(self.active_simulations)}"
        
        # Create initial simulation result
        result = SimulationResult(
            simulation_id=simulation_id,
            species_id=species_id,
            parameters=self.growth_parameters[species_id],
            current_phase=GrowthPhase.SPORE,
            biomass=self.growth_parameters[species_id].initial_mass,
            colony_size=0.0,
            fruiting_bodies=0,
            environmental_history=[environmental_conditions],
            phase_transitions={GrowthPhase.SPORE: datetime.utcnow()},
            metadata=custom_parameters or {}
        )
        
        self.active_simulations[simulation_id] = result
        await self.simulation_queue.put(simulation_id)
        
        self.metrics["simulations_started"] += 1
        return simulation_id

    async def update_environmental_conditions(
        self,
        simulation_id: str,
        conditions: EnvironmentalConditions
    ) -> None:
        """Update environmental conditions for a simulation"""
        if simulation_id not in self.active_simulations:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        simulation = self.active_simulations[simulation_id]
        simulation.environmental_history.append(conditions)
        simulation.updated_at = datetime.utcnow()
        
        # Trigger growth update
        await self._update_growth(simulation_id)

    async def get_simulation_result(self, simulation_id: str) -> Optional[SimulationResult]:
        """Get the current state of a simulation"""
        return self.active_simulations.get(simulation_id)

    async def _load_parameters(self) -> None:
        """Load growth parameters from disk"""
        parameters_file = self.data_dir / "growth_parameters.json"
        if parameters_file.exists():
            with open(parameters_file, "r") as f:
                parameters_data = json.load(f)
                
                for species_id, param_data in parameters_data.items():
                    optimal_conditions = EnvironmentalConditions(
                        temperature=param_data["optimal_conditions"]["temperature"],
                        humidity=param_data["optimal_conditions"]["humidity"],
                        co2_level=param_data["optimal_conditions"]["co2_level"],
                        light_intensity=param_data["optimal_conditions"]["light_intensity"],
                        air_flow=param_data["optimal_conditions"]["air_flow"],
                        ph=param_data["optimal_conditions"]["ph"],
                        substrate_moisture=param_data["optimal_conditions"]["substrate_moisture"]
                    )
                    
                    parameters = GrowthParameters(
                        species_id=species_id,
                        substrate_type=SubstrateType[param_data["substrate_type"]],
                        initial_mass=param_data["initial_mass"],
                        optimal_conditions=optimal_conditions,
                        tolerance_ranges=param_data["tolerance_ranges"],
                        growth_rate=param_data["growth_rate"],
                        colonization_rate=param_data["colonization_rate"],
                        fruiting_probability=param_data["fruiting_probability"],
                        metadata=param_data.get("metadata", {})
                    )
                    
                    self.growth_parameters[species_id] = parameters

    async def _save_parameters(self) -> None:
        """Save growth parameters to disk"""
        parameters_file = self.data_dir / "growth_parameters.json"
        parameters_data = {}
        
        for species_id, parameters in self.growth_parameters.items():
            param_data = {
                "substrate_type": parameters.substrate_type.name,
                "initial_mass": parameters.initial_mass,
                "optimal_conditions": {
                    "temperature": parameters.optimal_conditions.temperature,
                    "humidity": parameters.optimal_conditions.humidity,
                    "co2_level": parameters.optimal_conditions.co2_level,
                    "light_intensity": parameters.optimal_conditions.light_intensity,
                    "air_flow": parameters.optimal_conditions.air_flow,
                    "ph": parameters.optimal_conditions.ph,
                    "substrate_moisture": parameters.optimal_conditions.substrate_moisture
                },
                "tolerance_ranges": parameters.tolerance_ranges,
                "growth_rate": parameters.growth_rate,
                "colonization_rate": parameters.colonization_rate,
                "fruiting_probability": parameters.fruiting_probability,
                "metadata": parameters.metadata
            }
            parameters_data[species_id] = param_data
        
        with open(parameters_file, "w") as f:
            json.dump(parameters_data, f, indent=2)

    async def _process_simulation_queue(self) -> None:
        """Process the simulation queue"""
        while self.is_running:
            try:
                # Get next simulation
                simulation_id = await self.simulation_queue.get()
                
                # Update growth
                await self._update_growth(simulation_id)
                
                # Check if simulation should continue
                if self._should_continue_simulation(simulation_id):
                    await self.simulation_queue.put(simulation_id)
                else:
                    self.metrics["simulations_completed"] += 1
                
                # Mark task as complete
                self.simulation_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing simulation: {str(e)}")
                self.metrics["simulation_errors"] += 1
                continue

    async def _update_growth(self, simulation_id: str) -> None:
        """Update growth for a simulation"""
        simulation = self.active_simulations[simulation_id]
        current_conditions = simulation.environmental_history[-1]
        parameters = simulation.parameters
        
        try:
            # Calculate growth factors based on environmental conditions
            temperature_factor = self._calculate_temperature_factor(
                current_conditions.temperature,
                parameters.optimal_conditions.temperature,
                parameters.tolerance_ranges["temperature"]
            )
            
            humidity_factor = self._calculate_humidity_factor(
                current_conditions.humidity,
                parameters.optimal_conditions.humidity,
                parameters.tolerance_ranges["humidity"]
            )
            
            # Update biomass and colony size
            time_delta = (datetime.utcnow() - simulation.updated_at).total_seconds() / 86400  # Convert to days
            growth_factor = temperature_factor * humidity_factor
            
            simulation.biomass += parameters.growth_rate * growth_factor * time_delta
            simulation.colony_size += parameters.colonization_rate * growth_factor * time_delta
            
            # Check for phase transitions
            await self._check_phase_transitions(simulation_id)
            
        except Exception as e:
            self.logger.error(f"Error updating growth for simulation {simulation_id}: {str(e)}")
            self.metrics["simulation_errors"] += 1

    async def _check_phase_transitions(self, simulation_id: str) -> None:
        """Check and update growth phases"""
        simulation = self.active_simulations[simulation_id]
        
        # Define phase transition conditions (simplified)
        if simulation.current_phase == GrowthPhase.SPORE and simulation.biomass > 0.1:
            simulation.current_phase = GrowthPhase.GERMINATION
            simulation.phase_transitions[GrowthPhase.GERMINATION] = datetime.utcnow()
        
        elif simulation.current_phase == GrowthPhase.GERMINATION and simulation.colony_size > 5:
            simulation.current_phase = GrowthPhase.MYCELIUM
            simulation.phase_transitions[GrowthPhase.MYCELIUM] = datetime.utcnow()
        
        # Add more phase transition logic here

    def _should_continue_simulation(self, simulation_id: str) -> bool:
        """Check if a simulation should continue"""
        simulation = self.active_simulations[simulation_id]
        
        # Example conditions for ending simulation
        if simulation.current_phase == GrowthPhase.SPORULATION:
            return False
        
        if simulation.biomass <= 0:
            return False
        
        return True

    def _calculate_temperature_factor(
        self,
        current: float,
        optimal: float,
        tolerance: tuple
    ) -> float:
        """Calculate growth factor based on temperature"""
        min_temp, max_temp = tolerance
        if current < min_temp or current > max_temp:
            return 0.0
        
        # Simplified bell curve
        return np.exp(-((current - optimal) ** 2) / (2 * ((max_temp - min_temp) / 6) ** 2))

    def _calculate_humidity_factor(
        self,
        current: float,
        optimal: float,
        tolerance: tuple
    ) -> float:
        """Calculate growth factor based on humidity"""
        min_humidity, max_humidity = tolerance
        if current < min_humidity or current > max_humidity:
            return 0.0
        
        # Simplified bell curve
        return np.exp(-((current - optimal) ** 2) / (2 * ((max_humidity - min_humidity) / 6) ** 2)) 