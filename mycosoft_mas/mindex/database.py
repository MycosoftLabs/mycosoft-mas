"""
MINDEX Database Module

SQLite database for structured fungal data with optional ChromaDB 
integration for semantic search capabilities.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "mindex.db"


class MINDEXDatabase:
    """SQLite database for MINDEX fungal knowledge storage."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection with context management."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Species table - core taxonomic data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS species (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    scientific_name TEXT NOT NULL,
                    canonical_name TEXT,
                    common_name TEXT,
                    author TEXT,
                    year TEXT,
                    rank TEXT,
                    status TEXT,
                    kingdom TEXT DEFAULT 'Fungi',
                    phylum TEXT,
                    class TEXT,
                    order_name TEXT,
                    family TEXT,
                    genus TEXT,
                    species_epithet TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source, source_id)
                )
            """)
            
            # Observations table - occurrence/sighting data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    species_id INTEGER,
                    scientific_name TEXT,
                    common_name TEXT,
                    observer TEXT,
                    observed_on TEXT,
                    latitude REAL,
                    longitude REAL,
                    place_guess TEXT,
                    country TEXT,
                    quality_grade TEXT,
                    photos TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source, source_id),
                    FOREIGN KEY (species_id) REFERENCES species(id)
                )
            """)
            
            # Genomic data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS genomic_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    species_id INTEGER,
                    organism_name TEXT,
                    strain TEXT,
                    gene_id TEXT,
                    gene_name TEXT,
                    product TEXT,
                    sequence TEXT,
                    genome_size TEXT,
                    chromosome TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source, source_id),
                    FOREIGN KEY (species_id) REFERENCES species(id)
                )
            """)
            
            # Synonyms table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS synonyms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    species_id INTEGER NOT NULL,
                    synonym_name TEXT NOT NULL,
                    synonym_author TEXT,
                    synonym_year TEXT,
                    synonym_type TEXT,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (species_id) REFERENCES species(id)
                )
            """)
            
            # Scrape history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrape_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    records_count INTEGER,
                    errors_count INTEGER,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT,
                    metadata TEXT
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_species_scientific_name ON species(scientific_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_species_genus ON species(genus)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_species_family ON species(family)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_scientific_name ON observations(scientific_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_location ON observations(latitude, longitude)")
            
            # Full-text search table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS species_fts USING fts5(
                    scientific_name,
                    canonical_name,
                    common_name,
                    genus,
                    family,
                    content='species',
                    content_rowid='id'
                )
            """)
            
            logger.info(f"MINDEX database initialized at {self.db_path}")
    
    def insert_species(self, data: dict[str, Any]) -> int:
        """Insert or update a species record."""
        taxonomy = data.get("taxonomy", {})
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO species (
                    source, source_id, scientific_name, canonical_name, common_name,
                    author, year, rank, status, kingdom, phylum, class, order_name,
                    family, genus, species_epithet, raw_data, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("source", ""),
                data.get("source_id", ""),
                data.get("scientific_name", ""),
                data.get("canonical_name", ""),
                data.get("common_name", ""),
                data.get("author", ""),
                data.get("year", ""),
                data.get("rank", ""),
                data.get("status", ""),
                taxonomy.get("kingdom", "Fungi"),
                taxonomy.get("phylum", ""),
                taxonomy.get("class", ""),
                taxonomy.get("order", ""),
                taxonomy.get("family", ""),
                taxonomy.get("genus", ""),
                taxonomy.get("species", ""),
                json.dumps(data.get("raw_data", {})),
                datetime.utcnow().isoformat(),
            ))
            
            species_id = cursor.lastrowid
            
            # Update FTS index
            cursor.execute("""
                INSERT OR REPLACE INTO species_fts (rowid, scientific_name, canonical_name, common_name, genus, family)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                species_id,
                data.get("scientific_name", ""),
                data.get("canonical_name", ""),
                data.get("common_name", ""),
                taxonomy.get("genus", ""),
                taxonomy.get("family", ""),
            ))
            
            return species_id
    
    def insert_observation(self, data: dict[str, Any]) -> int:
        """Insert an observation record."""
        location = data.get("location", {})
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO observations (
                    source, source_id, scientific_name, common_name, observer,
                    observed_on, latitude, longitude, place_guess, country,
                    quality_grade, photos, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("source", ""),
                data.get("source_id", ""),
                data.get("scientific_name", ""),
                data.get("common_name", ""),
                data.get("observer", ""),
                data.get("observed_on", ""),
                location.get("latitude"),
                location.get("longitude"),
                location.get("place_guess", ""),
                location.get("country", ""),
                data.get("quality_grade", ""),
                json.dumps(data.get("photos", [])),
                json.dumps(data),
            ))
            
            return cursor.lastrowid
    
    def search_species(
        self,
        query: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Full-text search for species."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Use FTS for search
            cursor.execute("""
                SELECT s.* FROM species s
                JOIN species_fts fts ON s.id = fts.rowid
                WHERE species_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            return results
    
    def get_species_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """Get species by exact scientific name."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM species WHERE scientific_name = ? LIMIT 1",
                (name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_species_count(self) -> int:
        """Get total number of species in database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM species")
            return cursor.fetchone()[0]
    
    def get_observations_count(self) -> int:
        """Get total number of observations in database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM observations")
            return cursor.fetchone()[0]
    
    def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Species count by source
            cursor.execute("""
                SELECT source, COUNT(*) as count 
                FROM species 
                GROUP BY source
            """)
            stats["species_by_source"] = {row["source"]: row["count"] for row in cursor.fetchall()}
            
            # Observations count
            cursor.execute("SELECT COUNT(*) FROM observations")
            stats["total_observations"] = cursor.fetchone()[0]
            
            # Total species
            cursor.execute("SELECT COUNT(*) FROM species")
            stats["total_species"] = cursor.fetchone()[0]
            
            # Top genera
            cursor.execute("""
                SELECT genus, COUNT(*) as count 
                FROM species 
                WHERE genus != ''
                GROUP BY genus 
                ORDER BY count DESC 
                LIMIT 10
            """)
            stats["top_genera"] = [(row["genus"], row["count"]) for row in cursor.fetchall()]
            
            # Database size
            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
            
            return stats
    
    def log_scrape(
        self,
        source: str,
        data_type: str,
        records_count: int,
        errors_count: int,
        status: str,
        metadata: Optional[dict] = None,
    ):
        """Log a scrape operation."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scrape_history (
                    source, data_type, records_count, errors_count, 
                    completed_at, status, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                source,
                data_type,
                records_count,
                errors_count,
                datetime.utcnow().isoformat(),
                status,
                json.dumps(metadata) if metadata else None,
            ))
