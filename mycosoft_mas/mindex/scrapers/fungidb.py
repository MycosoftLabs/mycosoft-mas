"""
FungiDB Scraper for MINDEX

Fetches genomic and molecular data from FungiDB (VEuPathDB).
API Documentation: https://fungidb.org/fungidb/

Focus areas:
- Genomic sequences and annotations
- Gene ontology data
- Protein information
- Metabolic pathways
"""

import logging
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from .base import BaseScraper, ScraperConfig, ScraperResult

logger = logging.getLogger(__name__)


class FungiDBScraper(BaseScraper):
    """Scraper for FungiDB genomic data."""
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        # FungiDB has strict rate limits
        if config is None:
            config = ScraperConfig(rate_limit_per_second=0.5)
        super().__init__(config)
    
    @property
    def source_name(self) -> str:
        return "FungiDB"
    
    @property
    def base_url(self) -> str:
        return "https://fungidb.org/fungidb/service"
    
    async def search_species(
        self,
        query: str,
        limit: int = 100,
    ) -> ScraperResult:
        """Search for organisms/species in FungiDB."""
        records = []
        errors = []
        
        try:
            # FungiDB uses a custom search API
            data = await self._request(
                "record-types/organism/searches/GenomeDataTypes/reports/standard",
                method="POST",
                data={
                    "searchConfig": {
                        "parameters": {
                            "organism": query,
                        },
                    },
                    "reportConfig": {
                        "pagination": {"offset": 0, "numRecords": limit},
                    },
                },
            )
            
            if data and "records" in data:
                for record in data["records"]:
                    normalized = self.normalize_record(record)
                    if self.validate_record(normalized):
                        records.append(normalized)
                        
        except Exception as e:
            logger.error(f"Error searching FungiDB: {e}")
            errors.append(str(e))
            # Return empty result on API error - FungiDB API can be complex
        
        return ScraperResult(
            source=self.source_name,
            data_type="species_search",
            records=records,
            total_count=len(records),
            errors=errors,
            metadata={"query": query},
        )
    
    async def get_species_details(
        self,
        species_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get detailed genomic information about a species."""
        try:
            data = await self._request(f"record-types/organism/records/{species_id}")
            if data:
                return self.normalize_record(data)
        except Exception as e:
            logger.error(f"Error getting species {species_id}: {e}")
        return None
    
    async def get_genes(
        self,
        organism: str,
        limit: int = 100,
        offset: int = 0,
    ) -> ScraperResult:
        """Get genes for a specific organism."""
        records = []
        errors = []
        
        try:
            data = await self._request(
                "record-types/gene/searches/GenesByTaxon/reports/standard",
                method="POST",
                data={
                    "searchConfig": {
                        "parameters": {
                            "organism": organism,
                        },
                    },
                    "reportConfig": {
                        "pagination": {"offset": offset, "numRecords": limit},
                    },
                },
            )
            
            if data and "records" in data:
                for record in data["records"]:
                    normalized = self._normalize_gene(record)
                    if self.validate_record(normalized):
                        records.append(normalized)
                        
        except Exception as e:
            logger.error(f"Error fetching genes for {organism}: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            source=self.source_name,
            data_type="genes",
            records=records,
            total_count=data.get("meta", {}).get("totalCount", 0) if data else 0,
            errors=errors,
            metadata={"organism": organism, "offset": offset},
        )
    
    async def fetch_all(
        self,
        limit: Optional[int] = None,
    ) -> AsyncIterator[ScraperResult]:
        """Fetch all available organisms."""
        # Get list of organisms first
        organisms_result = await self._get_organisms()
        
        for organism in organisms_result.records[:limit or 100]:
            org_name = organism.get("organism_name", "")
            if org_name:
                genes_result = await self.get_genes(org_name, limit=100)
                yield genes_result
                
                logger.info(f"Fetched genes for {org_name} from FungiDB")
    
    async def _get_organisms(self) -> ScraperResult:
        """Get list of all organisms in FungiDB."""
        records = []
        errors = []
        
        try:
            data = await self._request("record-types/organism/records")
            if data and "records" in data:
                for record in data["records"]:
                    normalized = self.normalize_record(record)
                    records.append(normalized)
        except Exception as e:
            logger.error(f"Error fetching organisms: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            source=self.source_name,
            data_type="organisms",
            records=records,
            total_count=len(records),
            errors=errors,
        )
    
    def validate_record(self, record: dict[str, Any]) -> bool:
        """Validate a FungiDB record."""
        if not record:
            return False
        return bool(record.get("organism_name") or record.get("id"))
    
    def normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize an organism record to MINDEX format."""
        attributes = record.get("attributes", {})
        
        return {
            "source": self.source_name,
            "source_id": record.get("id", {}).get("value", "") if isinstance(record.get("id"), dict) else str(record.get("id", "")),
            "organism_name": attributes.get("organism_name", ""),
            "strain": attributes.get("strain", ""),
            "taxonomy": {
                "species": attributes.get("species", ""),
                "genus": attributes.get("genus", ""),
                "family": attributes.get("family", ""),
                "order": attributes.get("order", ""),
                "class": attributes.get("class", ""),
                "phylum": attributes.get("phylum", ""),
            },
            "genome_info": {
                "genome_size": attributes.get("genome_size", ""),
                "chromosome_count": attributes.get("chromosome_count", ""),
                "gene_count": attributes.get("gene_count", ""),
            },
            "data_source": attributes.get("data_source", ""),
            "scraped_at": datetime.utcnow().isoformat(),
            "raw_data": record,
        }
    
    def _normalize_gene(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize a gene record."""
        attributes = record.get("attributes", {})
        
        return {
            "source": self.source_name,
            "source_id": record.get("id", {}).get("value", "") if isinstance(record.get("id"), dict) else str(record.get("id", "")),
            "type": "gene",
            "gene_id": attributes.get("gene_source_id", ""),
            "gene_name": attributes.get("gene_name", ""),
            "product": attributes.get("product", ""),
            "organism": attributes.get("organism", ""),
            "location": {
                "chromosome": attributes.get("chromosome", ""),
                "start": attributes.get("start_min", ""),
                "end": attributes.get("end_max", ""),
                "strand": attributes.get("strand", ""),
            },
            "go_terms": attributes.get("go_terms", []),
            "ec_numbers": attributes.get("ec_numbers", []),
            "scraped_at": datetime.utcnow().isoformat(),
        }
