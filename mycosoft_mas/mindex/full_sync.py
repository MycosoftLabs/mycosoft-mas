"""
MINDEX Full ETL Sync Runner - Feb 5, 2026

Master script to run full sync from all data sources into MINDEX.
This populates MINDEX with 575,000+ fungal species and associated data.

Usage:
    python -m mycosoft_mas.mindex.full_sync --sources all
    python -m mycosoft_mas.mindex.full_sync --sources inaturalist,gbif
    python -m mycosoft_mas.mindex.full_sync --sources inaturalist --limit 10000
    
Environment Variables Required:
    - MINDEX_DATABASE_URL: PostgreSQL connection string
    - NCBI_API_KEY: For GenBank/PubMed (optional but recommended)
    - GBIF_USERNAME, GBIF_PASSWORD: For GBIF authentication
    - INATURALIST_API_TOKEN: For iNaturalist rate limits
    
Estimated Times (with good network):
    - iNaturalist: ~24 hours for 500,000 species
    - GBIF: ~12 hours for 300,000 species
    - MycoBank: ~6 hours for 150,000 species
    - Index Fungorum: ~4 hours for 100,000 species
    - GenBank: ~8 hours for 200,000 sequences
    - PubMed: ~4 hours for 50,000 papers
    - PubChem/ChEMBL: ~2 hours for 10,000 compounds
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"mindex_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
logger = logging.getLogger("mindex_sync")

# Import scrapers
try:
    from mycosoft_mas.mindex.scrapers.inaturalist_scraper import INaturalistScraper
    from mycosoft_mas.mindex.scrapers.gbif_scraper import GBIFScraper
    from mycosoft_mas.mindex.scrapers.mycobank_scraper import MycoBankScraper
    from mycosoft_mas.mindex.scrapers.index_fungorum_scraper import IndexFungorumScraper
    from mycosoft_mas.mindex.scrapers.genbank_scraper import GenBankScraper
    from mycosoft_mas.mindex.scrapers.pubmed_scraper import PubMedScraper
    from mycosoft_mas.mindex.scrapers.chemistry_scraper import ChemistryScraper
    from mycosoft_mas.mindex.blob_manager import BlobManager
except ImportError as e:
    logger.error(f"Failed to import scrapers: {e}")
    sys.exit(1)


# Priority genera for targeted sync
PRIORITY_GENERA = [
    # Edible/Culinary
    "Agaricus", "Boletus", "Cantharellus", "Pleurotus", "Morchella", 
    "Tuber", "Lentinula", "Grifola", "Laetiporus", "Hericium",
    # Medicinal
    "Ganoderma", "Trametes", "Cordyceps", "Inonotus", "Phellinus",
    "Fomes", "Fomitopsis", "Antrodia", "Wolfiporia",
    # Psychoactive
    "Psilocybe", "Panaeolus", "Gymnopilus", "Pluteus", "Inocybe",
    # Toxic
    "Amanita", "Cortinarius", "Galerina", "Lepiota", "Gyromitra",
    "Clitocybe", "Conocybe", "Russula",
    # Bioluminescent
    "Armillaria", "Mycena", "Omphalotus", "Panellus",
    # Mycorrhizal
    "Lactarius", "Suillus", "Tricholoma", "Hydnum", "Craterellus",
    # Pathogens
    "Fusarium", "Aspergillus", "Candida", "Cryptococcus",
    # Important research genera
    "Schizophyllum", "Coprinus", "Coprinopsis", "Neurospora",
]


async def sync_inaturalist(db, blob_manager: BlobManager, limit: Optional[int] = None) -> Dict:
    """Sync species and images from iNaturalist."""
    logger.info("Starting iNaturalist sync...")
    
    scraper = INaturalistScraper(
        db=db,
        api_token=os.environ.get("INATURALIST_API_TOKEN"),
    )
    
    stats = {"species": 0, "images": 0, "errors": 0}
    
    try:
        # Sync fungi kingdom
        result = await scraper.sync(limit=limit or 500000)
        stats["species"] = result.get("species_synced", 0)
        stats["images"] = result.get("images_synced", 0)
        
        logger.info(f"iNaturalist sync complete: {stats}")
    except Exception as e:
        logger.error(f"iNaturalist sync error: {e}")
        stats["errors"] += 1
    
    return stats


async def sync_gbif(db, blob_manager: BlobManager, limit: Optional[int] = None) -> Dict:
    """Sync species and occurrences from GBIF."""
    logger.info("Starting GBIF sync...")
    
    scraper = GBIFScraper(
        db=db,
        username=os.environ.get("GBIF_USERNAME"),
        password=os.environ.get("GBIF_PASSWORD"),
    )
    
    stats = {"species": 0, "occurrences": 0, "images": 0, "errors": 0}
    
    try:
        result = await scraper.sync(limit=limit or 300000)
        stats["species"] = result.get("species_synced", 0)
        stats["occurrences"] = result.get("occurrences_synced", 0)
        stats["images"] = result.get("images_synced", 0)
        
        logger.info(f"GBIF sync complete: {stats}")
    except Exception as e:
        logger.error(f"GBIF sync error: {e}")
        stats["errors"] += 1
    
    return stats


async def sync_mycobank(db, limit: Optional[int] = None) -> Dict:
    """Sync nomenclature from MycoBank."""
    logger.info("Starting MycoBank sync...")
    
    scraper = MycoBankScraper(db=db)
    
    stats = {"species": 0, "errors": 0}
    
    try:
        result = await scraper.sync(genera=PRIORITY_GENERA, limit=limit or 150000)
        stats["species"] = result.get("species_found", 0)
        
        logger.info(f"MycoBank sync complete: {stats}")
    except Exception as e:
        logger.error(f"MycoBank sync error: {e}")
        stats["errors"] += 1
    
    return stats


async def sync_index_fungorum(db, limit: Optional[int] = None) -> Dict:
    """Sync nomenclature from Index Fungorum."""
    logger.info("Starting Index Fungorum sync...")
    
    scraper = IndexFungorumScraper(db=db)
    
    stats = {"species": 0, "errors": 0}
    
    try:
        result = await scraper.sync(genera=PRIORITY_GENERA, limit=limit or 100000)
        stats["species"] = result.get("species_saved", 0)
        
        logger.info(f"Index Fungorum sync complete: {stats}")
    except Exception as e:
        logger.error(f"Index Fungorum sync error: {e}")
        stats["errors"] += 1
    
    return stats


async def sync_genbank(db, blob_manager: BlobManager, limit: Optional[int] = None) -> Dict:
    """Sync DNA sequences from GenBank."""
    logger.info("Starting GenBank sync...")
    
    scraper = GenBankScraper(
        db=db,
        api_key=os.environ.get("NCBI_API_KEY"),
        blob_manager=blob_manager,
    )
    
    stats = {"sequences": 0, "errors": 0}
    
    try:
        result = await scraper.sync(
            gene_regions=["ITS", "LSU", "SSU", "RPB2", "TEF1"],
            limit_per_gene=limit or 50000,
        )
        stats["sequences"] = result.get("total_fetched", 0)
        
        logger.info(f"GenBank sync complete: {stats}")
    except Exception as e:
        logger.error(f"GenBank sync error: {e}")
        stats["errors"] += 1
    
    return stats


async def sync_pubmed(db, blob_manager: BlobManager, limit: Optional[int] = None) -> Dict:
    """Sync research papers from PubMed."""
    logger.info("Starting PubMed sync...")
    
    scraper = PubMedScraper(
        db=db,
        api_key=os.environ.get("NCBI_API_KEY"),
        blob_manager=blob_manager,
    )
    
    stats = {"papers": 0, "errors": 0}
    
    try:
        # Get priority species for paper search
        species_list = [
            f"{g} muscaria" if g == "Amanita" else
            f"{g} cubensis" if g == "Psilocybe" else
            f"{g} lucidum" if g == "Ganoderma" else
            f"{g} erinaceus" if g == "Hericium" else
            f"{g} versicolor" if g == "Trametes" else
            f"{g} militaris" if g == "Cordyceps" else
            g
            for g in PRIORITY_GENERA[:20]
        ]
        
        result = await scraper.sync(
            species_list=species_list,
            topics=["medicinal", "taxonomy", "metabolites", "genomics", "ecology"],
            papers_per_species=limit or 100,
            papers_per_topic=limit or 500,
            years=10,
        )
        stats["papers"] = result.get("total_fetched", 0)
        
        logger.info(f"PubMed sync complete: {stats}")
    except Exception as e:
        logger.error(f"PubMed sync error: {e}")
        stats["errors"] += 1
    
    return stats


async def sync_chemistry(db, blob_manager: BlobManager, limit: Optional[int] = None) -> Dict:
    """Sync compounds from PubChem/ChEMBL."""
    logger.info("Starting chemistry sync...")
    
    scraper = ChemistryScraper(db=db, blob_manager=blob_manager)
    
    stats = {"compounds": 0, "errors": 0}
    
    try:
        species_list = [
            "Amanita muscaria", "Psilocybe cubensis", "Ganoderma lucidum",
            "Hericium erinaceus", "Cordyceps militaris", "Trametes versicolor",
            "Inonotus obliquus", "Grifola frondosa", "Lentinula edodes",
        ]
        
        result = await scraper.sync(
            species_list=species_list,
            limit_per_source=limit or 50,
        )
        stats["compounds"] = result.get("total_fetched", 0)
        
        logger.info(f"Chemistry sync complete: {stats}")
    except Exception as e:
        logger.error(f"Chemistry sync error: {e}")
        stats["errors"] += 1
    
    return stats


async def run_full_sync(
    sources: List[str],
    limit: Optional[int] = None,
    db_url: Optional[str] = None,
) -> Dict:
    """Run full ETL sync for specified sources."""
    
    # Initialize database
    db_url = db_url or os.environ.get("MINDEX_DATABASE_URL")
    if not db_url:
        logger.error("MINDEX_DATABASE_URL not set")
        return {"error": "No database URL"}
    
    # For now, use None as placeholder - in production, initialize actual DB connection
    db = None  # TODO: Initialize async database connection
    
    # Initialize blob manager
    blob_manager = BlobManager()
    
    all_stats = {
        "start_time": datetime.now().isoformat(),
        "sources": {},
        "total_species": 0,
        "total_sequences": 0,
        "total_papers": 0,
        "total_compounds": 0,
        "total_images": 0,
    }
    
    source_funcs = {
        "inaturalist": lambda: sync_inaturalist(db, blob_manager, limit),
        "gbif": lambda: sync_gbif(db, blob_manager, limit),
        "mycobank": lambda: sync_mycobank(db, limit),
        "index_fungorum": lambda: sync_index_fungorum(db, limit),
        "genbank": lambda: sync_genbank(db, blob_manager, limit),
        "pubmed": lambda: sync_pubmed(db, blob_manager, limit),
        "chemistry": lambda: sync_chemistry(db, blob_manager, limit),
    }
    
    if "all" in sources:
        sources = list(source_funcs.keys())
    
    for source in sources:
        if source not in source_funcs:
            logger.warning(f"Unknown source: {source}")
            continue
        
        try:
            stats = await source_funcs[source]()
            all_stats["sources"][source] = stats
            
            # Aggregate totals
            all_stats["total_species"] += stats.get("species", 0)
            all_stats["total_sequences"] += stats.get("sequences", 0)
            all_stats["total_papers"] += stats.get("papers", 0)
            all_stats["total_compounds"] += stats.get("compounds", 0)
            all_stats["total_images"] += stats.get("images", 0)
            
        except Exception as e:
            logger.error(f"Error syncing {source}: {e}")
            all_stats["sources"][source] = {"error": str(e)}
    
    all_stats["end_time"] = datetime.now().isoformat()
    
    logger.info("=" * 60)
    logger.info("FULL SYNC COMPLETE")
    logger.info(f"Total Species: {all_stats['total_species']}")
    logger.info(f"Total Sequences: {all_stats['total_sequences']}")
    logger.info(f"Total Papers: {all_stats['total_papers']}")
    logger.info(f"Total Compounds: {all_stats['total_compounds']}")
    logger.info(f"Total Images: {all_stats['total_images']}")
    logger.info("=" * 60)
    
    return all_stats


def main():
    parser = argparse.ArgumentParser(description="MINDEX Full ETL Sync")
    parser.add_argument(
        "--sources",
        type=str,
        default="all",
        help="Comma-separated list of sources (inaturalist,gbif,mycobank,index_fungorum,genbank,pubmed,chemistry) or 'all'",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit records per source (for testing)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL (defaults to MINDEX_DATABASE_URL env var)",
    )
    
    args = parser.parse_args()
    
    sources = [s.strip() for s in args.sources.split(",")]
    
    logger.info(f"Starting MINDEX sync for sources: {sources}")
    if args.limit:
        logger.info(f"Limit per source: {args.limit}")
    
    result = asyncio.run(run_full_sync(sources, args.limit, args.db_url))
    
    # Write results to file
    import json
    results_file = f"mindex_sync_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Results written to {results_file}")


if __name__ == "__main__":
    main()
