"""
Mycorrhizae Protocol Agent for Mycology BioAgent System

This agent manages mycorrhizal protocols, coordinates their execution,
and tracks protocol outcomes and optimizations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime
import json
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class ProtocolType(Enum):
    """Types of mycorrhizal protocols"""
    INOCULATION = auto()
    CULTIVATION = auto()
    HARVESTING = auto()
    PRESERVATION = auto()
    ANALYSIS = auto()
    OPTIMIZATION = auto()
    CUSTOM = auto()

class ProtocolStatus(Enum):
    """Status of protocol execution"""
    DRAFT = auto()
    VALIDATED = auto()
    SCHEDULED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

class ProtocolPriority(Enum):
    """Priority of protocol execution"""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

@dataclass
class ProtocolStep:
    """Single step in a protocol"""
    step_id: str
    name: str
    description: str
    duration: int  # minutes
    temperature: Optional[float] = None  # Celsius
    humidity: Optional[float] = None  # percentage
    ph: Optional[float] = None
    substrate: Optional[str] = None
    equipment: List[str] = field(default_factory=list)
    reagents: List[str] = field(default_factory=list)
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Protocol:
    """Mycorrhizal protocol information"""
    protocol_id: str
    name: str
    description: str
    protocol_type: ProtocolType
    steps: List[ProtocolStep]
    target_species: List[str]
    success_criteria: Dict[str, Any]
    version: str = "1.0.0"
    status: ProtocolStatus = ProtocolStatus.DRAFT
    priority: ProtocolPriority = ProtocolPriority.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ProtocolExecution:
    """Protocol execution record"""
    execution_id: str
    protocol_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: ProtocolStatus = ProtocolStatus.SCHEDULED
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProtocolOptimization:
    """Protocol optimization suggestion"""
    optimization_id: str
    protocol_id: str
    execution_id: str
    parameter: str
    current_value: Any
    suggested_value: Any
    confidence: float
    rationale: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

class MycorrhizaeProtocolAgent(BaseAgent):
    """Agent for managing mycorrhizal protocols"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.protocols: Dict[str, Protocol] = {}
        self.executions: Dict[str, ProtocolExecution] = {}
        self.optimizations: Dict[str, ProtocolOptimization] = {}
        self.execution_queue: asyncio.Queue = asyncio.Queue()
        
        # Create necessary directories
        self.data_dir = Path("data/mycorrhizae_protocols")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics
        self.metrics.update({
            "protocols_created": 0,
            "protocols_executed": 0,
            "executions_completed": 0,
            "executions_failed": 0,
            "optimizations_suggested": 0
        })
    
    async def initialize(self) -> None:
        """Initialize the agent"""
        await super().initialize()
        await self._load_protocols()
        self.status = AgentStatus.READY
        self.logger.info("Mycorrhizae Protocol Agent initialized")
    
    async def stop(self) -> None:
        """Stop the agent"""
        self.status = AgentStatus.STOPPING
        self.logger.info("Stopping Mycorrhizae Protocol Agent")
        await self._save_protocols()
        await super().stop()
    
    async def create_protocol(
        self,
        name: str,
        description: str,
        protocol_type: ProtocolType,
        steps: List[ProtocolStep],
        target_species: List[str],
        success_criteria: Dict[str, Any],
        version: str = "1.0.0",
        priority: ProtocolPriority = ProtocolPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new mycorrhizal protocol"""
        protocol_id = f"protocol_{uuid.uuid4().hex[:8]}"
        
        protocol = Protocol(
            protocol_id=protocol_id,
            name=name,
            description=description,
            protocol_type=protocol_type,
            steps=steps,
            target_species=target_species,
            success_criteria=success_criteria,
            version=version,
            status=ProtocolStatus.DRAFT,
            priority=priority,
            metadata=metadata or {}
        )
        
        self.protocols[protocol_id] = protocol
        await self._save_protocols()
        
        self.metrics["protocols_created"] += 1
        return protocol_id
    
    async def update_protocol(
        self,
        protocol_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        steps: Optional[List[ProtocolStep]] = None,
        target_species: Optional[List[str]] = None,
        success_criteria: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
        priority: Optional[ProtocolPriority] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update an existing protocol"""
        if protocol_id not in self.protocols:
            return False
        
        protocol = self.protocols[protocol_id]
        
        if name is not None:
            protocol.name = name
        if description is not None:
            protocol.description = description
        if steps is not None:
            protocol.steps = steps
        if target_species is not None:
            protocol.target_species = target_species
        if success_criteria is not None:
            protocol.success_criteria = success_criteria
        if version is not None:
            protocol.version = version
        if priority is not None:
            protocol.priority = priority
        if metadata is not None:
            protocol.metadata.update(metadata)
        
        protocol.updated_at = datetime.utcnow()
        await self._save_protocols()
        
        return True
    
    async def validate_protocol(self, protocol_id: str) -> bool:
        """Validate a protocol"""
        if protocol_id not in self.protocols:
            return False
        
        protocol = self.protocols[protocol_id]
        
        # Basic validation checks
        if not protocol.name or not protocol.description:
            return False
        
        if not protocol.steps:
            return False
        
        if not protocol.target_species:
            return False
        
        if not protocol.success_criteria:
            return False
        
        # Update status
        protocol.status = ProtocolStatus.VALIDATED
        protocol.updated_at = datetime.utcnow()
        await self._save_protocols()
        
        return True
    
    async def schedule_execution(
        self,
        protocol_id: str,
        start_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Schedule a protocol for execution"""
        if protocol_id not in self.protocols:
            raise ValueError(f"Protocol {protocol_id} not found")
        
        protocol = self.protocols[protocol_id]
        
        if protocol.status != ProtocolStatus.VALIDATED:
            raise ValueError(f"Protocol {protocol_id} is not validated")
        
        execution_id = f"execution_{uuid.uuid4().hex[:8]}"
        
        execution = ProtocolExecution(
            execution_id=execution_id,
            protocol_id=protocol_id,
            start_time=start_time or datetime.utcnow(),
            status=ProtocolStatus.SCHEDULED,
            metadata=metadata or {}
        )
        
        self.executions[execution_id] = execution
        await self.execution_queue.put(execution_id)
        
        return execution_id
    
    async def start_execution(self, execution_id: str) -> bool:
        """Start a scheduled protocol execution"""
        if execution_id not in self.executions:
            return False
        
        execution = self.executions[execution_id]
        protocol = self.protocols[execution.protocol_id]
        
        if execution.status != ProtocolStatus.SCHEDULED:
            return False
        
        execution.status = ProtocolStatus.IN_PROGRESS
        execution.current_step = protocol.steps[0].step_id if protocol.steps else None
        
        self.metrics["protocols_executed"] += 1
        return True
    
    async def complete_step(
        self,
        execution_id: str,
        step_id: str,
        results: Dict[str, Any]
    ) -> bool:
        """Complete a protocol step"""
        if execution_id not in self.executions:
            return False
        
        execution = self.executions[execution_id]
        protocol = self.protocols[execution.protocol_id]
        
        if execution.status != ProtocolStatus.IN_PROGRESS:
            return False
        
        if execution.current_step != step_id:
            return False
        
        # Record step completion
        execution.completed_steps.append(step_id)
        execution.results[step_id] = results
        
        # Move to next step or complete protocol
        current_step_index = next(
            (i for i, step in enumerate(protocol.steps) if step.step_id == step_id),
            -1
        )
        
        if current_step_index >= 0 and current_step_index < len(protocol.steps) - 1:
            execution.current_step = protocol.steps[current_step_index + 1].step_id
        else:
            execution.current_step = None
            execution.status = ProtocolStatus.COMPLETED
            execution.end_time = datetime.utcnow()
            self.metrics["executions_completed"] += 1
            
            # Check for optimization opportunities
            await self._check_optimization_opportunities(execution)
        
        return True
    
    async def fail_execution(
        self,
        execution_id: str,
        error: Dict[str, Any]
    ) -> bool:
        """Mark a protocol execution as failed"""
        if execution_id not in self.executions:
            return False
        
        execution = self.executions[execution_id]
        
        if execution.status not in [ProtocolStatus.IN_PROGRESS, ProtocolStatus.SCHEDULED]:
            return False
        
        execution.status = ProtocolStatus.FAILED
        execution.end_time = datetime.utcnow()
        execution.errors.append(error)
        
        self.metrics["executions_failed"] += 1
        return True
    
    async def get_protocol(self, protocol_id: str) -> Optional[Protocol]:
        """Get a protocol by ID"""
        return self.protocols.get(protocol_id)
    
    async def get_execution(self, execution_id: str) -> Optional[ProtocolExecution]:
        """Get a protocol execution by ID"""
        return self.executions.get(execution_id)
    
    async def get_optimizations(
        self,
        protocol_id: Optional[str] = None
    ) -> List[ProtocolOptimization]:
        """Get protocol optimizations"""
        if protocol_id:
            return [
                opt for opt in self.optimizations.values()
                if opt.protocol_id == protocol_id
            ]
        return list(self.optimizations.values())
    
    async def _load_protocols(self) -> None:
        """Load protocols from disk"""
        protocols_file = self.data_dir / "protocols.json"
        if protocols_file.exists():
            with open(protocols_file, "r") as f:
                protocols_data = json.load(f)
                
                for protocol_data in protocols_data:
                    # Convert steps data
                    steps = []
                    for step_data in protocol_data["steps"]:
                        step = ProtocolStep(
                            step_id=step_data["step_id"],
                            name=step_data["name"],
                            description=step_data["description"],
                            duration=step_data["duration"],
                            temperature=step_data.get("temperature"),
                            humidity=step_data.get("humidity"),
                            ph=step_data.get("ph"),
                            substrate=step_data.get("substrate"),
                            equipment=step_data.get("equipment", []),
                            reagents=step_data.get("reagents", []),
                            notes=step_data.get("notes", ""),
                            metadata=step_data.get("metadata", {})
                        )
                        steps.append(step)
                    
                    protocol = Protocol(
                        protocol_id=protocol_data["protocol_id"],
                        name=protocol_data["name"],
                        description=protocol_data["description"],
                        protocol_type=ProtocolType[protocol_data["protocol_type"]],
                        steps=steps,
                        target_species=protocol_data["target_species"],
                        success_criteria=protocol_data["success_criteria"],
                        version=protocol_data["version"],
                        status=ProtocolStatus[protocol_data["status"]],
                        priority=ProtocolPriority[protocol_data["priority"]],
                        metadata=protocol_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(protocol_data["created_at"]),
                        updated_at=datetime.fromisoformat(protocol_data["updated_at"])
                    )
                    
                    self.protocols[protocol.protocol_id] = protocol
        
        # Load executions
        executions_file = self.data_dir / "executions.json"
        if executions_file.exists():
            with open(executions_file, "r") as f:
                executions_data = json.load(f)
                
                for execution_data in executions_data:
                    execution = ProtocolExecution(
                        execution_id=execution_data["execution_id"],
                        protocol_id=execution_data["protocol_id"],
                        start_time=datetime.fromisoformat(execution_data["start_time"]),
                        end_time=datetime.fromisoformat(execution_data["end_time"]) if execution_data.get("end_time") else None,
                        status=ProtocolStatus[execution_data["status"]],
                        current_step=execution_data.get("current_step"),
                        completed_steps=execution_data.get("completed_steps", []),
                        results=execution_data.get("results", {}),
                        errors=execution_data.get("errors", []),
                        metadata=execution_data.get("metadata", {})
                    )
                    
                    self.executions[execution.execution_id] = execution
        
        # Load optimizations
        optimizations_file = self.data_dir / "optimizations.json"
        if optimizations_file.exists():
            with open(optimizations_file, "r") as f:
                optimizations_data = json.load(f)
                
                for optimization_data in optimizations_data:
                    optimization = ProtocolOptimization(
                        optimization_id=optimization_data["optimization_id"],
                        protocol_id=optimization_data["protocol_id"],
                        execution_id=optimization_data["execution_id"],
                        parameter=optimization_data["parameter"],
                        current_value=optimization_data["current_value"],
                        suggested_value=optimization_data["suggested_value"],
                        confidence=optimization_data["confidence"],
                        rationale=optimization_data["rationale"],
                        metadata=optimization_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(optimization_data["created_at"])
                    )
                    
                    self.optimizations[optimization.optimization_id] = optimization
    
    async def _save_protocols(self) -> None:
        """Save protocols to disk"""
        # Save protocols
        protocols_file = self.data_dir / "protocols.json"
        protocols_data = []
        
        for protocol in self.protocols.values():
            # Convert steps to serializable format
            steps_data = []
            for step in protocol.steps:
                step_data = {
                    "step_id": step.step_id,
                    "name": step.name,
                    "description": step.description,
                    "duration": step.duration,
                    "temperature": step.temperature,
                    "humidity": step.humidity,
                    "ph": step.ph,
                    "substrate": step.substrate,
                    "equipment": step.equipment,
                    "reagents": step.reagents,
                    "notes": step.notes,
                    "metadata": step.metadata
                }
                steps_data.append(step_data)
            
            protocol_data = {
                "protocol_id": protocol.protocol_id,
                "name": protocol.name,
                "description": protocol.description,
                "protocol_type": protocol.protocol_type.name,
                "steps": steps_data,
                "target_species": protocol.target_species,
                "success_criteria": protocol.success_criteria,
                "version": protocol.version,
                "status": protocol.status.name,
                "priority": protocol.priority.name,
                "metadata": protocol.metadata,
                "created_at": protocol.created_at.isoformat(),
                "updated_at": protocol.updated_at.isoformat()
            }
            protocols_data.append(protocol_data)
        
        with open(protocols_file, "w") as f:
            json.dump(protocols_data, f, indent=2)
        
        # Save executions
        executions_file = self.data_dir / "executions.json"
        executions_data = []
        
        for execution in self.executions.values():
            execution_data = {
                "execution_id": execution.execution_id,
                "protocol_id": execution.protocol_id,
                "start_time": execution.start_time.isoformat(),
                "end_time": execution.end_time.isoformat() if execution.end_time else None,
                "status": execution.status.name,
                "current_step": execution.current_step,
                "completed_steps": execution.completed_steps,
                "results": execution.results,
                "errors": execution.errors,
                "metadata": execution.metadata
            }
            executions_data.append(execution_data)
        
        with open(executions_file, "w") as f:
            json.dump(executions_data, f, indent=2)
        
        # Save optimizations
        optimizations_file = self.data_dir / "optimizations.json"
        optimizations_data = []
        
        for optimization in self.optimizations.values():
            optimization_data = {
                "optimization_id": optimization.optimization_id,
                "protocol_id": optimization.protocol_id,
                "execution_id": optimization.execution_id,
                "parameter": optimization.parameter,
                "current_value": optimization.current_value,
                "suggested_value": optimization.suggested_value,
                "confidence": optimization.confidence,
                "rationale": optimization.rationale,
                "metadata": optimization.metadata,
                "created_at": optimization.created_at.isoformat()
            }
            optimizations_data.append(optimization_data)
        
        with open(optimizations_file, "w") as f:
            json.dump(optimizations_data, f, indent=2)
    
    async def _process_execution_queue(self) -> None:
        """Process the execution queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next execution task
                execution_id = await self.execution_queue.get()
                
                # Start execution
                await self.start_execution(execution_id)
                
                # Mark task as complete
                self.execution_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing execution: {str(e)}")
                continue
    
    async def _check_optimization_opportunities(
        self,
        execution: ProtocolExecution
    ) -> None:
        """Check for protocol optimization opportunities"""
        protocol = self.protocols[execution.protocol_id]
        
        # Analyze execution results
        for step_id, results in execution.results.items():
            step = next(
                (s for s in protocol.steps if s.step_id == step_id),
                None
            )
            
            if not step:
                continue
            
            # Check for optimization opportunities
            if "temperature" in results and step.temperature is not None:
                current_temp = results["temperature"]
                if abs(current_temp - step.temperature) > 2.0:  # More than 2°C deviation
                    await self._suggest_optimization(
                        protocol.protocol_id,
                        execution.execution_id,
                        "temperature",
                        current_temp,
                        step.temperature,
                        0.8,  # Confidence
                        f"Temperature deviation detected in step {step.name}"
                    )
            
            if "humidity" in results and step.humidity is not None:
                current_humidity = results["humidity"]
                if abs(current_humidity - step.humidity) > 5.0:  # More than 5% deviation
                    await self._suggest_optimization(
                        protocol.protocol_id,
                        execution.execution_id,
                        "humidity",
                        current_humidity,
                        step.humidity,
                        0.8,  # Confidence
                        f"Humidity deviation detected in step {step.name}"
                    )
            
            if "ph" in results and step.ph is not None:
                current_ph = results["ph"]
                if abs(current_ph - step.ph) > 0.5:  # More than 0.5 pH deviation
                    await self._suggest_optimization(
                        protocol.protocol_id,
                        execution.execution_id,
                        "ph",
                        current_ph,
                        step.ph,
                        0.8,  # Confidence
                        f"pH deviation detected in step {step.name}"
                    )
    
    async def _suggest_optimization(
        self,
        protocol_id: str,
        execution_id: str,
        parameter: str,
        current_value: Any,
        suggested_value: Any,
        confidence: float,
        rationale: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Suggest a protocol optimization"""
        optimization_id = f"optimization_{uuid.uuid4().hex[:8]}"
        
        optimization = ProtocolOptimization(
            optimization_id=optimization_id,
            protocol_id=protocol_id,
            execution_id=execution_id,
            parameter=parameter,
            current_value=current_value,
            suggested_value=suggested_value,
            confidence=confidence,
            rationale=rationale,
            metadata=metadata or {}
        )
        
        self.optimizations[optimization_id] = optimization
        await self._save_protocols()
        
        self.metrics["optimizations_suggested"] += 1
        return optimization_id 