"""
MINDEX Manager

Orchestrates data collection, storage, and retrieval for the 
MINDEX fungal knowledge system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .database import MINDEXDatabase
from .scrapers import (
    BaseScraper,
    GBIFScraper,
    INaturalistScraper,
    FungiDBScraper,
    MycoBankScraper,
    GenBankScraper,
)

logger = logging.getLogger(__name__)


class MINDEXManager:
    """
    Central manager for MINDEX fungal knowledge system.
    
    Handles:
    - Data collection from multiple sources
    - Storage in SQLite database
    - Search and retrieval
    - Continuous sync and updates
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db = MINDEXDatabase(db_path)
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def search(
        self,
        query: str,
        sources: Optional[list[str]] = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Search for fungal species across all sources.
        
        First searches local database, then optionally queries
        external APIs for additional results.
        """
        results = {
            "query": query,
            "local_results": [],
            "api_results": [],
            "total_count": 0,
            "searched_at": datetime.utcnow().isoformat(),
        }
        
        # Search local database first
        local_results = self.db.search_species(query, limit=limit)
        results["local_results"] = local_results
        results["total_count"] += len(local_results)
        
        # If we have enough local results, return early
        if len(local_results) >= limit:
            return results
        
        # Otherwise, query external APIs
        remaining = limit - len(local_results)
        
        scrapers_to_use = {
            "iNaturalist": INaturalistScraper,
            "GBIF": GBIFScraper,
            "MycoBank": MycoBankScraper,
        }
        
        if sources:
            scrapers_to_use = {k: v for k, v in scrapers_to_use.items() if k in sources}
        
        for source_name, scraper_class in scrapers_to_use.items():
            try:
                async with scraper_class() as scraper:
                    result = await scraper.search_species(query, limit=remaining)
                    
                    if result.records:
                        results["api_results"].extend(result.records)
                        results["total_count"] += len(result.records)
                        
                        # Store new results in database
                        for record in result.records:
                            try:
                                self.db.insert_species(record)
                            except Exception as e:
                                logger.warning(f"Failed to store record: {e}")
            except Exception as e:
                logger.error(f"Error searching {source_name}: {e}")
        
        return results
    
    async def sync_source(
        self,
        source: str,
        limit: Optional[int] = None,
    ) -> dict[str, Any]:
        """Sync data from a specific source."""
        scraper_map = {
            "iNaturalist": INaturalistScraper,
            "GBIF": GBIFScraper,
            "FungiDB": FungiDBScraper,
            "MycoBank": MycoBankScraper,
            "GenBank": GenBankScraper,
        }
        
        if source not in scraper_map:
            return {"error": f"Unknown source: {source}"}
        
        stats = {
            "source": source,
            "records_fetched": 0,
            "records_stored": 0,
            "errors": [],
            "started_at": datetime.utcnow().isoformat(),
        }
        
        try:
            async with scraper_map[source]() as scraper:
                async for result in scraper.fetch_all(limit=limit):
                    stats["records_fetched"] += len(result.records)
                    
                    for record in result.records:
                        try:
                            if result.data_type == "observations":
                                self.db.insert_observation(record)
                            else:
                                self.db.insert_species(record)
                            stats["records_stored"] += 1
                        except Exception as e:
                            stats["errors"].append(str(e))
                    
                    if result.errors:
                        stats["errors"].extend(result.errors)
        
        except Exception as e:
            stats["errors"].append(str(e))
        
        stats["completed_at"] = datetime.utcnow().isoformat()
        
        # Log the sync
        self.db.log_scrape(
            source=source,
            data_type="sync",
            records_count=stats["records_stored"],
            errors_count=len(stats["errors"]),
            status="completed" if not stats["errors"] else "completed_with_errors",
            metadata=stats,
        )
        
        return stats
    
    async def sync_all(
        self,
        limit_per_source: int = 1000,
    ) -> dict[str, Any]:
        """Sync data from all sources."""
        results = {
            "started_at": datetime.utcnow().isoformat(),
            "sources": {},
        }
        
        sources = ["iNaturalist", "GBIF", "MycoBank", "FungiDB", "GenBank"]
        
        for source in sources:
            logger.info(f"Starting sync for {source}")
            result = await self.sync_source(source, limit=limit_per_source)
            results["sources"][source] = result
        
        results["completed_at"] = datetime.utcnow().isoformat()
        
        return results
    
    def start_continuous_sync(
        self,
        interval_hours: int = 24,
        limit_per_source: int = 1000,
    ):
        """Start continuous background sync."""
        if self._running:
            logger.warning("Continuous sync already running")
            return
        
        self._running = True
        
        async def sync_loop():
            while self._running:
                try:
                    logger.info("Starting scheduled MINDEX sync")
                    await self.sync_all(limit_per_source=limit_per_source)
                    logger.info("Completed scheduled MINDEX sync")
                except Exception as e:
                    logger.error(f"Error in MINDEX sync: {e}")
                
                # Wait for next sync
                await asyncio.sleep(interval_hours * 3600)
        
        self._sync_task = asyncio.create_task(sync_loop())
        logger.info(f"Started continuous MINDEX sync (every {interval_hours} hours)")
    
    def stop_continuous_sync(self):
        """Stop continuous background sync."""
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            self._sync_task = None
        logger.info("Stopped continuous MINDEX sync")
    
    def get_stats(self) -> dict[str, Any]:
        """Get MINDEX database statistics."""
        return self.db.get_stats()
    
    def get_species(self, name: str) -> Optional[dict[str, Any]]:
        """Get species by scientific name."""
        return self.db.get_species_by_name(name)
    
    async def get_species_with_api_fallback(
        self,
        name: str,
    ) -> Optional[dict[str, Any]]:
        """Get species, falling back to API if not in database."""
        # Check database first
        species = self.db.get_species_by_name(name)
        if species:
            return species
        
        # Try APIs
        async with INaturalistScraper() as scraper:
            result = await scraper.search_species(name, limit=1)
            if result.records:
                record = result.records[0]
                self.db.insert_species(record)
                return record
        
        async with GBIFScraper() as scraper:
            result = await scraper.search_species(name, limit=1)
            if result.records:
                record = result.records[0]
                self.db.insert_species(record)
                return record
        
        return None


# Singleton instance
_mindex_manager: Optional[MINDEXManager] = None


def get_mindex_manager() -> MINDEXManager:
    """Get or create the MINDEX manager singleton."""
    global _mindex_manager
    if _mindex_manager is None:
        _mindex_manager = MINDEXManager()
    return _mindex_manager
