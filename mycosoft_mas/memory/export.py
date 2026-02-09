"""Memory Export/Import - February 3, 2026

Export and import memory data for backup and portability.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MemoryExport")


class MemoryExporter:
    """Export and import memory data."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mycosoft")
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=3)
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def export_user_memory(self, user_id: str) -> Dict[str, Any]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                entries = await conn.fetch('''
                    SELECT scope, namespace, key, value, confidence, created_at
                    FROM memory.entries
                    WHERE namespace LIKE $1 OR namespace LIKE $2
                ''', f"user:{user_id}%", f"profile:{user_id}%")
                
                profile = await conn.fetchrow('''
                    SELECT * FROM memory.user_profiles WHERE user_id = $1::uuid
                ''', user_id)
                
                summaries = await conn.fetch('''
                    SELECT * FROM memory.conversation_summaries WHERE user_id = $1::uuid
                ''', user_id)
                
                return {
                    "export_version": "1.0",
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "user_id": user_id,
                    "entries": [dict(e) for e in entries],
                    "profile": dict(profile) if profile else None,
                    "conversation_summaries": [dict(s) for s in summaries],
                }
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {"error": str(e)}
    
    async def import_user_memory(self, data: Dict[str, Any]) -> int:
        if not self._pool:
            await self.connect()
        
        imported = 0
        user_id = data.get("user_id")
        
        try:
            async with self._pool.acquire() as conn:
                for entry in data.get("entries", []):
                    await conn.execute('''
                        INSERT INTO memory.entries (scope, namespace, key, value, confidence)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (scope, namespace, key) DO UPDATE SET
                            value = EXCLUDED.value,
                            confidence = EXCLUDED.confidence,
                            updated_at = NOW()
                    ''', entry["scope"], entry["namespace"], entry["key"], 
                        entry["value"], entry.get("confidence", 1.0))
                    imported += 1
                
                profile = data.get("profile")
                if profile:
                    await conn.execute('''
                        INSERT INTO memory.user_profiles (user_id, preferences, expertise_domains, personality_traits)
                        VALUES ($1::uuid, $2, $3, $4)
                        ON CONFLICT (user_id) DO UPDATE SET
                            preferences = EXCLUDED.preferences,
                            expertise_domains = EXCLUDED.expertise_domains,
                            updated_at = NOW()
                    ''', user_id, profile.get("preferences", {}), 
                        profile.get("expertise_domains", []), profile.get("personality_traits", {}))
                    imported += 1
            
            logger.info(f"Imported {imported} items for user {user_id}")
            return imported
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return 0
    
    async def backup_all_memory(self, output_path: str) -> bool:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                entries = await conn.fetch("SELECT * FROM memory.entries LIMIT 100000")
                profiles = await conn.fetch("SELECT * FROM memory.user_profiles")
                relationships = await conn.fetch("SELECT * FROM memory.relationships")
                
                backup = {
                    "backup_version": "1.0",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "entries": [dict(e) for e in entries],
                    "profiles": [dict(p) for p in profiles],
                    "relationships": [dict(r) for r in relationships],
                }
                
                with open(output_path, "w") as f:
                    json.dump(backup, f, default=str, indent=2)
                
                logger.info(f"Backup saved to {output_path}")
                return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    async def restore_from_backup(self, input_path: str) -> int:
        if not self._pool:
            await self.connect()
        
        try:
            with open(input_path, "r") as f:
                backup = json.load(f)
            
            restored = 0
            async with self._pool.acquire() as conn:
                for entry in backup.get("entries", []):
                    await conn.execute('''
                        INSERT INTO memory.entries (id, scope, namespace, key, value, source, confidence)
                        VALUES ($1::uuid, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (scope, namespace, key) DO NOTHING
                    ''', entry["id"], entry["scope"], entry["namespace"], entry["key"],
                        entry["value"], entry.get("source"), entry.get("confidence", 1.0))
                    restored += 1
            
            logger.info(f"Restored {restored} entries from {input_path}")
            return restored
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return 0


_exporter: Optional[MemoryExporter] = None


def get_exporter() -> MemoryExporter:
    global _exporter
    if _exporter is None:
        _exporter = MemoryExporter()
    return _exporter
