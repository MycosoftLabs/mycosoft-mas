"""Orchestrator Memory Logging - February 3, 2026

Logs MYCA orchestrator decisions and routing to memory for analysis.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("OrchestratorMemoryLog")


class OrchestratorMemoryLogger:
    """Logs orchestrator decisions to memory."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mycosoft")
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=3)
            logger.info("Orchestrator memory logger connected")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def log_routing_decision(
        self,
        conversation_id: str,
        user_input: str,
        selected_agent: str,
        confidence: float,
        alternatives: Optional[List[Dict[str, float]]] = None,
        reasoning: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        decision_id = str(uuid4())
        value = {
            "decision_id": decision_id,
            "decision_type": "agent_routing",
            "conversation_id": conversation_id,
            "user_input": user_input[:500],
            "selected_agent": selected_agent,
            "confidence": confidence,
            "alternatives": alternatives or [],
            "reasoning": reasoning,
            "latency_ms": latency_ms,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source, confidence)
                    VALUES ('agent', 'orchestrator:routing', $1, $2, 'orchestrator', $3)
                ''', decision_id, value, confidence)
            return True
        except Exception as e:
            logger.error(f"Log routing failed: {e}")
            return False
    
    async def log_tool_execution(
        self,
        conversation_id: str,
        agent: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Optional[Dict[str, Any]] = None,
        success: bool = True,
        latency_ms: Optional[int] = None,
        error: Optional[str] = None
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        execution_id = str(uuid4())
        value = {
            "execution_id": execution_id,
            "decision_type": "tool_execution",
            "conversation_id": conversation_id,
            "agent": agent,
            "tool_name": tool_name,
            "tool_input": str(tool_input)[:500],
            "tool_output": str(tool_output)[:500] if tool_output else None,
            "success": success,
            "latency_ms": latency_ms,
            "error": error,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source, confidence)
                    VALUES ('agent', 'orchestrator:tools', $1, $2, 'orchestrator', $3)
                ''', execution_id, value, 1.0 if success else 0.3)
            return True
        except Exception as e:
            logger.error(f"Log tool execution failed: {e}")
            return False
    
    async def log_context_switch(
        self,
        conversation_id: str,
        from_context: str,
        to_context: str,
        trigger: str,
        user_message: Optional[str] = None
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        switch_id = str(uuid4())
        value = {
            "switch_id": switch_id,
            "decision_type": "context_switch",
            "conversation_id": conversation_id,
            "from_context": from_context,
            "to_context": to_context,
            "trigger": trigger,
            "user_message": user_message[:200] if user_message else None,
            "switched_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source)
                    VALUES ('agent', 'orchestrator:context', $1, $2, 'orchestrator')
                ''', switch_id, value)
            return True
        except Exception as e:
            logger.error(f"Log context switch failed: {e}")
            return False
    
    async def get_routing_history(
        self,
        conversation_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                if conversation_id:
                    rows = await conn.fetch('''
                        SELECT value, created_at FROM memory.entries
                        WHERE scope = 'agent' 
                          AND namespace = 'orchestrator:routing'
                          AND value->>'conversation_id' = $1
                        ORDER BY created_at DESC
                        LIMIT $2
                    ''', conversation_id, limit)
                else:
                    rows = await conn.fetch('''
                        SELECT value, created_at FROM memory.entries
                        WHERE scope = 'agent' 
                          AND namespace = 'orchestrator:routing'
                        ORDER BY created_at DESC
                        LIMIT $1
                    ''', limit)
                return [dict(row["value"]) for row in rows]
        except Exception as e:
            logger.error(f"Get routing history failed: {e}")
            return []
    
    async def get_agent_usage_stats(self, hours: int = 24) -> Dict[str, int]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT value->>'selected_agent' as agent, COUNT(*) as count
                    FROM memory.entries
                    WHERE scope = 'agent' 
                      AND namespace = 'orchestrator:routing'
                      AND created_at > NOW() - ($1 || ' hours')::INTERVAL
                    GROUP BY value->>'selected_agent'
                    ORDER BY count DESC
                ''', str(hours))
                return {row["agent"]: row["count"] for row in rows}
        except Exception as e:
            logger.error(f"Get agent stats failed: {e}")
            return {}


_logger: Optional[OrchestratorMemoryLogger] = None


def get_orchestrator_logger() -> OrchestratorMemoryLogger:
    global _logger
    if _logger is None:
        _logger = OrchestratorMemoryLogger()
    return _logger
