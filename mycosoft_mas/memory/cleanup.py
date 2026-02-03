"""Memory Cleanup Service - February 3, 2026

Manages memory lifecycle: decay, compression, archival, and cleanup.
Runs as a background service to maintain memory health.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MemoryCleanupService")


class MemoryCleanupService:
    """Manage memory lifecycle with decay, compression, and archival."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mycosoft")
        self._running = False
        self._task = None
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=3)
            logger.info("Memory Cleanup Service connected")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def cleanup_expired(self) -> int:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval("SELECT memory.cleanup_expired()")
            logger.info(f"Cleaned up {result} expired memory entries")
            return result or 0
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    async def decay_old_memories(self, age_threshold_days: int = 30, decay_factor: float = 0.9) -> int:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    UPDATE memory.entries 
                    SET confidence = confidence * $1,
                        updated_at = NOW()
                    WHERE last_accessed_at < NOW() - ($2 || ' days')::INTERVAL
                      AND confidence > 0.1
                      AND scope NOT IN ('system', 'device')
                ''', decay_factor, str(age_threshold_days))
                
                count = int(result.split()[-1]) if result else 0
            logger.info(f"Decayed {count} old memory entries")
            return count
        except Exception as e:
            logger.error(f"Decay failed: {e}")
            return 0
    
    async def decay_graph_nodes(self, age_hours: int = 24) -> int:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval("SELECT memory.decay_graph_nodes($1)", age_hours)
            logger.info(f"Decayed {result} graph nodes")
            return result or 0
        except Exception as e:
            logger.error(f"Graph decay failed: {e}")
            return 0
    
    async def compress_conversation_history(self, conversation_id: str) -> Optional[str]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                entries = await conn.fetch('''
                    SELECT key, value FROM memory.entries
                    WHERE scope = 'conversation' AND namespace = $1
                    ORDER BY created_at
                ''', conversation_id)
                
                if len(entries) < 10:
                    return None
                
                messages = []
                for entry in entries:
                    if isinstance(entry["value"], dict):
                        messages.append(entry["value"])
                
                summary = f"Compressed conversation with {len(messages)} messages."
                topics = set()
                for msg in messages:
                    content = str(msg.get("content", "")).lower()
                    if "device" in content:
                        topics.add("devices")
                    if "agent" in content:
                        topics.add("agents")
                    if "workflow" in content:
                        topics.add("workflows")
                
                if topics:
                    summary += f" Topics: {', '.join(topics)}."
                
                await conn.execute('''
                    INSERT INTO memory.conversation_summaries 
                        (conversation_id, summary, topics, message_count)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (conversation_id) DO UPDATE SET
                        summary = EXCLUDED.summary,
                        topics = EXCLUDED.topics,
                        message_count = EXCLUDED.message_count
                ''', conversation_id, summary, list(topics), len(messages))
                
                await conn.execute('''
                    DELETE FROM memory.entries
                    WHERE scope = 'conversation' 
                      AND namespace = $1
                      AND created_at < (
                          SELECT created_at FROM memory.entries
                          WHERE scope = 'conversation' AND namespace = $1
                          ORDER BY created_at DESC
                          LIMIT 1 OFFSET 9
                      )
                ''', conversation_id)
            
            logger.info(f"Compressed conversation {conversation_id}")
            return summary
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return None
    
    async def archive_expired_sessions(self) -> int:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT session_id, conversation_id, user_id, turn_count
                    FROM memory.voice_sessions
                    WHERE is_active = FALSE 
                      AND ended_at < NOW() - INTERVAL '1 day'
                      AND ended_at IS NOT NULL
                ''')
                
                archived = 0
                for row in rows:
                    await conn.execute('''
                        INSERT INTO memory.entries 
                            (scope, namespace, key, value, source)
                        VALUES ('user', 'archived_sessions:' || $1, $2, 
                            jsonb_build_object(
                                'session_id', $2,
                                'conversation_id', $3,
                                'turn_count', $4,
                                'archived_at', NOW()
                            ), 'system')
                        ON CONFLICT DO NOTHING
                    ''', str(row["user_id"]) if row["user_id"] else "anonymous",
                        row["session_id"], row["conversation_id"], row["turn_count"])
                    archived += 1
            
            logger.info(f"Archived {archived} expired voice sessions")
            return archived
        except Exception as e:
            logger.error(f"Archive failed: {e}")
            return 0
    
    async def vacuum_orphaned_relationships(self) -> int:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM memory.relationships
                    WHERE from_entry_id NOT IN (SELECT id FROM memory.entries)
                       OR to_entry_id NOT IN (SELECT id FROM memory.entries)
                ''')
                count = int(result.split()[-1]) if result else 0
            logger.info(f"Vacuumed {count} orphaned relationships")
            return count
        except Exception as e:
            logger.error(f"Vacuum failed: {e}")
            return 0
    
    async def get_cleanup_stats(self) -> Dict[str, Any]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                expired_count = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.entries 
                    WHERE expires_at IS NOT NULL AND expires_at < NOW()
                ''')
                low_confidence = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.entries 
                    WHERE confidence < 0.2
                ''')
                old_conversations = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.entries 
                    WHERE scope = 'conversation' 
                      AND created_at < NOW() - INTERVAL '7 days'
                ''')
                orphaned_nodes = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.graph_nodes 
                    WHERE importance_score < 0.1
                ''')
                
                return {
                    "expired_entries": expired_count or 0,
                    "low_confidence_entries": low_confidence or 0,
                    "stale_conversations": old_conversations or 0,
                    "low_importance_nodes": orphaned_nodes or 0,
                }
        except Exception as e:
            logger.error(f"Stats failed: {e}")
            return {}
    
    async def run_maintenance_cycle(self) -> Dict[str, int]:
        results = {}
        
        results["expired_cleaned"] = await self.cleanup_expired()
        results["memories_decayed"] = await self.decay_old_memories()
        results["nodes_decayed"] = await self.decay_graph_nodes()
        results["sessions_archived"] = await self.archive_expired_sessions()
        results["orphans_vacuumed"] = await self.vacuum_orphaned_relationships()
        
        logger.info(f"Maintenance cycle complete: {results}")
        return results
    
    async def start_background_loop(self, interval_minutes: int = 60):
        self._running = True
        logger.info(f"Starting cleanup loop with {interval_minutes} minute interval")
        
        while self._running:
            try:
                await self.run_maintenance_cycle()
            except Exception as e:
                logger.error(f"Maintenance cycle failed: {e}")
            
            await asyncio.sleep(interval_minutes * 60)
    
    def start_async(self, interval_minutes: int = 60):
        self._task = asyncio.create_task(self.start_background_loop(interval_minutes))
        return self._task
    
    def stop(self):
        self._running = False


_cleanup_service: Optional[MemoryCleanupService] = None


def get_cleanup_service() -> MemoryCleanupService:
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = MemoryCleanupService()
    return _cleanup_service
