"""
Quick MINDEX Sync - Run from Windows connecting to MINDEX VM
"""
import asyncio
import aiohttp
import os
from datetime import datetime

# Config - use environment variables (set in .env); never commit secrets
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
MINDEX_DB = {
    "host": os.environ.get("MINDEX_DB_HOST", "192.168.0.189"),
    "port": int(os.environ.get("MINDEX_DB_PORT", "5432")),
    "user": os.environ.get("MINDEX_DB_USER", "mycosoft"),
    "password": os.environ.get("MINDEX_DB_PASSWORD", ""),
    "database": os.environ.get("MINDEX_DB_NAME", "mindex"),
}

# iNaturalist API - specifically target fungi
INAT_API = "https://api.inaturalist.org/v1"

async def fetch_inaturalist_fungi(session, page=1, per_page=100):
    """Fetch fungi from iNaturalist - using taxon_id for kingdom Fungi"""
    url = f"{INAT_API}/taxa"
    params = {
        "taxon_id": 47170,  # Kingdom Fungi
        "rank": "species",
        "per_page": per_page,
        "page": page,
        "order_by": "observations_count",
        "order": "desc",
    }
    
    async with session.get(url, params=params) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("results", [])
        else:
            print(f"Error fetching iNaturalist: {resp.status}")
            return []

async def sync_to_db(species_list):
    """Insert species into MINDEX database"""
    import asyncpg
    
    conn = await asyncpg.connect(
        host=MINDEX_DB["host"],
        port=MINDEX_DB["port"],
        user=MINDEX_DB["user"],
        password=MINDEX_DB["password"],
        database=MINDEX_DB["database"],
    )
    
    inserted = 0
    for sp in species_list:
        name = sp.get("name", "")
        parts = name.split() if name else []
        genus = parts[0] if len(parts) > 0 else None
        species_epithet = parts[1] if len(parts) > 1 else None
        
        try:
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
                sp.get("id"),
                sp.get("rank", "species"),
                sp.get("preferred_common_name"),
                "inaturalist",
                f"https://www.inaturalist.org/taxa/{sp.get('id')}"
            )
            inserted += 1
        except Exception as e:
            print(f"Error inserting {name}: {e}")
    
    await conn.close()
    return inserted

async def main():
    print(f"Starting MINDEX sync at {datetime.now()}")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Fetch first 50 pages (5000 species) as initial sync
        all_species = []
        for page in range(1, 51):
            print(f"Fetching page {page}/50...")
            species = await fetch_inaturalist_fungi(session, page=page)
            all_species.extend(species)
            if page % 10 == 0:
                print(f"  Progress: {len(all_species)} species fetched")
            await asyncio.sleep(0.5)  # Rate limit
        
        print("=" * 60)
        print(f"Total species fetched: {len(all_species)}")
        
        # Show some examples
        print("\nSample species:")
        for sp in all_species[:10]:
            print(f"  - {sp.get('name')} ({sp.get('preferred_common_name', 'no common name')})")
        
        # Insert into database
        print("\nSyncing to MINDEX database...")
        inserted = await sync_to_db(all_species)
        print(f"Inserted {inserted} species into core.taxon")

if __name__ == "__main__":
    asyncio.run(main())
