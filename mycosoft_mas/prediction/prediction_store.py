"""
Prediction Store - February 6, 2026

Stores predictions in MINDEX for timeline access.
Predictions are stored like regular timeline data but flagged as forecasts.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .prediction_types import (
    EntityType,
    PredictedPosition,
    PredictionResult,
    PredictionSource,
)

logger = logging.getLogger("PredictionStore")


class PredictionStore:
    """
    Stores predictions in MINDEX for unified timeline access.
    
    Predictions are stored in the same containers as historical data
    but marked with source="forecast" for differentiation.
    """
    
    # Table mapping by entity type
    ENTITY_TABLES = {
        EntityType.AIRCRAFT: "mindex.aircraft_tracks",
        EntityType.VESSEL: "mindex.vessel_tracks",
        EntityType.SATELLITE: "mindex.satellite_tracks",
        EntityType.WILDLIFE: "mindex.wildlife_observations",
        EntityType.STORM: "mindex.environmental_events",
        EntityType.WILDFIRE: "mindex.environmental_events",
        EntityType.EARTHQUAKE: "mindex.environmental_events",
        EntityType.WEATHER: "mindex.earth2_forecasts",
    }
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self._initialized = False
    
    async def initialize(self):
        """Initialize connection pool if not provided."""
        if self._initialized:
            return
        
        if self.db_pool is None:
            try:
                import asyncpg
                import os
                
                self.db_pool = await asyncpg.create_pool(
                    host=os.getenv("POSTGRES_HOST", "localhost"),
                    port=int(os.getenv("POSTGRES_PORT", "5432")),
                    user=os.getenv("POSTGRES_USER", "postgres"),
                    password=os.getenv("POSTGRES_PASSWORD", ""),
                    database=os.getenv("POSTGRES_DB", "mycosoft"),
                    min_size=2,
                    max_size=10,
                )
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise
        
        self._initialized = True
    
    async def store_predictions(
        self,
        result: PredictionResult,
        replace_existing: bool = True
    ) -> int:
        """
        Store prediction result in MINDEX.
        
        Args:
            result: Prediction result to store
            replace_existing: If True, delete existing predictions for this entity
        
        Returns:
            Number of predictions stored
        """
        if not result.predictions:
            return 0
        
        await self.initialize()
        
        entity_type = result.entity_type
        entity_id = result.entity_id
        
        async with self.db_pool.acquire() as conn:
            # Optionally delete existing predictions
            if replace_existing:
                await self._delete_predictions(
                    conn,
                    entity_type,
                    entity_id,
                    result.predictions[0].timestamp,
                    result.predictions[-1].timestamp,
                )
            
            # Insert new predictions
            count = await self._insert_predictions(conn, result.predictions)
            
            logger.info(
                f"Stored {count} predictions for {entity_type.value}/{entity_id}"
            )
            
            return count
    
    async def _delete_predictions(
        self,
        conn,
        entity_type: EntityType,
        entity_id: str,
        from_time: datetime,
        to_time: datetime
    ):
        """Delete existing predictions for an entity in a time range."""
        table = self.ENTITY_TABLES.get(entity_type)
        if not table:
            return
        
        # Delete where source indicates forecast
        await conn.execute(f"""
            DELETE FROM {table}
            WHERE entity_id = $1
              AND timestamp >= $2
              AND timestamp <= $3
              AND source IN ('forecast', 'prediction', 'extrapolation')
        """, entity_id, from_time, to_time)
    
    async def _insert_predictions(
        self,
        conn,
        predictions: List[PredictedPosition]
    ) -> int:
        """Insert predictions into appropriate table."""
        if not predictions:
            return 0
        
        entity_type = predictions[0].entity_type
        table = self.ENTITY_TABLES.get(entity_type)
        
        if not table:
            logger.warning(f"No table mapping for entity type: {entity_type}")
            return 0
        
        # Build values for batch insert
        values = []
        for pred in predictions:
            values.append((
                pred.entity_id,
                pred.entity_type.value,
                pred.timestamp,
                pred.position.lat,
                pred.position.lng,
                pred.position.altitude,
                pred.velocity.speed if pred.velocity else None,
                pred.velocity.heading if pred.velocity else None,
                pred.velocity.climb_rate if pred.velocity else None,
                pred.confidence,
                pred.uncertainty.radius_meters if pred.uncertainty else None,
                pred.prediction_source.value,
                pred.model_version,
                pred.metadata,
                pred.created_at,
            ))
        
        # Use COPY for efficiency if many rows
        if len(values) > 100:
            # Batch insert
            await conn.executemany(f"""
                INSERT INTO {table} (
                    entity_id, entity_type, timestamp,
                    lat, lng, altitude,
                    speed, heading, climb_rate,
                    confidence, uncertainty_radius,
                    source, model_version, metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (entity_id, timestamp) DO UPDATE SET
                    lat = EXCLUDED.lat,
                    lng = EXCLUDED.lng,
                    altitude = EXCLUDED.altitude,
                    confidence = EXCLUDED.confidence,
                    source = EXCLUDED.source
            """, values)
        else:
            for v in values:
                await conn.execute(f"""
                    INSERT INTO {table} (
                        entity_id, entity_type, timestamp,
                        lat, lng, altitude,
                        speed, heading, climb_rate,
                        confidence, uncertainty_radius,
                        source, model_version, metadata, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    ON CONFLICT (entity_id, timestamp) DO UPDATE SET
                        lat = EXCLUDED.lat,
                        lng = EXCLUDED.lng,
                        altitude = EXCLUDED.altitude,
                        confidence = EXCLUDED.confidence,
                        source = EXCLUDED.source
                """, *v)
        
        return len(values)
    
    async def get_predictions(
        self,
        entity_type: EntityType,
        entity_id: str,
        from_time: datetime,
        to_time: datetime,
        limit: int = 1000
    ) -> List[PredictedPosition]:
        """
        Retrieve stored predictions for an entity.
        """
        await self.initialize()
        
        table = self.ENTITY_TABLES.get(entity_type)
        if not table:
            return []
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT
                    entity_id, entity_type, timestamp,
                    lat, lng, altitude,
                    speed, heading, climb_rate,
                    confidence, uncertainty_radius,
                    source, model_version, metadata, created_at
                FROM {table}
                WHERE entity_id = $1
                  AND timestamp >= $2
                  AND timestamp <= $3
                  AND source IN ('forecast', 'prediction', 'extrapolation', 
                                 'flight_plan', 'orbit_propagation', 'earth2_forecast')
                ORDER BY timestamp
                LIMIT $4
            """, entity_id, from_time, to_time, limit)
        
        return [self._row_to_prediction(row) for row in rows]
    
    def _row_to_prediction(self, row) -> PredictedPosition:
        """Convert database row to PredictedPosition."""
        from .prediction_types import GeoPoint, Velocity, UncertaintyCone
        
        velocity = None
        if row["speed"] is not None:
            velocity = Velocity(
                speed=row["speed"],
                heading=row["heading"] or 0,
                climb_rate=row["climb_rate"],
            )
        
        uncertainty = None
        if row["uncertainty_radius"] is not None:
            uncertainty = UncertaintyCone(radius_meters=row["uncertainty_radius"])
        
        return PredictedPosition(
            entity_id=row["entity_id"],
            entity_type=EntityType(row["entity_type"]),
            timestamp=row["timestamp"],
            position=GeoPoint(
                lat=row["lat"],
                lng=row["lng"],
                altitude=row["altitude"],
            ),
            velocity=velocity,
            confidence=row["confidence"] or 1.0,
            uncertainty=uncertainty,
            prediction_source=PredictionSource(row["source"]),
            model_version=row["model_version"] or "1.0",
            metadata=row["metadata"] or {},
            created_at=row["created_at"],
        )
    
    async def cleanup_old_predictions(
        self,
        entity_type: EntityType,
        older_than: datetime
    ) -> int:
        """
        Remove predictions older than specified time.
        
        Used to clean up outdated forecasts.
        """
        await self.initialize()
        
        table = self.ENTITY_TABLES.get(entity_type)
        if not table:
            return 0
        
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(f"""
                DELETE FROM {table}
                WHERE timestamp < $1
                  AND source IN ('forecast', 'prediction', 'extrapolation')
            """, older_than)
            
            # Parse "DELETE X" to get count
            count = int(result.split()[-1]) if result else 0
            
            logger.info(f"Cleaned up {count} old predictions from {table}")
            
            return count


# Singleton instance
_store: Optional[PredictionStore] = None


async def get_prediction_store() -> PredictionStore:
    """Get the singleton prediction store instance."""
    global _store
    if _store is None:
        _store = PredictionStore()
        await _store.initialize()
    return _store