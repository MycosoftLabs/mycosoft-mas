"""
Data Flow Coordinator Agent for Mycology BioAgent System

This agent coordinates data flow between different agents,
manages data dependencies, and ensures data consistency across the system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable, Awaitable
from datetime import datetime
import json
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class DataType(Enum):
    """Types of data in the system"""
    SPECIES = auto()
    ENVIRONMENTAL = auto()
    GROWTH = auto()
    SIGNAL = auto()
    PROTOCOL = auto()
    ANALYSIS = auto()
    OPTIMIZATION = auto()
    CUSTOM = auto()

class DataStatus(Enum):
    """Status of data in the system"""
    PENDING = auto()
    PROCESSING = auto()
    READY = auto()
    ERROR = auto()
    DEPRECATED = auto()

class DataPriority(Enum):
    """Priority of data processing"""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

@dataclass
class DataDependency:
    """Data dependency information"""
    dependency_id: str
    source_agent_id: str
    target_agent_id: str
    data_type: DataType
    required_fields: List[str]
    optional_fields: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DataFlow:
    """Data flow information"""
    flow_id: str
    name: str
    description: str
    source_agent_id: str
    target_agent_id: str
    data_type: DataType
    transform_function: Optional[str] = None  # Name of transform function
    validation_function: Optional[str] = None  # Name of validation function
    priority: DataPriority = DataPriority.MEDIUM
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DataItem:
    """Data item information"""
    item_id: str
    data_type: DataType
    source_agent_id: str
    content: Dict[str, Any]
    status: DataStatus = DataStatus.PENDING
    priority: DataPriority = DataPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)  # List of dependency IDs
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DataFlowEvent:
    """Data flow event information"""
    event_id: str
    flow_id: str
    item_id: str
    event_type: str
    status: str
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

class DataFlowCoordinatorAgent(BaseAgent):
    """Agent for coordinating data flow between agents"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.dependencies: Dict[str, DataDependency] = {}
        self.flows: Dict[str, DataFlow] = {}
        self.data_items: Dict[str, DataItem] = {}
        self.events: Dict[str, DataFlowEvent] = {}
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self.transform_functions: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {}
        self.validation_functions: Dict[str, Callable[[Dict[str, Any]], Awaitable[bool]]] = {}
        
        # Create necessary directories
        self.data_dir = Path("data/data_flow")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics
        self.metrics.update({
            "dependencies_created": 0,
            "flows_created": 0,
            "items_processed": 0,
            "items_failed": 0,
            "events_recorded": 0
        })
    
    async def initialize(self) -> None:
        """Initialize the agent"""
        await super().initialize()
        await self._load_data()
        self.status = AgentStatus.READY
        self.logger.info("Data Flow Coordinator Agent initialized")
    
    async def stop(self) -> None:
        """Stop the agent"""
        self.status = AgentStatus.STOPPING
        self.logger.info("Stopping Data Flow Coordinator Agent")
        await self._save_data()
        await super().stop()
    
    async def register_dependency(
        self,
        source_agent_id: str,
        target_agent_id: str,
        data_type: DataType,
        required_fields: List[str],
        optional_fields: Optional[List[str]] = None,
        validation_rules: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a data dependency between agents"""
        dependency_id = f"dependency_{uuid.uuid4().hex[:8]}"
        
        dependency = DataDependency(
            dependency_id=dependency_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            data_type=data_type,
            required_fields=required_fields,
            optional_fields=optional_fields or [],
            validation_rules=validation_rules or {},
            metadata=metadata or {}
        )
        
        self.dependencies[dependency_id] = dependency
        await self._save_data()
        
        self.metrics["dependencies_created"] += 1
        return dependency_id
    
    async def create_data_flow(
        self,
        name: str,
        description: str,
        source_agent_id: str,
        target_agent_id: str,
        data_type: DataType,
        transform_function: Optional[str] = None,
        validation_function: Optional[str] = None,
        priority: DataPriority = DataPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new data flow"""
        flow_id = f"flow_{uuid.uuid4().hex[:8]}"
        
        flow = DataFlow(
            flow_id=flow_id,
            name=name,
            description=description,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            data_type=data_type,
            transform_function=transform_function,
            validation_function=validation_function,
            priority=priority,
            metadata=metadata or {}
        )
        
        self.flows[flow_id] = flow
        await self._save_data()
        
        self.metrics["flows_created"] += 1
        return flow_id
    
    async def register_transform_function(
        self,
        name: str,
        function: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ) -> None:
        """Register a transform function"""
        self.transform_functions[name] = function
    
    async def register_validation_function(
        self,
        name: str,
        function: Callable[[Dict[str, Any]], Awaitable[bool]]
    ) -> None:
        """Register a validation function"""
        self.validation_functions[name] = function
    
    async def submit_data(
        self,
        data_type: DataType,
        source_agent_id: str,
        content: Dict[str, Any],
        priority: DataPriority = DataPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Submit data for processing"""
        item_id = f"item_{uuid.uuid4().hex[:8]}"
        
        # Find dependencies for this data
        dependencies = [
            dep.dependency_id for dep in self.dependencies.values()
            if dep.source_agent_id == source_agent_id and dep.data_type == data_type
        ]
        
        item = DataItem(
            item_id=item_id,
            data_type=data_type,
            source_agent_id=source_agent_id,
            content=content,
            status=DataStatus.PENDING,
            priority=priority,
            dependencies=dependencies,
            metadata=metadata or {}
        )
        
        self.data_items[item_id] = item
        await self._save_data()
        
        # Add to processing queue
        await self.processing_queue.put(item_id)
        
        return item_id
    
    async def get_data_item(self, item_id: str) -> Optional[DataItem]:
        """Get a data item by ID"""
        return self.data_items.get(item_id)
    
    async def get_data_flow(self, flow_id: str) -> Optional[DataFlow]:
        """Get a data flow by ID"""
        return self.flows.get(flow_id)
    
    async def get_dependency(self, dependency_id: str) -> Optional[DataDependency]:
        """Get a data dependency by ID"""
        return self.dependencies.get(dependency_id)
    
    async def get_events(
        self,
        flow_id: Optional[str] = None,
        item_id: Optional[str] = None
    ) -> List[DataFlowEvent]:
        """Get data flow events"""
        if flow_id:
            return [e for e in self.events.values() if e.flow_id == flow_id]
        if item_id:
            return [e for e in self.events.values() if e.item_id == item_id]
        return list(self.events.values())
    
    async def _load_data(self) -> None:
        """Load data from disk"""
        # Load dependencies
        dependencies_file = self.data_dir / "dependencies.json"
        if dependencies_file.exists():
            with open(dependencies_file, "r") as f:
                dependencies_data = json.load(f)
                
                for dependency_data in dependencies_data:
                    dependency = DataDependency(
                        dependency_id=dependency_data["dependency_id"],
                        source_agent_id=dependency_data["source_agent_id"],
                        target_agent_id=dependency_data["target_agent_id"],
                        data_type=DataType[dependency_data["data_type"]],
                        required_fields=dependency_data["required_fields"],
                        optional_fields=dependency_data.get("optional_fields", []),
                        validation_rules=dependency_data.get("validation_rules", {}),
                        metadata=dependency_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(dependency_data["created_at"]),
                        updated_at=datetime.fromisoformat(dependency_data["updated_at"])
                    )
                    
                    self.dependencies[dependency.dependency_id] = dependency
        
        # Load flows
        flows_file = self.data_dir / "flows.json"
        if flows_file.exists():
            with open(flows_file, "r") as f:
                flows_data = json.load(f)
                
                for flow_data in flows_data:
                    flow = DataFlow(
                        flow_id=flow_data["flow_id"],
                        name=flow_data["name"],
                        description=flow_data["description"],
                        source_agent_id=flow_data["source_agent_id"],
                        target_agent_id=flow_data["target_agent_id"],
                        data_type=DataType[flow_data["data_type"]],
                        transform_function=flow_data.get("transform_function"),
                        validation_function=flow_data.get("validation_function"),
                        priority=DataPriority[flow_data["priority"]],
                        is_active=flow_data.get("is_active", True),
                        metadata=flow_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(flow_data["created_at"]),
                        updated_at=datetime.fromisoformat(flow_data["updated_at"])
                    )
                    
                    self.flows[flow.flow_id] = flow
        
        # Load data items
        items_file = self.data_dir / "items.json"
        if items_file.exists():
            with open(items_file, "r") as f:
                items_data = json.load(f)
                
                for item_data in items_data:
                    item = DataItem(
                        item_id=item_data["item_id"],
                        data_type=DataType[item_data["data_type"]],
                        source_agent_id=item_data["source_agent_id"],
                        content=item_data["content"],
                        status=DataStatus[item_data["status"]],
                        priority=DataPriority[item_data["priority"]],
                        dependencies=item_data.get("dependencies", []),
                        metadata=item_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(item_data["created_at"]),
                        updated_at=datetime.fromisoformat(item_data["updated_at"])
                    )
                    
                    self.data_items[item.item_id] = item
        
        # Load events
        events_file = self.data_dir / "events.json"
        if events_file.exists():
            with open(events_file, "r") as f:
                events_data = json.load(f)
                
                for event_data in events_data:
                    event = DataFlowEvent(
                        event_id=event_data["event_id"],
                        flow_id=event_data["flow_id"],
                        item_id=event_data["item_id"],
                        event_type=event_data["event_type"],
                        status=event_data["status"],
                        details=event_data.get("details", {}),
                        metadata=event_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(event_data["created_at"])
                    )
                    
                    self.events[event.event_id] = event
    
    async def _save_data(self) -> None:
        """Save data to disk"""
        # Save dependencies
        dependencies_file = self.data_dir / "dependencies.json"
        dependencies_data = []
        
        for dependency in self.dependencies.values():
            dependency_data = {
                "dependency_id": dependency.dependency_id,
                "source_agent_id": dependency.source_agent_id,
                "target_agent_id": dependency.target_agent_id,
                "data_type": dependency.data_type.name,
                "required_fields": dependency.required_fields,
                "optional_fields": dependency.optional_fields,
                "validation_rules": dependency.validation_rules,
                "metadata": dependency.metadata,
                "created_at": dependency.created_at.isoformat(),
                "updated_at": dependency.updated_at.isoformat()
            }
            dependencies_data.append(dependency_data)
        
        with open(dependencies_file, "w") as f:
            json.dump(dependencies_data, f, indent=2)
        
        # Save flows
        flows_file = self.data_dir / "flows.json"
        flows_data = []
        
        for flow in self.flows.values():
            flow_data = {
                "flow_id": flow.flow_id,
                "name": flow.name,
                "description": flow.description,
                "source_agent_id": flow.source_agent_id,
                "target_agent_id": flow.target_agent_id,
                "data_type": flow.data_type.name,
                "transform_function": flow.transform_function,
                "validation_function": flow.validation_function,
                "priority": flow.priority.name,
                "is_active": flow.is_active,
                "metadata": flow.metadata,
                "created_at": flow.created_at.isoformat(),
                "updated_at": flow.updated_at.isoformat()
            }
            flows_data.append(flow_data)
        
        with open(flows_file, "w") as f:
            json.dump(flows_data, f, indent=2)
        
        # Save data items
        items_file = self.data_dir / "items.json"
        items_data = []
        
        for item in self.data_items.values():
            item_data = {
                "item_id": item.item_id,
                "data_type": item.data_type.name,
                "source_agent_id": item.source_agent_id,
                "content": item.content,
                "status": item.status.name,
                "priority": item.priority.name,
                "dependencies": item.dependencies,
                "metadata": item.metadata,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat()
            }
            items_data.append(item_data)
        
        with open(items_file, "w") as f:
            json.dump(items_data, f, indent=2)
        
        # Save events
        events_file = self.data_dir / "events.json"
        events_data = []
        
        for event in self.events.values():
            event_data = {
                "event_id": event.event_id,
                "flow_id": event.flow_id,
                "item_id": event.item_id,
                "event_type": event.event_type,
                "status": event.status,
                "details": event.details,
                "metadata": event.metadata,
                "created_at": event.created_at.isoformat()
            }
            events_data.append(event_data)
        
        with open(events_file, "w") as f:
            json.dump(events_data, f, indent=2)
    
    async def _process_queue(self) -> None:
        """Process the data processing queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next item to process
                item_id = await self.processing_queue.get()
                
                # Process the item
                await self._process_data_item(item_id)
                
                # Mark task as complete
                self.processing_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing data item: {str(e)}")
                continue
    
    async def _process_data_item(self, item_id: str) -> None:
        """Process a data item"""
        if item_id not in self.data_items:
            return
        
        item = self.data_items[item_id]
        item.status = DataStatus.PROCESSING
        item.updated_at = datetime.utcnow()
        
        # Find applicable flows
        applicable_flows = [
            flow for flow in self.flows.values()
            if flow.source_agent_id == item.source_agent_id
            and flow.data_type == item.data_type
            and flow.is_active
        ]
        
        if not applicable_flows:
            item.status = DataStatus.READY
            item.updated_at = datetime.utcnow()
            await self._save_data()
            return
        
        # Process through each flow
        for flow in applicable_flows:
            try:
                # Record flow start event
                await self._record_event(
                    flow.flow_id,
                    item.item_id,
                    "flow_start",
                    "processing"
                )
                
                # Transform data if needed
                transformed_content = item.content
                if flow.transform_function and flow.transform_function in self.transform_functions:
                    transform_func = self.transform_functions[flow.transform_function]
                    transformed_content = await transform_func(item.content)
                
                # Validate data if needed
                is_valid = True
                if flow.validation_function and flow.validation_function in self.validation_functions:
                    validation_func = self.validation_functions[flow.validation_function]
                    is_valid = await validation_func(transformed_content)
                
                if not is_valid:
                    await self._record_event(
                        flow.flow_id,
                        item.item_id,
                        "validation_failed",
                        "error",
                        {"reason": "Data validation failed"}
                    )
                    continue
                
                # TODO: Send data to target agent
                # This would be implemented with actual agent communication
                
                # Record flow success event
                await self._record_event(
                    flow.flow_id,
                    item.item_id,
                    "flow_complete",
                    "success"
                )
                
                self.metrics["items_processed"] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing flow {flow.flow_id} for item {item_id}: {str(e)}")
                await self._record_event(
                    flow.flow_id,
                    item.item_id,
                    "flow_error",
                    "error",
                    {"error": str(e)}
                )
                self.metrics["items_failed"] += 1
        
        # Update item status
        item.status = DataStatus.READY
        item.updated_at = datetime.utcnow()
        await self._save_data()
    
    async def _record_event(
        self,
        flow_id: str,
        item_id: str,
        event_type: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a data flow event"""
        event_id = f"event_{uuid.uuid4().hex[:8]}"
        
        event = DataFlowEvent(
            event_id=event_id,
            flow_id=flow_id,
            item_id=item_id,
            event_type=event_type,
            status=status,
            details=details or {}
        )
        
        self.events[event_id] = event
        await self._save_data()
        
        self.metrics["events_recorded"] += 1
        return event_id 