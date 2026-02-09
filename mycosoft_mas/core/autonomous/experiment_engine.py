"""
Autonomous Experiment Engine
AI-driven closed-loop experimentation system
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)


class ExperimentStepType(str, Enum):
    SETUP = "setup"
    EXECUTE = "execute"
    MEASURE = "measure"
    ANALYZE = "analyze"
    DECIDE = "decide"


class ExperimentStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AutoExperimentStatus(str, Enum):
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentStep(BaseModel):
    id: str
    name: str
    type: ExperimentStepType
    status: ExperimentStepStatus = ExperimentStepStatus.PENDING
    startTime: Optional[float] = None
    endTime: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class ExperimentProtocol(BaseModel):
    id: str
    name: str
    version: str = "1.0"
    steps: List[ExperimentStep]
    parameters: Dict[str, Any] = {}
    constraints: Dict[str, Any] = {}


class Adaptation(BaseModel):
    timestamp: float
    reason: str
    change: str
    automated: bool = True


class AutoExperiment(BaseModel):
    id: str
    name: str
    hypothesis: str
    protocol: ExperimentProtocol
    status: AutoExperimentStatus = AutoExperimentStatus.PLANNING
    currentStep: int = 0
    totalSteps: int = 0
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    results: List[Any] = []
    adaptations: List[Adaptation] = []


class Finding(BaseModel):
    metric: str
    expected: Any
    observed: Any
    significance: float
    interpretation: str


class ExperimentResult(BaseModel):
    experimentId: str
    hypothesisValidated: bool
    confidence: float
    findings: List[Finding]
    recommendations: List[str]
    nextSteps: List[str]


class AutonomousExperimentEngine:
    """
    Manages autonomous scientific experiments with minimal human intervention.
    Generates protocols, executes steps, and adapts based on results.
    """
    
    def __init__(self):
        self.experiments: Dict[str, AutoExperiment] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._init_sample_experiments()
    
    def _init_sample_experiments(self):
        """Initialize with sample experiments"""
        protocol = ExperimentProtocol(
            id="proto-001",
            name="Growth Rate Protocol",
            version="1.0",
            steps=[
                ExperimentStep(id="s1", name="Initialize Environment", type=ExperimentStepType.SETUP, status=ExperimentStepStatus.COMPLETED),
                ExperimentStep(id="s2", name="Calibrate Instruments", type=ExperimentStepType.SETUP, status=ExperimentStepStatus.COMPLETED),
                ExperimentStep(id="s3", name="Prepare Samples", type=ExperimentStepType.SETUP, status=ExperimentStepStatus.COMPLETED),
                ExperimentStep(id="s4", name="Apply Treatment", type=ExperimentStepType.EXECUTE, status=ExperimentStepStatus.RUNNING),
                ExperimentStep(id="s5", name="Measure Growth", type=ExperimentStepType.MEASURE, status=ExperimentStepStatus.PENDING),
                ExperimentStep(id="s6", name="Analyze Data", type=ExperimentStepType.ANALYZE, status=ExperimentStepStatus.PENDING),
                ExperimentStep(id="s7", name="Validate Hypothesis", type=ExperimentStepType.DECIDE, status=ExperimentStepStatus.PENDING),
                ExperimentStep(id="s8", name="Generate Report", type=ExperimentStepType.DECIDE, status=ExperimentStepStatus.PENDING),
            ],
            parameters={"species": "P. ostreatus", "stimulus_frequency": "0.5Hz"},
            constraints={"max_duration_hours": 168, "min_samples": 5}
        )
        
        exp1 = AutoExperiment(
            id="auto-001",
            name="Growth Rate Optimization",
            hypothesis="Electrical stimulation at 0.5Hz increases P. ostreatus growth rate by 15-20%",
            protocol=protocol,
            status=AutoExperimentStatus.RUNNING,
            currentStep=4,
            totalSteps=8,
            startedAt="2026-02-03T08:00:00Z",
            adaptations=[
                Adaptation(timestamp=1706954400, reason="Detected suboptimal growth rate", change="Adjusted temperature from 25C to 24C", automated=True),
                Adaptation(timestamp=1706958000, reason="High variance in measurements", change="Extended data collection by 2 hours", automated=True),
            ]
        )
        
        self.experiments[exp1.id] = exp1
    
    async def create_experiment(self, hypothesis: str, parameters: Optional[Dict[str, Any]] = None) -> AutoExperiment:
        """Create a new autonomous experiment from a hypothesis"""
        exp_id = f"auto-{uuid.uuid4().hex[:6]}"
        
        # Generate protocol using AI (simplified version)
        protocol = await self._generate_protocol(hypothesis, parameters)
        
        experiment = AutoExperiment(
            id=exp_id,
            name=f"Auto Experiment {exp_id}",
            hypothesis=hypothesis,
            protocol=protocol,
            status=AutoExperimentStatus.PLANNING,
            currentStep=0,
            totalSteps=len(protocol.steps),
        )
        
        self.experiments[exp_id] = experiment
        logger.info(f"Created autonomous experiment: {exp_id}")
        
        return experiment
    
    async def _generate_protocol(self, hypothesis: str, parameters: Optional[Dict[str, Any]] = None) -> ExperimentProtocol:
        """Generate an experiment protocol based on hypothesis"""
        proto_id = f"proto-{uuid.uuid4().hex[:6]}"
        
        # In production, this would use LLM to generate appropriate steps
        steps = [
            ExperimentStep(id=f"s-{proto_id}-1", name="Environment Setup", type=ExperimentStepType.SETUP),
            ExperimentStep(id=f"s-{proto_id}-2", name="Instrument Calibration", type=ExperimentStepType.SETUP),
            ExperimentStep(id=f"s-{proto_id}-3", name="Sample Preparation", type=ExperimentStepType.SETUP),
            ExperimentStep(id=f"s-{proto_id}-4", name="Treatment Application", type=ExperimentStepType.EXECUTE),
            ExperimentStep(id=f"s-{proto_id}-5", name="Data Collection", type=ExperimentStepType.MEASURE),
            ExperimentStep(id=f"s-{proto_id}-6", name="Statistical Analysis", type=ExperimentStepType.ANALYZE),
            ExperimentStep(id=f"s-{proto_id}-7", name="Hypothesis Validation", type=ExperimentStepType.DECIDE),
        ]
        
        return ExperimentProtocol(
            id=proto_id,
            name=f"Protocol for: {hypothesis[:50]}...",
            version="1.0",
            steps=steps,
            parameters=parameters or {},
            constraints={"max_duration_hours": 168}
        )
    
    async def start_experiment(self, experiment_id: str) -> AutoExperiment:
        """Start executing an experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        exp = self.experiments[experiment_id]
        exp.status = AutoExperimentStatus.RUNNING
        exp.startedAt = datetime.utcnow().isoformat()
        exp.currentStep = 1
        
        # Start first step
        if exp.protocol.steps:
            exp.protocol.steps[0].status = ExperimentStepStatus.RUNNING
            exp.protocol.steps[0].startTime = datetime.utcnow().timestamp()
        
        logger.info(f"Started experiment: {experiment_id}")
        return exp
    
    async def pause_experiment(self, experiment_id: str) -> AutoExperiment:
        """Pause an experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        exp = self.experiments[experiment_id]
        exp.status = AutoExperimentStatus.PAUSED
        
        return exp
    
    async def resume_experiment(self, experiment_id: str) -> AutoExperiment:
        """Resume a paused experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        exp = self.experiments[experiment_id]
        exp.status = AutoExperimentStatus.RUNNING
        
        return exp
    
    async def abort_experiment(self, experiment_id: str, reason: str) -> AutoExperiment:
        """Abort an experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        exp = self.experiments[experiment_id]
        exp.status = AutoExperimentStatus.FAILED
        exp.completedAt = datetime.utcnow().isoformat()
        
        # Mark current step as failed
        if 0 <= exp.currentStep - 1 < len(exp.protocol.steps):
            exp.protocol.steps[exp.currentStep - 1].status = ExperimentStepStatus.FAILED
            exp.protocol.steps[exp.currentStep - 1].error = reason
        
        return exp
    
    async def suggest_adaptation(self, experiment_id: str) -> List[Adaptation]:
        """Suggest adaptations based on current experiment state"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # In production, this would analyze results and suggest adaptations
        suggestions = [
            Adaptation(
                timestamp=datetime.utcnow().timestamp(),
                reason="Variance in measurements above threshold",
                change="Increase sample size by 20%",
                automated=False
            ),
            Adaptation(
                timestamp=datetime.utcnow().timestamp(),
                reason="Growth rate below expected",
                change="Adjust humidity to 90%",
                automated=False
            ),
        ]
        
        return suggestions
    
    async def apply_adaptation(self, experiment_id: str, adaptation: Adaptation) -> AutoExperiment:
        """Apply an adaptation to an experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        exp = self.experiments[experiment_id]
        exp.adaptations.append(adaptation)
        
        logger.info(f"Applied adaptation to {experiment_id}: {adaptation.change}")
        return exp
    
    async def get_results(self, experiment_id: str) -> ExperimentResult:
        """Get results for a completed experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        exp = self.experiments[experiment_id]
        
        # Generate results (in production, this would analyze actual data)
        return ExperimentResult(
            experimentId=experiment_id,
            hypothesisValidated=True,
            confidence=0.87,
            findings=[
                Finding(
                    metric="growth_rate",
                    expected=0.18,
                    observed=0.21,
                    significance=0.92,
                    interpretation="Growth rate increased by 17%, within expected range"
                ),
                Finding(
                    metric="biomass",
                    expected=15.0,
                    observed=16.2,
                    significance=0.85,
                    interpretation="Biomass production increased by 8%"
                ),
            ],
            recommendations=[
                "Continue with 0.5Hz stimulation for production",
                "Test higher frequencies (1Hz, 2Hz) in follow-up",
            ],
            nextSteps=[
                "Scale up to production bioreactor",
                "Test on additional species (G. lucidum, H. erinaceus)",
            ]
        )
    
    def get_experiment(self, experiment_id: str) -> Optional[AutoExperiment]:
        """Get an experiment by ID"""
        return self.experiments.get(experiment_id)
    
    def list_experiments(self, status: Optional[AutoExperimentStatus] = None) -> List[AutoExperiment]:
        """List all experiments, optionally filtered by status"""
        experiments = list(self.experiments.values())
        if status:
            experiments = [e for e in experiments if e.status == status]
        return experiments


# Global engine instance
experiment_engine = AutonomousExperimentEngine()
