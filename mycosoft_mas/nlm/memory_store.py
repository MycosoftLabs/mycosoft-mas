"""NLM Memory Store - February 3, 2026

Stores Nature Learning Model training runs, checkpoints, and predictions
in the unified memory system for versioning and analysis.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("NLMMemoryStore")


class NLMMemoryStore:
    """Store NLM training and prediction data in memory."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mycosoft")
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=3)
            logger.info("NLM Memory Store connected")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def store_training_run(
        self,
        model_name: str,
        model_version: str,
        dataset_name: str,
        hyperparameters: Dict[str, Any],
        metrics: Dict[str, float],
        duration_seconds: int,
        checkpoint_path: Optional[str] = None
    ) -> Optional[str]:
        if not self._pool:
            await self.connect()
        
        run_id = str(uuid4())
        value = {
            "run_id": run_id,
            "model_name": model_name,
            "model_version": model_version,
            "dataset_name": dataset_name,
            "hyperparameters": hyperparameters,
            "metrics": metrics,
            "duration_seconds": duration_seconds,
            "checkpoint_path": checkpoint_path,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source, confidence)
                    VALUES ('experiment', 'nlm:training:' || $1, $2, $3, 'agent', $4)
                ''', model_name, run_id, value, metrics.get("accuracy", 0.5))
            
            logger.info(f"Stored training run {run_id} for {model_name}")
            return run_id
        except Exception as e:
            logger.error(f"Store training run failed: {e}")
            return None
    
    async def store_prediction(
        self,
        model_name: str,
        model_version: str,
        input_data: Dict[str, Any],
        prediction: Any,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        if not self._pool:
            await self.connect()
        
        prediction_id = str(uuid4())
        value = {
            "prediction_id": prediction_id,
            "model_name": model_name,
            "model_version": model_version,
            "input_summary": str(input_data)[:500],
            "prediction": prediction,
            "confidence": confidence,
            "metadata": metadata or {},
            "predicted_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source, confidence)
                    VALUES ('experiment', 'nlm:predictions:' || $1, $2, $3, 'agent', $4)
                ''', model_name, prediction_id, value, confidence)
            return prediction_id
        except Exception as e:
            logger.error(f"Store prediction failed: {e}")
            return None
    
    async def get_training_history(
        self,
        model_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT value, confidence, created_at FROM memory.entries
                    WHERE scope = 'experiment' 
                      AND namespace = 'nlm:training:' || $1
                    ORDER BY created_at DESC
                    LIMIT $2
                ''', model_name, limit)
                return [dict(row["value"]) for row in rows]
        except Exception as e:
            logger.error(f"Get history failed: {e}")
            return []
    
    async def get_best_model(self, model_name: str, metric: str = "accuracy") -> Optional[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT value FROM memory.entries
                    WHERE scope = 'experiment' 
                      AND namespace = 'nlm:training:' || $1
                    ORDER BY confidence DESC
                    LIMIT 1
                ''', model_name)
                return dict(rows[0]["value"]) if rows else None
        except Exception as e:
            logger.error(f"Get best model failed: {e}")
            return None
    
    async def get_prediction_stats(self, model_name: str, hours: int = 24) -> Dict[str, Any]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                count = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.entries
                    WHERE scope = 'experiment' 
                      AND namespace = 'nlm:predictions:' || $1
                      AND created_at > NOW() - ($2 || ' hours')::INTERVAL
                ''', model_name, str(hours))
                
                avg_conf = await conn.fetchval('''
                    SELECT AVG(confidence) FROM memory.entries
                    WHERE scope = 'experiment' 
                      AND namespace = 'nlm:predictions:' || $1
                      AND created_at > NOW() - ($2 || ' hours')::INTERVAL
                ''', model_name, str(hours))
                
                return {
                    "prediction_count": count or 0,
                    "avg_confidence": float(avg_conf) if avg_conf else 0.0,
                    "period_hours": hours,
                }
        except Exception as e:
            logger.error(f"Get stats failed: {e}")
            return {}


_nlm_store: Optional[NLMMemoryStore] = None


def get_nlm_store() -> NLMMemoryStore:
    global _nlm_store
    if _nlm_store is None:
        _nlm_store = NLMMemoryStore()
    return _nlm_store
