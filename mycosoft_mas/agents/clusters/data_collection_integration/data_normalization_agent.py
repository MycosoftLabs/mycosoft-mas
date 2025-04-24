"""
Data Normalization Agent for Mycology BioAgent System

This agent standardizes data formats across sources, maintains data schemas,
handles data transformation, and ensures consistency in MINDEX.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import json
import jsonschema
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class DataFormat(Enum):
    """Supported data formats"""
    JSON = auto()
    CSV = auto()
    XML = auto()
    YAML = auto()
    PROTOBUF = auto()
    CUSTOM = auto()

class NormalizationStatus(Enum):
    """Status of a normalization operation"""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass
class DataSchema:
    """Schema definition for data normalization"""
    schema_id: str
    name: str
    version: str
    format: DataFormat
    schema: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class NormalizationTask:
    """Configuration for a normalization task"""
    task_id: str
    source_format: DataFormat
    target_format: DataFormat
    data: Dict[str, Any]
    schema_id: Optional[str] = None
    custom_transformation: Optional[Dict[str, Any]] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class NormalizationResult:
    """Results of a normalization operation"""
    task_id: str
    source_format: DataFormat
    target_format: DataFormat
    normalized_data: Dict[str, Any]
    status: NormalizationStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class DataNormalizationAgent(BaseAgent):
    """Agent for standardizing data formats across sources"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.schemas: Dict[str, DataSchema] = {}
        self.normalization_tasks: Dict[str, NormalizationTask] = {}
        self.normalization_results: Dict[str, NormalizationResult] = {}
        self.normalization_queue: asyncio.Queue = asyncio.Queue()
        
        # Create necessary directories
        self.data_dir = Path("data/normalization")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics
        self.metrics.update({
            "schemas_loaded": 0,
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "data_points_normalized": 0,
            "normalization_errors": 0
        })
    
    async def initialize(self) -> None:
        """Initialize the agent"""
        await super().initialize()
        await self._load_schemas()
        self.status = AgentStatus.READY
        self.logger.info("Data Normalization Agent initialized")
    
    async def stop(self) -> None:
        """Stop the agent"""
        self.status = AgentStatus.STOPPING
        self.logger.info("Stopping Data Normalization Agent")
        await super().stop()
    
    async def register_schema(
        self,
        name: str,
        version: str,
        format: DataFormat,
        schema: Dict[str, Any]
    ) -> str:
        """Register a new data schema"""
        schema_id = f"schema_{len(self.schemas)}"
        
        data_schema = DataSchema(
            schema_id=schema_id,
            name=name,
            version=version,
            format=format,
            schema=schema
        )
        
        self.schemas[schema_id] = data_schema
        await self._save_schema(data_schema)
        
        self.metrics["schemas_loaded"] += 1
        return schema_id
    
    async def normalize_data(
        self,
        source_format: DataFormat,
        target_format: DataFormat,
        data: Dict[str, Any],
        schema_id: Optional[str] = None,
        custom_transformation: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> str:
        """Create a new normalization task"""
        task_id = f"normalize_{len(self.normalization_tasks)}"
        
        task = NormalizationTask(
            task_id=task_id,
            source_format=source_format,
            target_format=target_format,
            data=data,
            schema_id=schema_id,
            custom_transformation=custom_transformation,
            priority=priority
        )
        
        self.normalization_tasks[task_id] = task
        await self.normalization_queue.put(task)
        
        self.metrics["tasks_created"] += 1
        return task_id
    
    async def get_normalization_result(self, task_id: str) -> Optional[NormalizationResult]:
        """Get the results of a specific normalization task"""
        return self.normalization_results.get(task_id)
    
    async def _load_schemas(self) -> None:
        """Load schemas from disk"""
        schema_dir = self.data_dir / "schemas"
        schema_dir.mkdir(exist_ok=True)
        
        for schema_file in schema_dir.glob("*.json"):
            try:
                with open(schema_file, "r") as f:
                    schema_data = json.load(f)
                
                schema = DataSchema(
                    schema_id=schema_data["schema_id"],
                    name=schema_data["name"],
                    version=schema_data["version"],
                    format=DataFormat[schema_data["format"]],
                    schema=schema_data["schema"],
                    created_at=datetime.fromisoformat(schema_data["created_at"]),
                    updated_at=datetime.fromisoformat(schema_data["updated_at"])
                )
                
                self.schemas[schema.schema_id] = schema
                self.metrics["schemas_loaded"] += 1
                
            except Exception as e:
                self.logger.error(f"Error loading schema {schema_file}: {str(e)}")
    
    async def _save_schema(self, schema: DataSchema) -> None:
        """Save schema to disk"""
        schema_dir = self.data_dir / "schemas"
        schema_dir.mkdir(exist_ok=True)
        
        schema_file = schema_dir / f"{schema.schema_id}.json"
        
        schema_data = {
            "schema_id": schema.schema_id,
            "name": schema.name,
            "version": schema.version,
            "format": schema.format.name,
            "schema": schema.schema,
            "created_at": schema.created_at.isoformat(),
            "updated_at": schema.updated_at.isoformat()
        }
        
        with open(schema_file, "w") as f:
            json.dump(schema_data, f, indent=2)
    
    async def _process_normalization_queue(self) -> None:
        """Process the normalization queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next normalization task
                task = await self.normalization_queue.get()
                
                # Perform normalization
                result = await self._perform_normalization(task)
                
                # Store result
                self.normalization_results[task.task_id] = result
                
                # Update metrics
                if result.status == NormalizationStatus.COMPLETED:
                    self.metrics["tasks_completed"] += 1
                    self.metrics["data_points_normalized"] += self._count_data_points(result.normalized_data)
                else:
                    self.metrics["tasks_failed"] += 1
                    self.metrics["normalization_errors"] += 1
                
                # Mark task as complete
                self.normalization_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing normalization task: {str(e)}")
                self.metrics["normalization_errors"] += 1
                continue
    
    async def _perform_normalization(self, task: NormalizationTask) -> NormalizationResult:
        """Perform the actual normalization operation"""
        try:
            # Validate against schema if provided
            if task.schema_id and task.schema_id in self.schemas:
                schema = self.schemas[task.schema_id]
                jsonschema.validate(instance=task.data, schema=schema.schema)
            
            # Apply custom transformation if provided
            if task.custom_transformation:
                normalized_data = self._apply_custom_transformation(
                    task.data,
                    task.custom_transformation
                )
            else:
                normalized_data = self._apply_standard_transformation(
                    task.data,
                    task.source_format,
                    task.target_format
                )
            
            return NormalizationResult(
                task_id=task.task_id,
                source_format=task.source_format,
                target_format=task.target_format,
                normalized_data=normalized_data,
                status=NormalizationStatus.COMPLETED,
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Error performing normalization: {str(e)}")
            return NormalizationResult(
                task_id=task.task_id,
                source_format=task.source_format,
                target_format=task.target_format,
                normalized_data={},
                status=NormalizationStatus.FAILED,
                error_message=str(e),
                completed_at=datetime.utcnow()
            )
    
    def _apply_standard_transformation(
        self,
        data: Dict[str, Any],
        source_format: DataFormat,
        target_format: DataFormat
    ) -> Dict[str, Any]:
        """Apply standard transformation between formats"""
        # Implementation for standard transformation
        return data
    
    def _apply_custom_transformation(
        self,
        data: Dict[str, Any],
        transformation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply custom transformation"""
        # Implementation for custom transformation
        return data
    
    def _count_data_points(self, data: Dict[str, Any]) -> int:
        """Count the number of data points in the normalized data"""
        # Implementation for counting data points
        return 1 