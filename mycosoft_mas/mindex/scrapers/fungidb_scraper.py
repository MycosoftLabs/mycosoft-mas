"""
FungiDB Scraper for MINDEX

Fetches genomic and molecular data from FungiDB.
https://fungidb.org/
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp

logger = logging.getLogger(__name__)


class FungiDBScraper:
    """
    Scraper for FungiDB genomic data.
    
    Fetches:
    - Organism/genome information
    - Gene annotations
    - Sequence data
    - Pathway information
    """
    
    BASE_URL = "https://fungidb.org/fungidb/service"
    
    def __init__(self, db=None):
        self.db = db
    
    async def fetch_organisms(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetch list of organisms from FungiDB.
        """
        organisms = []
        
        async with aiohttp.ClientSession() as session:
            try:
                # Get organism list
                url = f"{self.BASE_URL}/record-types/organism/searches/GenomeDataTypes/reports/standard"
                
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"FungiDB API error: {response.status}")
                        return organisms
                    
                    data = await response.json()
                    records = data.get("records", [])
                    
                    for rec in records[:limit]:
                        parsed = self._parse_organism(rec)
                        if parsed:
                            organisms.append(parsed)
                    
                    logger.info(f"Fetched {len(organisms)} organisms from FungiDB")
                    
            except Exception as e:
                logger.error(f"Error fetching from FungiDB: {e}")
        
        return organisms
    
    async def fetch_genes(
        self,
        organism: str = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch gene information from FungiDB.
        """
        genes = []
        
        async with aiohttp.ClientSession() as session:
            try:
                params = {
                    "organism": organism or "*",
                    "limit": limit,
                }
                
                url = f"{self.BASE_URL}/record-types/gene/searches/GenesByTaxon/reports/standard"
                
                async with session.get(url, params=params, timeout=60) as response:
                    if response.status != 200:
                        logger.error(f"FungiDB genes API error: {response.status}")
                        return genes
                    
                    data = await response.json()
                    records = data.get("records", [])
                    
                    for rec in records[:limit]:
                        parsed = self._parse_gene(rec)
                        if parsed:
                            genes.append(parsed)
                    
                    logger.info(f"Fetched {len(genes)} genes from FungiDB")
                    
            except Exception as e:
                logger.error(f"Error fetching genes: {e}")
        
        return genes
    
    async def fetch_genome_sequences(
        self,
        organism: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch genome sequences for an organism.
        """
        sequences = []
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.BASE_URL}/record-types/genomic-sequence/searches/SequencesByTaxon/reports/standard"
                params = {"organism": organism, "limit": limit}
                
                async with session.get(url, params=params, timeout=60) as response:
                    if response.status == 200:
                        data = await response.json()
                        for rec in data.get("records", []):
                            sequences.append({
                                "accession": rec.get("id"),
                                "sequence_type": "genome",
                                "organism_name": organism,
                                "sequence_length": rec.get("attributes", {}).get("length"),
                                "source": "FungiDB",
                            })
                            
            except Exception as e:
                logger.error(f"Error fetching sequences: {e}")
        
        return sequences
    
    def _parse_organism(self, record: Dict) -> Optional[Dict[str, Any]]:
        """Parse organism record."""
        try:
            attrs = record.get("attributes", {})
            
            # Extract taxonomy
            taxonomy = attrs.get("organism_full", "").split()
            genus = taxonomy[0] if len(taxonomy) > 0 else None
            
            return {
                "scientific_name": attrs.get("organism_full"),
                "genus": genus,
                "kingdom": "Fungi",
                "source": "FungiDB",
                "external_ids": {"fungidb": record.get("id")},
                "description": attrs.get("description"),
            }
        except Exception as e:
            logger.error(f"Error parsing organism: {e}")
            return None
    
    def _parse_gene(self, record: Dict) -> Optional[Dict[str, Any]]:
        """Parse gene record for genetic_records table."""
        try:
            attrs = record.get("attributes", {})
            
            return {
                "accession": record.get("id"),
                "sequence_type": "gene",
                "gene_region": attrs.get("gene_type"),
                "organism_name": attrs.get("organism_full"),
                "source": "FungiDB",
                "source_id": record.get("id"),
            }
        except Exception as e:
            logger.error(f"Error parsing gene: {e}")
            return None
    
    async def sync(self, limit: int = 1000) -> Dict[str, int]:
        """
        Full sync from FungiDB.
        """
        stats = {
            "organisms_fetched": 0,
            "organisms_inserted": 0,
            "genes_fetched": 0,
            "genes_inserted": 0,
        }
        
        # Fetch organisms (as species)
        organisms = await self.fetch_organisms(limit=limit)
        stats["organisms_fetched"] = len(organisms)
        
        if self.db:
            for org in organisms:
                try:
                    self.db.insert_species(org)
                    stats["organisms_inserted"] += 1
                except Exception as e:
                    logger.error(f"Error inserting organism: {e}")
        
        # Fetch genes
        genes = await self.fetch_genes(limit=limit)
        stats["genes_fetched"] = len(genes)
        
        if self.db:
            for gene in genes:
                try:
                    self.db.insert_genetic_record(gene)
                    stats["genes_inserted"] += 1
                except Exception as e:
                    logger.error(f"Error inserting gene: {e}")
        
        return stats



























