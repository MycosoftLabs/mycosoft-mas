"""Memory Analytics - February 3, 2026

Analytics for memory system usage, patterns, and performance.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MemoryAnalytics")


class MemoryAnalytics:
    """Memory usage analytics and reporting."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mycosoft")
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=3)
            logger.info("Memory Analytics connected")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def get_scope_stats(self) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM memory.scope_stats")
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Scope stats failed: {e}")
            return []
    
    async def get_memory_usage_by_source(self) -> Dict[str, int]:
        if not self._pool:
            await self.connect()
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT source, COUNT(*) as count FROM memory.entries
                    WHERE source IS NOT NULL GROUP BY source
                ''')
                return {row["source"]: row["count"] for row in rows}
        except Exception as e:
            logger.error(f"Source stats failed: {e}")
            return {}
    
    async def get_access_patterns(self, hours: int = 24) -> Dict[str, Any]:
        if not self._pool:
            await self.connect()
        try:
            async with self._pool.acquire() as conn:
                total = await conn.fetchval("SELECT SUM(access_count) FROM memory.entries")
                top_accessed = await conn.fetch('''
                    SELECT namespace, key, access_count FROM memory.entries
                    ORDER BY access_count DESC LIMIT 10
                ''')
                return {
                    "total_accesses": total or 0,
                    "top_entries": [dict(row) for row in top_accessed],
                }
        except Exception as e:
            logger.error(f"Access patterns failed: {e}")
            return {}
    
    async def get_storage_growth(self, days: int = 7) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT DATE(created_at) as date, COUNT(*) as entries_created
                    FROM memory.entries
                    WHERE created_at > NOW() - ($1 || ' days')::INTERVAL
                    GROUP BY DATE(created_at) ORDER BY date
                ''', str(days))
                return [{"date": str(row["date"]), "count": row["entries_created"]} for row in rows]
        except Exception as e:
            logger.error(f"Growth stats failed: {e}")
            return []
    
    async def get_confidence_distribution(self) -> Dict[str, int]:
        if not self._pool:
            await self.connect()
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT 
                        CASE 
                            WHEN confidence >= 0.9 THEN 'high'
                            WHEN confidence >= 0.5 THEN 'medium'
                            ELSE 'low'
                        END as level,
                        COUNT(*) as count
                    FROM memory.entries GROUP BY level
                ''')
                return {row["level"]: row["count"] for row in rows}
        except Exception as e:
            logger.error(f"Confidence dist failed: {e}")
            return {}
    
    async def get_audit_summary(self, hours: int = 24) -> Dict[str, Any]:
        if not self._pool:
            await self.connect()
        try:
            async with self._pool.acquire() as conn:
                op_counts = await conn.fetch('''
                    SELECT operation, COUNT(*) as count, AVG(duration_ms) as avg_duration
                    FROM memory.audit_log
                    WHERE timestamp > NOW() - ($1 || ' hours')::INTERVAL
                    GROUP BY operation
                ''', str(hours))
                success_rate = await conn.fetchval('''
                    SELECT AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END)
                    FROM memory.audit_log
                    WHERE timestamp > NOW() - ($1 || ' hours')::INTERVAL
                ''', str(hours))
                return {
                    "operations": {row["operation"]: {"count": row["count"], "avg_duration_ms": float(row["avg_duration"] or 0)} for row in op_counts},
                    "success_rate": float(success_rate or 1.0),
                }
        except Exception as e:
            logger.error(f"Audit summary failed: {e}")
            return {}
    
    async def generate_report(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scope_stats": await self.get_scope_stats(),
            "source_distribution": await self.get_memory_usage_by_source(),
            "access_patterns": await self.get_access_patterns(),
            "confidence_distribution": await self.get_confidence_distribution(),
            "storage_growth": await self.get_storage_growth(),
            "audit_summary": await self.get_audit_summary(),
        }


_analytics: Optional[MemoryAnalytics] = None


def get_analytics() -> MemoryAnalytics:
    global _analytics
    if _analytics is None:
        _analytics = MemoryAnalytics()
    return _analytics
