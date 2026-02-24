"""
Mycosoft Multi-Agent System (MAS) - Petri Dish Simulator Agent

This module implements the PetriDishSimulatorAgent, which manages growth simulations
and processes environmental data for petri dish experiments.
"""

import asyncio
import logging
import json
import os
import numpy as np
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus
from mycosoft_mas.simulation.physics import PhysicsSimulator
from mycosoft_mas.simulation.petri_persistence import (
    save_simulation_state,
    load_simulation_state,
    notify_nlm_petri_outcome,
)

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
        self.petridishsim_url = config.get("petridishsim_url") or os.environ.get("PETRIDISHSIM_URL", "")
        self.chemical_fields: Dict[str, np.ndarray] = {}

    def initialize_chemical_fields(self, fields: Dict[str, List[List[float]]]) -> None:
        self.chemical_fields = {
            name: np.array(grid, dtype=np.float32) for name, grid in fields.items()
        }

    async def step_chemical_simulation(
        self,
        dt: float,
        diffusion_rates: Dict[str, float],
        reaction_params: Dict[str, Dict[str, float]],
        decay_rates: Optional[Dict[str, float]] = None,
    ) -> Dict[str, np.ndarray]:
        if not self.petridishsim_url:
            raise ValueError("PETRIDISHSIM_URL is not configured.")
        if not self.chemical_fields:
            raise ValueError("Chemical fields not initialized.")

        payload = {
            "fields": {k: v.tolist() for k, v in self.chemical_fields.items()},
            "diffusion_rates": diffusion_rates,
            "decay_rates": decay_rates or {},
            "dt": dt,
            "reaction_params": reaction_params,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(f"{self.petridishsim_url}/chemical/step", json=payload)
            response.raise_for_status()
            data = response.json()

        self.chemical_fields = {
            name: np.array(grid, dtype=np.float32) for name, grid in data.get("fields", {}).items()
        }
        return self.chemical_fields

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

            # Notify NLM for learning workflows
            asyncio.create_task(notify_nlm_petri_outcome(
                session_id=simulation_id,
                outcome_type="simulation_complete",
                summary={"species_id": parameters.species_id, "biomass_final": result.biomass_values[-1] if result.biomass_values else 0},
                metrics={"time_points": len(result.time_points), "phases": len(result.growth_phases)},
            ))
            
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

    def _dict_to_env_conditions(self, d: Dict[str, Any]) -> EnvironmentalConditions:
        """Reconstruct EnvironmentalConditions from dict."""
        ts = d.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                ts = datetime.utcnow()
        elif ts is None:
            ts = datetime.utcnow()
        return EnvironmentalConditions(
            temperature=float(d.get("temperature", 24.0)),
            humidity=float(d.get("humidity", 80.0)),
            ph=float(d.get("ph", 6.0)),
            light_intensity=float(d.get("light_intensity", 0.0)),
            co2_level=float(d.get("co2_level", 500.0)),
            nutrients=dict(d.get("nutrients") or {}),
            timestamp=ts,
        )

    def _dict_to_growth_parameters(self, d: Dict[str, Any]) -> GrowthParameters:
        """Reconstruct GrowthParameters from dict."""
        opt = d.get("optimal_conditions") or {}
        opt_cond = self._dict_to_env_conditions(opt) if isinstance(opt, dict) else EnvironmentalConditions(
            temperature=24.0, humidity=80.0, ph=6.0, light_intensity=0.0, co2_level=500.0,
            nutrients={}, timestamp=datetime.utcnow(),
        )
        return GrowthParameters(
            species_id=str(d.get("species_id", "")),
            initial_biomass=float(d.get("initial_biomass", 0.001)),
            growth_rate=float(d.get("growth_rate", 0.1)),
            optimal_conditions=opt_cond,
            tolerance_ranges=dict(d.get("tolerance_ranges") or {}),
            metadata=dict(d.get("metadata") or {}),
        )

    def _dict_to_simulation_result(self, d: Dict[str, Any]) -> Optional[SimulationResult]:
        """Reconstruct SimulationResult from dict. Returns None if invalid."""
        try:
            params_d = d.get("parameters") or {}
            params = self._dict_to_growth_parameters(params_d) if isinstance(params_d, dict) else None
            if params is None:
                params = self._dict_to_growth_parameters({"species_id": "unknown"})
            time_points: List[datetime] = []
            for tp in d.get("time_points") or []:
                if isinstance(tp, str):
                    try:
                        time_points.append(datetime.fromisoformat(tp.replace("Z", "+00:00")))
                    except Exception:
                        pass
            env_data: List[EnvironmentalConditions] = []
            for ed in d.get("environmental_data") or []:
                if isinstance(ed, dict):
                    env_data.append(self._dict_to_env_conditions(ed))
            growth_phases: List[Tuple[datetime, GrowthPhase]] = []
            for gp in d.get("growth_phases") or []:
                if isinstance(gp, (list, tuple)) and len(gp) >= 2:
                    dt_val = gp[0]
                    if isinstance(dt_val, str):
                        try:
                            dt_val = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
                        except Exception:
                            continue
                    phase_val = gp[1]
                    if isinstance(phase_val, str):
                        try:
                            phase_val = GrowthPhase(phase_val)
                        except ValueError:
                            phase_val = GrowthPhase.LAG
                    growth_phases.append((dt_val, phase_val))
            created = d.get("created_at")
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except Exception:
                    created = datetime.utcnow()
            elif created is None:
                created = datetime.utcnow()
            return SimulationResult(
                simulation_id=str(d.get("simulation_id", "")),
                parameters=params,
                time_points=time_points,
                biomass_values=[float(x) for x in (d.get("biomass_values") or [])],
                environmental_data=env_data,
                growth_phases=growth_phases,
                metadata=dict(d.get("metadata") or {}),
                created_at=created,
            )
        except Exception as e:
            self.logger.warning("Could not reconstruct SimulationResult: %s", e)
            return None

    async def _load_simulation_data(self):
        """Load simulation data from storage."""
        sims_raw, params_raw = load_simulation_state()
        for sid, p in params_raw.items():
            if isinstance(p, dict):
                try:
                    self.parameters[sid] = self._dict_to_growth_parameters(p)
                except Exception as e:
                    self.logger.debug("Skip loading parameter %s: %s", sid, e)
        for sid, s in sims_raw.items():
            if isinstance(s, dict):
                rec = self._dict_to_simulation_result(s)
                if rec:
                    self.simulations[sid] = rec

    async def _save_simulation_data(self):
        """Save simulation data to storage."""
        mindex_url = os.environ.get("MINDEX_API_URL")
        save_simulation_state(
            self.simulations,
            self.parameters,
            mindex_url=mindex_url,
        )

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
            chemical_config = parameters.metadata.get("chemical_simulation") if parameters.metadata else None
            if chemical_config:
                if "fields" in chemical_config and not self.chemical_fields:
                    self.initialize_chemical_fields(chemical_config["fields"])
                diffusion_rates = chemical_config.get("diffusion_rates", {})
                reaction_params = chemical_config.get("reaction_params", {})
                decay_rates = chemical_config.get("decay_rates", {})
                dt = chemical_config.get("dt")
                if diffusion_rates and reaction_params and dt:
                    try:
                        await self.step_chemical_simulation(
                            dt=float(dt),
                            diffusion_rates=diffusion_rates,
                            reaction_params=reaction_params,
                            decay_rates=decay_rates,
                        )
                    except Exception as exc:
                        self.logger.warning(f"Chemical simulation step failed: {exc}")

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