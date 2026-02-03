"""
Scientific API Router
REST endpoints for all scientific operations
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Models ---

class InstrumentType(str, Enum):
    INCUBATOR = "incubator"
    PIPETTOR = "pipettor"
    BIOREACTOR = "bioreactor"
    MICROSCOPE = "microscope"
    SEQUENCER = "sequencer"
    CENTRIFUGE = "centrifuge"


class InstrumentStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    MAINTENANCE = "maintenance"


class SimulationType(str, Enum):
    ALPHAFOLD = "alphafold"
    BOLTZGEN = "boltzgen"
    MYCELIUM = "mycelium"
    COBRAPY = "cobrapy"
    PHYSICS = "physics"
    MOLECULAR = "molecular"


class SimulationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    TESTING = "testing"
    VALIDATED = "validated"
    REJECTED = "rejected"


class FCISessionStatus(str, Enum):
    RECORDING = "recording"
    STIMULATING = "stimulating"
    IDLE = "idle"
    PAUSED = "paused"


# --- Pydantic Models ---

class Instrument(BaseModel):
    id: str
    name: str
    type: InstrumentType
    status: InstrumentStatus
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    currentTask: Optional[str] = None


class InstrumentCreate(BaseModel):
    name: str
    type: InstrumentType


class Simulation(BaseModel):
    id: str
    name: str
    type: SimulationType
    status: SimulationStatus
    progress: int = 0
    eta: Optional[str] = None
    gpu: Optional[str] = None
    config: Dict[str, Any] = {}


class SimulationCreate(BaseModel):
    name: str
    type: SimulationType
    config: Dict[str, Any] = {}


class Experiment(BaseModel):
    id: str
    name: str
    status: ExperimentStatus
    currentStep: int = 0
    totalSteps: int
    parameters: Dict[str, Any] = {}
    startedAt: Optional[str] = None


class ExperimentCreate(BaseModel):
    name: str
    parameters: Dict[str, Any] = {}


class Hypothesis(BaseModel):
    id: str
    statement: str
    status: HypothesisStatus
    confidence: Optional[float] = None
    experiments: List[str] = []


class HypothesisCreate(BaseModel):
    statement: str


class FCISession(BaseModel):
    id: str
    species: str
    strain: Optional[str] = None
    status: FCISessionStatus
    duration: int = 0
    electrodesActive: int
    totalElectrodes: int = 64
    sampleRate: int = 1000


class FCISessionCreate(BaseModel):
    species: str
    strain: Optional[str] = None


# --- In-memory storage (replace with database) ---

_instruments: Dict[str, Instrument] = {}
_simulations: Dict[str, Simulation] = {}
_experiments: Dict[str, Experiment] = {}
_hypotheses: Dict[str, Hypothesis] = {}
_fci_sessions: Dict[str, FCISession] = {}

# Initialize with sample data
def _init_sample_data():
    global _instruments, _simulations, _experiments, _hypotheses, _fci_sessions
    
    _instruments = {
        "inc-01": Instrument(id="inc-01", name="Incubator-01", type=InstrumentType.INCUBATOR, status=InstrumentStatus.ONLINE, temperature=25.5, humidity=85),
        "pip-01": Instrument(id="pip-01", name="Pipettor-A", type=InstrumentType.PIPETTOR, status=InstrumentStatus.BUSY, currentTask="Sample transfer"),
        "bio-01": Instrument(id="bio-01", name="Bioreactor-1", type=InstrumentType.BIOREACTOR, status=InstrumentStatus.ONLINE),
        "mic-01": Instrument(id="mic-01", name="Microscope-HD", type=InstrumentType.MICROSCOPE, status=InstrumentStatus.MAINTENANCE),
    }
    
    _simulations = {
        "sim-001": Simulation(id="sim-001", name="Psilocybin Synthase Structure", type=SimulationType.ALPHAFOLD, status=SimulationStatus.RUNNING, progress=67, eta="23 min", gpu="RTX 5090"),
        "sim-002": Simulation(id="sim-002", name="Mycelium Network Growth", type=SimulationType.MYCELIUM, status=SimulationStatus.RUNNING, progress=34, eta="1h 12m"),
        "sim-003": Simulation(id="sim-003", name="Metabolic Pathway - Shiitake", type=SimulationType.COBRAPY, status=SimulationStatus.QUEUED, progress=0),
    }
    
    _experiments = {
        "E-042": Experiment(id="E-042", name="Bioelectric Mapping - P. ostreatus", status=ExperimentStatus.RUNNING, currentStep=3, totalSteps=7, startedAt="2026-02-03T08:00:00Z"),
        "E-041": Experiment(id="E-041", name="Growth Rate Optimization", status=ExperimentStatus.COMPLETED, currentStep=5, totalSteps=5, startedAt="2026-02-02T10:00:00Z"),
        "E-043": Experiment(id="E-043", name="Spore Germination Analysis", status=ExperimentStatus.PENDING, currentStep=0, totalSteps=4),
    }
    
    _hypotheses = {
        "H-001": Hypothesis(id="H-001", statement="Electrical stimulation increases mycelium growth rate by 15-20%", status=HypothesisStatus.VALIDATED, confidence=0.87, experiments=["E-038", "E-039", "E-040"]),
        "H-002": Hypothesis(id="H-002", statement="P. ostreatus exhibits pattern recognition capabilities", status=HypothesisStatus.TESTING, confidence=0.65, experiments=["E-042"]),
        "H-003": Hypothesis(id="H-003", statement="Bioelectric signals correlate with substrate nutrient content", status=HypothesisStatus.PROPOSED, confidence=None, experiments=[]),
    }
    
    _fci_sessions = {
        "fci-001": FCISession(id="fci-001", species="Pleurotus ostreatus", strain="PO-001", status=FCISessionStatus.RECORDING, duration=9240, electrodesActive=58, totalElectrodes=64, sampleRate=1000),
        "fci-002": FCISession(id="fci-002", species="Ganoderma lucidum", strain="GL-003", status=FCISessionStatus.STIMULATING, duration=2700, electrodesActive=62, totalElectrodes=64, sampleRate=1000),
    }

_init_sample_data()


# --- Lab Instruments API ---

@router.get("/lab/instruments")
async def list_instruments():
    return {
        "instruments": list(_instruments.values()),
        "source": "live"
    }


@router.post("/lab/instruments")
async def create_instrument(data: InstrumentCreate):
    inst_id = f"inst-{uuid.uuid4().hex[:8]}"
    instrument = Instrument(
        id=inst_id,
        name=data.name,
        type=data.type,
        status=InstrumentStatus.ONLINE
    )
    _instruments[inst_id] = instrument
    return instrument


@router.get("/lab/instruments/{instrument_id}")
async def get_instrument(instrument_id: str):
    if instrument_id not in _instruments:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return _instruments[instrument_id]


@router.post("/lab/instruments/{instrument_id}/calibrate")
async def calibrate_instrument(instrument_id: str):
    if instrument_id not in _instruments:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return {"status": "calibrating", "instrumentId": instrument_id}


# --- Simulations API ---

@router.get("/simulation/jobs")
async def list_simulations():
    running = [s for s in _simulations.values() if s.status == SimulationStatus.RUNNING]
    return {
        "simulations": list(_simulations.values()),
        "gpuUtilization": 78,
        "queueLength": len([s for s in _simulations.values() if s.status == SimulationStatus.QUEUED]),
        "source": "live"
    }


@router.post("/simulation/jobs")
async def create_simulation(data: SimulationCreate):
    sim_id = f"sim-{uuid.uuid4().hex[:8]}"
    simulation = Simulation(
        id=sim_id,
        name=data.name,
        type=data.type,
        status=SimulationStatus.QUEUED,
        progress=0,
        config=data.config
    )
    _simulations[sim_id] = simulation
    return simulation


@router.get("/simulation/jobs/{simulation_id}")
async def get_simulation(simulation_id: str):
    if simulation_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return _simulations[simulation_id]


@router.post("/simulation/jobs/{simulation_id}/{action}")
async def control_simulation(simulation_id: str, action: str):
    if simulation_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    sim = _simulations[simulation_id]
    if action == "pause":
        sim.status = SimulationStatus.PAUSED
    elif action == "resume":
        sim.status = SimulationStatus.RUNNING
    elif action == "cancel":
        sim.status = SimulationStatus.FAILED
    
    return {"status": sim.status, "simulationId": simulation_id}


# --- Experiments API ---

@router.get("/experiments")
async def list_experiments():
    stats = {
        "running": len([e for e in _experiments.values() if e.status == ExperimentStatus.RUNNING]),
        "pending": len([e for e in _experiments.values() if e.status == ExperimentStatus.PENDING]),
        "completed": len([e for e in _experiments.values() if e.status == ExperimentStatus.COMPLETED]),
        "failed": len([e for e in _experiments.values() if e.status == ExperimentStatus.FAILED]),
    }
    return {
        "experiments": list(_experiments.values()),
        "stats": stats,
        "source": "live"
    }


@router.post("/experiments")
async def create_experiment(data: ExperimentCreate):
    exp_id = f"E-{uuid.uuid4().hex[:4].upper()}"
    experiment = Experiment(
        id=exp_id,
        name=data.name,
        status=ExperimentStatus.PENDING,
        currentStep=0,
        totalSteps=5,
        parameters=data.parameters
    )
    _experiments[exp_id] = experiment
    return experiment


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    if experiment_id not in _experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _experiments[experiment_id]


@router.post("/experiments/{experiment_id}/{action}")
async def control_experiment(experiment_id: str, action: str):
    if experiment_id not in _experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    exp = _experiments[experiment_id]
    if action == "start":
        exp.status = ExperimentStatus.RUNNING
        exp.startedAt = datetime.utcnow().isoformat()
    elif action == "pause":
        exp.status = ExperimentStatus.PENDING
    elif action == "cancel":
        exp.status = ExperimentStatus.FAILED
    
    return {"status": exp.status, "experimentId": experiment_id}


# --- Hypotheses API ---

@router.get("/hypotheses")
async def list_hypotheses():
    stats = {
        "proposed": len([h for h in _hypotheses.values() if h.status == HypothesisStatus.PROPOSED]),
        "testing": len([h for h in _hypotheses.values() if h.status == HypothesisStatus.TESTING]),
        "validated": len([h for h in _hypotheses.values() if h.status == HypothesisStatus.VALIDATED]),
        "rejected": len([h for h in _hypotheses.values() if h.status == HypothesisStatus.REJECTED]),
    }
    return {
        "hypotheses": list(_hypotheses.values()),
        "stats": stats,
        "source": "live"
    }


@router.post("/hypotheses")
async def create_hypothesis(data: HypothesisCreate):
    hyp_id = f"H-{uuid.uuid4().hex[:4].upper()}"
    hypothesis = Hypothesis(
        id=hyp_id,
        statement=data.statement,
        status=HypothesisStatus.PROPOSED
    )
    _hypotheses[hyp_id] = hypothesis
    return hypothesis


@router.post("/hypotheses/{hypothesis_id}/test")
async def test_hypothesis(hypothesis_id: str):
    if hypothesis_id not in _hypotheses:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
    hyp = _hypotheses[hypothesis_id]
    hyp.status = HypothesisStatus.TESTING
    return {"status": hyp.status, "hypothesisId": hypothesis_id}


# --- Bio/FCI API ---

@router.get("/bio/fci/sessions")
async def list_fci_sessions():
    electrodes = []
    for i in range(64):
        electrodes.append({
            "index": i,
            "active": i < 58,
            "impedance": 50 + (i % 10) * 5,
            "signal": 20 + (i % 8) * 10
        })
    
    return {
        "sessions": list(_fci_sessions.values()),
        "electrodeStatus": electrodes,
        "signalQuality": 92,
        "source": "live"
    }


@router.post("/bio/fci/sessions")
async def create_fci_session(data: FCISessionCreate):
    session_id = f"fci-{uuid.uuid4().hex[:6]}"
    session = FCISession(
        id=session_id,
        species=data.species,
        strain=data.strain,
        status=FCISessionStatus.IDLE,
        duration=0,
        electrodesActive=60,
        totalElectrodes=64,
        sampleRate=1000
    )
    _fci_sessions[session_id] = session
    return session


@router.post("/bio/fci/sessions/{session_id}/{action}")
async def control_fci_session(session_id: str, action: str):
    if session_id not in _fci_sessions:
        raise HTTPException(status_code=404, detail="FCI session not found")
    
    session = _fci_sessions[session_id]
    if action == "start":
        session.status = FCISessionStatus.RECORDING
    elif action == "pause":
        session.status = FCISessionStatus.PAUSED
    elif action == "stop":
        session.status = FCISessionStatus.IDLE
    elif action == "stimulate":
        session.status = FCISessionStatus.STIMULATING
    
    return {"status": session.status, "sessionId": session_id}


@router.get("/bio/fci/sessions/{session_id}/signals")
async def get_fci_signals(session_id: str):
    if session_id not in _fci_sessions:
        raise HTTPException(status_code=404, detail="FCI session not found")
    
    import random
    channels = [[random.uniform(-50, 50) for _ in range(100)] for _ in range(64)]
    return {"channels": channels, "sampleRate": 1000}


# --- Bio/MycoBrain API ---

@router.get("/bio/mycobrain/status")
async def get_mycobrain_status():
    return {
        "status": "online",
        "queuedComputations": 3,
        "completedToday": 12,
        "capabilities": ["graph_solving", "pattern_recognition", "analog_compute"],
        "currentLoad": 45,
        "source": "live"
    }


@router.post("/bio/mycobrain/compute")
async def submit_mycobrain_compute(mode: str = Body(...), input: dict = Body(...)):
    job_id = f"mcb-{uuid.uuid4().hex[:8]}"
    return {
        "jobId": job_id,
        "status": "queued",
        "mode": mode,
        "estimatedTime": "2-5 seconds"
    }


# --- Safety API ---

@router.get("/safety/status")
async def get_safety_status():
    return {
        "overallStatus": "nominal",
        "metrics": [
            {"name": "Biosafety Level", "value": 2, "max": 4, "status": "normal"},
            {"name": "Air Quality Index", "value": 95, "max": 100, "status": "normal"},
            {"name": "Containment Integrity", "value": 100, "max": 100, "status": "normal"},
            {"name": "Active Experiments", "value": 3, "max": 15, "status": "normal"},
            {"name": "Unreviewed Actions", "value": 0, "max": 50, "status": "normal"},
            {"name": "System Alignment", "value": 98, "max": 100, "status": "normal"},
        ],
        "source": "live"
    }
