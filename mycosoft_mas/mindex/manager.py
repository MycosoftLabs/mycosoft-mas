"""
MINDEX Manager

Orchestrates data collection, storage, and search for the MINDEX system.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import threading

from .database import MINDEXDatabase
from .scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    FungiDBScraper,
    GenBankScraper,
)

logger = logging.getLogger(__name__)


class MINDEXManager:
    """
    Manager for MINDEX data operations.
    
    Handles:
    - Database initialization
    - Data scraping orchestration
    - Search across all sources
    - Continuous sync scheduling
    """
    
    SCRAPERS = {
        "iNaturalist": INaturalistScraper,
        "GBIF": GBIFScraper,
        "MycoBank": MycoBankScraper,
        "FungiDB": FungiDBScraper,
        "GenBank": GenBankScraper,
    }
    
    def __init__(self, db_path: Path):
        self.db = MINDEXDatabase(db_path)
        self._running = False
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.db.get_stats()
    
    async def search(
        self,
        query: str,
        sources: List[str] = None,
        kingdom: str = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Search for species across the database.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            sql = """
                SELECT * FROM species 
                WHERE (
                    scientific_name LIKE ? 
                    OR common_names LIKE ?
                    OR genus LIKE ?
                )
            """
            params = [f"%{query}%", f"%{query}%", f"%{query}%"]
            
            if kingdom:
                sql += " AND kingdom = ?"
                params.append(kingdom)
            
            if sources:
                placeholders = ",".join(["?" for _ in sources])
                sql += f" AND source IN ({placeholders})"
                params.extend(sources)
            
            sql += " ORDER BY scientific_name LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            return {
                "query": query,
                "results": results,
                "total": len(results),
            }
    
    async def sync_source(
        self,
        source: str,
        limit: int = 1000,
    ) -> Dict[str, int]:
        """
        Sync data from a specific source.
        """
        if source not in self.SCRAPERS:
            raise ValueError(f"Unknown source: {source}")
        
        logger.info(f"Starting sync from {source} (limit={limit})")
        
        # Record start
        start_time = datetime.now()
        
        try:
            scraper_class = self.SCRAPERS[source]
            scraper = scraper_class(db=self.db)
            
            stats = await scraper.sync(limit=limit)
            
            # Record completion
            duration = (datetime.now() - start_time).total_seconds()
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scrape_history 
                    (source, started_at, completed_at, status, 
                     records_fetched, records_inserted, duration_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    source,
                    start_time.isoformat(),
                    datetime.now().isoformat(),
                    "success",
                    stats.get("species_fetched", 0) + stats.get("observations_fetched", 0),
                    stats.get("species_inserted", 0) + stats.get("observations_inserted", 0),
                    duration,
                ))
                conn.commit()
            
            logger.info(f"Completed sync from {source}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Sync error for {source}: {e}")
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scrape_history 
                    (source, started_at, completed_at, status, errors, duration_seconds)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    source,
                    start_time.isoformat(),
                    datetime.now().isoformat(),
                    "error",
                    str(e),
                    (datetime.now() - start_time).total_seconds(),
                ))
                conn.commit()
            
            raise
    
    async def sync_all(self, limit_per_source: int = 1000) -> Dict[str, Dict[str, int]]:
        """
        Sync data from all sources.
        """
        all_stats = {}
        
        for source in self.SCRAPERS.keys():
            try:
                stats = await self.sync_source(source, limit=limit_per_source)
                all_stats[source] = stats
            except Exception as e:
                all_stats[source] = {"error": str(e)}
        
        return all_stats
    
    def start_continuous_sync(
        self,
        interval_hours: int = 24,
        limit_per_source: int = 1000,
    ):
        """
        Start continuous background sync.
        """
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        
        def sync_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while not self._stop_event.is_set():
                try:
                    loop.run_until_complete(
                        self.sync_all(limit_per_source=limit_per_source)
                    )
                except Exception as e:
                    logger.error(f"Continuous sync error: {e}")
                
                # Wait for next interval
                self._stop_event.wait(timeout=interval_hours * 3600)
            
            loop.close()
        
        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()
        logger.info(f"Started continuous sync every {interval_hours} hours")
    
    def stop_continuous_sync(self):
        """
        Stop continuous background sync.
        """
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        
        logger.info("Stopped continuous sync")


# Singleton instance
_manager: Optional[MINDEXManager] = None


def get_mindex_manager(db_path: Path = None) -> MINDEXManager:
    """Get or create the MINDEX manager instance."""
    global _manager
    
    if _manager is None:
        if db_path is None:
            db_path = Path("/app/data/mindex.db")
        _manager = MINDEXManager(db_path=db_path)
    
    return _manager
