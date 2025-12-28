"""
MycoBank Scraper for MINDEX

Fetches taxonomic nomenclature data from MycoBank.
Website: https://www.mycobank.org/

Focus areas:
- Fungal species names and nomenclature
- Type specimen information
- Taxonomic synonyms
- Publication references
"""

import logging
import re
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from .base import BaseScraper, ScraperConfig, ScraperResult

logger = logging.getLogger(__name__)


class MycoBankScraper(BaseScraper):
    """Scraper for MycoBank taxonomic data."""
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        # MycoBank API - be conservative with rate limiting
        if config is None:
            config = ScraperConfig(rate_limit_per_second=0.5)
        super().__init__(config)
    
    @property
    def source_name(self) -> str:
        return "MycoBank"
    
    @property
    def base_url(self) -> str:
        return "https://www.mycobank.org/Services/Generic/SearchService.svc"
    
    async def search_species(
        self,
        query: str,
        limit: int = 100,
    ) -> ScraperResult:
        """Search for fungal names in MycoBank."""
        records = []
        errors = []
        
        try:
            # MycoBank uses JSONP-style API
            data = await self._request(
                "SearchNames",
                params={
                    "searchText": query,
                    "searchType": "name",
                    "format": "json",
                    "limit": limit,
                },
            )
            
            if data:
                # Parse results - MycoBank returns various formats
                results = data if isinstance(data, list) else data.get("results", [])
                for item in results:
                    normalized = self.normalize_record(item)
                    if self.validate_record(normalized):
                        records.append(normalized)
                        
        except Exception as e:
            logger.error(f"Error searching MycoBank: {e}")
            errors.append(str(e))
        
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
        """Get detailed nomenclatural information about a species."""
        try:
            data = await self._request(
                "GetRecord",
                params={
                    "id": species_id,
                    "format": "json",
                },
            )
            if data:
                return self.normalize_record(data)
        except Exception as e:
            logger.error(f"Error getting species {species_id}: {e}")
        return None
    
    async def get_taxon_by_name(
        self,
        name: str,
    ) -> ScraperResult:
        """Get taxon information by exact name match."""
        records = []
        errors = []
        
        try:
            data = await self._request(
                "SearchNames",
                params={
                    "searchText": name,
                    "searchType": "exactMatch",
                    "format": "json",
                },
            )
            
            if data:
                results = data if isinstance(data, list) else [data]
                for item in results:
                    normalized = self.normalize_record(item)
                    if self.validate_record(normalized):
                        records.append(normalized)
                        
        except Exception as e:
            logger.error(f"Error searching for exact name {name}: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            source=self.source_name,
            data_type="taxon_lookup",
            records=records,
            total_count=len(records),
            errors=errors,
            metadata={"name": name},
        )
    
    async def get_synonyms(
        self,
        taxon_id: str,
    ) -> ScraperResult:
        """Get all synonyms for a taxon."""
        records = []
        errors = []
        
        try:
            data = await self._request(
                "GetSynonyms",
                params={
                    "id": taxon_id,
                    "format": "json",
                },
            )
            
            if data:
                synonyms = data if isinstance(data, list) else data.get("synonyms", [])
                for syn in synonyms:
                    records.append({
                        "source": self.source_name,
                        "type": "synonym",
                        "parent_id": taxon_id,
                        "synonym_name": syn.get("name", ""),
                        "synonym_author": syn.get("author", ""),
                        "synonym_year": syn.get("year", ""),
                        "synonym_type": syn.get("type", ""),
                        "scraped_at": datetime.utcnow().isoformat(),
                    })
                    
        except Exception as e:
            logger.error(f"Error getting synonyms for {taxon_id}: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            source=self.source_name,
            data_type="synonyms",
            records=records,
            total_count=len(records),
            errors=errors,
            metadata={"taxon_id": taxon_id},
        )
    
    async def fetch_all(
        self,
        limit: Optional[int] = None,
    ) -> AsyncIterator[ScraperResult]:
        """Fetch taxa using alphabetical pagination."""
        # Start with common fungal genus names
        genera = [
            "Agaricus", "Amanita", "Boletus", "Cantharellus", "Cortinarius",
            "Ganoderma", "Hericium", "Lactarius", "Morchella", "Pleurotus",
            "Psilocybe", "Russula", "Trametes", "Trichoderma", "Tuber",
        ]
        
        total_fetched = 0
        max_records = limit or self.config.max_records or 1000
        
        for genus in genera:
            if total_fetched >= max_records:
                break
                
            result = await self.search_species(genus, limit=100)
            if result.records:
                yield result
                total_fetched += len(result.records)
                logger.info(f"Fetched {len(result.records)} records for genus {genus}")
    
    def validate_record(self, record: dict[str, Any]) -> bool:
        """Validate a MycoBank record."""
        if not record:
            return False
        return bool(record.get("name") or record.get("scientific_name") or record.get("id"))
    
    def normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize a MycoBank record to MINDEX format."""
        # Extract author and year from name string if present
        name = record.get("name", "") or record.get("nameComplete", "")
        author = record.get("authorName", "") or record.get("authorsAbbrev", "")
        year = record.get("year", "")
        
        # Parse name components
        name_parts = self._parse_name(name)
        
        return {
            "source": self.source_name,
            "source_id": str(record.get("_id", record.get("mycobank_id", record.get("id", "")))),
            "scientific_name": name_parts.get("scientific_name", name),
            "author": author,
            "year": year,
            "rank": record.get("rank", name_parts.get("rank", "")),
            "status": record.get("status", record.get("nameStatus", "")),
            "taxonomy": {
                "genus": record.get("genus", name_parts.get("genus", "")),
                "species": record.get("species", name_parts.get("species", "")),
                "infraspecific": record.get("infraspecific", ""),
            },
            "type_specimen": {
                "herbarium": record.get("typeHerbarium", ""),
                "specimen": record.get("typeSpecimen", ""),
            },
            "basionym": record.get("basionym", ""),
            "current_name": record.get("currentName", ""),
            "publication": {
                "reference": record.get("literatureOriginal", ""),
                "page": record.get("page", ""),
            },
            "notes": record.get("remarks", ""),
            "scraped_at": datetime.utcnow().isoformat(),
            "raw_data": record,
        }
    
    def _parse_name(self, name: str) -> dict[str, str]:
        """Parse a scientific name into components."""
        parts = name.split()
        result = {"scientific_name": name, "rank": "species"}
        
        if len(parts) >= 2:
            result["genus"] = parts[0]
            result["species"] = parts[1] if len(parts) > 1 else ""
            
            # Check for infraspecific epithets
            if len(parts) > 2:
                infraspecific_ranks = ["var.", "f.", "subsp.", "ssp."]
                for i, part in enumerate(parts[2:], 2):
                    if part in infraspecific_ranks:
                        result["rank"] = part.rstrip(".")
                        if i + 1 < len(parts):
                            result["infraspecific"] = parts[i + 1]
        elif len(parts) == 1:
            result["genus"] = parts[0]
            result["rank"] = "genus"
        
        return result
