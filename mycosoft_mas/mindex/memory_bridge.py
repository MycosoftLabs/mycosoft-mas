"""MINDEX Memory Bridge - February 3, 2026

Bridges MINDEX taxonomic database with the unified memory system.
Enables semantic search over species observations and research hypotheses.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger("MINDEXMemoryBridge")


class MINDEXMemoryBridge:
    """Bridges MINDEX to the unified memory system."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("MINDEX_DATABASE_URL", os.getenv("DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/mindex"))
        self._memory_url = os.getenv("DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/mycosoft")
        self._memory_pool = None
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=5)
            self._memory_pool = await asyncpg.create_pool(self._memory_url, min_size=1, max_size=5)
            logger.info("MINDEX Memory Bridge connected")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
        if self._memory_pool:
            await self._memory_pool.close()
            self._memory_pool = None
    
    async def store_observation(
        self,
        taxon_id: str,
        scientific_name: str,
        common_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        observed_at: Optional[datetime] = None,
        image_urls: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> Optional[str]:
        if not self._memory_pool:
            await self.connect()
        
        observation_id = str(uuid4())
        value = {
            "observation_id": observation_id,
            "taxon_id": taxon_id,
            "scientific_name": scientific_name,
            "common_name": common_name,
            "location": {"latitude": latitude, "longitude": longitude} if latitude and longitude else None,
            "observed_at": observed_at.isoformat() if observed_at else datetime.now(timezone.utc).isoformat(),
            "image_urls": image_urls or [],
            "metadata": metadata or {},
        }
        
        try:
            async with self._memory_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source, embedding)
                    VALUES ('system', $1, $2, $3, 'mindex', $4)
                    ON CONFLICT (scope, namespace, key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = NOW()
                ''', f"mindex:observations:{taxon_id}", observation_id, value, embedding)
            
            logger.debug(f"Stored observation {observation_id} for {scientific_name}")
            return observation_id
        except Exception as e:
            logger.error(f"Failed to store observation: {e}")
            return None
    
    async def store_hypothesis(
        self,
        hypothesis_id: Optional[str] = None,
        title: str = "",
        description: str = "",
        related_taxa: Optional[List[str]] = None,
        status: str = "proposed",
        confidence: float = 0.5,
        evidence: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> Optional[str]:
        if not self._memory_pool:
            await self.connect()
        
        hypothesis_id = hypothesis_id or str(uuid4())
        value = {
            "hypothesis_id": hypothesis_id,
            "title": title,
            "description": description,
            "related_taxa": related_taxa or [],
            "status": status,
            "confidence": confidence,
            "evidence": evidence or [],
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            async with self._memory_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source, confidence, embedding)
                    VALUES ('experiment', 'mindex:hypotheses', $1, $2, 'mindex', $3, $4)
                    ON CONFLICT (scope, namespace, key) DO UPDATE SET
                        value = EXCLUDED.value,
                        confidence = EXCLUDED.confidence,
                        updated_at = NOW()
                ''', hypothesis_id, value, confidence, embedding)
            
            logger.info(f"Stored hypothesis: {title[:50]}...")
            return hypothesis_id
        except Exception as e:
            logger.error(f"Failed to store hypothesis: {e}")
            return None
    
    async def search_observations_semantic(
        self,
        query_embedding: List[float],
        taxon_filter: Optional[str] = None,
        limit: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        if not self._memory_pool:
            await self.connect()
        
        try:
            async with self._memory_pool.acquire() as conn:
                query = '''
                    SELECT id, namespace, key, value, source, confidence,
                           1 - (embedding <=> $1::vector) as similarity
                    FROM memory.entries
                    WHERE scope = 'system' 
                      AND namespace LIKE 'mindex:observations:%'
                      AND embedding IS NOT NULL
                '''
                params = [query_embedding]
                
                if taxon_filter:
                    query += " AND namespace LIKE $2"
                    params.append(f"mindex:observations:{taxon_filter}%")
                
                query += " ORDER BY embedding <=> $1::vector LIMIT " + str(limit)
                
                rows = await conn.fetch(query, *params)
                
                results = []
                for row in rows:
                    results.append((dict(row["value"]), float(row["similarity"])))
                
                return results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    async def search_hypotheses_semantic(
        self,
        query_embedding: List[float],
        status_filter: Optional[str] = None,
        limit: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        if not self._memory_pool:
            await self.connect()
        
        try:
            async with self._memory_pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT id, key, value, confidence,
                           1 - (embedding <=> $1::vector) as similarity
                    FROM memory.entries
                    WHERE scope = 'experiment' 
                      AND namespace = 'mindex:hypotheses'
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                ''', query_embedding, limit)
                
                results = []
                for row in rows:
                    if status_filter and row["value"].get("status") != status_filter:
                        continue
                    results.append((dict(row["value"]), float(row["similarity"])))
                
                return results
        except Exception as e:
            logger.error(f"Hypothesis search failed: {e}")
            return []
    
    async def sync_taxa_to_memory(self, limit: int = 1000) -> int:
        if not self._pool or not self._memory_pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as mindex_conn:
                taxa = await mindex_conn.fetch('''
                    SELECT id, scientific_name, common_name, kingdom, phylum, 
                           class, "order", family, genus, species, rank, metadata
                    FROM taxa
                    ORDER BY updated_at DESC
                    LIMIT $1
                ''', limit)
            
            synced = 0
            async with self._memory_pool.acquire() as mem_conn:
                for taxon in taxa:
                    value = {
                        "taxon_id": str(taxon["id"]),
                        "scientific_name": taxon["scientific_name"],
                        "common_name": taxon["common_name"],
                        "taxonomy": {
                            "kingdom": taxon["kingdom"],
                            "phylum": taxon["phylum"],
                            "class": taxon["class"],
                            "order": taxon["order"],
                            "family": taxon["family"],
                            "genus": taxon["genus"],
                            "species": taxon["species"],
                        },
                        "rank": taxon["rank"],
                        "metadata": taxon["metadata"] or {},
                    }
                    
                    await mem_conn.execute('''
                        INSERT INTO memory.entries 
                            (scope, namespace, key, value, source)
                        VALUES ('system', 'mindex:taxa', $1, $2, 'mindex')
                        ON CONFLICT (scope, namespace, key) DO UPDATE SET
                            value = EXCLUDED.value,
                            updated_at = NOW()
                    ''', str(taxon["id"]), value)
                    synced += 1
            
            logger.info(f"Synced {synced} taxa to memory")
            return synced
        except Exception as e:
            logger.error(f"Taxa sync failed: {e}")
            return 0
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        if not self._memory_pool:
            await self.connect()
        
        try:
            async with self._memory_pool.acquire() as conn:
                observation_count = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.entries 
                    WHERE namespace LIKE 'mindex:observations:%'
                ''')
                hypothesis_count = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.entries 
                    WHERE namespace = 'mindex:hypotheses'
                ''')
                taxa_count = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.entries 
                    WHERE namespace = 'mindex:taxa'
                ''')
                
                return {
                    "observations_in_memory": observation_count or 0,
                    "hypotheses_in_memory": hypothesis_count or 0,
                    "taxa_in_memory": taxa_count or 0,
                }
        except Exception as e:
            logger.error(f"Stats failed: {e}")
            return {}


_bridge: Optional[MINDEXMemoryBridge] = None


def get_mindex_bridge() -> MINDEXMemoryBridge:
    global _bridge
    if _bridge is None:
        _bridge = MINDEXMemoryBridge()
    return _bridge


async def init_mindex_bridge() -> MINDEXMemoryBridge:
    bridge = get_mindex_bridge()
    await bridge.connect()
    return bridge
