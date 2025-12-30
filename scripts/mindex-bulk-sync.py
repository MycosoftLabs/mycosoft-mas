"""
MINDEX Bulk Data Sync Script

This script fetches massive amounts of fungal species data from multiple sources
and populates the MINDEX database for the ancestry explorer.

Target: 50,000+ species from:
- iNaturalist (primary - has most comprehensive data)
- GBIF (secondary - global biodiversity)
- MycoBank (taxonomic authority)
- GenBank (genomic data)

Usage:
    python scripts/mindex-bulk-sync.py --limit 50000
    python scripts/mindex-bulk-sync.py --source iNaturalist --limit 30000
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.mindex import MINDEXManager
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    GenBankScraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def sync_inaturalist(manager: MINDEXManager, limit: int = 30000):
    """Sync fungal species from iNaturalist."""
    logger.info(f"Starting iNaturalist sync (limit: {limit})")
    
    async with INaturalistScraper() as scraper:
        total = 0
        page = 1
        
        while total < limit:
            try:
                # Fetch taxa directly
                result = await scraper._request(
                    "taxa",
                    params={
                        "taxon_id": 47170,  # Fungi kingdom
                        "per_page": 200,
                        "page": page,
                        "rank": "species,subspecies,variety",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('name')}: {e}")
                
                logger.info(f"iNaturalist: Synced {total} species (page {page})")
                page += 1
                
                if total >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"iNaturalist sync error: {e}")
                break
    
    logger.info(f"iNaturalist sync complete: {total} species")
    return total


async def sync_gbif(manager: MINDEXManager, limit: int = 20000):
    """Sync fungal species from GBIF."""
    logger.info(f"Starting GBIF sync (limit: {limit})")
    
    async with GBIFScraper() as scraper:
        total = 0
        offset = 0
        
        while total < limit:
            try:
                result = await scraper._request(
                    "species/search",
                    params={
                        "kingdom": "Fungi",
                        "rank": "SPECIES",
                        "limit": 300,
                        "offset": offset,
                        "status": "ACCEPTED",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('scientificName')}: {e}")
                
                logger.info(f"GBIF: Synced {total} species")
                offset += 300
                
                if total >= limit or offset >= result.get("count", 0):
                    break
                    
            except Exception as e:
                logger.error(f"GBIF sync error: {e}")
                break
    
    logger.info(f"GBIF sync complete: {total} species")
    return total


async def sync_mycobank(manager: MINDEXManager, limit: int = 10000):
    """Sync fungal names from MycoBank."""
    logger.info(f"Starting MycoBank sync (limit: {limit})")
    
    async with MycoBankScraper() as scraper:
        total = 0
        
        async for result in scraper.fetch_all(limit=limit):
            for record in result.records:
                try:
                    manager.db.insert_species(record)
                    total += 1
                except Exception as e:
                    logger.warning(f"Failed to insert: {e}")
            
            logger.info(f"MycoBank: Synced {total} species")
    
    logger.info(f"MycoBank sync complete: {total} species")
    return total


async def main():
    parser = argparse.ArgumentParser(description="MINDEX Bulk Data Sync")
    parser.add_argument("--limit", type=int, default=50000, help="Total species limit")
    parser.add_argument("--source", type=str, help="Specific source to sync")
    parser.add_argument("--db-path", type=str, help="Database path")
    args = parser.parse_args()
    
    # Initialize manager
    db_path = Path(args.db_path) if args.db_path else None
    manager = MINDEXManager(db_path=db_path)
    
    logger.info("=" * 60)
    logger.info("MINDEX Bulk Data Sync")
    logger.info(f"Target: {args.limit} species")
    logger.info("=" * 60)
    
    # Get current stats
    stats = manager.get_stats()
    logger.info(f"Current database: {stats.get('total_species', 0)} species")
    
    total_synced = 0
    
    if args.source:
        # Sync specific source
        if args.source.lower() == "inaturalist":
            total_synced = await sync_inaturalist(manager, args.limit)
        elif args.source.lower() == "gbif":
            total_synced = await sync_gbif(manager, args.limit)
        elif args.source.lower() == "mycobank":
            total_synced = await sync_mycobank(manager, args.limit)
        else:
            logger.error(f"Unknown source: {args.source}")
            return
    else:
        # Sync all sources proportionally
        inat_limit = int(args.limit * 0.6)  # 60% from iNaturalist
        gbif_limit = int(args.limit * 0.3)  # 30% from GBIF
        mycobank_limit = int(args.limit * 0.1)  # 10% from MycoBank
        
        inat_count = await sync_inaturalist(manager, inat_limit)
        gbif_count = await sync_gbif(manager, gbif_limit)
        mycobank_count = await sync_mycobank(manager, mycobank_limit)
        
        total_synced = inat_count + gbif_count + mycobank_count
    
    # Final stats
    final_stats = manager.get_stats()
    
    logger.info("=" * 60)
    logger.info("Sync Complete!")
    logger.info(f"Total synced this run: {total_synced}")
    logger.info(f"Total in database: {final_stats.get('total_species', 0)} species")
    logger.info(f"Database size: {final_stats.get('db_size_mb', 0):.2f} MB")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

"""
MINDEX Bulk Data Sync Script

This script fetches massive amounts of fungal species data from multiple sources
and populates the MINDEX database for the ancestry explorer.

Target: 50,000+ species from:
- iNaturalist (primary - has most comprehensive data)
- GBIF (secondary - global biodiversity)
- MycoBank (taxonomic authority)
- GenBank (genomic data)

Usage:
    python scripts/mindex-bulk-sync.py --limit 50000
    python scripts/mindex-bulk-sync.py --source iNaturalist --limit 30000
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.mindex import MINDEXManager
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    GenBankScraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def sync_inaturalist(manager: MINDEXManager, limit: int = 30000):
    """Sync fungal species from iNaturalist."""
    logger.info(f"Starting iNaturalist sync (limit: {limit})")
    
    async with INaturalistScraper() as scraper:
        total = 0
        page = 1
        
        while total < limit:
            try:
                # Fetch taxa directly
                result = await scraper._request(
                    "taxa",
                    params={
                        "taxon_id": 47170,  # Fungi kingdom
                        "per_page": 200,
                        "page": page,
                        "rank": "species,subspecies,variety",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('name')}: {e}")
                
                logger.info(f"iNaturalist: Synced {total} species (page {page})")
                page += 1
                
                if total >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"iNaturalist sync error: {e}")
                break
    
    logger.info(f"iNaturalist sync complete: {total} species")
    return total


async def sync_gbif(manager: MINDEXManager, limit: int = 20000):
    """Sync fungal species from GBIF."""
    logger.info(f"Starting GBIF sync (limit: {limit})")
    
    async with GBIFScraper() as scraper:
        total = 0
        offset = 0
        
        while total < limit:
            try:
                result = await scraper._request(
                    "species/search",
                    params={
                        "kingdom": "Fungi",
                        "rank": "SPECIES",
                        "limit": 300,
                        "offset": offset,
                        "status": "ACCEPTED",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('scientificName')}: {e}")
                
                logger.info(f"GBIF: Synced {total} species")
                offset += 300
                
                if total >= limit or offset >= result.get("count", 0):
                    break
                    
            except Exception as e:
                logger.error(f"GBIF sync error: {e}")
                break
    
    logger.info(f"GBIF sync complete: {total} species")
    return total


async def sync_mycobank(manager: MINDEXManager, limit: int = 10000):
    """Sync fungal names from MycoBank."""
    logger.info(f"Starting MycoBank sync (limit: {limit})")
    
    async with MycoBankScraper() as scraper:
        total = 0
        
        async for result in scraper.fetch_all(limit=limit):
            for record in result.records:
                try:
                    manager.db.insert_species(record)
                    total += 1
                except Exception as e:
                    logger.warning(f"Failed to insert: {e}")
            
            logger.info(f"MycoBank: Synced {total} species")
    
    logger.info(f"MycoBank sync complete: {total} species")
    return total


async def main():
    parser = argparse.ArgumentParser(description="MINDEX Bulk Data Sync")
    parser.add_argument("--limit", type=int, default=50000, help="Total species limit")
    parser.add_argument("--source", type=str, help="Specific source to sync")
    parser.add_argument("--db-path", type=str, help="Database path")
    args = parser.parse_args()
    
    # Initialize manager
    db_path = Path(args.db_path) if args.db_path else None
    manager = MINDEXManager(db_path=db_path)
    
    logger.info("=" * 60)
    logger.info("MINDEX Bulk Data Sync")
    logger.info(f"Target: {args.limit} species")
    logger.info("=" * 60)
    
    # Get current stats
    stats = manager.get_stats()
    logger.info(f"Current database: {stats.get('total_species', 0)} species")
    
    total_synced = 0
    
    if args.source:
        # Sync specific source
        if args.source.lower() == "inaturalist":
            total_synced = await sync_inaturalist(manager, args.limit)
        elif args.source.lower() == "gbif":
            total_synced = await sync_gbif(manager, args.limit)
        elif args.source.lower() == "mycobank":
            total_synced = await sync_mycobank(manager, args.limit)
        else:
            logger.error(f"Unknown source: {args.source}")
            return
    else:
        # Sync all sources proportionally
        inat_limit = int(args.limit * 0.6)  # 60% from iNaturalist
        gbif_limit = int(args.limit * 0.3)  # 30% from GBIF
        mycobank_limit = int(args.limit * 0.1)  # 10% from MycoBank
        
        inat_count = await sync_inaturalist(manager, inat_limit)
        gbif_count = await sync_gbif(manager, gbif_limit)
        mycobank_count = await sync_mycobank(manager, mycobank_limit)
        
        total_synced = inat_count + gbif_count + mycobank_count
    
    # Final stats
    final_stats = manager.get_stats()
    
    logger.info("=" * 60)
    logger.info("Sync Complete!")
    logger.info(f"Total synced this run: {total_synced}")
    logger.info(f"Total in database: {final_stats.get('total_species', 0)} species")
    logger.info(f"Database size: {final_stats.get('db_size_mb', 0):.2f} MB")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


"""
MINDEX Bulk Data Sync Script

This script fetches massive amounts of fungal species data from multiple sources
and populates the MINDEX database for the ancestry explorer.

Target: 50,000+ species from:
- iNaturalist (primary - has most comprehensive data)
- GBIF (secondary - global biodiversity)
- MycoBank (taxonomic authority)
- GenBank (genomic data)

Usage:
    python scripts/mindex-bulk-sync.py --limit 50000
    python scripts/mindex-bulk-sync.py --source iNaturalist --limit 30000
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.mindex import MINDEXManager
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    GenBankScraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def sync_inaturalist(manager: MINDEXManager, limit: int = 30000):
    """Sync fungal species from iNaturalist."""
    logger.info(f"Starting iNaturalist sync (limit: {limit})")
    
    async with INaturalistScraper() as scraper:
        total = 0
        page = 1
        
        while total < limit:
            try:
                # Fetch taxa directly
                result = await scraper._request(
                    "taxa",
                    params={
                        "taxon_id": 47170,  # Fungi kingdom
                        "per_page": 200,
                        "page": page,
                        "rank": "species,subspecies,variety",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('name')}: {e}")
                
                logger.info(f"iNaturalist: Synced {total} species (page {page})")
                page += 1
                
                if total >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"iNaturalist sync error: {e}")
                break
    
    logger.info(f"iNaturalist sync complete: {total} species")
    return total


async def sync_gbif(manager: MINDEXManager, limit: int = 20000):
    """Sync fungal species from GBIF."""
    logger.info(f"Starting GBIF sync (limit: {limit})")
    
    async with GBIFScraper() as scraper:
        total = 0
        offset = 0
        
        while total < limit:
            try:
                result = await scraper._request(
                    "species/search",
                    params={
                        "kingdom": "Fungi",
                        "rank": "SPECIES",
                        "limit": 300,
                        "offset": offset,
                        "status": "ACCEPTED",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('scientificName')}: {e}")
                
                logger.info(f"GBIF: Synced {total} species")
                offset += 300
                
                if total >= limit or offset >= result.get("count", 0):
                    break
                    
            except Exception as e:
                logger.error(f"GBIF sync error: {e}")
                break
    
    logger.info(f"GBIF sync complete: {total} species")
    return total


async def sync_mycobank(manager: MINDEXManager, limit: int = 10000):
    """Sync fungal names from MycoBank."""
    logger.info(f"Starting MycoBank sync (limit: {limit})")
    
    async with MycoBankScraper() as scraper:
        total = 0
        
        async for result in scraper.fetch_all(limit=limit):
            for record in result.records:
                try:
                    manager.db.insert_species(record)
                    total += 1
                except Exception as e:
                    logger.warning(f"Failed to insert: {e}")
            
            logger.info(f"MycoBank: Synced {total} species")
    
    logger.info(f"MycoBank sync complete: {total} species")
    return total


async def main():
    parser = argparse.ArgumentParser(description="MINDEX Bulk Data Sync")
    parser.add_argument("--limit", type=int, default=50000, help="Total species limit")
    parser.add_argument("--source", type=str, help="Specific source to sync")
    parser.add_argument("--db-path", type=str, help="Database path")
    args = parser.parse_args()
    
    # Initialize manager
    db_path = Path(args.db_path) if args.db_path else None
    manager = MINDEXManager(db_path=db_path)
    
    logger.info("=" * 60)
    logger.info("MINDEX Bulk Data Sync")
    logger.info(f"Target: {args.limit} species")
    logger.info("=" * 60)
    
    # Get current stats
    stats = manager.get_stats()
    logger.info(f"Current database: {stats.get('total_species', 0)} species")
    
    total_synced = 0
    
    if args.source:
        # Sync specific source
        if args.source.lower() == "inaturalist":
            total_synced = await sync_inaturalist(manager, args.limit)
        elif args.source.lower() == "gbif":
            total_synced = await sync_gbif(manager, args.limit)
        elif args.source.lower() == "mycobank":
            total_synced = await sync_mycobank(manager, args.limit)
        else:
            logger.error(f"Unknown source: {args.source}")
            return
    else:
        # Sync all sources proportionally
        inat_limit = int(args.limit * 0.6)  # 60% from iNaturalist
        gbif_limit = int(args.limit * 0.3)  # 30% from GBIF
        mycobank_limit = int(args.limit * 0.1)  # 10% from MycoBank
        
        inat_count = await sync_inaturalist(manager, inat_limit)
        gbif_count = await sync_gbif(manager, gbif_limit)
        mycobank_count = await sync_mycobank(manager, mycobank_limit)
        
        total_synced = inat_count + gbif_count + mycobank_count
    
    # Final stats
    final_stats = manager.get_stats()
    
    logger.info("=" * 60)
    logger.info("Sync Complete!")
    logger.info(f"Total synced this run: {total_synced}")
    logger.info(f"Total in database: {final_stats.get('total_species', 0)} species")
    logger.info(f"Database size: {final_stats.get('db_size_mb', 0):.2f} MB")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

"""
MINDEX Bulk Data Sync Script

This script fetches massive amounts of fungal species data from multiple sources
and populates the MINDEX database for the ancestry explorer.

Target: 50,000+ species from:
- iNaturalist (primary - has most comprehensive data)
- GBIF (secondary - global biodiversity)
- MycoBank (taxonomic authority)
- GenBank (genomic data)

Usage:
    python scripts/mindex-bulk-sync.py --limit 50000
    python scripts/mindex-bulk-sync.py --source iNaturalist --limit 30000
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.mindex import MINDEXManager
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    GenBankScraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def sync_inaturalist(manager: MINDEXManager, limit: int = 30000):
    """Sync fungal species from iNaturalist."""
    logger.info(f"Starting iNaturalist sync (limit: {limit})")
    
    async with INaturalistScraper() as scraper:
        total = 0
        page = 1
        
        while total < limit:
            try:
                # Fetch taxa directly
                result = await scraper._request(
                    "taxa",
                    params={
                        "taxon_id": 47170,  # Fungi kingdom
                        "per_page": 200,
                        "page": page,
                        "rank": "species,subspecies,variety",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('name')}: {e}")
                
                logger.info(f"iNaturalist: Synced {total} species (page {page})")
                page += 1
                
                if total >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"iNaturalist sync error: {e}")
                break
    
    logger.info(f"iNaturalist sync complete: {total} species")
    return total


async def sync_gbif(manager: MINDEXManager, limit: int = 20000):
    """Sync fungal species from GBIF."""
    logger.info(f"Starting GBIF sync (limit: {limit})")
    
    async with GBIFScraper() as scraper:
        total = 0
        offset = 0
        
        while total < limit:
            try:
                result = await scraper._request(
                    "species/search",
                    params={
                        "kingdom": "Fungi",
                        "rank": "SPECIES",
                        "limit": 300,
                        "offset": offset,
                        "status": "ACCEPTED",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('scientificName')}: {e}")
                
                logger.info(f"GBIF: Synced {total} species")
                offset += 300
                
                if total >= limit or offset >= result.get("count", 0):
                    break
                    
            except Exception as e:
                logger.error(f"GBIF sync error: {e}")
                break
    
    logger.info(f"GBIF sync complete: {total} species")
    return total


async def sync_mycobank(manager: MINDEXManager, limit: int = 10000):
    """Sync fungal names from MycoBank."""
    logger.info(f"Starting MycoBank sync (limit: {limit})")
    
    async with MycoBankScraper() as scraper:
        total = 0
        
        async for result in scraper.fetch_all(limit=limit):
            for record in result.records:
                try:
                    manager.db.insert_species(record)
                    total += 1
                except Exception as e:
                    logger.warning(f"Failed to insert: {e}")
            
            logger.info(f"MycoBank: Synced {total} species")
    
    logger.info(f"MycoBank sync complete: {total} species")
    return total


async def main():
    parser = argparse.ArgumentParser(description="MINDEX Bulk Data Sync")
    parser.add_argument("--limit", type=int, default=50000, help="Total species limit")
    parser.add_argument("--source", type=str, help="Specific source to sync")
    parser.add_argument("--db-path", type=str, help="Database path")
    args = parser.parse_args()
    
    # Initialize manager
    db_path = Path(args.db_path) if args.db_path else None
    manager = MINDEXManager(db_path=db_path)
    
    logger.info("=" * 60)
    logger.info("MINDEX Bulk Data Sync")
    logger.info(f"Target: {args.limit} species")
    logger.info("=" * 60)
    
    # Get current stats
    stats = manager.get_stats()
    logger.info(f"Current database: {stats.get('total_species', 0)} species")
    
    total_synced = 0
    
    if args.source:
        # Sync specific source
        if args.source.lower() == "inaturalist":
            total_synced = await sync_inaturalist(manager, args.limit)
        elif args.source.lower() == "gbif":
            total_synced = await sync_gbif(manager, args.limit)
        elif args.source.lower() == "mycobank":
            total_synced = await sync_mycobank(manager, args.limit)
        else:
            logger.error(f"Unknown source: {args.source}")
            return
    else:
        # Sync all sources proportionally
        inat_limit = int(args.limit * 0.6)  # 60% from iNaturalist
        gbif_limit = int(args.limit * 0.3)  # 30% from GBIF
        mycobank_limit = int(args.limit * 0.1)  # 10% from MycoBank
        
        inat_count = await sync_inaturalist(manager, inat_limit)
        gbif_count = await sync_gbif(manager, gbif_limit)
        mycobank_count = await sync_mycobank(manager, mycobank_limit)
        
        total_synced = inat_count + gbif_count + mycobank_count
    
    # Final stats
    final_stats = manager.get_stats()
    
    logger.info("=" * 60)
    logger.info("Sync Complete!")
    logger.info(f"Total synced this run: {total_synced}")
    logger.info(f"Total in database: {final_stats.get('total_species', 0)} species")
    logger.info(f"Database size: {final_stats.get('db_size_mb', 0):.2f} MB")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())





"""
MINDEX Bulk Data Sync Script

This script fetches massive amounts of fungal species data from multiple sources
and populates the MINDEX database for the ancestry explorer.

Target: 50,000+ species from:
- iNaturalist (primary - has most comprehensive data)
- GBIF (secondary - global biodiversity)
- MycoBank (taxonomic authority)
- GenBank (genomic data)

Usage:
    python scripts/mindex-bulk-sync.py --limit 50000
    python scripts/mindex-bulk-sync.py --source iNaturalist --limit 30000
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.mindex import MINDEXManager
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    GenBankScraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def sync_inaturalist(manager: MINDEXManager, limit: int = 30000):
    """Sync fungal species from iNaturalist."""
    logger.info(f"Starting iNaturalist sync (limit: {limit})")
    
    async with INaturalistScraper() as scraper:
        total = 0
        page = 1
        
        while total < limit:
            try:
                # Fetch taxa directly
                result = await scraper._request(
                    "taxa",
                    params={
                        "taxon_id": 47170,  # Fungi kingdom
                        "per_page": 200,
                        "page": page,
                        "rank": "species,subspecies,variety",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('name')}: {e}")
                
                logger.info(f"iNaturalist: Synced {total} species (page {page})")
                page += 1
                
                if total >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"iNaturalist sync error: {e}")
                break
    
    logger.info(f"iNaturalist sync complete: {total} species")
    return total


async def sync_gbif(manager: MINDEXManager, limit: int = 20000):
    """Sync fungal species from GBIF."""
    logger.info(f"Starting GBIF sync (limit: {limit})")
    
    async with GBIFScraper() as scraper:
        total = 0
        offset = 0
        
        while total < limit:
            try:
                result = await scraper._request(
                    "species/search",
                    params={
                        "kingdom": "Fungi",
                        "rank": "SPECIES",
                        "limit": 300,
                        "offset": offset,
                        "status": "ACCEPTED",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('scientificName')}: {e}")
                
                logger.info(f"GBIF: Synced {total} species")
                offset += 300
                
                if total >= limit or offset >= result.get("count", 0):
                    break
                    
            except Exception as e:
                logger.error(f"GBIF sync error: {e}")
                break
    
    logger.info(f"GBIF sync complete: {total} species")
    return total


async def sync_mycobank(manager: MINDEXManager, limit: int = 10000):
    """Sync fungal names from MycoBank."""
    logger.info(f"Starting MycoBank sync (limit: {limit})")
    
    async with MycoBankScraper() as scraper:
        total = 0
        
        async for result in scraper.fetch_all(limit=limit):
            for record in result.records:
                try:
                    manager.db.insert_species(record)
                    total += 1
                except Exception as e:
                    logger.warning(f"Failed to insert: {e}")
            
            logger.info(f"MycoBank: Synced {total} species")
    
    logger.info(f"MycoBank sync complete: {total} species")
    return total


async def main():
    parser = argparse.ArgumentParser(description="MINDEX Bulk Data Sync")
    parser.add_argument("--limit", type=int, default=50000, help="Total species limit")
    parser.add_argument("--source", type=str, help="Specific source to sync")
    parser.add_argument("--db-path", type=str, help="Database path")
    args = parser.parse_args()
    
    # Initialize manager
    db_path = Path(args.db_path) if args.db_path else None
    manager = MINDEXManager(db_path=db_path)
    
    logger.info("=" * 60)
    logger.info("MINDEX Bulk Data Sync")
    logger.info(f"Target: {args.limit} species")
    logger.info("=" * 60)
    
    # Get current stats
    stats = manager.get_stats()
    logger.info(f"Current database: {stats.get('total_species', 0)} species")
    
    total_synced = 0
    
    if args.source:
        # Sync specific source
        if args.source.lower() == "inaturalist":
            total_synced = await sync_inaturalist(manager, args.limit)
        elif args.source.lower() == "gbif":
            total_synced = await sync_gbif(manager, args.limit)
        elif args.source.lower() == "mycobank":
            total_synced = await sync_mycobank(manager, args.limit)
        else:
            logger.error(f"Unknown source: {args.source}")
            return
    else:
        # Sync all sources proportionally
        inat_limit = int(args.limit * 0.6)  # 60% from iNaturalist
        gbif_limit = int(args.limit * 0.3)  # 30% from GBIF
        mycobank_limit = int(args.limit * 0.1)  # 10% from MycoBank
        
        inat_count = await sync_inaturalist(manager, inat_limit)
        gbif_count = await sync_gbif(manager, gbif_limit)
        mycobank_count = await sync_mycobank(manager, mycobank_limit)
        
        total_synced = inat_count + gbif_count + mycobank_count
    
    # Final stats
    final_stats = manager.get_stats()
    
    logger.info("=" * 60)
    logger.info("Sync Complete!")
    logger.info(f"Total synced this run: {total_synced}")
    logger.info(f"Total in database: {final_stats.get('total_species', 0)} species")
    logger.info(f"Database size: {final_stats.get('db_size_mb', 0):.2f} MB")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

"""
MINDEX Bulk Data Sync Script

This script fetches massive amounts of fungal species data from multiple sources
and populates the MINDEX database for the ancestry explorer.

Target: 50,000+ species from:
- iNaturalist (primary - has most comprehensive data)
- GBIF (secondary - global biodiversity)
- MycoBank (taxonomic authority)
- GenBank (genomic data)

Usage:
    python scripts/mindex-bulk-sync.py --limit 50000
    python scripts/mindex-bulk-sync.py --source iNaturalist --limit 30000
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.mindex import MINDEXManager
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    GenBankScraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def sync_inaturalist(manager: MINDEXManager, limit: int = 30000):
    """Sync fungal species from iNaturalist."""
    logger.info(f"Starting iNaturalist sync (limit: {limit})")
    
    async with INaturalistScraper() as scraper:
        total = 0
        page = 1
        
        while total < limit:
            try:
                # Fetch taxa directly
                result = await scraper._request(
                    "taxa",
                    params={
                        "taxon_id": 47170,  # Fungi kingdom
                        "per_page": 200,
                        "page": page,
                        "rank": "species,subspecies,variety",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('name')}: {e}")
                
                logger.info(f"iNaturalist: Synced {total} species (page {page})")
                page += 1
                
                if total >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"iNaturalist sync error: {e}")
                break
    
    logger.info(f"iNaturalist sync complete: {total} species")
    return total


async def sync_gbif(manager: MINDEXManager, limit: int = 20000):
    """Sync fungal species from GBIF."""
    logger.info(f"Starting GBIF sync (limit: {limit})")
    
    async with GBIFScraper() as scraper:
        total = 0
        offset = 0
        
        while total < limit:
            try:
                result = await scraper._request(
                    "species/search",
                    params={
                        "kingdom": "Fungi",
                        "rank": "SPECIES",
                        "limit": 300,
                        "offset": offset,
                        "status": "ACCEPTED",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('scientificName')}: {e}")
                
                logger.info(f"GBIF: Synced {total} species")
                offset += 300
                
                if total >= limit or offset >= result.get("count", 0):
                    break
                    
            except Exception as e:
                logger.error(f"GBIF sync error: {e}")
                break
    
    logger.info(f"GBIF sync complete: {total} species")
    return total


async def sync_mycobank(manager: MINDEXManager, limit: int = 10000):
    """Sync fungal names from MycoBank."""
    logger.info(f"Starting MycoBank sync (limit: {limit})")
    
    async with MycoBankScraper() as scraper:
        total = 0
        
        async for result in scraper.fetch_all(limit=limit):
            for record in result.records:
                try:
                    manager.db.insert_species(record)
                    total += 1
                except Exception as e:
                    logger.warning(f"Failed to insert: {e}")
            
            logger.info(f"MycoBank: Synced {total} species")
    
    logger.info(f"MycoBank sync complete: {total} species")
    return total


async def main():
    parser = argparse.ArgumentParser(description="MINDEX Bulk Data Sync")
    parser.add_argument("--limit", type=int, default=50000, help="Total species limit")
    parser.add_argument("--source", type=str, help="Specific source to sync")
    parser.add_argument("--db-path", type=str, help="Database path")
    args = parser.parse_args()
    
    # Initialize manager
    db_path = Path(args.db_path) if args.db_path else None
    manager = MINDEXManager(db_path=db_path)
    
    logger.info("=" * 60)
    logger.info("MINDEX Bulk Data Sync")
    logger.info(f"Target: {args.limit} species")
    logger.info("=" * 60)
    
    # Get current stats
    stats = manager.get_stats()
    logger.info(f"Current database: {stats.get('total_species', 0)} species")
    
    total_synced = 0
    
    if args.source:
        # Sync specific source
        if args.source.lower() == "inaturalist":
            total_synced = await sync_inaturalist(manager, args.limit)
        elif args.source.lower() == "gbif":
            total_synced = await sync_gbif(manager, args.limit)
        elif args.source.lower() == "mycobank":
            total_synced = await sync_mycobank(manager, args.limit)
        else:
            logger.error(f"Unknown source: {args.source}")
            return
    else:
        # Sync all sources proportionally
        inat_limit = int(args.limit * 0.6)  # 60% from iNaturalist
        gbif_limit = int(args.limit * 0.3)  # 30% from GBIF
        mycobank_limit = int(args.limit * 0.1)  # 10% from MycoBank
        
        inat_count = await sync_inaturalist(manager, inat_limit)
        gbif_count = await sync_gbif(manager, gbif_limit)
        mycobank_count = await sync_mycobank(manager, mycobank_limit)
        
        total_synced = inat_count + gbif_count + mycobank_count
    
    # Final stats
    final_stats = manager.get_stats()
    
    logger.info("=" * 60)
    logger.info("Sync Complete!")
    logger.info(f"Total synced this run: {total_synced}")
    logger.info(f"Total in database: {final_stats.get('total_species', 0)} species")
    logger.info(f"Database size: {final_stats.get('db_size_mb', 0):.2f} MB")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


"""
MINDEX Bulk Data Sync Script

This script fetches massive amounts of fungal species data from multiple sources
and populates the MINDEX database for the ancestry explorer.

Target: 50,000+ species from:
- iNaturalist (primary - has most comprehensive data)
- GBIF (secondary - global biodiversity)
- MycoBank (taxonomic authority)
- GenBank (genomic data)

Usage:
    python scripts/mindex-bulk-sync.py --limit 50000
    python scripts/mindex-bulk-sync.py --source iNaturalist --limit 30000
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.mindex import MINDEXManager
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    GenBankScraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def sync_inaturalist(manager: MINDEXManager, limit: int = 30000):
    """Sync fungal species from iNaturalist."""
    logger.info(f"Starting iNaturalist sync (limit: {limit})")
    
    async with INaturalistScraper() as scraper:
        total = 0
        page = 1
        
        while total < limit:
            try:
                # Fetch taxa directly
                result = await scraper._request(
                    "taxa",
                    params={
                        "taxon_id": 47170,  # Fungi kingdom
                        "per_page": 200,
                        "page": page,
                        "rank": "species,subspecies,variety",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('name')}: {e}")
                
                logger.info(f"iNaturalist: Synced {total} species (page {page})")
                page += 1
                
                if total >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"iNaturalist sync error: {e}")
                break
    
    logger.info(f"iNaturalist sync complete: {total} species")
    return total


async def sync_gbif(manager: MINDEXManager, limit: int = 20000):
    """Sync fungal species from GBIF."""
    logger.info(f"Starting GBIF sync (limit: {limit})")
    
    async with GBIFScraper() as scraper:
        total = 0
        offset = 0
        
        while total < limit:
            try:
                result = await scraper._request(
                    "species/search",
                    params={
                        "kingdom": "Fungi",
                        "rank": "SPECIES",
                        "limit": 300,
                        "offset": offset,
                        "status": "ACCEPTED",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('scientificName')}: {e}")
                
                logger.info(f"GBIF: Synced {total} species")
                offset += 300
                
                if total >= limit or offset >= result.get("count", 0):
                    break
                    
            except Exception as e:
                logger.error(f"GBIF sync error: {e}")
                break
    
    logger.info(f"GBIF sync complete: {total} species")
    return total


async def sync_mycobank(manager: MINDEXManager, limit: int = 10000):
    """Sync fungal names from MycoBank."""
    logger.info(f"Starting MycoBank sync (limit: {limit})")
    
    async with MycoBankScraper() as scraper:
        total = 0
        
        async for result in scraper.fetch_all(limit=limit):
            for record in result.records:
                try:
                    manager.db.insert_species(record)
                    total += 1
                except Exception as e:
                    logger.warning(f"Failed to insert: {e}")
            
            logger.info(f"MycoBank: Synced {total} species")
    
    logger.info(f"MycoBank sync complete: {total} species")
    return total


async def main():
    parser = argparse.ArgumentParser(description="MINDEX Bulk Data Sync")
    parser.add_argument("--limit", type=int, default=50000, help="Total species limit")
    parser.add_argument("--source", type=str, help="Specific source to sync")
    parser.add_argument("--db-path", type=str, help="Database path")
    args = parser.parse_args()
    
    # Initialize manager
    db_path = Path(args.db_path) if args.db_path else None
    manager = MINDEXManager(db_path=db_path)
    
    logger.info("=" * 60)
    logger.info("MINDEX Bulk Data Sync")
    logger.info(f"Target: {args.limit} species")
    logger.info("=" * 60)
    
    # Get current stats
    stats = manager.get_stats()
    logger.info(f"Current database: {stats.get('total_species', 0)} species")
    
    total_synced = 0
    
    if args.source:
        # Sync specific source
        if args.source.lower() == "inaturalist":
            total_synced = await sync_inaturalist(manager, args.limit)
        elif args.source.lower() == "gbif":
            total_synced = await sync_gbif(manager, args.limit)
        elif args.source.lower() == "mycobank":
            total_synced = await sync_mycobank(manager, args.limit)
        else:
            logger.error(f"Unknown source: {args.source}")
            return
    else:
        # Sync all sources proportionally
        inat_limit = int(args.limit * 0.6)  # 60% from iNaturalist
        gbif_limit = int(args.limit * 0.3)  # 30% from GBIF
        mycobank_limit = int(args.limit * 0.1)  # 10% from MycoBank
        
        inat_count = await sync_inaturalist(manager, inat_limit)
        gbif_count = await sync_gbif(manager, gbif_limit)
        mycobank_count = await sync_mycobank(manager, mycobank_limit)
        
        total_synced = inat_count + gbif_count + mycobank_count
    
    # Final stats
    final_stats = manager.get_stats()
    
    logger.info("=" * 60)
    logger.info("Sync Complete!")
    logger.info(f"Total synced this run: {total_synced}")
    logger.info(f"Total in database: {final_stats.get('total_species', 0)} species")
    logger.info(f"Database size: {final_stats.get('db_size_mb', 0):.2f} MB")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

"""
MINDEX Bulk Data Sync Script

This script fetches massive amounts of fungal species data from multiple sources
and populates the MINDEX database for the ancestry explorer.

Target: 50,000+ species from:
- iNaturalist (primary - has most comprehensive data)
- GBIF (secondary - global biodiversity)
- MycoBank (taxonomic authority)
- GenBank (genomic data)

Usage:
    python scripts/mindex-bulk-sync.py --limit 50000
    python scripts/mindex-bulk-sync.py --source iNaturalist --limit 30000
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.mindex import MINDEXManager
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    GenBankScraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def sync_inaturalist(manager: MINDEXManager, limit: int = 30000):
    """Sync fungal species from iNaturalist."""
    logger.info(f"Starting iNaturalist sync (limit: {limit})")
    
    async with INaturalistScraper() as scraper:
        total = 0
        page = 1
        
        while total < limit:
            try:
                # Fetch taxa directly
                result = await scraper._request(
                    "taxa",
                    params={
                        "taxon_id": 47170,  # Fungi kingdom
                        "per_page": 200,
                        "page": page,
                        "rank": "species,subspecies,variety",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('name')}: {e}")
                
                logger.info(f"iNaturalist: Synced {total} species (page {page})")
                page += 1
                
                if total >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"iNaturalist sync error: {e}")
                break
    
    logger.info(f"iNaturalist sync complete: {total} species")
    return total


async def sync_gbif(manager: MINDEXManager, limit: int = 20000):
    """Sync fungal species from GBIF."""
    logger.info(f"Starting GBIF sync (limit: {limit})")
    
    async with GBIFScraper() as scraper:
        total = 0
        offset = 0
        
        while total < limit:
            try:
                result = await scraper._request(
                    "species/search",
                    params={
                        "kingdom": "Fungi",
                        "rank": "SPECIES",
                        "limit": 300,
                        "offset": offset,
                        "status": "ACCEPTED",
                    }
                )
                
                if not result or "results" not in result:
                    break
                
                taxa = result["results"]
                if not taxa:
                    break
                
                for taxon in taxa:
                    try:
                        normalized = scraper.normalize_record(taxon)
                        manager.db.insert_species(normalized)
                        total += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert {taxon.get('scientificName')}: {e}")
                
                logger.info(f"GBIF: Synced {total} species")
                offset += 300
                
                if total >= limit or offset >= result.get("count", 0):
                    break
                    
            except Exception as e:
                logger.error(f"GBIF sync error: {e}")
                break
    
    logger.info(f"GBIF sync complete: {total} species")
    return total


async def sync_mycobank(manager: MINDEXManager, limit: int = 10000):
    """Sync fungal names from MycoBank."""
    logger.info(f"Starting MycoBank sync (limit: {limit})")
    
    async with MycoBankScraper() as scraper:
        total = 0
        
        async for result in scraper.fetch_all(limit=limit):
            for record in result.records:
                try:
                    manager.db.insert_species(record)
                    total += 1
                except Exception as e:
                    logger.warning(f"Failed to insert: {e}")
            
            logger.info(f"MycoBank: Synced {total} species")
    
    logger.info(f"MycoBank sync complete: {total} species")
    return total


async def main():
    parser = argparse.ArgumentParser(description="MINDEX Bulk Data Sync")
    parser.add_argument("--limit", type=int, default=50000, help="Total species limit")
    parser.add_argument("--source", type=str, help="Specific source to sync")
    parser.add_argument("--db-path", type=str, help="Database path")
    args = parser.parse_args()
    
    # Initialize manager
    db_path = Path(args.db_path) if args.db_path else None
    manager = MINDEXManager(db_path=db_path)
    
    logger.info("=" * 60)
    logger.info("MINDEX Bulk Data Sync")
    logger.info(f"Target: {args.limit} species")
    logger.info("=" * 60)
    
    # Get current stats
    stats = manager.get_stats()
    logger.info(f"Current database: {stats.get('total_species', 0)} species")
    
    total_synced = 0
    
    if args.source:
        # Sync specific source
        if args.source.lower() == "inaturalist":
            total_synced = await sync_inaturalist(manager, args.limit)
        elif args.source.lower() == "gbif":
            total_synced = await sync_gbif(manager, args.limit)
        elif args.source.lower() == "mycobank":
            total_synced = await sync_mycobank(manager, args.limit)
        else:
            logger.error(f"Unknown source: {args.source}")
            return
    else:
        # Sync all sources proportionally
        inat_limit = int(args.limit * 0.6)  # 60% from iNaturalist
        gbif_limit = int(args.limit * 0.3)  # 30% from GBIF
        mycobank_limit = int(args.limit * 0.1)  # 10% from MycoBank
        
        inat_count = await sync_inaturalist(manager, inat_limit)
        gbif_count = await sync_gbif(manager, gbif_limit)
        mycobank_count = await sync_mycobank(manager, mycobank_limit)
        
        total_synced = inat_count + gbif_count + mycobank_count
    
    # Final stats
    final_stats = manager.get_stats()
    
    logger.info("=" * 60)
    logger.info("Sync Complete!")
    logger.info(f"Total synced this run: {total_synced}")
    logger.info(f"Total in database: {final_stats.get('total_species', 0)} species")
    logger.info(f"Database size: {final_stats.get('db_size_mb', 0):.2f} MB")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())





