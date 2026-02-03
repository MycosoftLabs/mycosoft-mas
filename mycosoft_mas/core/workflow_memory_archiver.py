"""N8N Workflow Memory Archival - February 3, 2026

Archives n8n workflow executions to memory for analytics and history.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("N8NWorkflowArchival")


class WorkflowMemoryArchiver:
    """Archives n8n workflow executions to memory."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mycosoft")
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=3)
            logger.info("Workflow archiver connected")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def archive_execution(
        self,
        workflow_id: str,
        workflow_name: str,
        execution_id: str,
        status: str,
        started_at: datetime,
        ended_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        trigger_type: str = "manual",
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        value = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "status": status,
            "trigger_type": trigger_type,
            "started_at": started_at.isoformat() if started_at else None,
            "ended_at": ended_at.isoformat() if ended_at else None,
            "duration_ms": duration_ms,
            "input_summary": str(input_data)[:1000] if input_data else None,
            "output_summary": str(output_data)[:1000] if output_data else None,
            "error_message": error_message,
        }
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source, confidence)
                    VALUES ('workflow', 'n8n:executions:' || $1, $2, $3, 'n8n', 
                        CASE $4 WHEN 'success' THEN 1.0 WHEN 'error' THEN 0.3 ELSE 0.5 END)
                    ON CONFLICT (scope, namespace, key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = NOW()
                ''', workflow_id, execution_id, value, status)
            
            logger.debug(f"Archived execution {execution_id} for workflow {workflow_name}")
            return True
        except Exception as e:
            logger.error(f"Archive failed: {e}")
            return False
    
    async def archive_workflow_state(
        self,
        workflow_id: str,
        workflow_name: str,
        is_active: bool,
        nodes_count: int,
        category: str,
        version: int,
        description: str = ""
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        value = {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "is_active": is_active,
            "nodes_count": nodes_count,
            "category": category,
            "version": version,
            "description": description,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source)
                    VALUES ('system', 'n8n:workflows', $1, $2, 'n8n')
                    ON CONFLICT (scope, namespace, key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = NOW()
                ''', workflow_id, value)
            return True
        except Exception as e:
            logger.error(f"State archive failed: {e}")
            return False
    
    async def get_execution_history(
        self,
        workflow_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT value, created_at FROM memory.entries
                    WHERE scope = 'workflow' 
                      AND namespace = 'n8n:executions:' || $1
                    ORDER BY created_at DESC
                    LIMIT $2
                ''', workflow_id, limit)
                return [dict(row["value"]) for row in rows]
        except Exception as e:
            logger.error(f"Get history failed: {e}")
            return []
    
    async def get_workflow_stats(self, workflow_id: str) -> Dict[str, Any]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                total = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.entries
                    WHERE scope = 'workflow' 
                      AND namespace = 'n8n:executions:' || $1
                ''', workflow_id)
                success = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.entries
                    WHERE scope = 'workflow' 
                      AND namespace = 'n8n:executions:' || $1
                      AND value->>'status' = 'success'
                ''', workflow_id)
                return {
                    "workflow_id": workflow_id,
                    "total_executions": total or 0,
                    "successful_executions": success or 0,
                    "success_rate": (success / total * 100) if total > 0 else 0,
                }
        except Exception as e:
            logger.error(f"Get stats failed: {e}")
            return {}


_archiver: Optional[WorkflowMemoryArchiver] = None


def get_workflow_archiver() -> WorkflowMemoryArchiver:
    global _archiver
    if _archiver is None:
        _archiver = WorkflowMemoryArchiver()
    return _archiver
