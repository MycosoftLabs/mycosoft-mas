"""
Scientific PostgreSQL models and data access.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

try:
    import asyncpg
except Exception:  # pragma: no cover
    asyncpg = None


class ScientificExperiment(BaseModel):
    id: str
    name: str
    status: str
    protocol_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ScientificExperimentCreate(BaseModel):
    name: str
    status: str = "pending"
    protocol_json: Dict[str, Any] = Field(default_factory=dict)


class ScientificObservation(BaseModel):
    id: str
    experiment_id: str
    timestamp: datetime
    data_json: Dict[str, Any] = Field(default_factory=dict)
    sensor_source: Optional[str] = None


class ScientificObservationCreate(BaseModel):
    experiment_id: str
    data_json: Dict[str, Any] = Field(default_factory=dict)
    sensor_source: Optional[str] = None


class ScientificEquipment(BaseModel):
    id: str
    name: str
    status: str
    last_calibration: Optional[datetime] = None


class ScientificEquipmentCreate(BaseModel):
    name: str
    status: str = "online"
    last_calibration: Optional[datetime] = None


class ScientificDataset(BaseModel):
    id: str
    name: str
    source: str
    row_count: int = 0
    schema_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ScientificDatasetCreate(BaseModel):
    name: str
    source: str
    row_count: int = 0
    schema_json: Dict[str, Any] = Field(default_factory=dict)


class ScientificDataStore:
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = (
            database_url or os.getenv("DATABASE_URL") or os.getenv("MINDEX_DATABASE_URL")
        )
        if not self._database_url:
            raise RuntimeError("DATABASE_URL or MINDEX_DATABASE_URL is required.")
        self._pool: Optional["asyncpg.Pool"] = None

    async def initialize(self) -> None:
        if self._pool:
            return
        if asyncpg is None:
            raise RuntimeError("asyncpg is required for scientific data store.")
        self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=6)
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE SCHEMA IF NOT EXISTS mindex;")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS mindex.experiments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    protocol_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS mindex.observations (
                    id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL REFERENCES mindex.experiments(id) ON DELETE CASCADE,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    sensor_source TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_observations_experiment_id
                    ON mindex.observations (experiment_id);
                CREATE INDEX IF NOT EXISTS idx_observations_timestamp
                    ON mindex.observations (timestamp DESC);
                """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS mindex.lab_equipment (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_calibration TIMESTAMPTZ
                );
                """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS mindex.datasets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    row_count INTEGER NOT NULL DEFAULT 0,
                    schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """)

    async def list_experiments(self) -> List[ScientificExperiment]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name, status, protocol_json, created_at FROM mindex.experiments ORDER BY created_at DESC"
            )
        return [
            ScientificExperiment(
                id=row["id"],
                name=row["name"],
                status=row["status"],
                protocol_json=row["protocol_json"] or {},
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def create_experiment(self, data: ScientificExperimentCreate) -> ScientificExperiment:
        await self.initialize()
        experiment_id = f"exp-{uuid4().hex[:10]}"
        created_at = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.experiments (id, name, status, protocol_json, created_at)
                VALUES ($1, $2, $3, $4::jsonb, $5)
                """,
                experiment_id,
                data.name,
                data.status,
                json.dumps(data.protocol_json or {}),
                created_at,
            )
        return ScientificExperiment(
            id=experiment_id,
            name=data.name,
            status=data.status,
            protocol_json=data.protocol_json,
            created_at=created_at,
        )

    async def list_observations(
        self, experiment_id: Optional[str] = None
    ) -> List[ScientificObservation]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            if experiment_id:
                rows = await conn.fetch(
                    """
                    SELECT id, experiment_id, timestamp, data_json, sensor_source
                    FROM mindex.observations
                    WHERE experiment_id = $1
                    ORDER BY timestamp DESC
                    """,
                    experiment_id,
                )
            else:
                rows = await conn.fetch("""
                    SELECT id, experiment_id, timestamp, data_json, sensor_source
                    FROM mindex.observations
                    ORDER BY timestamp DESC
                    LIMIT 500
                    """)
        return [
            ScientificObservation(
                id=row["id"],
                experiment_id=row["experiment_id"],
                timestamp=row["timestamp"],
                data_json=row["data_json"] or {},
                sensor_source=row["sensor_source"],
            )
            for row in rows
        ]

    async def create_observation(self, data: ScientificObservationCreate) -> ScientificObservation:
        await self.initialize()
        observation_id = f"obs-{uuid4().hex[:10]}"
        timestamp = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.observations (id, experiment_id, timestamp, data_json, sensor_source)
                VALUES ($1, $2, $3, $4::jsonb, $5)
                """,
                observation_id,
                data.experiment_id,
                timestamp,
                json.dumps(data.data_json or {}),
                data.sensor_source,
            )
        return ScientificObservation(
            id=observation_id,
            experiment_id=data.experiment_id,
            timestamp=timestamp,
            data_json=data.data_json,
            sensor_source=data.sensor_source,
        )

    async def list_datasets(self) -> List[ScientificDataset]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name, source, row_count, schema_json, created_at FROM mindex.datasets ORDER BY created_at DESC"
            )
        return [
            ScientificDataset(
                id=row["id"],
                name=row["name"],
                source=row["source"],
                row_count=row["row_count"] or 0,
                schema_json=row["schema_json"] or {},
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def create_dataset(self, data: ScientificDatasetCreate) -> ScientificDataset:
        await self.initialize()
        dataset_id = f"ds-{uuid4().hex[:10]}"
        created_at = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.datasets (id, name, source, row_count, schema_json, created_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                dataset_id,
                data.name,
                data.source,
                data.row_count,
                json.dumps(data.schema_json or {}),
                created_at,
            )
        return ScientificDataset(
            id=dataset_id,
            name=data.name,
            source=data.source,
            row_count=data.row_count,
            schema_json=data.schema_json,
            created_at=created_at,
        )

    async def list_equipment(self) -> List[ScientificEquipment]:
        await self.initialize()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name, status, last_calibration FROM mindex.lab_equipment ORDER BY name ASC"
            )
        return [
            ScientificEquipment(
                id=row["id"],
                name=row["name"],
                status=row["status"],
                last_calibration=row["last_calibration"],
            )
            for row in rows
        ]

    async def create_equipment(self, data: ScientificEquipmentCreate) -> ScientificEquipment:
        await self.initialize()
        equipment_id = f"eq-{uuid4().hex[:10]}"
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.lab_equipment (id, name, status, last_calibration)
                VALUES ($1, $2, $3, $4)
                """,
                equipment_id,
                data.name,
                data.status,
                data.last_calibration,
            )
        return ScientificEquipment(
            id=equipment_id,
            name=data.name,
            status=data.status,
            last_calibration=data.last_calibration,
        )
