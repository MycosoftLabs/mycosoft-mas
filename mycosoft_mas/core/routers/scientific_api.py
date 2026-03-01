"""
Scientific API Router
REST endpoints for all scientific operations
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum
import uuid
import logging
import os
import json
import httpx

logger = logging.getLogger(__name__)

router = APIRouter()

try:
    import asyncpg
except ImportError:
    asyncpg = None


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


# --- PostgreSQL-backed storage ---


class ScientificStore:
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = (
            database_url
            or os.getenv("DATABASE_URL")
            or os.getenv("MINDEX_DATABASE_URL")
        )
        if not self._database_url:
            raise RuntimeError("DATABASE_URL or MINDEX_DATABASE_URL is required.")
        self._pool: Optional["asyncpg.Pool"] = None

    async def initialize(self) -> None:
        if self._pool:
            return
        if asyncpg is None:
            raise RuntimeError("asyncpg is required for scientific storage.")
        self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=6)
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE SCHEMA IF NOT EXISTS mindex;")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mindex.scientific_instruments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    temperature DOUBLE PRECISION,
                    humidity DOUBLE PRECISION,
                    current_task TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mindex.scientific_simulations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    eta TEXT,
                    gpu TEXT,
                    config JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mindex.scientific_experiments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_step INTEGER NOT NULL DEFAULT 0,
                    total_steps INTEGER NOT NULL DEFAULT 0,
                    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
                    started_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mindex.scientific_hypotheses (
                    id TEXT PRIMARY KEY,
                    statement TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence DOUBLE PRECISION,
                    experiments JSONB NOT NULL DEFAULT '[]'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mindex.scientific_fci_sessions (
                    id TEXT PRIMARY KEY,
                    species TEXT NOT NULL,
                    strain TEXT,
                    status TEXT NOT NULL,
                    duration INTEGER NOT NULL DEFAULT 0,
                    electrodes_active INTEGER NOT NULL,
                    total_electrodes INTEGER NOT NULL DEFAULT 64,
                    sample_rate INTEGER NOT NULL DEFAULT 1000,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

    async def list_instruments(self) -> List[Instrument]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM mindex.scientific_instruments ORDER BY updated_at DESC")
        return [
            Instrument(
                id=row["id"],
                name=row["name"],
                type=InstrumentType(row["type"]),
                status=InstrumentStatus(row["status"]),
                temperature=row["temperature"],
                humidity=row["humidity"],
                currentTask=row["current_task"],
            )
            for row in rows
        ]

    async def get_instrument(self, instrument_id: str) -> Optional[Instrument]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mindex.scientific_instruments WHERE id = $1",
                instrument_id,
            )
        if not row:
            return None
        return Instrument(
            id=row["id"],
            name=row["name"],
            type=InstrumentType(row["type"]),
            status=InstrumentStatus(row["status"]),
            temperature=row["temperature"],
            humidity=row["humidity"],
            currentTask=row["current_task"],
        )

    async def create_instrument(self, data: InstrumentCreate) -> Instrument:
        await self.initialize()
        inst_id = f"inst-{uuid.uuid4().hex[:8]}"
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.scientific_instruments
                (id, name, type, status, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                """,
                inst_id,
                data.name,
                data.type.value,
                InstrumentStatus.ONLINE.value,
            )
        return Instrument(id=inst_id, name=data.name, type=data.type, status=InstrumentStatus.ONLINE)

    async def set_instrument_status(self, instrument_id: str, status: InstrumentStatus) -> bool:
        await self.initialize()
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE mindex.scientific_instruments
                SET status = $2, updated_at = NOW()
                WHERE id = $1
                """,
                instrument_id,
                status.value,
            )
        return result and result.split()[-1] != "0"

    async def list_simulations(self) -> List[Simulation]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM mindex.scientific_simulations ORDER BY updated_at DESC")
        return [
            Simulation(
                id=row["id"],
                name=row["name"],
                type=SimulationType(row["type"]),
                status=SimulationStatus(row["status"]),
                progress=row["progress"] or 0,
                eta=row["eta"],
                gpu=row["gpu"],
                config=row["config"] or {},
            )
            for row in rows
        ]

    async def get_simulation(self, simulation_id: str) -> Optional[Simulation]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mindex.scientific_simulations WHERE id = $1",
                simulation_id,
            )
        if not row:
            return None
        return Simulation(
            id=row["id"],
            name=row["name"],
            type=SimulationType(row["type"]),
            status=SimulationStatus(row["status"]),
            progress=row["progress"] or 0,
            eta=row["eta"],
            gpu=row["gpu"],
            config=row["config"] or {},
        )

    async def create_simulation(self, data: SimulationCreate) -> Simulation:
        await self.initialize()
        sim_id = f"sim-{uuid.uuid4().hex[:8]}"
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.scientific_simulations
                (id, name, type, status, progress, config, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, NOW())
                """,
                sim_id,
                data.name,
                data.type.value,
                SimulationStatus.QUEUED.value,
                0,
                json.dumps(data.config or {}),
            )
        return Simulation(
            id=sim_id,
            name=data.name,
            type=data.type,
            status=SimulationStatus.QUEUED,
            progress=0,
            config=data.config,
        )

    async def set_simulation_status(self, simulation_id: str, status: SimulationStatus) -> bool:
        await self.initialize()
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE mindex.scientific_simulations
                SET status = $2, updated_at = NOW()
                WHERE id = $1
                """,
                simulation_id,
                status.value,
            )
        return result and result.split()[-1] != "0"

    async def list_experiments(self) -> List[Experiment]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM mindex.scientific_experiments ORDER BY updated_at DESC")
        return [
            Experiment(
                id=row["id"],
                name=row["name"],
                status=ExperimentStatus(row["status"]),
                currentStep=row["current_step"] or 0,
                totalSteps=row["total_steps"] or 0,
                parameters=row["parameters"] or {},
                startedAt=row["started_at"].isoformat() if row["started_at"] else None,
            )
            for row in rows
        ]

    async def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mindex.scientific_experiments WHERE id = $1",
                experiment_id,
            )
        if not row:
            return None
        return Experiment(
            id=row["id"],
            name=row["name"],
            status=ExperimentStatus(row["status"]),
            currentStep=row["current_step"] or 0,
            totalSteps=row["total_steps"] or 0,
            parameters=row["parameters"] or {},
            startedAt=row["started_at"].isoformat() if row["started_at"] else None,
        )

    async def create_experiment(self, data: ExperimentCreate) -> Experiment:
        await self.initialize()
        exp_id = f"E-{uuid.uuid4().hex[:4].upper()}"
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.scientific_experiments
                (id, name, status, current_step, total_steps, parameters, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, NOW())
                """,
                exp_id,
                data.name,
                ExperimentStatus.PENDING.value,
                0,
                0,
                json.dumps(data.parameters or {}),
            )
        return Experiment(
            id=exp_id,
            name=data.name,
            status=ExperimentStatus.PENDING,
            currentStep=0,
            totalSteps=0,
            parameters=data.parameters,
        )

    async def set_experiment_status(
        self, experiment_id: str, status: ExperimentStatus, started_at: Optional[datetime] = None
    ) -> bool:
        await self.initialize()
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE mindex.scientific_experiments
                SET status = $2,
                    started_at = COALESCE($3, started_at),
                    updated_at = NOW()
                WHERE id = $1
                """,
                experiment_id,
                status.value,
                started_at,
            )
        return result and result.split()[-1] != "0"

    async def list_hypotheses(self) -> List[Hypothesis]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM mindex.scientific_hypotheses ORDER BY updated_at DESC")
        return [
            Hypothesis(
                id=row["id"],
                statement=row["statement"],
                status=HypothesisStatus(row["status"]),
                confidence=row["confidence"],
                experiments=row["experiments"] or [],
            )
            for row in rows
        ]

    async def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mindex.scientific_hypotheses WHERE id = $1",
                hypothesis_id,
            )
        if not row:
            return None
        return Hypothesis(
            id=row["id"],
            statement=row["statement"],
            status=HypothesisStatus(row["status"]),
            confidence=row["confidence"],
            experiments=row["experiments"] or [],
        )

    async def create_hypothesis(self, data: HypothesisCreate) -> Hypothesis:
        await self.initialize()
        hyp_id = f"H-{uuid.uuid4().hex[:4].upper()}"
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.scientific_hypotheses
                (id, statement, status, updated_at)
                VALUES ($1, $2, $3, NOW())
                """,
                hyp_id,
                data.statement,
                HypothesisStatus.PROPOSED.value,
            )
        return Hypothesis(id=hyp_id, statement=data.statement, status=HypothesisStatus.PROPOSED)

    async def set_hypothesis_status(self, hypothesis_id: str, status: HypothesisStatus) -> bool:
        await self.initialize()
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE mindex.scientific_hypotheses
                SET status = $2, updated_at = NOW()
                WHERE id = $1
                """,
                hypothesis_id,
                status.value,
            )
        return result and result.split()[-1] != "0"

    async def list_fci_sessions(self) -> List[FCISession]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM mindex.scientific_fci_sessions ORDER BY updated_at DESC")
        return [
            FCISession(
                id=row["id"],
                species=row["species"],
                strain=row["strain"],
                status=FCISessionStatus(row["status"]),
                duration=row["duration"] or 0,
                electrodesActive=row["electrodes_active"],
                totalElectrodes=row["total_electrodes"],
                sampleRate=row["sample_rate"],
            )
            for row in rows
        ]

    async def get_fci_session(self, session_id: str) -> Optional[FCISession]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mindex.scientific_fci_sessions WHERE id = $1",
                session_id,
            )
        if not row:
            return None
        return FCISession(
            id=row["id"],
            species=row["species"],
            strain=row["strain"],
            status=FCISessionStatus(row["status"]),
            duration=row["duration"] or 0,
            electrodesActive=row["electrodes_active"],
            totalElectrodes=row["total_electrodes"],
            sampleRate=row["sample_rate"],
        )

    async def create_fci_session(self, data: FCISessionCreate) -> FCISession:
        await self.initialize()
        session_id = f"fci-{uuid.uuid4().hex[:6]}"
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.scientific_fci_sessions
                (id, species, strain, status, duration, electrodes_active, total_electrodes, sample_rate, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """,
                session_id,
                data.species,
                data.strain,
                FCISessionStatus.IDLE.value,
                0,
                60,
                64,
                1000,
            )
        return FCISession(
            id=session_id,
            species=data.species,
            strain=data.strain,
            status=FCISessionStatus.IDLE,
            duration=0,
            electrodesActive=60,
            totalElectrodes=64,
            sampleRate=1000,
        )

    async def set_fci_session_status(self, session_id: str, status: FCISessionStatus) -> bool:
        await self.initialize()
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE mindex.scientific_fci_sessions
                SET status = $2, updated_at = NOW()
                WHERE id = $1
                """,
                session_id,
                status.value,
            )
        return result and result.split()[-1] != "0"


_store: Optional[ScientificStore] = None


async def get_scientific_store() -> ScientificStore:
    global _store
    if _store is None:
        _store = ScientificStore()
        await _store.initialize()
    return _store


# --- Lab Instruments API ---

@router.get("/lab/instruments")
async def list_instruments():
    store = await get_scientific_store()
    instruments = await store.list_instruments()
    return {
        "instruments": instruments,
        "source": "live"
    }


@router.post("/lab/instruments")
async def create_instrument(data: InstrumentCreate):
    store = await get_scientific_store()
    return await store.create_instrument(data)


@router.get("/lab/instruments/{instrument_id}")
async def get_instrument(instrument_id: str):
    store = await get_scientific_store()
    instrument = await store.get_instrument(instrument_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return instrument


@router.post("/lab/instruments/{instrument_id}/calibrate")
async def calibrate_instrument(instrument_id: str):
    store = await get_scientific_store()
    updated = await store.set_instrument_status(instrument_id, InstrumentStatus.MAINTENANCE)
    if not updated:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return {"status": "calibrating", "instrumentId": instrument_id}


# --- Simulations API ---

@router.get("/simulation/jobs")
async def list_simulations():
    store = await get_scientific_store()
    simulations = await store.list_simulations()
    running = [s for s in simulations if s.status == SimulationStatus.RUNNING]
    return {
        "simulations": simulations,
        "gpuUtilization": None,
        "queueLength": len([s for s in simulations if s.status == SimulationStatus.QUEUED]),
        "source": "live"
    }


@router.post("/simulation/jobs")
async def create_simulation(data: SimulationCreate):
    store = await get_scientific_store()
    return await store.create_simulation(data)


@router.get("/simulation/jobs/{simulation_id}")
async def get_simulation(simulation_id: str):
    store = await get_scientific_store()
    simulation = await store.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulation


@router.post("/simulation/jobs/{simulation_id}/{action}")
async def control_simulation(simulation_id: str, action: str):
    store = await get_scientific_store()
    if action == "pause":
        status = SimulationStatus.PAUSED
    elif action == "resume":
        status = SimulationStatus.RUNNING
    elif action == "cancel":
        status = SimulationStatus.FAILED
    else:
        raise HTTPException(status_code=400, detail="Unsupported action")
    updated = await store.set_simulation_status(simulation_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"status": status, "simulationId": simulation_id}


# --- Experiments API ---

@router.get("/experiments")
async def list_experiments():
    store = await get_scientific_store()
    experiments = await store.list_experiments()
    stats = {
        "running": len([e for e in experiments if e.status == ExperimentStatus.RUNNING]),
        "pending": len([e for e in experiments if e.status == ExperimentStatus.PENDING]),
        "completed": len([e for e in experiments if e.status == ExperimentStatus.COMPLETED]),
        "failed": len([e for e in experiments if e.status == ExperimentStatus.FAILED]),
    }
    return {
        "experiments": experiments,
        "stats": stats,
        "source": "live"
    }


@router.post("/experiments")
async def create_experiment(data: ExperimentCreate):
    store = await get_scientific_store()
    return await store.create_experiment(data)


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    store = await get_scientific_store()
    experiment = await store.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.post("/experiments/{experiment_id}/{action}")
async def control_experiment(experiment_id: str, action: str):
    if action == "start":
        status = ExperimentStatus.RUNNING
        started_at = datetime.now(timezone.utc)
    elif action == "pause":
        status = ExperimentStatus.PENDING
        started_at = None
    elif action == "cancel":
        status = ExperimentStatus.FAILED
        started_at = None
    else:
        raise HTTPException(status_code=400, detail="Unsupported action")
    store = await get_scientific_store()
    updated = await store.set_experiment_status(experiment_id, status, started_at=started_at)
    if not updated:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"status": status, "experimentId": experiment_id}


# --- Hypotheses API ---

@router.get("/hypotheses")
async def list_hypotheses():
    store = await get_scientific_store()
    hypotheses = await store.list_hypotheses()
    stats = {
        "proposed": len([h for h in hypotheses if h.status == HypothesisStatus.PROPOSED]),
        "testing": len([h for h in hypotheses if h.status == HypothesisStatus.TESTING]),
        "validated": len([h for h in hypotheses if h.status == HypothesisStatus.VALIDATED]),
        "rejected": len([h for h in hypotheses if h.status == HypothesisStatus.REJECTED]),
    }
    return {
        "hypotheses": hypotheses,
        "stats": stats,
        "source": "live"
    }


@router.post("/hypotheses")
async def create_hypothesis(data: HypothesisCreate):
    store = await get_scientific_store()
    return await store.create_hypothesis(data)


@router.post("/hypotheses/{hypothesis_id}/test")
async def test_hypothesis(hypothesis_id: str):
    store = await get_scientific_store()
    updated = await store.set_hypothesis_status(hypothesis_id, HypothesisStatus.TESTING)
    if not updated:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return {"status": HypothesisStatus.TESTING, "hypothesisId": hypothesis_id}


# --- Bio/FCI API ---

@router.get("/bio/fci/sessions")
async def list_fci_sessions():
    store = await get_scientific_store()
    sessions = await store.list_fci_sessions()
    return {
        "sessions": sessions,
        "electrodeStatus": [],
        "signalQuality": None,
        "source": "live"
    }


@router.post("/bio/fci/sessions")
async def create_fci_session(data: FCISessionCreate):
    store = await get_scientific_store()
    return await store.create_fci_session(data)


@router.post("/bio/fci/sessions/{session_id}/{action}")
async def control_fci_session(session_id: str, action: str):
    store = await get_scientific_store()
    if action == "start":
        status = FCISessionStatus.RECORDING
    elif action == "pause":
        status = FCISessionStatus.PAUSED
    elif action == "stop":
        status = FCISessionStatus.IDLE
    elif action == "stimulate":
        status = FCISessionStatus.STIMULATING
    else:
        raise HTTPException(status_code=400, detail="Unsupported action")

    updated = await store.set_fci_session_status(session_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail="FCI session not found")

    return {"status": status, "sessionId": session_id}


@router.get("/bio/fci/sessions/{session_id}/signals")
async def get_fci_signals(session_id: str):
    store = await get_scientific_store()
    session = await store.get_fci_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="FCI session not found")
    raise HTTPException(status_code=503, detail="FCI signal stream not available")


# --- Bio/MycoBrain API ---

@router.get("/bio/mycobrain/status")
async def get_mycobrain_status():
    service_url = os.getenv("MYCOBRAIN_SERVICE_URL") or os.getenv("MYCOBRAIN_API_URL")
    if not service_url:
        raise HTTPException(status_code=503, detail="MYCOBRAIN_SERVICE_URL not configured")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service_url.rstrip('/')}/health")
            response.raise_for_status()
            payload = response.json()
        return {"status": "online", "health": payload, "source": "live"}
    except Exception as exc:
        logger.warning("MycoBrain status fetch failed: %s", exc)
        raise HTTPException(status_code=503, detail="MycoBrain service unavailable")


@router.post("/bio/mycobrain/compute")
async def submit_mycobrain_compute(mode: str = Body(...), input: dict = Body(...)):
    raise HTTPException(status_code=503, detail="MycoBrain compute endpoint not configured")


# --- Safety API ---

@router.get("/safety/status")
async def get_safety_status():
    status_url = os.getenv("SAFETY_STATUS_URL")
    if not status_url:
        raise HTTPException(status_code=503, detail="SAFETY_STATUS_URL not configured")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(status_url)
            response.raise_for_status()
            payload = response.json()
        payload["source"] = "live"
        return payload
    except Exception as exc:
        logger.warning("Safety status fetch failed: %s", exc)
        raise HTTPException(status_code=503, detail="Safety status unavailable")
