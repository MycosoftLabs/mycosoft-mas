"""
NLM Data Pipeline - Data ingestion and processing for NLM training

Handles:
1. Data collection from various sources
2. Preprocessing and normalization
3. Quality filtering
4. Training dataset creation
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Generator
from pathlib import Path
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class NLMDataPipeline:
    """
    Data pipeline for Nature Learning Model training.
    
    Ingests data from:
    - Species databases (taxonomy, descriptions)
    - Research papers and documents
    - Environmental sensor data
    - Genetic databases
    - Geographic/distribution data
    - Mycosoft internal knowledge bases
    """
    
    def __init__(
        self,
        output_dir: str = "/data/nlm_training",
        min_quality_score: float = 0.7,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.min_quality_score = min_quality_score
        
        # Data sources configuration
        self.sources = {
            "mindex": {
                "type": "api",
                "url": "http://localhost:8002/api/v1",
                "categories": ["species", "taxonomy", "genetics"],
            },
            "research_papers": {
                "type": "file",
                "path": "/data/papers",
                "formats": ["pdf", "txt", "json"],
            },
            "sensor_data": {
                "type": "database",
                "connection": "postgresql://mas:maspassword@postgres:5432/mas",
                "tables": ["environmental_readings", "sensor_logs"],
            },
            "knowledge_graph": {
                "type": "qdrant",
                "url": "http://localhost:6345",
                "collections": ["species", "research", "interactions"],
            },
        }
    
    async def ingest_from_mindex(self) -> Generator[Dict[str, Any], None, None]:
        """
        Ingest species and taxonomy data from MINDEX.
        
        Yields:
            Processed data records
        """
        logger.info("Ingesting from MINDEX...")
        
        # This would call the actual MINDEX API
        # For now, yield sample structure
        sample_data = [
            {
                "id": "species_001",
                "name": "Psilocybe cubensis",
                "taxonomy": {
                    "kingdom": "Fungi",
                    "phylum": "Basidiomycota",
                    "class": "Agaricomycetes",
                    "order": "Agaricales",
                    "family": "Hymenogastraceae",
                    "genus": "Psilocybe",
                    "species": "cubensis",
                },
                "description": "A species of psychoactive mushroom...",
                "habitat": "Tropical and subtropical regions",
                "characteristics": {
                    "cap_size": "2-8 cm",
                    "color": "golden to pale brown",
                    "spore_print": "dark purplish-brown",
                },
            }
        ]
        
        for record in sample_data:
            processed = self._process_species_record(record)
            if self._quality_check(processed):
                yield processed
    
    async def ingest_from_sensors(self) -> Generator[Dict[str, Any], None, None]:
        """
        Ingest environmental sensor data.
        
        Yields:
            Processed sensor readings with context
        """
        logger.info("Ingesting sensor data...")
        
        sample_data = [
            {
                "sensor_id": "env_001",
                "timestamp": datetime.now().isoformat(),
                "readings": {
                    "temperature": 23.5,
                    "humidity": 85.2,
                    "co2_ppm": 1200,
                    "light_lux": 150,
                },
                "location": "Growth Chamber A",
                "context": "Oyster mushroom cultivation",
            }
        ]
        
        for record in sample_data:
            processed = self._process_sensor_record(record)
            if self._quality_check(processed):
                yield processed
    
    async def ingest_from_papers(self) -> Generator[Dict[str, Any], None, None]:
        """
        Ingest research papers and documents.
        
        Yields:
            Processed document records
        """
        logger.info("Ingesting research papers...")
        
        papers_path = Path(self.sources["research_papers"]["path"])
        if not papers_path.exists():
            return
        
        for file_path in papers_path.glob("**/*.json"):
            try:
                with open(file_path) as f:
                    paper = json.load(f)
                processed = self._process_paper_record(paper)
                if self._quality_check(processed):
                    yield processed
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")
    
    def _process_species_record(self, record: Dict) -> Dict[str, Any]:
        """Process a species record into training format."""
        taxonomy_str = " > ".join([
            record["taxonomy"].get(level, "Unknown")
            for level in ["kingdom", "phylum", "class", "order", "family", "genus", "species"]
        ])
        
        return {
            "type": "species",
            "id": record["id"],
            "text": f"""Species: {record['name']}
Taxonomy: {taxonomy_str}
Description: {record.get('description', '')}
Habitat: {record.get('habitat', '')}
Characteristics: {json.dumps(record.get('characteristics', {}))}""",
            "metadata": {
                "source": "mindex",
                "category": "species_taxonomy",
                "name": record["name"],
            },
        }
    
    def _process_sensor_record(self, record: Dict) -> Dict[str, Any]:
        """Process a sensor reading into training format."""
        readings_str = ", ".join([
            f"{k}: {v}" for k, v in record.get("readings", {}).items()
        ])
        
        return {
            "type": "sensor",
            "id": record["sensor_id"],
            "text": f"""Environmental Reading
Location: {record.get('location', 'Unknown')}
Context: {record.get('context', '')}
Readings: {readings_str}
Timestamp: {record.get('timestamp', '')}""",
            "metadata": {
                "source": "sensors",
                "category": "environmental_sensors",
                "location": record.get("location"),
            },
        }
    
    def _process_paper_record(self, paper: Dict) -> Dict[str, Any]:
        """Process a research paper into training format."""
        return {
            "type": "paper",
            "id": paper.get("id", "unknown"),
            "text": f"""Research Paper
Title: {paper.get('title', '')}
Authors: {', '.join(paper.get('authors', []))}
Abstract: {paper.get('abstract', '')}
Keywords: {', '.join(paper.get('keywords', []))}""",
            "metadata": {
                "source": "papers",
                "category": "mycology_research",
                "title": paper.get("title"),
            },
        }
    
    def _quality_check(self, record: Dict) -> bool:
        """
        Check if a record meets quality standards.
        
        Returns:
            True if record passes quality checks
        """
        # Check minimum text length
        text = record.get("text", "")
        if len(text) < 50:
            return False
        
        # Check for required fields
        if not record.get("type") or not record.get("metadata"):
            return False
        
        return True
    
    async def run_pipeline(
        self,
        sources: Optional[List[str]] = None,
        output_format: str = "jsonl",
    ) -> Dict[str, int]:
        """
        Run the full data pipeline.
        
        Args:
            sources: Specific sources to process (default: all)
            output_format: Output format (jsonl, parquet, etc.)
            
        Returns:
            Statistics about processed records
        """
        stats = {"total": 0, "by_source": {}}
        
        # Determine sources to process
        source_methods = {
            "mindex": self.ingest_from_mindex,
            "sensors": self.ingest_from_sensors,
            "papers": self.ingest_from_papers,
        }
        
        sources_to_process = sources or list(source_methods.keys())
        
        # Process each source
        for source_name in sources_to_process:
            if source_name not in source_methods:
                continue
            
            output_file = self.output_dir / f"{source_name}_data.jsonl"
            count = 0
            
            with open(output_file, "w") as f:
                async for record in source_methods[source_name]():
                    f.write(json.dumps(record) + "\n")
                    count += 1
            
            stats["by_source"][source_name] = count
            stats["total"] += count
            logger.info(f"Processed {count} records from {source_name}")
        
        return stats

