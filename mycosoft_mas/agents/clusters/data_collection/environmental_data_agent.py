"""
Mycosoft Multi-Agent System (MAS) - Environmental Data Agent

This module implements the EnvironmentalDataAgent, which manages environmental data collection,
processing, and analysis for mycology research.
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

class EnvironmentalFactor(Enum):
    """Enumeration of environmental factors."""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    CO2 = "co2"
    LIGHT = "light"
    PH = "ph"
    NUTRIENTS = "nutrients"
    AIR_FLOW = "air_flow"
    PRESSURE = "pressure"

class DataQuality(Enum):
    """Enumeration of data quality levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

@dataclass
class EnvironmentalReading:
    """Data class for storing environmental readings."""
    reading_id: str
    timestamp: datetime
    factor: EnvironmentalFactor
    value: float
    unit: str
    quality: DataQuality
    device_id: str
    metadata: Dict[str, Any]

@dataclass
class EnvironmentalDataset:
    """Data class for storing environmental datasets."""
    dataset_id: str
    name: str
    description: str
    start_time: datetime
    end_time: datetime
    readings: List[EnvironmentalReading]
    metadata: Dict[str, Any]

@dataclass
class EnvironmentalAnalysis:
    """Data class for storing environmental analysis results."""
    analysis_id: str
    dataset_id: str
    timestamp: datetime
    factor: EnvironmentalFactor
    mean: float
    std: float
    min: float
    max: float
    trend: str
    anomalies: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class EnvironmentalDataAgent(BaseAgent):
    """
    Agent responsible for managing environmental data collection, processing,
    and analysis for mycology research.
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the EnvironmentalDataAgent."""
        super().__init__(agent_id, name, config)
        
        # Initialize storage
        self.datasets: Dict[str, EnvironmentalDataset] = {}
        self.analyses: Dict[str, List[EnvironmentalAnalysis]] = {}
        self.active_collections: Set[str] = set()
        
        # Initialize directories
        self.data_dir = Path(config.get('data_dir', 'data/environmental'))
        self.analysis_dir = Path(config.get('analysis_dir', 'data/analysis'))
        
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize queues
        self.collection_queue = asyncio.Queue()
        self.processing_queue = asyncio.Queue()
        self.analysis_queue = asyncio.Queue()
        
        # Initialize metrics
        self.metrics.update({
            "datasets_created": 0,
            "readings_collected": 0,
            "analyses_performed": 0,
            "anomalies_detected": 0,
            "processing_errors": 0
        })

    async def initialize(self) -> bool:
        """Initialize the agent and its services."""
        try:
            self.status = AgentStatus.INITIALIZING
            self.logger.info(f"Initializing EnvironmentalDataAgent {self.name}")
            
            # Load existing datasets
            await self._load_datasets()
            
            # Start background tasks
            self.background_tasks.extend([
                asyncio.create_task(self._process_collection_queue()),
                asyncio.create_task(self._process_processing_queue()),
                asyncio.create_task(self._process_analysis_queue())
            ])
            
            self.status = AgentStatus.ACTIVE
            self.is_running = True
            self.metrics["start_time"] = datetime.now()
            
            self.logger.info(f"EnvironmentalDataAgent {self.name} initialized successfully")
            return True
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to initialize EnvironmentalDataAgent {self.name}: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop the agent and cleanup resources."""
        try:
            self.logger.info(f"Stopping EnvironmentalDataAgent {self.name}")
            self.is_running = False
            
            # Stop all active collections
            for dataset_id in self.active_collections:
                await self.stop_collection(dataset_id)
            
            # Save datasets
            await self._save_datasets()
            
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
            
            self.logger.info(f"EnvironmentalDataAgent {self.name} stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping EnvironmentalDataAgent {self.name}: {str(e)}")
            return False

    async def create_dataset(self, name: str, description: str, metadata: Dict[str, Any]) -> str:
        """
        Create a new environmental dataset.
        
        Args:
            name: Name of the dataset
            description: Description of the dataset
            metadata: Additional metadata
            
        Returns:
            str: ID of the created dataset
        """
        try:
            # Generate dataset ID
            dataset_id = f"env_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create dataset
            dataset = EnvironmentalDataset(
                dataset_id=dataset_id,
                name=name,
                description=description,
                start_time=datetime.now(),
                end_time=datetime.now(),
                readings=[],
                metadata=metadata
            )
            
            # Store dataset
            self.datasets[dataset_id] = dataset
            
            # Save dataset
            await self._save_dataset(dataset_id)
            
            self.metrics["datasets_created"] += 1
            self.logger.info(f"Created dataset: {dataset_id}")
            return dataset_id
            
        except Exception as e:
            self.logger.error(f"Error creating dataset: {str(e)}")
            return ""

    async def start_collection(self, dataset_id: str, device_id: str, factors: List[EnvironmentalFactor], interval: int) -> bool:
        """
        Start collecting environmental data.
        
        Args:
            dataset_id: ID of the dataset to collect data for
            device_id: ID of the device to collect data from
            factors: List of environmental factors to collect
            interval: Collection interval in seconds
            
        Returns:
            bool: True if collection was started successfully, False otherwise
        """
        try:
            # Check if dataset exists
            if dataset_id not in self.datasets:
                raise ValueError(f"Dataset not found: {dataset_id}")
            
            # Check if collection is already active
            if dataset_id in self.active_collections:
                raise ValueError(f"Collection already active for dataset: {dataset_id}")
            
            # Add to collection queue
            await self.collection_queue.put({
                "dataset_id": dataset_id,
                "device_id": device_id,
                "factors": factors,
                "interval": interval,
                "action": "start"
            })
            
            self.logger.info(f"Queued collection start for dataset: {dataset_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting collection for dataset {dataset_id}: {str(e)}")
            return False

    async def stop_collection(self, dataset_id: str) -> bool:
        """
        Stop collecting environmental data.
        
        Args:
            dataset_id: ID of the dataset to stop collecting data for
            
        Returns:
            bool: True if collection was stopped successfully, False otherwise
        """
        try:
            # Check if dataset exists
            if dataset_id not in self.datasets:
                raise ValueError(f"Dataset not found: {dataset_id}")
            
            # Check if collection is active
            if dataset_id not in self.active_collections:
                raise ValueError(f"Collection not active for dataset: {dataset_id}")
            
            # Add to collection queue
            await self.collection_queue.put({
                "dataset_id": dataset_id,
                "action": "stop"
            })
            
            self.logger.info(f"Queued collection stop for dataset: {dataset_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping collection for dataset {dataset_id}: {str(e)}")
            return False

    async def add_reading(self, dataset_id: str, reading: EnvironmentalReading) -> bool:
        """
        Add an environmental reading to a dataset.
        
        Args:
            dataset_id: ID of the dataset to add reading to
            reading: The reading to add
            
        Returns:
            bool: True if reading was added successfully, False otherwise
        """
        try:
            # Check if dataset exists
            if dataset_id not in self.datasets:
                raise ValueError(f"Dataset not found: {dataset_id}")
            
            # Add to processing queue
            await self.processing_queue.put({
                "dataset_id": dataset_id,
                "reading": reading
            })
            
            self.logger.info(f"Queued reading for dataset: {dataset_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding reading to dataset {dataset_id}: {str(e)}")
            return False

    async def analyze_dataset(self, dataset_id: str, factors: Optional[List[EnvironmentalFactor]] = None) -> bool:
        """
        Analyze an environmental dataset.
        
        Args:
            dataset_id: ID of the dataset to analyze
            factors: List of environmental factors to analyze, or None for all factors
            
        Returns:
            bool: True if analysis was started successfully, False otherwise
        """
        try:
            # Check if dataset exists
            if dataset_id not in self.datasets:
                raise ValueError(f"Dataset not found: {dataset_id}")
            
            # Add to analysis queue
            await self.analysis_queue.put({
                "dataset_id": dataset_id,
                "factors": factors
            })
            
            self.logger.info(f"Queued analysis for dataset: {dataset_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error analyzing dataset {dataset_id}: {str(e)}")
            return False

    async def get_dataset(self, dataset_id: str) -> Optional[EnvironmentalDataset]:
        """
        Get an environmental dataset.
        
        Args:
            dataset_id: ID of the dataset to get
            
        Returns:
            Optional[EnvironmentalDataset]: The dataset, or None if not found
        """
        try:
            # Check if dataset exists
            if dataset_id not in self.datasets:
                raise ValueError(f"Dataset not found: {dataset_id}")
            
            return self.datasets[dataset_id]
            
        except Exception as e:
            self.logger.error(f"Error getting dataset {dataset_id}: {str(e)}")
            return None

    async def get_analysis(self, dataset_id: str, factor: Optional[EnvironmentalFactor] = None) -> List[EnvironmentalAnalysis]:
        """
        Get analysis results for a dataset.
        
        Args:
            dataset_id: ID of the dataset to get analysis for
            factor: Environmental factor to get analysis for, or None for all factors
            
        Returns:
            List[EnvironmentalAnalysis]: List of analysis results
        """
        try:
            # Check if dataset exists
            if dataset_id not in self.datasets:
                raise ValueError(f"Dataset not found: {dataset_id}")
            
            # Get analyses
            analyses = self.analyses.get(dataset_id, [])
            
            # Filter by factor if specified
            if factor:
                analyses = [a for a in analyses if a.factor == factor]
            
            return analyses
            
        except Exception as e:
            self.logger.error(f"Error getting analysis for dataset {dataset_id}: {str(e)}")
            return []

    async def _load_datasets(self):
        """Load datasets from storage."""
        try:
            # Load dataset files
            for file_path in self.data_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                        # Convert to EnvironmentalDataset
                        dataset = self._dict_to_dataset(data)
                        
                        # Store dataset
                        self.datasets[dataset.dataset_id] = dataset
                        self.analyses[dataset.dataset_id] = []
                        
                        self.logger.info(f"Loaded dataset: {dataset.dataset_id}")
                except Exception as e:
                    self.logger.error(f"Error loading dataset from {file_path}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error loading datasets: {str(e)}")

    async def _save_datasets(self):
        """Save datasets to storage."""
        try:
            # Save each dataset
            for dataset_id, dataset in self.datasets.items():
                try:
                    # Convert to dictionary
                    data = self._dataset_to_dict(dataset)
                    
                    # Save to file
                    file_path = self.data_dir / f"{dataset_id}.json"
                    with open(file_path, 'w') as f:
                        json.dump(data, f, default=str)
                except Exception as e:
                    self.logger.error(f"Error saving dataset {dataset_id}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error saving datasets: {str(e)}")

    async def _save_dataset(self, dataset_id: str):
        """Save a dataset to storage."""
        try:
            if dataset_id in self.datasets:
                # Convert to dictionary
                data = self._dataset_to_dict(self.datasets[dataset_id])
                
                # Save to file
                file_path = self.data_dir / f"{dataset_id}.json"
                with open(file_path, 'w') as f:
                    json.dump(data, f, default=str)
        except Exception as e:
            self.logger.error(f"Error saving dataset {dataset_id}: {str(e)}")

    async def _process_collection_queue(self):
        """Process the collection queue."""
        while self.is_running:
            try:
                task = await self.collection_queue.get()
                dataset_id = task.get('dataset_id')
                action = task.get('action')
                
                if dataset_id in self.datasets:
                    if action == 'start':
                        # Start collection
                        device_id = task.get('device_id')
                        factors = task.get('factors')
                        interval = task.get('interval')
                        
                        # This is a placeholder for actual collection logic
                        # In a real implementation, this would start a background task
                        # to collect data at the specified interval
                        
                        self.active_collections.add(dataset_id)
                        self.logger.info(f"Started collection for dataset: {dataset_id}")
                    elif action == 'stop':
                        # Stop collection
                        self.active_collections.remove(dataset_id)
                        self.logger.info(f"Stopped collection for dataset: {dataset_id}")
                
                self.collection_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing collection queue: {str(e)}")
                await asyncio.sleep(1)

    async def _process_processing_queue(self):
        """Process the processing queue."""
        while self.is_running:
            try:
                task = await self.processing_queue.get()
                dataset_id = task.get('dataset_id')
                reading = task.get('reading')
                
                if dataset_id in self.datasets:
                    # Add reading to dataset
                    self.datasets[dataset_id].readings.append(reading)
                    self.datasets[dataset_id].end_time = reading.timestamp
                    
                    # Save dataset
                    await self._save_dataset(dataset_id)
                    
                    self.metrics["readings_collected"] += 1
                
                self.processing_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing processing queue: {str(e)}")
                self.metrics["processing_errors"] += 1
                await asyncio.sleep(1)

    async def _process_analysis_queue(self):
        """Process the analysis queue."""
        while self.is_running:
            try:
                task = await self.analysis_queue.get()
                dataset_id = task.get('dataset_id')
                factors = task.get('factors')
                
                if dataset_id in self.datasets:
                    # Get dataset
                    dataset = self.datasets[dataset_id]
                    
                    # Get factors to analyze
                    if factors is None:
                        factors = list(set(r.factor for r in dataset.readings))
                    
                    # Analyze each factor
                    for factor in factors:
                        # Get readings for factor
                        readings = [r for r in dataset.readings if r.factor == factor]
                        
                        if readings:
                            # Calculate statistics
                            values = [r.value for r in readings]
                            mean = np.mean(values)
                            std = np.std(values)
                            min_val = np.min(values)
                            max_val = np.max(values)
                            
                            # Calculate trend
                            trend = self._calculate_trend(values)
                            
                            # Detect anomalies
                            anomalies = self._detect_anomalies(values, mean, std)
                            
                            # Create analysis
                            analysis = EnvironmentalAnalysis(
                                analysis_id=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                dataset_id=dataset_id,
                                timestamp=datetime.now(),
                                factor=factor,
                                mean=mean,
                                std=std,
                                min=min_val,
                                max=max_val,
                                trend=trend,
                                anomalies=anomalies,
                                metadata={}
                            )
                            
                            # Store analysis
                            if dataset_id not in self.analyses:
                                self.analyses[dataset_id] = []
                            self.analyses[dataset_id].append(analysis)
                            
                            # Save analysis
                            file_path = self.analysis_dir / f"{analysis.analysis_id}.json"
                            with open(file_path, 'w') as f:
                                json.dump(self._analysis_to_dict(analysis), f, default=str)
                            
                            self.metrics["analyses_performed"] += 1
                            self.metrics["anomalies_detected"] += len(anomalies)
                
                self.analysis_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing analysis queue: {str(e)}")
                await asyncio.sleep(1)

    def _calculate_trend(self, values: List[float]) -> str:
        """
        Calculate the trend of a series of values.
        
        Args:
            values: List of values
            
        Returns:
            str: Trend description
        """
        try:
            # Convert to numpy array
            arr = np.array(values)
            
            # Calculate linear regression
            x = np.arange(len(arr))
            slope, _ = np.polyfit(x, arr, 1)
            
            # Determine trend
            if slope > 0.1:
                return "increasing"
            elif slope < -0.1:
                return "decreasing"
            else:
                return "stable"
        except Exception:
            return "unknown"

    def _detect_anomalies(self, values: List[float], mean: float, std: float, threshold: float = 3.0) -> List[Dict[str, Any]]:
        """
        Detect anomalies in a series of values.
        
        Args:
            values: List of values
            mean: Mean of the values
            std: Standard deviation of the values
            threshold: Threshold for anomaly detection
            
        Returns:
            List[Dict[str, Any]]: List of anomalies
        """
        try:
            anomalies = []
            
            # Calculate z-scores
            z_scores = np.abs((values - mean) / std)
            
            # Find anomalies
            for i, z_score in enumerate(z_scores):
                if z_score > threshold:
                    anomalies.append({
                        "index": i,
                        "value": values[i],
                        "z_score": z_score
                    })
            
            return anomalies
        except Exception:
            return []

    def _dataset_to_dict(self, dataset: EnvironmentalDataset) -> Dict[str, Any]:
        """Convert EnvironmentalDataset to dictionary."""
        return {
            "dataset_id": dataset.dataset_id,
            "name": dataset.name,
            "description": dataset.description,
            "start_time": dataset.start_time,
            "end_time": dataset.end_time,
            "readings": [self._reading_to_dict(r) for r in dataset.readings],
            "metadata": dataset.metadata
        }

    def _dict_to_dataset(self, data: Dict[str, Any]) -> EnvironmentalDataset:
        """Convert dictionary to EnvironmentalDataset."""
        return EnvironmentalDataset(
            dataset_id=data.get("dataset_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            start_time=datetime.fromisoformat(data.get("start_time", datetime.now().isoformat())),
            end_time=datetime.fromisoformat(data.get("end_time", datetime.now().isoformat())),
            readings=[self._dict_to_reading(r) for r in data.get("readings", [])],
            metadata=data.get("metadata", {})
        )

    def _reading_to_dict(self, reading: EnvironmentalReading) -> Dict[str, Any]:
        """Convert EnvironmentalReading to dictionary."""
        return {
            "reading_id": reading.reading_id,
            "timestamp": reading.timestamp,
            "factor": reading.factor.value,
            "value": reading.value,
            "unit": reading.unit,
            "quality": reading.quality.value,
            "device_id": reading.device_id,
            "metadata": reading.metadata
        }

    def _dict_to_reading(self, data: Dict[str, Any]) -> EnvironmentalReading:
        """Convert dictionary to EnvironmentalReading."""
        return EnvironmentalReading(
            reading_id=data.get("reading_id", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            factor=EnvironmentalFactor(data.get("factor", "temperature")),
            value=data.get("value", 0.0),
            unit=data.get("unit", ""),
            quality=DataQuality(data.get("quality", "unknown")),
            device_id=data.get("device_id", ""),
            metadata=data.get("metadata", {})
        )

    def _analysis_to_dict(self, analysis: EnvironmentalAnalysis) -> Dict[str, Any]:
        """Convert EnvironmentalAnalysis to dictionary."""
        return {
            "analysis_id": analysis.analysis_id,
            "dataset_id": analysis.dataset_id,
            "timestamp": analysis.timestamp,
            "factor": analysis.factor.value,
            "mean": analysis.mean,
            "std": analysis.std,
            "min": analysis.min,
            "max": analysis.max,
            "trend": analysis.trend,
            "anomalies": analysis.anomalies,
            "metadata": analysis.metadata
        } 