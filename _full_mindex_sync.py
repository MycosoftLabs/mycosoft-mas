"""
Full MINDEX Sync - Background sync from multiple sources
Run: python _full_mindex_sync.py
"""
import asyncio
import aiohttp
import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"mindex_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
logger = logging.getLogger("mindex_sync")

# Config
NCBI_API_KEY = "eb2264e1bc6f521cf2bcf7fc5f32447a7108"
MINDEX_DB = {
    "host": "192.168.0.189",
    "port": 5432,
    "user": "mycosoft",
    "password": "mycosoft_mindex_2026",
    "database": "mindex"
}

# APIs
INAT_API = "https://api.inaturalist.org/v1"
GBIF_API = "https://api.gbif.org/v1"
GENBANK_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# iNaturalist - taxon_id for Kingdom Fungi
FUNGI_TAXON_ID = 47170

async def fetch_inat_fungi(session, page=1, per_page=100):
    """Fetch fungi from iNaturalist"""
    url = f"{INAT_API}/taxa"
    params = {
        "taxon_id": FUNGI_TAXON_ID,
        "rank": "species",
        "per_page": per_page,
        "page": page,
        "order_by": "observations_count",
        "order": "desc",
    }
    
    try:
        async with session.get(url, params=params, timeout=30) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("results", [])
            else:
                logger.warning(f"iNat page {page}: status {resp.status}")
                return []
    except Exception as e:
        logger.error(f"iNat page {page} error: {e}")
        return []

async def fetch_gbif_fungi(session, offset=0, limit=100):
    """Fetch fungi from GBIF"""
    url = f"{GBIF_API}/species/search"
    params = {
        "kingdom": "Fungi",
        "rank": "SPECIES",
        "status": "ACCEPTED",
        "limit": limit,
        "offset": offset,
    }
    
    try:
        async with session.get(url, params=params, timeout=30) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("results", [])
            else:
                logger.warning(f"GBIF offset {offset}: status {resp.status}")
                return []
    except Exception as e:
        logger.error(f"GBIF offset {offset} error: {e}")
        return []

async def fetch_genbank_sequences(session, query, retstart=0, retmax=100):
    """Fetch fungal DNA sequences from GenBank"""
    # Search for sequence IDs
    search_url = f"{GENBANK_API}/esearch.fcgi"
    params = {
        "db": "nucleotide",
        "term": query,
        "retstart": retstart,
        "retmax": retmax,
        "retmode": "json",
        "api_key": NCBI_API_KEY,
    }
    
    try:
        async with session.get(search_url, params=params, timeout=30) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("esearchresult", {}).get("idlist", [])
            else:
                logger.warning(f"GenBank search status {resp.status}")
                return []
    except Exception as e:
        logger.error(f"GenBank search error: {e}")
        return []

async def sync_species_to_db(conn, species_list, source="inaturalist"):
    """Insert species into MINDEX database"""
    inserted = 0
    
    for sp in species_list:
        name = sp.get("name") or sp.get("scientificName") or sp.get("canonicalName", "")
        if not name:
            continue
            
        parts = name.split() if name else []
        genus = parts[0] if len(parts) > 0 else None
        species_epithet = parts[1] if len(parts) > 1 else None
        
        # Get IDs based on source
        inat_id = sp.get("id") if source == "inaturalist" else None
        gbif_key = sp.get("key") or sp.get("nubKey") if source == "gbif" else None
        
        common_name = sp.get("preferred_common_name") or sp.get("vernacularName")
        
        try:
            if source == "inaturalist":
                await conn.execute(
                    """
                    INSERT INTO core.taxon (
                        scientific_name, canonical_name, genus, species,
                        inat_id, rank, common_name, source, source_url
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT DO NOTHING
                    """,
                    name,
                    name,
                    genus,
                    species_epithet,
                    inat_id,
                    sp.get("rank", "species"),
                    common_name,
                    source,
                    f"https://www.inaturalist.org/taxa/{inat_id}" if inat_id else None
                )
            elif source == "gbif":
                await conn.execute(
                    """
                    INSERT INTO core.taxon (
                        scientific_name, canonical_name, genus, species,
                        gbif_key, rank, common_name, 
                        phylum, class_name, order_name, family,
                        source, source_url
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT DO NOTHING
                    """,
                    name,
                    sp.get("canonicalName", name),
                    genus,
                    species_epithet,
                    gbif_key,
                    sp.get("rank", "SPECIES").lower(),
                    common_name,
                    sp.get("phylum"),
                    sp.get("class"),
                    sp.get("order"),
                    sp.get("family"),
                    source,
                    f"https://www.gbif.org/species/{gbif_key}" if gbif_key else None
                )
            inserted += 1
        except Exception as e:
            logger.debug(f"Insert error for {name}: {e}")
    
    return inserted

async def sync_sequences_to_db(conn, sequences, species_name):
    """Insert DNA sequences into MINDEX database"""
    inserted = 0
    for acc in sequences:
        try:
            await conn.execute(
                """
                INSERT INTO core.dna_sequences (
                    scientific_name, accession, source
                ) VALUES ($1, $2, $3)
                ON CONFLICT (accession) DO NOTHING
                """,
                species_name,
                acc,
                "genbank"
            )
            inserted += 1
        except Exception as e:
            logger.debug(f"Sequence insert error: {e}")
    return inserted

async def sync_inaturalist(session, conn, max_pages=500):
    """Sync from iNaturalist (up to 50,000 species)"""
    logger.info("Starting iNaturalist sync...")
    total = 0
    
    for page in range(1, max_pages + 1):
        species = await fetch_inat_fungi(session, page=page, per_page=100)
        if not species:
            break
            
        inserted = await sync_species_to_db(conn, species, "inaturalist")
        total += inserted
        
        if page % 50 == 0:
            logger.info(f"  iNaturalist progress: page {page}, total {total}")
        
        await asyncio.sleep(0.5)  # Rate limit
    
    logger.info(f"iNaturalist sync complete: {total} species")
    return total

async def sync_gbif(session, conn, max_records=100000):
    """Sync from GBIF"""
    logger.info("Starting GBIF sync...")
    total = 0
    offset = 0
    batch_size = 100
    
    while offset < max_records:
        species = await fetch_gbif_fungi(session, offset=offset, limit=batch_size)
        if not species:
            break
            
        inserted = await sync_species_to_db(conn, species, "gbif")
        total += inserted
        offset += batch_size
        
        if offset % 5000 == 0:
            logger.info(f"  GBIF progress: offset {offset}, total {total}")
        
        await asyncio.sleep(0.3)  # Rate limit
    
    logger.info(f"GBIF sync complete: {total} species")
    return total

async def sync_genbank(session, conn, species_list):
    """Sync DNA sequences from GenBank for specific species"""
    logger.info("Starting GenBank sync...")
    total = 0
    
    # Gene regions to search
    gene_regions = ["ITS", "18S rRNA", "28S rRNA"]
    
    for species in species_list[:100]:  # Limit for now
        for gene in gene_regions:
            query = f'"{species}"[Organism] AND {gene}[Title] AND fungi[Filter]'
            ids = await fetch_genbank_sequences(session, query, retmax=10)
            
            if ids:
                inserted = await sync_sequences_to_db(conn, ids, species)
                total += inserted
            
            await asyncio.sleep(0.15)  # Rate limit (10 req/sec with API key)
    
    logger.info(f"GenBank sync complete: {total} sequences")
    return total

async def main():
    import asyncpg
    
    logger.info("=" * 60)
    logger.info("MINDEX Full Sync Started")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 60)
    
    # Connect to database
    conn = await asyncpg.connect(
        host=MINDEX_DB["host"],
        port=MINDEX_DB["port"],
        user=MINDEX_DB["user"],
        password=MINDEX_DB["password"],
        database=MINDEX_DB["database"],
    )
    
    stats = {
        "inat_species": 0,
        "gbif_species": 0,
        "genbank_sequences": 0,
    }
    
    async with aiohttp.ClientSession() as session:
        # Sync from iNaturalist (50,000 species max)
        stats["inat_species"] = await sync_inaturalist(session, conn, max_pages=500)
        
        # Sync from GBIF (100,000 species max)
        stats["gbif_species"] = await sync_gbif(session, conn, max_records=100000)
        
        # Get top species for GenBank search
        rows = await conn.fetch(
            "SELECT scientific_name FROM core.taxon WHERE source = 'inaturalist' LIMIT 100"
        )
        species_list = [r["scientific_name"] for r in rows]
        
        # Sync GenBank sequences
        stats["genbank_sequences"] = await sync_genbank(session, conn, species_list)
    
    # Final count
    count = await conn.fetchval("SELECT COUNT(*) FROM core.taxon")
    seq_count = await conn.fetchval("SELECT COUNT(*) FROM core.dna_sequences")
    
    await conn.close()
    
    logger.info("=" * 60)
    logger.info("MINDEX Full Sync Complete")
    logger.info(f"Total species in database: {count}")
    logger.info(f"Total sequences in database: {seq_count}")
    logger.info(f"Stats: {stats}")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
