"""
MINDEX Database Schema

Comprehensive SQLite database for the Mycological Index system.
Stores species, taxonomy, images, genetic data, and observations.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MINDEXDatabase:
    """
    SQLite database manager for MINDEX.
    Stores all fungal knowledge data with proper schema.
    """
    
    SCHEMA_VERSION = "2.1.0"
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database with complete schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Schema version tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            
            # ==================== SPECIES ====================
            # Master species table with unique MINDEX IDs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS species (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mindex_id TEXT UNIQUE,
                    scientific_name TEXT NOT NULL,
                    canonical_name TEXT,
                    common_names TEXT,
                    
                    -- Taxonomy
                    kingdom TEXT DEFAULT 'Fungi',
                    phylum TEXT,
                    class_name TEXT,
                    order_name TEXT,
                    family TEXT,
                    genus TEXT,
                    species_epithet TEXT,
                    subspecies TEXT,
                    variety TEXT,
                    form TEXT,
                    
                    -- Nomenclature
                    author TEXT,
                    year_described INTEGER,
                    basionym TEXT,
                    type_specimen TEXT,
                    nomenclatural_status TEXT,
                    
                    -- Characteristics
                    description TEXT,
                    habitat TEXT,
                    distribution TEXT,
                    edibility TEXT,
                    toxicity TEXT,
                    medicinal_uses TEXT,
                    ecological_role TEXT,
                    
                    -- Data sources
                    source TEXT,
                    sources TEXT,
                    external_ids TEXT,
                    
                    -- Statistics
                    image_count INTEGER DEFAULT 0,
                    observation_count INTEGER DEFAULT 0,
                    genetic_record_count INTEGER DEFAULT 0,
                    
                    -- Metadata
                    created_at TEXT,
                    updated_at TEXT,
                    
                    UNIQUE(scientific_name, author)
                )
            """)
            
            # ==================== TAXONOMY ====================
            # Hierarchical taxonomy for ancestry/phylogeny
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS taxonomy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    species_id TEXT,
                    rank TEXT NOT NULL,
                    rank_order INTEGER,
                    name TEXT NOT NULL,
                    parent_id INTEGER,
                    source TEXT,
                    external_id TEXT,
                    created_at TEXT,
                    FOREIGN KEY (species_id) REFERENCES species(mindex_id)
                )
            """)
            
            # ==================== IMAGES ====================
            # Image library for training and display
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    species_id TEXT,
                    mindex_id TEXT,
                    url TEXT NOT NULL,
                    local_path TEXT,
                    thumbnail_path TEXT,
                    
                    -- Source info
                    source TEXT NOT NULL,
                    source_id TEXT,
                    photographer TEXT,
                    license TEXT,
                    attribution TEXT,
                    
                    -- Quality and training
                    quality_score REAL,
                    is_training_data INTEGER DEFAULT 0,
                    is_validated INTEGER DEFAULT 0,
                    validation_source TEXT,
                    
                    -- Image metadata
                    width INTEGER,
                    height INTEGER,
                    format TEXT,
                    file_size INTEGER,
                    
                    -- Tags for ML
                    tags TEXT,
                    features TEXT,
                    
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (species_id) REFERENCES species(mindex_id)
                )
            """)
            
            # ==================== GENETIC DATA ====================
            # Genomic sequences and molecular data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS genetic_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    species_id TEXT,
                    mindex_id TEXT,
                    
                    -- Sequence info
                    accession TEXT UNIQUE,
                    sequence_type TEXT,
                    gene_region TEXT,
                    sequence TEXT,
                    sequence_length INTEGER,
                    
                    -- Source
                    source TEXT NOT NULL,
                    source_id TEXT,
                    
                    -- Metadata
                    organism_name TEXT,
                    strain TEXT,
                    isolate TEXT,
                    country TEXT,
                    collection_date TEXT,
                    
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (species_id) REFERENCES species(mindex_id)
                )
            """)
            
            # ==================== OBSERVATIONS ====================
            # Field observations from iNaturalist, GBIF, etc.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    species_id TEXT,
                    external_id TEXT UNIQUE,
                    
                    -- Taxonomy
                    scientific_name TEXT,
                    common_name TEXT,
                    
                    -- Location
                    latitude REAL,
                    longitude REAL,
                    location_name TEXT,
                    country TEXT,
                    state_province TEXT,
                    
                    -- Time
                    observed_on TEXT,
                    time_observed TEXT,
                    
                    -- Quality
                    quality_grade TEXT,
                    research_grade INTEGER DEFAULT 0,
                    
                    -- Media
                    photo_count INTEGER DEFAULT 0,
                    photos TEXT,
                    
                    -- Observer
                    observer TEXT,
                    observer_id TEXT,
                    
                    -- Source
                    source TEXT NOT NULL,
                    source_url TEXT,
                    
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (species_id) REFERENCES species(mindex_id)
                )
            """)
            
            # ==================== SCRAPE HISTORY ====================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrape_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    status TEXT,
                    records_fetched INTEGER DEFAULT 0,
                    records_inserted INTEGER DEFAULT 0,
                    records_updated INTEGER DEFAULT 0,
                    errors TEXT,
                    duration_seconds REAL
                )
            """)
            
            # ==================== TELEMETRY ====================
            # Device telemetry data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    device_id TEXT,
                    timestamp TEXT,
                    data TEXT,
                    created_at TEXT
                )
            """)
            
            # ==================== INDEXES ====================
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_species_scientific_name 
                ON species(scientific_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_species_genus 
                ON species(genus)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_species_family 
                ON species(family)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_species_kingdom 
                ON species(kingdom)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_images_species 
                ON images(species_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_genetic_species 
                ON genetic_records(species_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_observations_species 
                ON observations(species_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_taxonomy_species 
                ON taxonomy(species_id)
            """)
            
            # Update schema version
            cursor.execute("""
                INSERT OR REPLACE INTO schema_info (key, value, updated_at)
                VALUES ('version', ?, ?)
            """, (self.SCHEMA_VERSION, datetime.now().isoformat()))
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count species
            cursor.execute("SELECT COUNT(*) FROM species")
            stats["total_species"] = cursor.fetchone()[0]
            
            # Count observations
            cursor.execute("SELECT COUNT(*) FROM observations")
            stats["total_observations"] = cursor.fetchone()[0]
            
            # Count images
            cursor.execute("SELECT COUNT(*) FROM images")
            stats["total_images"] = cursor.fetchone()[0]
            
            # Count genetic records
            cursor.execute("SELECT COUNT(*) FROM genetic_records")
            stats["total_genetic_records"] = cursor.fetchone()[0]
            
            # Species by source
            cursor.execute("""
                SELECT source, COUNT(*) as count 
                FROM species 
                WHERE source IS NOT NULL
                GROUP BY source
            """)
            stats["species_by_source"] = {
                row["source"]: row["count"] 
                for row in cursor.fetchall()
            }
            
            # Species by kingdom
            cursor.execute("""
                SELECT kingdom, COUNT(*) as count 
                FROM species 
                GROUP BY kingdom
            """)
            stats["species_by_kingdom"] = {
                row["kingdom"] or "Unknown": row["count"] 
                for row in cursor.fetchall()
            }
            
            # Top genera
            cursor.execute("""
                SELECT genus, COUNT(*) as count 
                FROM species 
                WHERE genus IS NOT NULL
                GROUP BY genus 
                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid

                ORDER BY count DESC 
                LIMIT 20
            """)
            stats["top_genera"] = [
                {"genus": row["genus"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_species(self, species: Dict[str, Any]) -> int:
        """Insert or update a species record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate MINDEX ID if not present
            if not species.get("mindex_id"):
                cursor.execute("SELECT MAX(id) FROM species")
                max_id = cursor.fetchone()[0] or 0
                species["mindex_id"] = f"MX-{max_id + 1:08d}"
            
            species["updated_at"] = datetime.now().isoformat()
            if not species.get("created_at"):
                species["created_at"] = species["updated_at"]
            
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    mindex_id, scientific_name, canonical_name, common_names,
                    kingdom, phylum, class_name, order_name, family, genus,
                    species_epithet, author, year_described, source, sources,
                    external_ids, description, habitat, edibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                species.get("mindex_id"),
                species.get("scientific_name"),
                species.get("canonical_name"),
                species.get("common_names"),
                species.get("kingdom", "Fungi"),
                species.get("phylum"),
                species.get("class_name"),
                species.get("order_name"),
                species.get("family"),
                species.get("genus"),
                species.get("species_epithet"),
                species.get("author"),
                species.get("year_described"),
                species.get("source"),
                species.get("sources"),
                str(species.get("external_ids")) if species.get("external_ids") else None,
                species.get("description"),
                species.get("habitat"),
                species.get("edibility"),
                species.get("created_at"),
                species.get("updated_at"),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def insert_image(self, image: Dict[str, Any]) -> int:
        """Insert an image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            image["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO images (
                    species_id, url, source, source_id, license, attribution,
                    quality_score, is_training_data, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.get("species_id"),
                image.get("url"),
                image.get("source"),
                image.get("source_id"),
                image.get("license"),
                image.get("attribution"),
                image.get("quality_score"),
                1 if image.get("is_training_data") else 0,
                image.get("tags"),
                image.get("created_at"),
            ))
            conn.commit()
            
            # Update species image count
            if image.get("species_id"):
                cursor.execute("""
                    UPDATE species SET image_count = image_count + 1
                    WHERE mindex_id = ?
                """, (image.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_genetic_record(self, record: Dict[str, Any]) -> int:
        """Insert a genetic record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            record["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO genetic_records (
                    species_id, accession, sequence_type, gene_region,
                    sequence, sequence_length, source, organism_name,
                    strain, country, collection_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("species_id"),
                record.get("accession"),
                record.get("sequence_type"),
                record.get("gene_region"),
                record.get("sequence"),
                record.get("sequence_length"),
                record.get("source"),
                record.get("organism_name"),
                record.get("strain"),
                record.get("country"),
                record.get("collection_date"),
                record.get("created_at"),
            ))
            conn.commit()
            
            # Update species genetic count
            if record.get("species_id"):
                cursor.execute("""
                    UPDATE species SET genetic_record_count = genetic_record_count + 1
                    WHERE mindex_id = ?
                """, (record.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
    
    def insert_observation(self, obs: Dict[str, Any]) -> int:
        """Insert an observation record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            obs["created_at"] = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO observations (
                    species_id, external_id, scientific_name, common_name,
                    latitude, longitude, location_name, country, observed_on,
                    quality_grade, research_grade, photo_count, photos,
                    observer, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.get("species_id"),
                obs.get("external_id"),
                obs.get("scientific_name"),
                obs.get("common_name"),
                obs.get("latitude"),
                obs.get("longitude"),
                obs.get("location_name"),
                obs.get("country"),
                obs.get("observed_on"),
                obs.get("quality_grade"),
                1 if obs.get("research_grade") else 0,
                obs.get("photo_count", 0),
                obs.get("photos"),
                obs.get("observer"),
                obs.get("source"),
                obs.get("source_url"),
                obs.get("created_at"),
            ))
            conn.commit()
            
            # Update species observation count
            if obs.get("species_id"):
                cursor.execute("""
                    UPDATE species SET observation_count = observation_count + 1
                    WHERE mindex_id = ?
                """, (obs.get("species_id"),))
                conn.commit()
            
            return cursor.lastrowid
