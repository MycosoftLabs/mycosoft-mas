"""Scientific Agent Memory Integration - February 3, 2026

Memory integration for scientific agents: experiments, hypotheses, results.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("ScientificAgentMemory")


class ScientificAgentMemory:
    """Memory integration for scientific agents."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mycosoft")
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=3)
            logger.info("Scientific agent memory connected")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def store_experiment(
        self,
        experiment_id: str,
        experiment_name: str,
        hypothesis: str,
        agent: str,
        parameters: Dict[str, Any],
        status: str = "running",
        results: Optional[Dict[str, Any]] = None,
        conclusion: Optional[str] = None,
        confidence: float = 0.5
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        value = {
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "hypothesis": hypothesis,
            "agent": agent,
            "parameters": parameters,
            "status": status,
            "results": results,
            "conclusion": conclusion,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source, confidence)
                    VALUES ('experiment', 'scientific:experiments', $1, $2, 'agent', $3)
                    ON CONFLICT (scope, namespace, key) DO UPDATE SET
                        value = EXCLUDED.value,
                        confidence = EXCLUDED.confidence,
                        updated_at = NOW()
                ''', experiment_id, value, confidence)
            
            logger.info(f"Stored experiment: {experiment_name}")
            return True
        except Exception as e:
            logger.error(f"Store experiment failed: {e}")
            return False
    
    async def update_experiment_results(
        self,
        experiment_id: str,
        results: Dict[str, Any],
        conclusion: str,
        status: str = "completed",
        confidence: float = 0.8
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    UPDATE memory.entries 
                    SET value = value || $1,
                        confidence = $2,
                        updated_at = NOW()
                    WHERE scope = 'experiment' 
                      AND namespace = 'scientific:experiments'
                      AND key = $3
                ''', {"results": results, "conclusion": conclusion, "status": status, 
                     "completed_at": datetime.now(timezone.utc).isoformat()},
                    confidence, experiment_id)
            return True
        except Exception as e:
            logger.error(f"Update results failed: {e}")
            return False
    
    async def store_simulation_run(
        self,
        simulation_id: str,
        simulation_type: str,
        parameters: Dict[str, Any],
        output: Dict[str, Any],
        agent: str,
        duration_seconds: int
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        value = {
            "simulation_id": simulation_id,
            "simulation_type": simulation_type,
            "parameters": parameters,
            "output_summary": str(output)[:2000],
            "agent": agent,
            "duration_seconds": duration_seconds,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source)
                    VALUES ('experiment', 'scientific:simulations', $1, $2, 'agent')
                ''', simulation_id, value)
            return True
        except Exception as e:
            logger.error(f"Store simulation failed: {e}")
            return False
    
    async def store_discovery(
        self,
        discovery_id: str,
        title: str,
        description: str,
        discovery_type: str,
        related_experiments: List[str],
        evidence: Dict[str, Any],
        confidence: float = 0.7
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        value = {
            "discovery_id": discovery_id,
            "title": title,
            "description": description,
            "discovery_type": discovery_type,
            "related_experiments": related_experiments,
            "evidence": evidence,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source, confidence)
                    VALUES ('system', 'scientific:discoveries', $1, $2, 'agent', $3)
                ''', discovery_id, value, confidence)
            
            logger.info(f"Stored discovery: {title}")
            return True
        except Exception as e:
            logger.error(f"Store discovery failed: {e}")
            return False
    
    async def get_experiments_by_agent(self, agent: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT value, confidence, created_at FROM memory.entries
                    WHERE scope = 'experiment' 
                      AND namespace = 'scientific:experiments'
                      AND value->>'agent' = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                ''', agent, limit)
                return [dict(row["value"]) for row in rows]
        except Exception as e:
            logger.error(f"Get experiments failed: {e}")
            return []
    
    async def search_experiments(
        self,
        query: str,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                sql = '''
                    SELECT value, confidence FROM memory.entries
                    WHERE scope = 'experiment' 
                      AND namespace = 'scientific:experiments'
                      AND (value->>'experiment_name' ILIKE $1 
                           OR value->>'hypothesis' ILIKE $1)
                '''
                params = [f"%{query}%"]
                
                if status:
                    sql += " AND value->>'status' = $2"
                    params.append(status)
                
                sql += f" ORDER BY confidence DESC LIMIT {limit}"
                
                rows = await conn.fetch(sql, *params)
                return [dict(row["value"]) for row in rows]
        except Exception as e:
            logger.error(f"Search experiments failed: {e}")
            return []
    
    async def get_recent_discoveries(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT value, confidence FROM memory.entries
                    WHERE scope = 'system' 
                      AND namespace = 'scientific:discoveries'
                      AND created_at > NOW() - ($1 || ' days')::INTERVAL
                    ORDER BY confidence DESC, created_at DESC
                    LIMIT $2
                ''', str(days), limit)
                return [dict(row["value"]) for row in rows]
        except Exception as e:
            logger.error(f"Get discoveries failed: {e}")
            return []


_sci_memory: Optional[ScientificAgentMemory] = None


def get_scientific_memory() -> ScientificAgentMemory:
    global _sci_memory
    if _sci_memory is None:
        _sci_memory = ScientificAgentMemory()
    return _sci_memory
