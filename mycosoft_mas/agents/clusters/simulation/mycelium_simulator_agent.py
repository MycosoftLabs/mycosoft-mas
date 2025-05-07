"""
Mycosoft Multi-Agent System (MAS) - Mycelium Simulator Agent

This module implements the MyceliumSimulatorAgent, which integrates with the web-based
petri dish simulator, handling data processing, logging, and communication with other agents.
"""

import asyncio
import logging
import json
import os
import base64
import aiofiles
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import contextlib

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

class SimulatorMode(Enum):
    """Enumeration of simulator modes."""
    WEB = "web"
    MOBILE = "mobile"
    API = "api"
    WEBSOCKET = "websocket"

class DataFormat(Enum):
    """Enumeration of data formats."""
    JSON = "json"
    WEBP = "webp"
    MP4 = "mp4"
    PNG = "png"
    JPG = "jpg"

@dataclass
class SimulationConfig:
    """Data class for storing simulation configuration."""
    species: str
    agar_type: str
    ph: float
    temperature: float
    humidity: float
    speed: int
    contaminants: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class SimulationData:
    """Data class for storing simulation data."""
    id: str
    config: SimulationConfig
    virtual_hours: int
    samples: List[Dict[str, Any]]
    contaminants: List[Dict[str, Any]]
    nutrient_grid: List[List[float]]
    occupancy_grid: List[List[Any]]
    antifungal_grid: List[List[float]]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class SimulationResult:
    """Data class for storing simulation results."""
    id: str
    data: SimulationData
    json_data: Dict[str, Any]
    video_path: Optional[str] = None
    screenshots: List[str] = None
    metrics: Dict[str, Any] = None
    created_at: datetime = None

class MyceliumSimulatorAgent(BaseAgent):
    """
    Agent responsible for integrating with the web-based petri dish simulator.
    
    This agent handles data processing, logging, and communication with other agents
    for the mycelium simulation system.
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the MyceliumSimulatorAgent."""
        super().__init__(agent_id, name, config)
        
        # Initialize storage
        self.simulations: Dict[str, SimulationData] = {}
        self.results: Dict[str, SimulationResult] = {}
        
        # Initialize directories
        self.data_dir = Path(config.get('data_dir', 'data/simulations'))
        self.video_dir = Path(config.get('video_dir', 'data/videos'))
        self.screenshot_dir = Path(config.get('screenshot_dir', 'data/screenshots'))
        
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize queues
        self.simulation_queue = asyncio.Queue()
        self.data_queue = asyncio.Queue()
        self.export_queue = asyncio.Queue()
        
        # Initialize mode
        self.mode = SimulatorMode.WEB
        
        # Initialize metrics
        self.metrics.update({
            "simulations_created": 0,
            "simulations_loaded": 0,
            "simulations_saved": 0,
            "simulations_exported": 0,
            "videos_processed": 0,
            "screenshots_processed": 0
        })

    async def initialize(self) -> bool:
        """Initialize the agent and its services."""
        try:
            self.status = AgentStatus.INITIALIZING
            self.logger.info(f"Initializing MyceliumSimulatorAgent {self.name}")
            
            # Load existing simulations
            await self._load_simulations()
            
            # Start background tasks
            self.background_tasks.extend([
                asyncio.create_task(self._process_simulation_queue()),
                asyncio.create_task(self._process_data_queue()),
                asyncio.create_task(self._process_export_queue())
            ])
            
            self.status = AgentStatus.ACTIVE
            self.is_running = True
            self.metrics["start_time"] = datetime.now()
            
            self.logger.info(f"MyceliumSimulatorAgent {self.name} initialized successfully")
            return True
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to initialize MyceliumSimulatorAgent {self.name}: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop the agent and cleanup resources."""
        try:
            self.logger.info(f"Stopping MyceliumSimulatorAgent {self.name}")
            self.is_running = False
            
            # Save simulations
            await self._save_simulations()
            
            # Cancel background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
            
            self.background_tasks = []
            self.status = AgentStatus.STOPPED
            
            self.logger.info(f"MyceliumSimulatorAgent {self.name} stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping MyceliumSimulatorAgent {self.name}: {str(e)}")
            return False

    async def create_simulation(self, config: SimulationConfig) -> str:
        """
        Create a new simulation.
        
        Args:
            config: The simulation configuration
            
        Returns:
            str: ID of the created simulation
        """
        try:
            # Generate simulation ID
            simulation_id = f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create simulation data
            simulation = SimulationData(
                id=simulation_id,
                config=config,
                virtual_hours=0,
                samples=[],
                contaminants=[],
                nutrient_grid=[],
                occupancy_grid=[],
                antifungal_grid=[],
                metadata={},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store simulation
            self.simulations[simulation_id] = simulation
            self.metrics["simulations_created"] += 1
            
            self.logger.info(f"Created simulation: {simulation_id}")
            return simulation_id
            
        except Exception as e:
            self.logger.error(f"Error creating simulation: {str(e)}")
            return None

    async def update_simulation(self, simulation_id: str, data: Dict[str, Any]) -> bool:
        """
        Update an existing simulation with new data.
        
        Args:
            simulation_id: ID of the simulation to update
            data: The new simulation data
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            if simulation_id not in self.simulations:
                raise ValueError(f"Simulation not found: {simulation_id}")
            
            simulation = self.simulations[simulation_id]
            
            # Update simulation data
            if "virtual_hours" in data:
                simulation.virtual_hours = data["virtual_hours"]
            
            if "samples" in data:
                simulation.samples = data["samples"]
            
            if "contaminants" in data:
                simulation.contaminants = data["contaminants"]
            
            if "nutrient_grid" in data:
                simulation.nutrient_grid = data["nutrient_grid"]
            
            if "occupancy_grid" in data:
                simulation.occupancy_grid = data["occupancy_grid"]
            
            if "antifungal_grid" in data:
                simulation.antifungal_grid = data["antifungal_grid"]
            
            if "metadata" in data:
                simulation.metadata.update(data["metadata"])
            
            simulation.updated_at = datetime.now()
            
            # Add to data queue for processing
            await self.data_queue.put({
                "simulation_id": simulation_id,
                "action": "update"
            })
            
            self.logger.info(f"Updated simulation: {simulation_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating simulation {simulation_id}: {str(e)}")
            return False

    async def export_simulation(self, simulation_id: str, formats: List[DataFormat]) -> SimulationResult:
        """
        Export a simulation in specified formats.
        
        Args:
            simulation_id: ID of the simulation to export
            formats: List of formats to export in
            
        Returns:
            SimulationResult containing the exported data
        """
        try:
            if simulation_id not in self.simulations:
                raise ValueError(f"Simulation not found: {simulation_id}")
            
            simulation = self.simulations[simulation_id]
            
            # Generate result ID
            result_id = f"result_{simulation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create result
            result = SimulationResult(
                id=result_id,
                data=simulation,
                json_data={},
                video_path=None,
                screenshots=[],
                metrics={},
                created_at=datetime.now()
            )
            
            # Add to export queue
            await self.export_queue.put({
                "result_id": result_id,
                "simulation_id": simulation_id,
                "formats": formats
            })
            
            self.logger.info(f"Queued simulation for export: {simulation_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error exporting simulation {simulation_id}: {str(e)}")
            return None

    async def get_simulation(self, simulation_id: str) -> SimulationData:
        """
        Get a simulation by ID.
        
        Args:
            simulation_id: ID of the simulation to get
            
        Returns:
            SimulationData containing the simulation data
        """
        try:
            if simulation_id not in self.simulations:
                raise ValueError(f"Simulation not found: {simulation_id}")
            
            return self.simulations[simulation_id]
            
        except Exception as e:
            self.logger.error(f"Error getting simulation {simulation_id}: {str(e)}")
            return None

    async def get_result(self, result_id: str) -> SimulationResult:
        """
        Get a simulation result by ID.
        
        Args:
            result_id: ID of the result to get
            
        Returns:
            SimulationResult containing the result data
        """
        try:
            if result_id not in self.results:
                raise ValueError(f"Result not found: {result_id}")
            
            return self.results[result_id]
            
        except Exception as e:
            self.logger.error(f"Error getting result {result_id}: {str(e)}")
            return None

    async def set_mode(self, mode: SimulatorMode) -> bool:
        """
        Set the simulator mode.
        
        Args:
            mode: The new simulator mode
            
        Returns:
            bool: True if mode was set successfully, False otherwise
        """
        try:
            self.mode = mode
            self.logger.info(f"Set simulator mode to: {mode.value}")
            return True
        except Exception as e:
            self.logger.error(f"Error setting simulator mode: {str(e)}")
            return False

    async def _load_simulations(self):
        """Load simulations from storage."""
        try:
            # Load simulation files
            for file_path in self.data_dir.glob("*.json"):
                try:
                    async with aiofiles.open(file_path, 'r') as f:
                        data = json.loads(await f.read())
                        
                        # Convert to SimulationData
                        simulation = self._dict_to_simulation_data(data)
                        
                        # Store simulation
                        self.simulations[simulation.id] = simulation
                        self.metrics["simulations_loaded"] += 1
                        
                        self.logger.info(f"Loaded simulation: {simulation.id}")
                except Exception as e:
                    self.logger.error(f"Error loading simulation from {file_path}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error loading simulations: {str(e)}")

    async def _save_simulations(self):
        """Save simulations to storage."""
        try:
            # Save each simulation
            for simulation_id, simulation in self.simulations.items():
                try:
                    # Convert to dictionary
                    data = self._simulation_data_to_dict(simulation)
                    
                    # Save to file
                    file_path = self.data_dir / f"{simulation_id}.json"
                    async with aiofiles.open(file_path, 'w') as f:
                        await f.write(json.dumps(data, default=str))
                    
                    self.metrics["simulations_saved"] += 1
                except Exception as e:
                    self.logger.error(f"Error saving simulation {simulation_id}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error saving simulations: {str(e)}")

    async def _process_simulation_queue(self):
        """Process the simulation queue."""
        while self.is_running:
            try:
                task = await self.simulation_queue.get()
                action = task.get('action')
                
                if action == 'create':
                    config = task.get('config')
                    await self.create_simulation(config)
                elif action == 'delete':
                    simulation_id = task.get('simulation_id')
                    if simulation_id in self.simulations:
                        del self.simulations[simulation_id]
                
                self.simulation_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing simulation queue: {str(e)}")
                await asyncio.sleep(1)

    async def _process_data_queue(self):
        """Process the data queue."""
        while self.is_running:
            try:
                task = await self.data_queue.get()
                simulation_id = task.get('simulation_id')
                action = task.get('action')
                
                if action == 'update' and simulation_id in self.simulations:
                    # Save simulation to file
                    simulation = self.simulations[simulation_id]
                    data = self._simulation_data_to_dict(simulation)
                    
                    file_path = self.data_dir / f"{simulation_id}.json"
                    async with aiofiles.open(file_path, 'w') as f:
                        await f.write(json.dumps(data, default=str))
                    
                    self.metrics["simulations_saved"] += 1
                
                self.data_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing data queue: {str(e)}")
                await asyncio.sleep(1)

    async def _process_export_queue(self):
        """Process the export queue."""
        while self.is_running:
            try:
                task = await self.export_queue.get()
                result_id = task.get('result_id')
                simulation_id = task.get('simulation_id')
                formats = task.get('formats', [])
                
                if simulation_id in self.simulations:
                    simulation = self.simulations[simulation_id]
                    
                    # Create result
                    result = SimulationResult(
                        id=result_id,
                        data=simulation,
                        json_data=self._simulation_data_to_dict(simulation),
                        video_path=None,
                        screenshots=[],
                        metrics={},
                        created_at=datetime.now()
                    )
                    
                    # Process each format
                    for format in formats:
                        if format == DataFormat.JSON:
                            # JSON is already processed
                            pass
                        elif format == DataFormat.WEBP:
                            # Process video
                            video_path = await self._process_video(simulation)
                            result.video_path = video_path
                            self.metrics["videos_processed"] += 1
                        elif format in [DataFormat.PNG, DataFormat.JPG]:
                            # Process screenshots
                            screenshot_path = await self._process_screenshot(simulation, format)
                            result.screenshots.append(screenshot_path)
                            self.metrics["screenshots_processed"] += 1
                    
                    # Store result
                    self.results[result_id] = result
                    self.metrics["simulations_exported"] += 1
                    
                    self.logger.info(f"Exported simulation {simulation_id} to formats: {[f.value for f in formats]}")
                
                self.export_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing export queue: {str(e)}")
                await asyncio.sleep(1)

    async def _process_video(self, simulation: SimulationData) -> str:
        """Process video for a simulation."""
        # This is a placeholder for video processing
        # In a real implementation, this would generate a video from the simulation data
        video_path = str(self.video_dir / f"{simulation.id}.webp")
        return video_path

    async def _process_screenshot(self, simulation: SimulationData, format: DataFormat) -> str:
        """Process screenshot for a simulation."""
        # This is a placeholder for screenshot processing
        # In a real implementation, this would generate a screenshot from the simulation data
        extension = format.value
        screenshot_path = str(self.screenshot_dir / f"{simulation.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}")
        return screenshot_path

    def _simulation_data_to_dict(self, simulation: SimulationData) -> Dict[str, Any]:
        """Convert SimulationData to dictionary."""
        return {
            "id": simulation.id,
            "config": {
                "species": simulation.config.species,
                "agar_type": simulation.config.agar_type,
                "ph": simulation.config.ph,
                "temperature": simulation.config.temperature,
                "humidity": simulation.config.humidity,
                "speed": simulation.config.speed,
                "contaminants": simulation.config.contaminants,
                "metadata": simulation.config.metadata,
                "created_at": simulation.config.created_at,
                "updated_at": simulation.config.updated_at
            },
            "virtual_hours": simulation.virtual_hours,
            "samples": simulation.samples,
            "contaminants": simulation.contaminants,
            "nutrient_grid": simulation.nutrient_grid,
            "occupancy_grid": simulation.occupancy_grid,
            "antifungal_grid": simulation.antifungal_grid,
            "metadata": simulation.metadata,
            "created_at": simulation.created_at,
            "updated_at": simulation.updated_at
        }

    def _dict_to_simulation_data(self, data: Dict[str, Any]) -> SimulationData:
        """Convert dictionary to SimulationData."""
        config_data = data.get("config", {})
        config = SimulationConfig(
            species=config_data.get("species", ""),
            agar_type=config_data.get("agar_type", ""),
            ph=config_data.get("ph", 6.0),
            temperature=config_data.get("temperature", 70.0),
            humidity=config_data.get("humidity", 70.0),
            speed=config_data.get("speed", 5),
            contaminants=config_data.get("contaminants", []),
            metadata=config_data.get("metadata", {}),
            created_at=datetime.fromisoformat(config_data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(config_data.get("updated_at", datetime.now().isoformat()))
        )
        
        return SimulationData(
            id=data.get("id", ""),
            config=config,
            virtual_hours=data.get("virtual_hours", 0),
            samples=data.get("samples", []),
            contaminants=data.get("contaminants", []),
            nutrient_grid=data.get("nutrient_grid", []),
            occupancy_grid=data.get("occupancy_grid", []),
            antifungal_grid=data.get("antifungal_grid", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        ) 