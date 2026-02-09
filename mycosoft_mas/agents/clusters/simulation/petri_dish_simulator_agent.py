"""
Mycosoft Multi-Agent System (MAS) - Petri Dish Simulator Agent

This module implements the PetriDishSimulatorAgent, which manages growth simulations
and processes environmental data for petri dish experiments.
"""

import asyncio
import logging
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus
from mycosoft_mas.simulation.physics import PhysicsSimulator

class GrowthPhase(Enum):
    """Enumeration of fungal growth phases."""
    LAG = "lag"
    EXPONENTIAL = "exponential"
    STATIONARY = "stationary"
    DECLINE = "decline"

@dataclass
class EnvironmentalConditions:
    """Data class for storing environmental conditions."""
    temperature: float
    humidity: float
    ph: float
    light_intensity: float
    co2_level: float
    nutrients: Dict[str, float]
    timestamp: datetime

@dataclass
class GrowthParameters:
    """Data class for storing growth parameters."""
    species_id: str
    initial_biomass: float
    growth_rate: float
    optimal_conditions: EnvironmentalConditions
    tolerance_ranges: Dict[str, Tuple[float, float]]
    metadata: Dict[str, Any]

@dataclass
class SimulationResult:
    """Data class for storing simulation results."""
    simulation_id: str
    parameters: GrowthParameters
    time_points: List[datetime]
    biomass_values: List[float]
    environmental_data: List[EnvironmentalConditions]
    growth_phases: List[Tuple[datetime, GrowthPhase]]
    metadata: Dict[str, Any]
    created_at: datetime

class PetriDishSimulatorAgent(BaseAgent):
    """
    Agent responsible for managing growth simulations in petri dishes.
    
    This agent processes environmental data, coordinates with real device data,
    and updates simulation parameters based on experimental results.
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the PetriDishSimulatorAgent."""
        super().__init__(agent_id, name, config)
        
        # Initialize storage
        self.simulations: Dict[str, SimulationResult] = {}
        self.parameters: Dict[str, GrowthParameters] = {}
        
        # Initialize queues
        self.simulation_queue = asyncio.Queue()
        self.environment_queue = asyncio.Queue()
        self.parameter_queue = asyncio.Queue()
        
        # Initialize metrics
        self.metrics.update({
            "simulations_run": 0,
            "simulations_completed": 0,
            "simulations_failed": 0,
            "parameters_updated": 0
        })
        self.physics_simulator = PhysicsSimulator()

    async def initialize(self) -> bool:
        """Initialize the agent and its services."""
        try:
            self.status = AgentStatus.INITIALIZING
            self.logger.info(f"Initializing PetriDishSimulatorAgent {self.name}")
            
            # Load simulation data
            await self._load_simulation_data()
            
            # Start background tasks
            self.background_tasks.extend([
                asyncio.create_task(self._process_simulation_queue()),
                asyncio.create_task(self._process_environment_queue()),
                asyncio.create_task(self._process_parameter_queue())
            ])
            
            self.status = AgentStatus.ACTIVE
            self.is_running = True
            self.metrics["start_time"] = datetime.now()
            
            self.logger.info(f"PetriDishSimulatorAgent {self.name} initialized successfully")
            return True
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to initialize PetriDishSimulatorAgent {self.name}: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop the agent and cleanup resources."""
        try:
            self.logger.info(f"Stopping PetriDishSimulatorAgent {self.name}")
            self.is_running = False
            
            # Save simulation data
            await self._save_simulation_data()
            
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
            
            self.logger.info(f"PetriDishSimulatorAgent {self.name} stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping PetriDishSimulatorAgent {self.name}: {str(e)}")
            return False

    async def run_simulation(self, parameters: GrowthParameters) -> SimulationResult:
        """
        Run a growth simulation with given parameters.
        
        Args:
            parameters: The growth parameters for the simulation
            
        Returns:
            SimulationResult containing the simulation results
        """
        try:
            self.metrics["simulations_run"] += 1
            
            # Generate simulation ID
            simulation_id = f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Run simulation
            result = await self._run_growth_simulation(parameters)
            
            # Store results
            self.simulations[simulation_id] = result
            self.metrics["simulations_completed"] += 1
            
            self.logger.info(f"Completed simulation: {simulation_id}")
            return result
            
        except Exception as e:
            self.metrics["simulations_failed"] += 1
            self.logger.error(f"Error running simulation: {str(e)}")
            return None

    async def update_parameters(self, species_id: str, new_parameters: GrowthParameters) -> bool:
        """
        Update growth parameters for a species.
        
        Args:
            species_id: ID of the species
            new_parameters: New growth parameters
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            self.parameters[species_id] = new_parameters
            self.metrics["parameters_updated"] += 1
            
            self.logger.info(f"Updated parameters for species: {species_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating parameters for species {species_id}: {str(e)}")
            return False

    async def process_environmental_data(self, data: EnvironmentalConditions) -> Dict[str, Any]:
        """
        Process environmental data and update simulations.
        
        Args:
            data: Environmental conditions data
            
        Returns:
            Dict[str, Any]: Processing results
        """
        try:
            # Process environmental data
            results = await self._process_environmental_conditions(data)
            
            # Update affected simulations
            await self._update_simulations_with_environment(data)
            
            return results
        except Exception as e:
            self.logger.error(f"Error processing environmental data: {str(e)}")
            return {}

    async def _load_simulation_data(self):
        """Load simulation data from storage."""
        # Implementation for loading simulation data
        pass

    async def _save_simulation_data(self):
        """Save simulation data to storage."""
        # Implementation for saving simulation data
        pass

    async def _run_growth_simulation(self, parameters: GrowthParameters) -> SimulationResult:
        """Run a growth simulation with given parameters."""
        simulation_id = f"petri_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        time_points: List[datetime] = []
        biomass_values: List[float] = []
        environmental_data: List[EnvironmentalConditions] = []
        growth_phases: List[Tuple[datetime, GrowthPhase]] = []

        nutrient_grid = {(x, y): 1.0 for x in range(8) for y in range(8)}
        biomass = max(parameters.initial_biomass, 0.001)
        now = datetime.utcnow()
        for step in range(max(1, min(parameters.time_steps, 120))):
            diffusion = await self.physics_simulator.simulate_growth_physics(
                nutrient_field=nutrient_grid,
                diffusion_coefficient=0.02,
            )
            final_field = diffusion.get("final_field", [])
            mean_nutrient = 1.0
            if final_field and isinstance(final_field, list):
                try:
                    mean_nutrient = float(np.mean(np.array(final_field, dtype=np.float32)))
                except Exception:
                    mean_nutrient = 1.0

            growth_factor = max(0.05, min(2.5, mean_nutrient))
            biomass += parameters.growth_rate * growth_factor * (parameters.duration / max(parameters.time_steps, 1))

            point_time = now + timedelta(hours=step)
            time_points.append(point_time)
            biomass_values.append(float(biomass))
            env = EnvironmentalConditions(
                temperature=float(parameters.reaction_conditions.get("temperature", 24.0)),
                humidity=float(parameters.reaction_conditions.get("humidity", 80.0)),
                ph=float(parameters.reaction_conditions.get("ph", 6.0)),
                light_intensity=float(parameters.reaction_conditions.get("light_intensity", 0.0)),
                co2_level=float(parameters.reaction_conditions.get("co2_level", 500.0)),
                nutrients={"mean_nutrient": mean_nutrient},
                timestamp=point_time,
            )
            environmental_data.append(env)
            phase = GrowthPhase.EXPONENTIAL if biomass > parameters.initial_biomass * 1.2 else GrowthPhase.LAG
            growth_phases.append((point_time, phase))

        return SimulationResult(
            simulation_id=simulation_id,
            parameters=parameters,
            time_points=time_points,
            biomass_values=biomass_values,
            environmental_data=environmental_data,
            growth_phases=growth_phases,
            metadata={"engine": "physicsnemo"},
            created_at=datetime.utcnow(),
        )

    async def _process_environmental_conditions(self, data: EnvironmentalConditions) -> Dict[str, Any]:
        """Process environmental conditions data."""
        heat = await self.physics_simulator.simulate_heat_transfer(
            geometry={"width": 16, "height": 16, "thermal_diffusivity": 0.02},
            boundary_conditions={"ambient": data.temperature},
            time_seconds=30.0,
        )
        max_temp = float(heat.get("max_temperature", data.temperature))
        return {
            "status": "processed",
            "max_temperature": max_temp,
            "humidity": data.humidity,
            "co2_level": data.co2_level,
            "engine": "physicsnemo",
        }

    async def _update_simulations_with_environment(self, data: EnvironmentalConditions):
        """Update simulations with new environmental data."""
        for simulation_id, simulation in self.simulations.items():
            if simulation.environmental_data:
                simulation.environmental_data[-1] = data
                simulation.metadata["last_environment_update"] = datetime.utcnow().isoformat()

    async def _process_simulation_queue(self):
        """Process the simulation queue."""
        while self.is_running:
            try:
                task = await self.simulation_queue.get()
                parameters = task['parameters']
                
                await self.run_simulation(parameters)
                
                self.simulation_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing simulation queue: {str(e)}")
                await asyncio.sleep(1)

    async def _process_environment_queue(self):
        """Process the environment queue."""
        while self.is_running:
            try:
                task = await self.environment_queue.get()
                data = task['data']
                
                await self.process_environmental_data(data)
                
                self.environment_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing environment queue: {str(e)}")
                await asyncio.sleep(1)

    async def _process_parameter_queue(self):
        """Process the parameter queue."""
        while self.is_running:
            try:
                task = await self.parameter_queue.get()
                species_id = task['species_id']
                parameters = task['parameters']
                
                await self.update_parameters(species_id, parameters)
                
                self.parameter_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing parameter queue: {str(e)}")
                await asyncio.sleep(1) 