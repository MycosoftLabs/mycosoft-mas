"""
MINDEX API Service

FastAPI-based REST API for the MINDEX fungal knowledge system.
Provides endpoints for:
- Species search and retrieval
- Observation data access
- ETL (scraping) status and control
- Statistics and health checks
- Telemetry ingestion for device data
- Image tagging and training data management
"""

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from mycosoft_mas.mindex import MINDEXManager, MINDEXDatabase
    from mycosoft_mas.mindex.scrapers import (
        INaturalistScraper,
        GBIFScraper,
        MycoBankScraper,
        FungiDBScraper,
        GenBankScraper,
    )
    HAS_SCRAPERS = True
except ImportError:
    HAS_SCRAPERS = False
    MINDEXManager = None
    MINDEXDatabase = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
NAS_DATA_PATH = Path(os.getenv("MINDEX_NAS_PATH", "/mnt/nas/mindex"))
LOCAL_DATA_PATH = Path(os.getenv("MINDEX_LOCAL_PATH", "/app/data"))
DB_PATH = LOCAL_DATA_PATH / "mindex.db"
SYNC_INTERVAL_HOURS = int(os.getenv("MINDEX_SYNC_INTERVAL", "24"))
MAX_RECORDS_PER_SYNC = int(os.getenv("MINDEX_MAX_RECORDS", "50000"))

# Global manager instance
manager: Optional["MINDEXManager"] = None
startup_time: datetime = datetime.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global manager, startup_time
    startup_time = datetime.now()
    
    # Ensure data directories exist
    LOCAL_DATA_PATH.mkdir(parents=True, exist_ok=True)
    NAS_DATA_PATH.mkdir(parents=True, exist_ok=True)
    
    if HAS_SCRAPERS and MINDEXManager:
        # Initialize manager with local path (syncs to NAS periodically)
        manager = MINDEXManager(db_path=DB_PATH)
        logger.info(f"MINDEX initialized with database at {DB_PATH}")
        
        # Start continuous sync if enabled
        if os.getenv("MINDEX_AUTO_SYNC", "true").lower() == "true":
            manager.start_continuous_sync(
                interval_hours=SYNC_INTERVAL_HOURS,
                limit_per_source=MAX_RECORDS_PER_SYNC,
            )
            logger.info(f"Started continuous sync every {SYNC_INTERVAL_HOURS} hours")
    else:
        logger.warning("MINDEX scrapers not available - running in limited mode")
    
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
    - Mushroom.world (additional species data)
    
    Provides instant local access to all fungal data for MYCOSOFT systems.
    Powers the Species Explorer, Ancestry tools, and AI learning systems.
    """,
    version="2.1.0",
    lifespan=lifespan,
)

# CORS for web dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    uptime_seconds: int
    db_path: str
    db_size_mb: float


class StatsResponse(BaseModel):
    total_species: int
    total_observations: int
    total_images: int
    total_genetic_records: int
    species_by_source: dict
    species_by_kingdom: dict
    top_genera: list
    db_size_mb: float
    last_sync: Optional[str] = None


class SyncRequest(BaseModel):
    sources: Optional[List[str]] = None
    limit: Optional[int] = None


class SyncResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None


class TelemetryRequest(BaseModel):
    source: str
    device_id: Optional[str] = None
    timestamp: Optional[str] = None
    data: dict


class SpeciesRecord(BaseModel):
    mindex_id: Optional[str] = None
    scientific_name: str
    common_names: Optional[List[str]] = None
    kingdom: str = "Fungi"
    phylum: Optional[str] = None
    class_name: Optional[str] = None
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    species: Optional[str] = None
    subspecies: Optional[str] = None
    author: Optional[str] = None
    year_described: Optional[int] = None
    type_specimen: Optional[str] = None
    sources: Optional[List[str]] = None
    external_ids: Optional[dict] = None


class ImageRecord(BaseModel):
    species_id: str
    url: str
    source: str
    license: Optional[str] = None
    attribution: Optional[str] = None
    quality_score: Optional[float] = None
    is_training_data: bool = False
    tags: Optional[List[str]] = None


# ============== Health Endpoints ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health."""
    db_exists = DB_PATH.exists()
    db_size = DB_PATH.stat().st_size / (1024 * 1024) if db_exists else 0
    uptime = (datetime.now() - startup_time).total_seconds()
    
    etl_status = "disabled"
    if manager:
        etl_status = "running" if getattr(manager, '_running', False) else "idle"
    
    return HealthResponse(
        status="healthy" if db_exists else "degraded",
        api=True,
        database=db_exists,
        etl=etl_status,
        version="2.1.0",
        uptime_seconds=int(uptime),
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
        # Return mock stats when manager not available
        return StatsResponse(
            total_species=0,
            total_observations=0,
            total_images=0,
            total_genetic_records=0,
            species_by_source={},
            species_by_kingdom={},
            top_genera=[],
            db_size_mb=0,
        )
    
    stats = manager.get_stats()
    
    return StatsResponse(
        total_species=stats.get("total_species", 0),
        total_observations=stats.get("total_observations", 0),
        total_images=stats.get("total_images", 0),
        total_genetic_records=stats.get("total_genetic_records", 0),
        species_by_source=stats.get("species_by_source", {}),
        species_by_kingdom=stats.get("species_by_kingdom", {"Fungi": 0}),
        top_genera=stats.get("top_genera", []),
        db_size_mb=stats.get("db_size_mb", 0),
    )


# ============== Search Endpoints ==============

@app.get("/api/mindex/search")
async def search_species(
    q: str = Query(..., min_length=2, description="Search query"),
    sources: Optional[str] = Query(None, description="Comma-separated sources"),
    kingdom: Optional[str] = Query(None, description="Filter by kingdom (Fungi, etc.)"),
    limit: int = Query(50, ge=1, le=500),
):
    """Search for species across all sources."""
    if not manager:
        return {"results": [], "total": 0, "query": q}
    
    source_list = sources.split(",") if sources else None
    results = await manager.search(
        q, 
        sources=source_list, 
        kingdom=kingdom,
        limit=limit
    )
    
    return results


@app.get("/api/mindex/species")
async def list_species(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    kingdom: Optional[str] = Query("Fungi", description="Kingdom filter"),
    phylum: Optional[str] = None,
    family: Optional[str] = None,
    genus: Optional[str] = None,
    has_images: Optional[bool] = None,
    has_genetics: Optional[bool] = None,
):
    """List species with pagination and filters."""
    if not manager:
        return {"data": [], "total": 0, "page": page, "per_page": per_page}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM species WHERE 1=1"
        params = []
        
        if kingdom:
            query += " AND kingdom = ?"
            params.append(kingdom)
        if phylum:
            query += " AND phylum = ?"
            params.append(phylum)
        if family:
            query += " AND family = ?"
            params.append(family)
        if genus:
            query += " AND genus = ?"
            params.append(genus)
        if has_images:
            query += " AND image_count > 0"
        if has_genetics:
            query += " AND genetic_record_count > 0"
        
        query += " ORDER BY scientific_name LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM species WHERE 1=1"
        count_params = []
        if kingdom:
            count_query += " AND kingdom = ?"
            count_params.append(kingdom)
        if phylum:
            count_query += " AND phylum = ?"
            count_params.append(phylum)
        if family:
            count_query += " AND family = ?"
            count_params.append(family)
        if genus:
            count_query += " AND genus = ?"
            count_params.append(genus)
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
    
    return {
        "data": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@app.get("/api/mindex/species/{species_id}")
async def get_species(species_id: str):
    """Get detailed information about a specific species."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Try by mindex_id first, then by numeric id
        cursor.execute(
            "SELECT * FROM species WHERE mindex_id = ? OR id = ?", 
            (species_id, species_id)
        )
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Species not found")
        
        species = dict(row)
        
        # Get associated images
        cursor.execute(
            "SELECT * FROM images WHERE species_id = ? LIMIT 50",
            (species.get("id") or species.get("mindex_id"),)
        )
        species["images"] = [dict(r) for r in cursor.fetchall()]
        
        # Get genetic data
        cursor.execute(
            "SELECT * FROM genetic_records WHERE species_id = ? LIMIT 20",
            (species.get("id") or species.get("mindex_id"),)
        )
        species["genetic_records"] = [dict(r) for r in cursor.fetchall()]
        
        # Get taxonomy hierarchy
        cursor.execute("""
            SELECT * FROM taxonomy 
            WHERE species_id = ? 
            ORDER BY rank_order
        """, (species.get("id") or species.get("mindex_id"),))
        species["taxonomy"] = [dict(r) for r in cursor.fetchall()]
        
        return species


# ============== Legacy Taxa Endpoints (for backward compatibility) ==============

@app.get("/api/mindex/taxa")
async def list_taxa(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    family: Optional[str] = None,
    genus: Optional[str] = None,
):
    """List taxa with pagination (legacy endpoint)."""
    return await list_species(page=page, per_page=per_page, family=family, genus=genus)


@app.get("/api/mindex/taxa/{taxon_id}")
async def get_taxon(taxon_id: int):
    """Get detailed information about a specific taxon (legacy endpoint)."""
    return await get_species(str(taxon_id))


# ============== Observations ==============

@app.get("/api/mindex/observations")
async def list_observations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    species_name: Optional[str] = None,
    species_id: Optional[str] = None,
    quality: Optional[str] = None,
    has_photo: Optional[bool] = None,
):
    """List observations with pagination."""
    if not manager:
        return {"observations": [], "total": 0, "page": page, "per_page": per_page}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM observations WHERE 1=1"
        params = []
        
        if species_name:
            query += " AND scientific_name LIKE ?"
            params.append(f"%{species_name}%")
        if species_id:
            query += " AND species_id = ?"
            params.append(species_id)
        if quality:
            query += " AND quality_grade = ?"
            params.append(quality)
        if has_photo:
            query += " AND photo_count > 0"
        
        query += " ORDER BY observed_on DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM observations")
        total = cursor.fetchone()[0]
    
    return {
        "observations": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ============== Images ==============

@app.get("/api/mindex/images")
async def list_images(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    species_id: Optional[str] = None,
    source: Optional[str] = None,
    is_training: Optional[bool] = None,
    min_quality: Optional[float] = None,
):
    """List images with pagination."""
    if not manager:
        return {"images": [], "total": 0, "page": page}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM images WHERE 1=1"
        params = []
        
        if species_id:
            query += " AND species_id = ?"
            params.append(species_id)
        if source:
            query += " AND source = ?"
            params.append(source)
        if is_training is not None:
            query += " AND is_training_data = ?"
            params.append(1 if is_training else 0)
        if min_quality:
            query += " AND quality_score >= ?"
            params.append(min_quality)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM images")
        total = cursor.fetchone()[0]
    
    return {
        "images": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@app.post("/api/mindex/images")
async def add_image(image: ImageRecord):
    """Add an image record."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO images (species_id, url, source, license, attribution, 
                               quality_score, is_training_data, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            image.species_id,
            image.url,
            image.source,
            image.license,
            image.attribution,
            image.quality_score,
            1 if image.is_training_data else 0,
            ",".join(image.tags) if image.tags else None,
            datetime.now().isoformat(),
        ))
        conn.commit()
        image_id = cursor.lastrowid
    
    return {"id": image_id, "status": "created"}


# ============== Genetic Data ==============

@app.get("/api/mindex/genetics")
async def list_genetic_records(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    species_id: Optional[str] = None,
    source: Optional[str] = None,
    sequence_type: Optional[str] = None,
):
    """List genetic records with pagination."""
    if not manager:
        return {"records": [], "total": 0, "page": page}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM genetic_records WHERE 1=1"
        params = []
        
        if species_id:
            query += " AND species_id = ?"
            params.append(species_id)
        if source:
            query += " AND source = ?"
            params.append(source)
        if sequence_type:
            query += " AND sequence_type = ?"
            params.append(sequence_type)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM genetic_records")
        total = cursor.fetchone()[0]
    
    return {
        "records": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# Legacy endpoint
@app.get("/api/mindex/compounds")
async def get_compounds(
    species: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Get compound/genomic data (legacy endpoint)."""
    return await list_genetic_records(species_id=species, per_page=limit)


# ============== ETL/Sync Endpoints ==============

@app.get("/api/mindex/etl-status")
async def get_etl_status():
    """Get current ETL (scraping) status."""
    if not manager:
        return {
            "status": "disabled",
            "message": "Scrapers not available",
            "available_sources": [],
        }
    
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
            "MushroomWorld",
        ],
    }


@app.post("/api/mindex/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger a manual data sync from all or specified sources."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    sources = request.sources or [
        "iNaturalist", "GBIF", "MycoBank", "FungiDB", "GenBank"
    ]
    limit = request.limit or 1000
    
    async def run_sync():
        for source in sources:
            try:
                await manager.sync_source(source, limit=limit)
                logger.info(f"Completed sync from {source}")
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
    
    valid_sources = [
        "iNaturalist", "GBIF", "MycoBank", "FungiDB", "GenBank", "MushroomWorld"
    ]
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


# ============== Telemetry Ingestion ==============

@app.post("/api/mindex/telemetry")
@app.post("/telemetry/device")
async def ingest_telemetry(request: TelemetryRequest):
    """Ingest telemetry data from devices (MycoBrain, sensors, etc.)."""
    timestamp = request.timestamp or datetime.now().isoformat()
    
    if manager:
        with manager.db.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure telemetry table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    device_id TEXT,
                    timestamp TEXT NOT NULL,
                    data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO telemetry (source, device_id, timestamp, data, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                request.source,
                request.device_id,
                timestamp,
                json.dumps(request.data) if isinstance(request.data, dict) else str(request.data),
                datetime.now().isoformat(),
            ))
            conn.commit()
    
    return {
        "status": "received",
        "source": request.source,
        "device_id": request.device_id,
        "timestamp": timestamp,
    }


# ============== Device Registration ==============

class DeviceRegistrationRequest(BaseModel):
    device_id: str
    device_type: str = "mycobrain"
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    location: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None


@app.post("/api/mindex/devices/register")
async def register_device(request: DeviceRegistrationRequest):
    """Register a MycoBrain or other device with MINDEX."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Ensure devices table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                device_type TEXT NOT NULL,
                serial_number TEXT,
                firmware_version TEXT,
                location_lat REAL,
                location_lon REAL,
                metadata TEXT,
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # Insert or update device
        cursor.execute("""
            INSERT OR REPLACE INTO devices 
            (device_id, device_type, serial_number, firmware_version, 
             location_lat, location_lon, metadata, last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.device_id,
            request.device_type,
            request.serial_number,
            request.firmware_version,
            request.location.get("lat") if request.location else None,
            request.location.get("lon") if request.location else None,
            json.dumps(request.metadata) if request.metadata else None,
            datetime.now().isoformat(),
            "active",
        ))
        conn.commit()
    
    return {
        "status": "registered",
        "device_id": request.device_id,
        "device_type": request.device_type,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/mindex/devices")
async def list_devices(
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List registered devices."""
    if not manager:
        return {"devices": [], "count": 0}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Ensure devices table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                device_type TEXT NOT NULL,
                serial_number TEXT,
                firmware_version TEXT,
                location_lat REAL,
                location_lon REAL,
                metadata TEXT,
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        
        query = "SELECT * FROM devices WHERE 1=1"
        params = []
        
        if device_type:
            query += " AND device_type = ?"
            params.append(device_type)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY last_seen DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        devices = []
        for row in rows:
            devices.append({
                "device_id": row["device_id"],
                "device_type": row["device_type"],
                "serial_number": row["serial_number"],
                "firmware_version": row["firmware_version"],
                "location": {
                    "lat": row["location_lat"],
                    "lon": row["location_lon"],
                } if row["location_lat"] and row["location_lon"] else None,
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "registered_at": row["registered_at"],
                "last_seen": row["last_seen"],
                "status": row["status"],
            })
    
    return {
        "devices": devices,
        "count": len(devices),
    }


# ============== Species Master List Generation ==============

@app.post("/api/mindex/generate-master-list")
async def generate_master_list(
    background_tasks: BackgroundTasks,
    limit: int = Query(100000, description="Maximum species to process"),
):
    """
    Generate or update the master species list with unique MINDEX IDs.
    This aggregates species from all sources and assigns unique identifiers.
    """
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    async def build_master_list():
        logger.info("Starting master species list generation...")
        
        with manager.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create master species table if needed
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS species_master (
                    mindex_id TEXT PRIMARY KEY,
                    scientific_name TEXT NOT NULL,
                    canonical_name TEXT,
                    common_names TEXT,
                    kingdom TEXT DEFAULT 'Fungi',
                    phylum TEXT,
                    class_name TEXT,
                    order_name TEXT,
                    family TEXT,
                    genus TEXT,
                    species_epithet TEXT,
                    subspecies TEXT,
                    author TEXT,
                    year_described INTEGER,
                    type_specimen TEXT,
                    sources TEXT,
                    external_ids TEXT,
                    image_count INTEGER DEFAULT 0,
                    observation_count INTEGER DEFAULT 0,
                    genetic_record_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    UNIQUE(scientific_name, author)
                )
            """)
            
            # Aggregate from all source tables
            cursor.execute("""
                INSERT OR REPLACE INTO species_master 
                (mindex_id, scientific_name, kingdom, phylum, class_name, 
                 order_name, family, genus, sources, created_at, updated_at)
                SELECT 
                    'MX-' || printf('%08d', ROW_NUMBER() OVER (ORDER BY scientific_name)),
                    scientific_name,
                    COALESCE(kingdom, 'Fungi'),
                    phylum,
                    class_name,
                    order_name,
                    family,
                    genus,
                    GROUP_CONCAT(DISTINCT source),
                    MIN(created_at),
                    datetime('now')
                FROM species
                GROUP BY scientific_name
                LIMIT ?
            """, (limit,))
            
            conn.commit()
            
            # Get count
            cursor.execute("SELECT COUNT(*) FROM species_master")
            count = cursor.fetchone()[0]
            
            logger.info(f"Master species list generated with {count} entries")
    
    background_tasks.add_task(build_master_list)
    
    return {
        "status": "started",
        "message": "Master species list generation started",
        "limit": limit,
    }


@app.get("/api/mindex/master-list")
async def get_master_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
):
    """Get the master species list with unique MINDEX IDs."""
    if not manager:
        return {"species": [], "total": 0, "page": page}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if master list exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='species_master'
        """)
        if not cursor.fetchone():
            return {
                "species": [],
                "total": 0,
                "page": page,
                "message": "Master list not generated yet. Call POST /api/mindex/generate-master-list first."
            }
        
        query = "SELECT * FROM species_master WHERE 1=1"
        params = []
        
        if search:
            query += " AND (scientific_name LIKE ? OR common_names LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        query += " ORDER BY scientific_name LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM species_master")
        total = cursor.fetchone()[0]
    
    return {
        "species": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


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
- Telemetry ingestion for device data
- Image tagging and training data management
"""

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from mycosoft_mas.mindex import MINDEXManager, MINDEXDatabase
    from mycosoft_mas.mindex.scrapers import (
        INaturalistScraper,
        GBIFScraper,
        MycoBankScraper,
        FungiDBScraper,
        GenBankScraper,
    )
    HAS_SCRAPERS = True
except ImportError:
    HAS_SCRAPERS = False
    MINDEXManager = None
    MINDEXDatabase = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
NAS_DATA_PATH = Path(os.getenv("MINDEX_NAS_PATH", "/mnt/nas/mindex"))
LOCAL_DATA_PATH = Path(os.getenv("MINDEX_LOCAL_PATH", "/app/data"))
DB_PATH = LOCAL_DATA_PATH / "mindex.db"
SYNC_INTERVAL_HOURS = int(os.getenv("MINDEX_SYNC_INTERVAL", "24"))
MAX_RECORDS_PER_SYNC = int(os.getenv("MINDEX_MAX_RECORDS", "50000"))

# Global manager instance
manager: Optional["MINDEXManager"] = None
startup_time: datetime = datetime.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global manager, startup_time
    startup_time = datetime.now()
    
    # Ensure data directories exist
    LOCAL_DATA_PATH.mkdir(parents=True, exist_ok=True)
    NAS_DATA_PATH.mkdir(parents=True, exist_ok=True)
    
    if HAS_SCRAPERS and MINDEXManager:
        # Initialize manager with local path (syncs to NAS periodically)
        manager = MINDEXManager(db_path=DB_PATH)
        logger.info(f"MINDEX initialized with database at {DB_PATH}")
        
        # Start continuous sync if enabled
        if os.getenv("MINDEX_AUTO_SYNC", "true").lower() == "true":
            manager.start_continuous_sync(
                interval_hours=SYNC_INTERVAL_HOURS,
                limit_per_source=MAX_RECORDS_PER_SYNC,
            )
            logger.info(f"Started continuous sync every {SYNC_INTERVAL_HOURS} hours")
    else:
        logger.warning("MINDEX scrapers not available - running in limited mode")
    
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
    - Mushroom.world (additional species data)
    
    Provides instant local access to all fungal data for MYCOSOFT systems.
    Powers the Species Explorer, Ancestry tools, and AI learning systems.
    """,
    version="2.1.0",
    lifespan=lifespan,
)

# CORS for web dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    uptime_seconds: int
    db_path: str
    db_size_mb: float


class StatsResponse(BaseModel):
    total_species: int
    total_observations: int
    total_images: int
    total_genetic_records: int
    species_by_source: dict
    species_by_kingdom: dict
    top_genera: list
    db_size_mb: float
    last_sync: Optional[str] = None


class SyncRequest(BaseModel):
    sources: Optional[List[str]] = None
    limit: Optional[int] = None


class SyncResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None


class TelemetryRequest(BaseModel):
    source: str
    device_id: Optional[str] = None
    timestamp: Optional[str] = None
    data: dict


class SpeciesRecord(BaseModel):
    mindex_id: Optional[str] = None
    scientific_name: str
    common_names: Optional[List[str]] = None
    kingdom: str = "Fungi"
    phylum: Optional[str] = None
    class_name: Optional[str] = None
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    species: Optional[str] = None
    subspecies: Optional[str] = None
    author: Optional[str] = None
    year_described: Optional[int] = None
    type_specimen: Optional[str] = None
    sources: Optional[List[str]] = None
    external_ids: Optional[dict] = None


class ImageRecord(BaseModel):
    species_id: str
    url: str
    source: str
    license: Optional[str] = None
    attribution: Optional[str] = None
    quality_score: Optional[float] = None
    is_training_data: bool = False
    tags: Optional[List[str]] = None


# ============== Health Endpoints ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health."""
    db_exists = DB_PATH.exists()
    db_size = DB_PATH.stat().st_size / (1024 * 1024) if db_exists else 0
    uptime = (datetime.now() - startup_time).total_seconds()
    
    etl_status = "disabled"
    if manager:
        etl_status = "running" if getattr(manager, '_running', False) else "idle"
    
    return HealthResponse(
        status="healthy" if db_exists else "degraded",
        api=True,
        database=db_exists,
        etl=etl_status,
        version="2.1.0",
        uptime_seconds=int(uptime),
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
        # Return mock stats when manager not available
        return StatsResponse(
            total_species=0,
            total_observations=0,
            total_images=0,
            total_genetic_records=0,
            species_by_source={},
            species_by_kingdom={},
            top_genera=[],
            db_size_mb=0,
        )
    
    stats = manager.get_stats()
    
    return StatsResponse(
        total_species=stats.get("total_species", 0),
        total_observations=stats.get("total_observations", 0),
        total_images=stats.get("total_images", 0),
        total_genetic_records=stats.get("total_genetic_records", 0),
        species_by_source=stats.get("species_by_source", {}),
        species_by_kingdom=stats.get("species_by_kingdom", {"Fungi": 0}),
        top_genera=stats.get("top_genera", []),
        db_size_mb=stats.get("db_size_mb", 0),
    )


# ============== Search Endpoints ==============

@app.get("/api/mindex/search")
async def search_species(
    q: str = Query(..., min_length=2, description="Search query"),
    sources: Optional[str] = Query(None, description="Comma-separated sources"),
    kingdom: Optional[str] = Query(None, description="Filter by kingdom (Fungi, etc.)"),
    limit: int = Query(50, ge=1, le=500),
):
    """Search for species across all sources."""
    if not manager:
        return {"results": [], "total": 0, "query": q}
    
    source_list = sources.split(",") if sources else None
    results = await manager.search(
        q, 
        sources=source_list, 
        kingdom=kingdom,
        limit=limit
    )
    
    return results


@app.get("/api/mindex/species")
async def list_species(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    kingdom: Optional[str] = Query("Fungi", description="Kingdom filter"),
    phylum: Optional[str] = None,
    family: Optional[str] = None,
    genus: Optional[str] = None,
    has_images: Optional[bool] = None,
    has_genetics: Optional[bool] = None,
):
    """List species with pagination and filters."""
    if not manager:
        return {"data": [], "total": 0, "page": page, "per_page": per_page}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM species WHERE 1=1"
        params = []
        
        if kingdom:
            query += " AND kingdom = ?"
            params.append(kingdom)
        if phylum:
            query += " AND phylum = ?"
            params.append(phylum)
        if family:
            query += " AND family = ?"
            params.append(family)
        if genus:
            query += " AND genus = ?"
            params.append(genus)
        if has_images:
            query += " AND image_count > 0"
        if has_genetics:
            query += " AND genetic_record_count > 0"
        
        query += " ORDER BY scientific_name LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM species WHERE 1=1"
        count_params = []
        if kingdom:
            count_query += " AND kingdom = ?"
            count_params.append(kingdom)
        if phylum:
            count_query += " AND phylum = ?"
            count_params.append(phylum)
        if family:
            count_query += " AND family = ?"
            count_params.append(family)
        if genus:
            count_query += " AND genus = ?"
            count_params.append(genus)
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
    
    return {
        "data": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@app.get("/api/mindex/species/{species_id}")
async def get_species(species_id: str):
    """Get detailed information about a specific species."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Try by mindex_id first, then by numeric id
        cursor.execute(
            "SELECT * FROM species WHERE mindex_id = ? OR id = ?", 
            (species_id, species_id)
        )
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Species not found")
        
        species = dict(row)
        
        # Get associated images
        cursor.execute(
            "SELECT * FROM images WHERE species_id = ? LIMIT 50",
            (species.get("id") or species.get("mindex_id"),)
        )
        species["images"] = [dict(r) for r in cursor.fetchall()]
        
        # Get genetic data
        cursor.execute(
            "SELECT * FROM genetic_records WHERE species_id = ? LIMIT 20",
            (species.get("id") or species.get("mindex_id"),)
        )
        species["genetic_records"] = [dict(r) for r in cursor.fetchall()]
        
        # Get taxonomy hierarchy
        cursor.execute("""
            SELECT * FROM taxonomy 
            WHERE species_id = ? 
            ORDER BY rank_order
        """, (species.get("id") or species.get("mindex_id"),))
        species["taxonomy"] = [dict(r) for r in cursor.fetchall()]
        
        return species


# ============== Legacy Taxa Endpoints (for backward compatibility) ==============

@app.get("/api/mindex/taxa")
async def list_taxa(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    family: Optional[str] = None,
    genus: Optional[str] = None,
):
    """List taxa with pagination (legacy endpoint)."""
    return await list_species(page=page, per_page=per_page, family=family, genus=genus)


@app.get("/api/mindex/taxa/{taxon_id}")
async def get_taxon(taxon_id: int):
    """Get detailed information about a specific taxon (legacy endpoint)."""
    return await get_species(str(taxon_id))


# ============== Observations ==============

@app.get("/api/mindex/observations")
async def list_observations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    species_name: Optional[str] = None,
    species_id: Optional[str] = None,
    quality: Optional[str] = None,
    has_photo: Optional[bool] = None,
):
    """List observations with pagination."""
    if not manager:
        return {"observations": [], "total": 0, "page": page, "per_page": per_page}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM observations WHERE 1=1"
        params = []
        
        if species_name:
            query += " AND scientific_name LIKE ?"
            params.append(f"%{species_name}%")
        if species_id:
            query += " AND species_id = ?"
            params.append(species_id)
        if quality:
            query += " AND quality_grade = ?"
            params.append(quality)
        if has_photo:
            query += " AND photo_count > 0"
        
        query += " ORDER BY observed_on DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM observations")
        total = cursor.fetchone()[0]
    
    return {
        "observations": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ============== Images ==============

@app.get("/api/mindex/images")
async def list_images(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    species_id: Optional[str] = None,
    source: Optional[str] = None,
    is_training: Optional[bool] = None,
    min_quality: Optional[float] = None,
):
    """List images with pagination."""
    if not manager:
        return {"images": [], "total": 0, "page": page}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM images WHERE 1=1"
        params = []
        
        if species_id:
            query += " AND species_id = ?"
            params.append(species_id)
        if source:
            query += " AND source = ?"
            params.append(source)
        if is_training is not None:
            query += " AND is_training_data = ?"
            params.append(1 if is_training else 0)
        if min_quality:
            query += " AND quality_score >= ?"
            params.append(min_quality)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM images")
        total = cursor.fetchone()[0]
    
    return {
        "images": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@app.post("/api/mindex/images")
async def add_image(image: ImageRecord):
    """Add an image record."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO images (species_id, url, source, license, attribution, 
                               quality_score, is_training_data, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            image.species_id,
            image.url,
            image.source,
            image.license,
            image.attribution,
            image.quality_score,
            1 if image.is_training_data else 0,
            ",".join(image.tags) if image.tags else None,
            datetime.now().isoformat(),
        ))
        conn.commit()
        image_id = cursor.lastrowid
    
    return {"id": image_id, "status": "created"}


# ============== Genetic Data ==============

@app.get("/api/mindex/genetics")
async def list_genetic_records(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    species_id: Optional[str] = None,
    source: Optional[str] = None,
    sequence_type: Optional[str] = None,
):
    """List genetic records with pagination."""
    if not manager:
        return {"records": [], "total": 0, "page": page}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM genetic_records WHERE 1=1"
        params = []
        
        if species_id:
            query += " AND species_id = ?"
            params.append(species_id)
        if source:
            query += " AND source = ?"
            params.append(source)
        if sequence_type:
            query += " AND sequence_type = ?"
            params.append(sequence_type)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM genetic_records")
        total = cursor.fetchone()[0]
    
    return {
        "records": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# Legacy endpoint
@app.get("/api/mindex/compounds")
async def get_compounds(
    species: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Get compound/genomic data (legacy endpoint)."""
    return await list_genetic_records(species_id=species, per_page=limit)


# ============== ETL/Sync Endpoints ==============

@app.get("/api/mindex/etl-status")
async def get_etl_status():
    """Get current ETL (scraping) status."""
    if not manager:
        return {
            "status": "disabled",
            "message": "Scrapers not available",
            "available_sources": [],
        }
    
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
            "MushroomWorld",
        ],
    }


@app.post("/api/mindex/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger a manual data sync from all or specified sources."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    sources = request.sources or [
        "iNaturalist", "GBIF", "MycoBank", "FungiDB", "GenBank"
    ]
    limit = request.limit or 1000
    
    async def run_sync():
        for source in sources:
            try:
                await manager.sync_source(source, limit=limit)
                logger.info(f"Completed sync from {source}")
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
    
    valid_sources = [
        "iNaturalist", "GBIF", "MycoBank", "FungiDB", "GenBank", "MushroomWorld"
    ]
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


# ============== Telemetry Ingestion ==============

@app.post("/api/mindex/telemetry")
@app.post("/telemetry/device")
async def ingest_telemetry(request: TelemetryRequest):
    """Ingest telemetry data from devices (MycoBrain, sensors, etc.)."""
    timestamp = request.timestamp or datetime.now().isoformat()
    
    if manager:
        with manager.db.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure telemetry table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    device_id TEXT,
                    timestamp TEXT NOT NULL,
                    data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO telemetry (source, device_id, timestamp, data, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                request.source,
                request.device_id,
                timestamp,
                json.dumps(request.data) if isinstance(request.data, dict) else str(request.data),
                datetime.now().isoformat(),
            ))
            conn.commit()
    
    return {
        "status": "received",
        "source": request.source,
        "device_id": request.device_id,
        "timestamp": timestamp,
    }


# ============== Device Registration ==============

class DeviceRegistrationRequest(BaseModel):
    device_id: str
    device_type: str = "mycobrain"
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    location: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None


@app.post("/api/mindex/devices/register")
async def register_device(request: DeviceRegistrationRequest):
    """Register a MycoBrain or other device with MINDEX."""
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Ensure devices table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                device_type TEXT NOT NULL,
                serial_number TEXT,
                firmware_version TEXT,
                location_lat REAL,
                location_lon REAL,
                metadata TEXT,
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # Insert or update device
        cursor.execute("""
            INSERT OR REPLACE INTO devices 
            (device_id, device_type, serial_number, firmware_version, 
             location_lat, location_lon, metadata, last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.device_id,
            request.device_type,
            request.serial_number,
            request.firmware_version,
            request.location.get("lat") if request.location else None,
            request.location.get("lon") if request.location else None,
            json.dumps(request.metadata) if request.metadata else None,
            datetime.now().isoformat(),
            "active",
        ))
        conn.commit()
    
    return {
        "status": "registered",
        "device_id": request.device_id,
        "device_type": request.device_type,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/mindex/devices")
async def list_devices(
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List registered devices."""
    if not manager:
        return {"devices": [], "count": 0}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Ensure devices table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                device_type TEXT NOT NULL,
                serial_number TEXT,
                firmware_version TEXT,
                location_lat REAL,
                location_lon REAL,
                metadata TEXT,
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        
        query = "SELECT * FROM devices WHERE 1=1"
        params = []
        
        if device_type:
            query += " AND device_type = ?"
            params.append(device_type)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY last_seen DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        devices = []
        for row in rows:
            devices.append({
                "device_id": row["device_id"],
                "device_type": row["device_type"],
                "serial_number": row["serial_number"],
                "firmware_version": row["firmware_version"],
                "location": {
                    "lat": row["location_lat"],
                    "lon": row["location_lon"],
                } if row["location_lat"] and row["location_lon"] else None,
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "registered_at": row["registered_at"],
                "last_seen": row["last_seen"],
                "status": row["status"],
            })
    
    return {
        "devices": devices,
        "count": len(devices),
    }


# ============== Species Master List Generation ==============

@app.post("/api/mindex/generate-master-list")
async def generate_master_list(
    background_tasks: BackgroundTasks,
    limit: int = Query(100000, description="Maximum species to process"),
):
    """
    Generate or update the master species list with unique MINDEX IDs.
    This aggregates species from all sources and assigns unique identifiers.
    """
    if not manager:
        raise HTTPException(status_code=503, detail="MINDEX not initialized")
    
    async def build_master_list():
        logger.info("Starting master species list generation...")
        
        with manager.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create master species table if needed
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS species_master (
                    mindex_id TEXT PRIMARY KEY,
                    scientific_name TEXT NOT NULL,
                    canonical_name TEXT,
                    common_names TEXT,
                    kingdom TEXT DEFAULT 'Fungi',
                    phylum TEXT,
                    class_name TEXT,
                    order_name TEXT,
                    family TEXT,
                    genus TEXT,
                    species_epithet TEXT,
                    subspecies TEXT,
                    author TEXT,
                    year_described INTEGER,
                    type_specimen TEXT,
                    sources TEXT,
                    external_ids TEXT,
                    image_count INTEGER DEFAULT 0,
                    observation_count INTEGER DEFAULT 0,
                    genetic_record_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    UNIQUE(scientific_name, author)
                )
            """)
            
            # Aggregate from all source tables
            cursor.execute("""
                INSERT OR REPLACE INTO species_master 
                (mindex_id, scientific_name, kingdom, phylum, class_name, 
                 order_name, family, genus, sources, created_at, updated_at)
                SELECT 
                    'MX-' || printf('%08d', ROW_NUMBER() OVER (ORDER BY scientific_name)),
                    scientific_name,
                    COALESCE(kingdom, 'Fungi'),
                    phylum,
                    class_name,
                    order_name,
                    family,
                    genus,
                    GROUP_CONCAT(DISTINCT source),
                    MIN(created_at),
                    datetime('now')
                FROM species
                GROUP BY scientific_name
                LIMIT ?
            """, (limit,))
            
            conn.commit()
            
            # Get count
            cursor.execute("SELECT COUNT(*) FROM species_master")
            count = cursor.fetchone()[0]
            
            logger.info(f"Master species list generated with {count} entries")
    
    background_tasks.add_task(build_master_list)
    
    return {
        "status": "started",
        "message": "Master species list generation started",
        "limit": limit,
    }


@app.get("/api/mindex/master-list")
async def get_master_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
):
    """Get the master species list with unique MINDEX IDs."""
    if not manager:
        return {"species": [], "total": 0, "page": page}
    
    with manager.db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if master list exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='species_master'
        """)
        if not cursor.fetchone():
            return {
                "species": [],
                "total": 0,
                "page": page,
                "message": "Master list not generated yet. Call POST /api/mindex/generate-master-list first."
            }
        
        query = "SELECT * FROM species_master WHERE 1=1"
        params = []
        
        if search:
            query += " AND (scientific_name LIKE ? OR common_names LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        query += " ORDER BY scientific_name LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM species_master")
        total = cursor.fetchone()[0]
    
    return {
        "species": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


# ============== Run Server ==============

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("MINDEX_PORT", "8000"))
    host = os.getenv("MINDEX_HOST", "0.0.0.0")
    
    logger.info(f"Starting MINDEX API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

