"""
MINDEX API Service

FastAPI-based REST API for the MINDEX fungal knowledge system.
Provides endpoints for:
- Species search and retrieval
- Observation data access
- ETL (scraping) status and control
- Statistics and health checks
"""

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mycosoft_mas.mindex import MINDEXManager, MINDEXDatabase
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    FungiDBScraper,
    GenBankScraper,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
NAS_DATA_PATH = Path(os.getenv("MINDEX_NAS_PATH", "/mnt/nas/mindex"))
DB_PATH = NAS_DATA_PATH / "mindex.db"
SYNC_INTERVAL_HOURS = int(os.getenv("MINDEX_SYNC_INTERVAL", "24"))
MAX_RECORDS_PER_SYNC = int(os.getenv("MINDEX_MAX_RECORDS", "50000"))

# Global manager instance
manager: Optional[MINDEXManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global manager
    
    # Ensure data directory exists
    NAS_DATA_PATH.mkdir(parents=True, exist_ok=True)
    
    # Initialize manager with NAS path
    manager = MINDEXManager(db_path=DB_PATH)
    logger.info(f"MINDEX initialized with database at {DB_PATH}")
    
    # Start continuous sync if enabled
    if os.getenv("MINDEX_AUTO_SYNC", "true").lower() == "true":
        manager.start_continuous_sync(
            interval_hours=SYNC_INTERVAL_HOURS,
            limit_per_source=MAX_RECORDS_PER_SYNC,
        )
        logger.info(f"Started continuous sync every {SYNC_INTERVAL_HOURS} hours")
    
    yield
    
    # Cleanup
    if manager:
        manager.stop_continuous_sync()
    logger.info("MINDEX shutdown complete")


app = FastAPI(
    title="MINDEX - Mycological Index Data System",
    description="""
    Central knowledge base for fungal information, integrating data from:
    - iNaturalist (observations and species data)
    - FungiDB (genomic and molecular data)
    - MycoBank (taxonomic nomenclature)
    - GBIF (global biodiversity information)
    - GenBank (NCBI genomic sequences)
    
    Provides instant local access to all fungal data for MYCOSOFT systems.
    """,
    version="2.0.0",
    lifespan=lifespan,
)

# CORS for web dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Models ==============

class HealthResponse(BaseModel):
    status: str
    api: bool
    database: bool
    etl: str
    version: str
    uptime: int
    db_path: str
    db_size_mb: float


class StatsResponse(BaseModel):
    total_species: int
    total_observations: int
    species_by_source: dict
    top_genera: list
    db_size_mb: float
    last_sync: Optional[str] = None


class SyncRequest(BaseModel):
    sources: Optional[list[str]] = None
    limit: Optional[int] = None


class SyncResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None


# ============== Health Endpoints ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    db_exists = DB_PATH.exists()
    db_size = DB_PATH.stat().st_size / (1024 * 1024) if db_exists else 0
    
    return HealthResponse(
        status="healthy" if db_exists else "degraded",
        api=True,
        database=db_exists,
        etl="running" if manager._running else "idle",
        version="2.0.0",
        uptime=0,  # Would track actual uptime
        db_path=str(DB_PATH),
        db_size_mb=round(db_size, 2),
    )


@app.get("/api/mindex/health")
async def mindex_health():
    """MINDEX-specific health endpoint (for dashboard compatibility)."""
    return await health_check()


# ============== Statistics ==============

@app.get("/api/mindex/stats", response_model=StatsResponse)
async def get_stats():
    """Get MINDEX database statistics."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    stats = manager.get_stats()
    
    return StatsResponse(
        total_species=stats.get("total_species", 0),
        total_observations=stats.get("total_observations", 0),
        species_by_source=stats.get("species_by_source", {}),
        top_genera=stats.get("top_genera", []),
        db_size_mb=stats.get("db_size_mb", 0),
    )


# ============== Search Endpoints ==============

@app.get("/api/mindex/search")
async def search_species(
    q: str = Query(..., min_length=2, description="Search query"),
    sources: Optional[str] = Query(None, description="Comma-separated sources"),
    limit: int = Query(50, ge=1, le=500),
):
    """Search for species across all sources."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    source_list = sources.split(",") if sources else None
    results = await manager.search(q, sources=source_list, limit=limit)
    
    return results


@app.get("/api/mindex/taxa")
async def list_taxa(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    family: Optional[str] = None,
    genus: Optional[str] = None,
):
    """List taxa with pagination."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    # Query database directly for listing
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM species WHERE 1=1"
        params = []
        
        if family:
            query += " AND family = ?"
            params.append(family)
        if genus:
            query += " AND genus = ?"
            params.append(genus)
        
        query += " ORDER BY scientific_name LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM species WHERE 1=1"
        if family:
            count_query += f" AND family = '{family}'"
        if genus:
            count_query += f" AND genus = '{genus}'"
        cursor.execute(count_query)
        total = cursor.fetchone()[0]
    
    return {
        "data": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@app.get("/api/mindex/taxa/{taxon_id}")
async def get_taxon(taxon_id: int):
    """Get detailed information about a specific taxon."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM species WHERE id = ?", (taxon_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Taxon not found")
        
        return dict(row)


@app.get("/api/mindex/observations")
async def list_observations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    species_name: Optional[str] = None,
    quality: Optional[str] = None,
):
    """List observations with pagination."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM observations WHERE 1=1"
        params = []
        
        if species_name:
            query += " AND scientific_name LIKE ?"
            params.append(f"%{species_name}%")
        if quality:
            query += " AND quality_grade = ?"
            params.append(quality)
        
        query += " ORDER BY observed_on DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM observations")
        total = cursor.fetchone()[0]
    
    return {
        "observations": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ============== ETL/Sync Endpoints ==============

@app.get("/api/mindex/etl-status")
async def get_etl_status():
    """Get current ETL (scraping) status."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    # Get recent scrape history
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM scrape_history 
            ORDER BY completed_at DESC 
            LIMIT 10
        """)
        history = [dict(row) for row in cursor.fetchall()]
    
    return {
        "status": "running" if manager._running else "idle",
        "sync_interval_hours": SYNC_INTERVAL_HOURS,
        "max_records_per_source": MAX_RECORDS_PER_SYNC,
        "recent_syncs": history,
        "available_sources": [
            "iNaturalist",
            "GBIF",
            "MycoBank",
            "FungiDB",
            "GenBank",
        ],
    }


@app.post("/api/mindex/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger a manual data sync."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    sources = request.sources or ["iNaturalist", "GBIF", "MycoBank", "GenBank"]
    limit = request.limit or 1000
    
    async def run_sync():
        for source in sources:
            try:
                await manager.sync_source(source, limit=limit)
            except Exception as e:
                logger.error(f"Sync error for {source}: {e}")
    
    background_tasks.add_task(run_sync)
    
    return SyncResponse(
        status="started",
        message=f"Sync started for sources: {', '.join(sources)}",
        task_id=datetime.utcnow().isoformat(),
    )


@app.post("/api/mindex/sync/{source}")
async def sync_source(
    source: str,
    limit: int = Query(1000, ge=100, le=100000),
    background_tasks: BackgroundTasks = None,
):
    """Sync data from a specific source."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    valid_sources = ["iNaturalist", "GBIF", "MycoBank", "FungiDB", "GenBank"]
    if source not in valid_sources:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}"
        )
    
    if background_tasks:
        background_tasks.add_task(manager.sync_source, source, limit)
        return {"status": "started", "source": source, "limit": limit}
    else:
        result = await manager.sync_source(source, limit=limit)
        return result


# ============== Compounds/Genomics (FungiDB/GenBank) ==============

@app.get("/api/mindex/compounds")
async def get_compounds(
    species: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Get compound/genomic data."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM genomic_data WHERE 1=1"
        params = []
        
        if species:
            query += " AND organism_name LIKE ?"
            params.append(f"%{species}%")
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
    
    return {"data": results, "total": len(results)}


# ============== Run Server ==============

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("MINDEX_PORT", "8000"))
    host = os.getenv("MINDEX_HOST", "0.0.0.0")
    
    logger.info(f"Starting MINDEX API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

"""
MINDEX API Service

FastAPI-based REST API for the MINDEX fungal knowledge system.
Provides endpoints for:
- Species search and retrieval
- Observation data access
- ETL (scraping) status and control
- Statistics and health checks
"""

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mycosoft_mas.mindex import MINDEXManager, MINDEXDatabase
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    FungiDBScraper,
    GenBankScraper,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
NAS_DATA_PATH = Path(os.getenv("MINDEX_NAS_PATH", "/mnt/nas/mindex"))
DB_PATH = NAS_DATA_PATH / "mindex.db"
SYNC_INTERVAL_HOURS = int(os.getenv("MINDEX_SYNC_INTERVAL", "24"))
MAX_RECORDS_PER_SYNC = int(os.getenv("MINDEX_MAX_RECORDS", "50000"))

# Global manager instance
manager: Optional[MINDEXManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global manager
    
    # Ensure data directory exists
    NAS_DATA_PATH.mkdir(parents=True, exist_ok=True)
    
    # Initialize manager with NAS path
    manager = MINDEXManager(db_path=DB_PATH)
    logger.info(f"MINDEX initialized with database at {DB_PATH}")
    
    # Start continuous sync if enabled
    if os.getenv("MINDEX_AUTO_SYNC", "true").lower() == "true":
        manager.start_continuous_sync(
            interval_hours=SYNC_INTERVAL_HOURS,
            limit_per_source=MAX_RECORDS_PER_SYNC,
        )
        logger.info(f"Started continuous sync every {SYNC_INTERVAL_HOURS} hours")
    
    yield
    
    # Cleanup
    if manager:
        manager.stop_continuous_sync()
    logger.info("MINDEX shutdown complete")


app = FastAPI(
    title="MINDEX - Mycological Index Data System",
    description="""
    Central knowledge base for fungal information, integrating data from:
    - iNaturalist (observations and species data)
    - FungiDB (genomic and molecular data)
    - MycoBank (taxonomic nomenclature)
    - GBIF (global biodiversity information)
    - GenBank (NCBI genomic sequences)
    
    Provides instant local access to all fungal data for MYCOSOFT systems.
    """,
    version="2.0.0",
    lifespan=lifespan,
)

# CORS for web dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Models ==============

class HealthResponse(BaseModel):
    status: str
    api: bool
    database: bool
    etl: str
    version: str
    uptime: int
    db_path: str
    db_size_mb: float


class StatsResponse(BaseModel):
    total_species: int
    total_observations: int
    species_by_source: dict
    top_genera: list
    db_size_mb: float
    last_sync: Optional[str] = None


class SyncRequest(BaseModel):
    sources: Optional[list[str]] = None
    limit: Optional[int] = None


class SyncResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None


# ============== Health Endpoints ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    db_exists = DB_PATH.exists()
    db_size = DB_PATH.stat().st_size / (1024 * 1024) if db_exists else 0
    
    return HealthResponse(
        status="healthy" if db_exists else "degraded",
        api=True,
        database=db_exists,
        etl="running" if manager._running else "idle",
        version="2.0.0",
        uptime=0,  # Would track actual uptime
        db_path=str(DB_PATH),
        db_size_mb=round(db_size, 2),
    )


@app.get("/api/mindex/health")
async def mindex_health():
    """MINDEX-specific health endpoint (for dashboard compatibility)."""
    return await health_check()


# ============== Statistics ==============

@app.get("/api/mindex/stats", response_model=StatsResponse)
async def get_stats():
    """Get MINDEX database statistics."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    stats = manager.get_stats()
    
    return StatsResponse(
        total_species=stats.get("total_species", 0),
        total_observations=stats.get("total_observations", 0),
        species_by_source=stats.get("species_by_source", {}),
        top_genera=stats.get("top_genera", []),
        db_size_mb=stats.get("db_size_mb", 0),
    )


# ============== Search Endpoints ==============

@app.get("/api/mindex/search")
async def search_species(
    q: str = Query(..., min_length=2, description="Search query"),
    sources: Optional[str] = Query(None, description="Comma-separated sources"),
    limit: int = Query(50, ge=1, le=500),
):
    """Search for species across all sources."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    source_list = sources.split(",") if sources else None
    results = await manager.search(q, sources=source_list, limit=limit)
    
    return results


@app.get("/api/mindex/taxa")
async def list_taxa(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    family: Optional[str] = None,
    genus: Optional[str] = None,
):
    """List taxa with pagination."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    # Query database directly for listing
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM species WHERE 1=1"
        params = []
        
        if family:
            query += " AND family = ?"
            params.append(family)
        if genus:
            query += " AND genus = ?"
            params.append(genus)
        
        query += " ORDER BY scientific_name LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM species WHERE 1=1"
        if family:
            count_query += f" AND family = '{family}'"
        if genus:
            count_query += f" AND genus = '{genus}'"
        cursor.execute(count_query)
        total = cursor.fetchone()[0]
    
    return {
        "data": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@app.get("/api/mindex/taxa/{taxon_id}")
async def get_taxon(taxon_id: int):
    """Get detailed information about a specific taxon."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM species WHERE id = ?", (taxon_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Taxon not found")
        
        return dict(row)


@app.get("/api/mindex/observations")
async def list_observations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    species_name: Optional[str] = None,
    quality: Optional[str] = None,
):
    """List observations with pagination."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM observations WHERE 1=1"
        params = []
        
        if species_name:
            query += " AND scientific_name LIKE ?"
            params.append(f"%{species_name}%")
        if quality:
            query += " AND quality_grade = ?"
            params.append(quality)
        
        query += " ORDER BY observed_on DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM observations")
        total = cursor.fetchone()[0]
    
    return {
        "observations": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ============== ETL/Sync Endpoints ==============

@app.get("/api/mindex/etl-status")
async def get_etl_status():
    """Get current ETL (scraping) status."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    # Get recent scrape history
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM scrape_history 
            ORDER BY completed_at DESC 
            LIMIT 10
        """)
        history = [dict(row) for row in cursor.fetchall()]
    
    return {
        "status": "running" if manager._running else "idle",
        "sync_interval_hours": SYNC_INTERVAL_HOURS,
        "max_records_per_source": MAX_RECORDS_PER_SYNC,
        "recent_syncs": history,
        "available_sources": [
            "iNaturalist",
            "GBIF",
            "MycoBank",
            "FungiDB",
            "GenBank",
        ],
    }


@app.post("/api/mindex/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger a manual data sync."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    sources = request.sources or ["iNaturalist", "GBIF", "MycoBank", "GenBank"]
    limit = request.limit or 1000
    
    async def run_sync():
        for source in sources:
            try:
                await manager.sync_source(source, limit=limit)
            except Exception as e:
                logger.error(f"Sync error for {source}: {e}")
    
    background_tasks.add_task(run_sync)
    
    return SyncResponse(
        status="started",
        message=f"Sync started for sources: {', '.join(sources)}",
        task_id=datetime.utcnow().isoformat(),
    )


@app.post("/api/mindex/sync/{source}")
async def sync_source(
    source: str,
    limit: int = Query(1000, ge=100, le=100000),
    background_tasks: BackgroundTasks = None,
):
    """Sync data from a specific source."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    valid_sources = ["iNaturalist", "GBIF", "MycoBank", "FungiDB", "GenBank"]
    if source not in valid_sources:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}"
        )
    
    if background_tasks:
        background_tasks.add_task(manager.sync_source, source, limit)
        return {"status": "started", "source": source, "limit": limit}
    else:
        result = await manager.sync_source(source, limit=limit)
        return result


# ============== Compounds/Genomics (FungiDB/GenBank) ==============

@app.get("/api/mindex/compounds")
async def get_compounds(
    species: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Get compound/genomic data."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM genomic_data WHERE 1=1"
        params = []
        
        if species:
            query += " AND organism_name LIKE ?"
            params.append(f"%{species}%")
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
    
    return {"data": results, "total": len(results)}


# ============== Run Server ==============

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("MINDEX_PORT", "8000"))
    host = os.getenv("MINDEX_HOST", "0.0.0.0")
    
    logger.info(f"Starting MINDEX API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


"""
MINDEX API Service

FastAPI-based REST API for the MINDEX fungal knowledge system.
Provides endpoints for:
- Species search and retrieval
- Observation data access
- ETL (scraping) status and control
- Statistics and health checks
"""

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mycosoft_mas.mindex import MINDEXManager, MINDEXDatabase
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    FungiDBScraper,
    GenBankScraper,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
NAS_DATA_PATH = Path(os.getenv("MINDEX_NAS_PATH", "/mnt/nas/mindex"))
DB_PATH = NAS_DATA_PATH / "mindex.db"
SYNC_INTERVAL_HOURS = int(os.getenv("MINDEX_SYNC_INTERVAL", "24"))
MAX_RECORDS_PER_SYNC = int(os.getenv("MINDEX_MAX_RECORDS", "50000"))

# Global manager instance
manager: Optional[MINDEXManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global manager
    
    # Ensure data directory exists
    NAS_DATA_PATH.mkdir(parents=True, exist_ok=True)
    
    # Initialize manager with NAS path
    manager = MINDEXManager(db_path=DB_PATH)
    logger.info(f"MINDEX initialized with database at {DB_PATH}")
    
    # Start continuous sync if enabled
    if os.getenv("MINDEX_AUTO_SYNC", "true").lower() == "true":
        manager.start_continuous_sync(
            interval_hours=SYNC_INTERVAL_HOURS,
            limit_per_source=MAX_RECORDS_PER_SYNC,
        )
        logger.info(f"Started continuous sync every {SYNC_INTERVAL_HOURS} hours")
    
    yield
    
    # Cleanup
    if manager:
        manager.stop_continuous_sync()
    logger.info("MINDEX shutdown complete")


app = FastAPI(
    title="MINDEX - Mycological Index Data System",
    description="""
    Central knowledge base for fungal information, integrating data from:
    - iNaturalist (observations and species data)
    - FungiDB (genomic and molecular data)
    - MycoBank (taxonomic nomenclature)
    - GBIF (global biodiversity information)
    - GenBank (NCBI genomic sequences)
    
    Provides instant local access to all fungal data for MYCOSOFT systems.
    """,
    version="2.0.0",
    lifespan=lifespan,
)

# CORS for web dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Models ==============

class HealthResponse(BaseModel):
    status: str
    api: bool
    database: bool
    etl: str
    version: str
    uptime: int
    db_path: str
    db_size_mb: float


class StatsResponse(BaseModel):
    total_species: int
    total_observations: int
    species_by_source: dict
    top_genera: list
    db_size_mb: float
    last_sync: Optional[str] = None


class SyncRequest(BaseModel):
    sources: Optional[list[str]] = None
    limit: Optional[int] = None


class SyncResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None


# ============== Health Endpoints ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    db_exists = DB_PATH.exists()
    db_size = DB_PATH.stat().st_size / (1024 * 1024) if db_exists else 0
    
    return HealthResponse(
        status="healthy" if db_exists else "degraded",
        api=True,
        database=db_exists,
        etl="running" if manager._running else "idle",
        version="2.0.0",
        uptime=0,  # Would track actual uptime
        db_path=str(DB_PATH),
        db_size_mb=round(db_size, 2),
    )


@app.get("/api/mindex/health")
async def mindex_health():
    """MINDEX-specific health endpoint (for dashboard compatibility)."""
    return await health_check()


# ============== Statistics ==============

@app.get("/api/mindex/stats", response_model=StatsResponse)
async def get_stats():
    """Get MINDEX database statistics."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    stats = manager.get_stats()
    
    return StatsResponse(
        total_species=stats.get("total_species", 0),
        total_observations=stats.get("total_observations", 0),
        species_by_source=stats.get("species_by_source", {}),
        top_genera=stats.get("top_genera", []),
        db_size_mb=stats.get("db_size_mb", 0),
    )


# ============== Search Endpoints ==============

@app.get("/api/mindex/search")
async def search_species(
    q: str = Query(..., min_length=2, description="Search query"),
    sources: Optional[str] = Query(None, description="Comma-separated sources"),
    limit: int = Query(50, ge=1, le=500),
):
    """Search for species across all sources."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    source_list = sources.split(",") if sources else None
    results = await manager.search(q, sources=source_list, limit=limit)
    
    return results


@app.get("/api/mindex/taxa")
async def list_taxa(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    family: Optional[str] = None,
    genus: Optional[str] = None,
):
    """List taxa with pagination."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    # Query database directly for listing
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM species WHERE 1=1"
        params = []
        
        if family:
            query += " AND family = ?"
            params.append(family)
        if genus:
            query += " AND genus = ?"
            params.append(genus)
        
        query += " ORDER BY scientific_name LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM species WHERE 1=1"
        if family:
            count_query += f" AND family = '{family}'"
        if genus:
            count_query += f" AND genus = '{genus}'"
        cursor.execute(count_query)
        total = cursor.fetchone()[0]
    
    return {
        "data": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@app.get("/api/mindex/taxa/{taxon_id}")
async def get_taxon(taxon_id: int):
    """Get detailed information about a specific taxon."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM species WHERE id = ?", (taxon_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Taxon not found")
        
        return dict(row)


@app.get("/api/mindex/observations")
async def list_observations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    species_name: Optional[str] = None,
    quality: Optional[str] = None,
):
    """List observations with pagination."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM observations WHERE 1=1"
        params = []
        
        if species_name:
            query += " AND scientific_name LIKE ?"
            params.append(f"%{species_name}%")
        if quality:
            query += " AND quality_grade = ?"
            params.append(quality)
        
        query += " ORDER BY observed_on DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM observations")
        total = cursor.fetchone()[0]
    
    return {
        "observations": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ============== ETL/Sync Endpoints ==============

@app.get("/api/mindex/etl-status")
async def get_etl_status():
    """Get current ETL (scraping) status."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    # Get recent scrape history
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM scrape_history 
            ORDER BY completed_at DESC 
            LIMIT 10
        """)
        history = [dict(row) for row in cursor.fetchall()]
    
    return {
        "status": "running" if manager._running else "idle",
        "sync_interval_hours": SYNC_INTERVAL_HOURS,
        "max_records_per_source": MAX_RECORDS_PER_SYNC,
        "recent_syncs": history,
        "available_sources": [
            "iNaturalist",
            "GBIF",
            "MycoBank",
            "FungiDB",
            "GenBank",
        ],
    }


@app.post("/api/mindex/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger a manual data sync."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    sources = request.sources or ["iNaturalist", "GBIF", "MycoBank", "GenBank"]
    limit = request.limit or 1000
    
    async def run_sync():
        for source in sources:
            try:
                await manager.sync_source(source, limit=limit)
            except Exception as e:
                logger.error(f"Sync error for {source}: {e}")
    
    background_tasks.add_task(run_sync)
    
    return SyncResponse(
        status="started",
        message=f"Sync started for sources: {', '.join(sources)}",
        task_id=datetime.utcnow().isoformat(),
    )


@app.post("/api/mindex/sync/{source}")
async def sync_source(
    source: str,
    limit: int = Query(1000, ge=100, le=100000),
    background_tasks: BackgroundTasks = None,
):
    """Sync data from a specific source."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    valid_sources = ["iNaturalist", "GBIF", "MycoBank", "FungiDB", "GenBank"]
    if source not in valid_sources:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}"
        )
    
    if background_tasks:
        background_tasks.add_task(manager.sync_source, source, limit)
        return {"status": "started", "source": source, "limit": limit}
    else:
        result = await manager.sync_source(source, limit=limit)
        return result


# ============== Compounds/Genomics (FungiDB/GenBank) ==============

@app.get("/api/mindex/compounds")
async def get_compounds(
    species: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Get compound/genomic data."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM genomic_data WHERE 1=1"
        params = []
        
        if species:
            query += " AND organism_name LIKE ?"
            params.append(f"%{species}%")
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
    
    return {"data": results, "total": len(results)}


# ============== Run Server ==============

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("MINDEX_PORT", "8000"))
    host = os.getenv("MINDEX_HOST", "0.0.0.0")
    
    logger.info(f"Starting MINDEX API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

"""
MINDEX API Service

FastAPI-based REST API for the MINDEX fungal knowledge system.
Provides endpoints for:
- Species search and retrieval
- Observation data access
- ETL (scraping) status and control
- Statistics and health checks
"""

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mycosoft_mas.mindex import MINDEXManager, MINDEXDatabase
from mycosoft_mas.mindex.scrapers import (
    INaturalistScraper,
    GBIFScraper,
    MycoBankScraper,
    FungiDBScraper,
    GenBankScraper,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
NAS_DATA_PATH = Path(os.getenv("MINDEX_NAS_PATH", "/mnt/nas/mindex"))
DB_PATH = NAS_DATA_PATH / "mindex.db"
SYNC_INTERVAL_HOURS = int(os.getenv("MINDEX_SYNC_INTERVAL", "24"))
MAX_RECORDS_PER_SYNC = int(os.getenv("MINDEX_MAX_RECORDS", "50000"))

# Global manager instance
manager: Optional[MINDEXManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global manager
    
    # Ensure data directory exists
    NAS_DATA_PATH.mkdir(parents=True, exist_ok=True)
    
    # Initialize manager with NAS path
    manager = MINDEXManager(db_path=DB_PATH)
    logger.info(f"MINDEX initialized with database at {DB_PATH}")
    
    # Start continuous sync if enabled
    if os.getenv("MINDEX_AUTO_SYNC", "true").lower() == "true":
        manager.start_continuous_sync(
            interval_hours=SYNC_INTERVAL_HOURS,
            limit_per_source=MAX_RECORDS_PER_SYNC,
        )
        logger.info(f"Started continuous sync every {SYNC_INTERVAL_HOURS} hours")
    
    yield
    
    # Cleanup
    if manager:
        manager.stop_continuous_sync()
    logger.info("MINDEX shutdown complete")


app = FastAPI(
    title="MINDEX - Mycological Index Data System",
    description="""
    Central knowledge base for fungal information, integrating data from:
    - iNaturalist (observations and species data)
    - FungiDB (genomic and molecular data)
    - MycoBank (taxonomic nomenclature)
    - GBIF (global biodiversity information)
    - GenBank (NCBI genomic sequences)
    
    Provides instant local access to all fungal data for MYCOSOFT systems.
    """,
    version="2.0.0",
    lifespan=lifespan,
)

# CORS for web dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Models ==============

class HealthResponse(BaseModel):
    status: str
    api: bool
    database: bool
    etl: str
    version: str
    uptime: int
    db_path: str
    db_size_mb: float


class StatsResponse(BaseModel):
    total_species: int
    total_observations: int
    species_by_source: dict
    top_genera: list
    db_size_mb: float
    last_sync: Optional[str] = None


class SyncRequest(BaseModel):
    sources: Optional[list[str]] = None
    limit: Optional[int] = None


class SyncResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None


# ============== Health Endpoints ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    db_exists = DB_PATH.exists()
    db_size = DB_PATH.stat().st_size / (1024 * 1024) if db_exists else 0
    
    return HealthResponse(
        status="healthy" if db_exists else "degraded",
        api=True,
        database=db_exists,
        etl="running" if manager._running else "idle",
        version="2.0.0",
        uptime=0,  # Would track actual uptime
        db_path=str(DB_PATH),
        db_size_mb=round(db_size, 2),
    )


@app.get("/api/mindex/health")
async def mindex_health():
    """MINDEX-specific health endpoint (for dashboard compatibility)."""
    return await health_check()


# ============== Statistics ==============

@app.get("/api/mindex/stats", response_model=StatsResponse)
async def get_stats():
    """Get MINDEX database statistics."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    stats = manager.get_stats()
    
    return StatsResponse(
        total_species=stats.get("total_species", 0),
        total_observations=stats.get("total_observations", 0),
        species_by_source=stats.get("species_by_source", {}),
        top_genera=stats.get("top_genera", []),
        db_size_mb=stats.get("db_size_mb", 0),
    )


# ============== Search Endpoints ==============

@app.get("/api/mindex/search")
async def search_species(
    q: str = Query(..., min_length=2, description="Search query"),
    sources: Optional[str] = Query(None, description="Comma-separated sources"),
    limit: int = Query(50, ge=1, le=500),
):
    """Search for species across all sources."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    source_list = sources.split(",") if sources else None
    results = await manager.search(q, sources=source_list, limit=limit)
    
    return results


@app.get("/api/mindex/taxa")
async def list_taxa(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    family: Optional[str] = None,
    genus: Optional[str] = None,
):
    """List taxa with pagination."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    # Query database directly for listing
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM species WHERE 1=1"
        params = []
        
        if family:
            query += " AND family = ?"
            params.append(family)
        if genus:
            query += " AND genus = ?"
            params.append(genus)
        
        query += " ORDER BY scientific_name LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM species WHERE 1=1"
        if family:
            count_query += f" AND family = '{family}'"
        if genus:
            count_query += f" AND genus = '{genus}'"
        cursor.execute(count_query)
        total = cursor.fetchone()[0]
    
    return {
        "data": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@app.get("/api/mindex/taxa/{taxon_id}")
async def get_taxon(taxon_id: int):
    """Get detailed information about a specific taxon."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM species WHERE id = ?", (taxon_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Taxon not found")
        
        return dict(row)


@app.get("/api/mindex/observations")
async def list_observations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    species_name: Optional[str] = None,
    quality: Optional[str] = None,
):
    """List observations with pagination."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM observations WHERE 1=1"
        params = []
        
        if species_name:
            query += " AND scientific_name LIKE ?"
            params.append(f"%{species_name}%")
        if quality:
            query += " AND quality_grade = ?"
            params.append(quality)
        
        query += " ORDER BY observed_on DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM observations")
        total = cursor.fetchone()[0]
    
    return {
        "observations": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ============== ETL/Sync Endpoints ==============

@app.get("/api/mindex/etl-status")
async def get_etl_status():
    """Get current ETL (scraping) status."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    # Get recent scrape history
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM scrape_history 
            ORDER BY completed_at DESC 
            LIMIT 10
        """)
        history = [dict(row) for row in cursor.fetchall()]
    
    return {
        "status": "running" if manager._running else "idle",
        "sync_interval_hours": SYNC_INTERVAL_HOURS,
        "max_records_per_source": MAX_RECORDS_PER_SYNC,
        "recent_syncs": history,
        "available_sources": [
            "iNaturalist",
            "GBIF",
            "MycoBank",
            "FungiDB",
            "GenBank",
        ],
    }


@app.post("/api/mindex/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger a manual data sync."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    sources = request.sources or ["iNaturalist", "GBIF", "MycoBank", "GenBank"]
    limit = request.limit or 1000
    
    async def run_sync():
        for source in sources:
            try:
                await manager.sync_source(source, limit=limit)
            except Exception as e:
                logger.error(f"Sync error for {source}: {e}")
    
    background_tasks.add_task(run_sync)
    
    return SyncResponse(
        status="started",
        message=f"Sync started for sources: {', '.join(sources)}",
        task_id=datetime.utcnow().isoformat(),
    )


@app.post("/api/mindex/sync/{source}")
async def sync_source(
    source: str,
    limit: int = Query(1000, ge=100, le=100000),
    background_tasks: BackgroundTasks = None,
):
    """Sync data from a specific source."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    valid_sources = ["iNaturalist", "GBIF", "MycoBank", "FungiDB", "GenBank"]
    if source not in valid_sources:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}"
        )
    
    if background_tasks:
        background_tasks.add_task(manager.sync_source, source, limit)
        return {"status": "started", "source": source, "limit": limit}
    else:
        result = await manager.sync_source(source, limit=limit)
        return result


# ============== Compounds/Genomics (FungiDB/GenBank) ==============

@app.get("/api/mindex/compounds")
async def get_compounds(
    species: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Get compound/genomic data."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM genomic_data WHERE 1=1"
        params = []
        
        if species:
            query += " AND organism_name LIKE ?"
            params.append(f"%{species}%")
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
    
    return {"data": results, "total": len(results)}


# ============== Run Server ==============

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("MINDEX_PORT", "8000"))
    host = os.getenv("MINDEX_HOST", "0.0.0.0")
    
    logger.info(f"Starting MINDEX API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)




