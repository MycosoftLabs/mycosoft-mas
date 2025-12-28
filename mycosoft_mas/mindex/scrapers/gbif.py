"""
GBIF (Global Biodiversity Information Facility) Scraper for MINDEX

Fetches global occurrence and biodiversity data from GBIF.
API Documentation: https://www.gbif.org/developer/summary

Focus areas:
- Species occurrence records
- Geographic distribution
- Collection specimen data
- Dataset information
"""

import logging
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from .base import BaseScraper, ScraperConfig, ScraperResult

logger = logging.getLogger(__name__)

# GBIF kingdom key for Fungi
FUNGI_KINGDOM_KEY = 5


class GBIFScraper(BaseScraper):
    """Scraper for GBIF biodiversity data."""
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        # GBIF allows reasonable rate limits
        if config is None:
            config = ScraperConfig(rate_limit_per_second=1.0, batch_size=300)
        super().__init__(config)
    
    @property
    def source_name(self) -> str:
        return "GBIF"
    
    @property
    def base_url(self) -> str:
        return "https://api.gbif.org/v1"
    
    async def search_species(
        self,
        query: str,
        limit: int = 100,
    ) -> ScraperResult:
        """Search for fungal species in GBIF."""
        records = []
        errors = []
        
        try:
            data = await self._request(
                "species/search",
                params={
                    "q": query,
                    "kingdom": "Fungi",
                    "limit": min(limit, 100),
                    "status": "ACCEPTED",
                },
            )
            
            if data and "results" in data:
                for species in data["results"]:
                    normalized = self.normalize_record(species)
                    if self.validate_record(normalized):
                        records.append(normalized)
                        
        except Exception as e:
            logger.error(f"Error searching GBIF: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            source=self.source_name,
            data_type="species_search",
            records=records,
            total_count=data.get("count", 0) if data else 0,
            errors=errors,
            metadata={"query": query},
        )
    
    async def get_species_details(
        self,
        species_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get detailed information about a species."""
        try:
            data = await self._request(f"species/{species_id}")
            if data:
                # Also get vernacular names
                vernacular = await self._request(f"species/{species_id}/vernacularNames")
                if vernacular and "results" in vernacular:
                    data["vernacular_names"] = vernacular["results"]
                
                return self.normalize_record(data)
        except Exception as e:
            logger.error(f"Error getting species {species_id}: {e}")
        return None
    
    async def get_occurrences(
        self,
        taxon_key: Optional[int] = None,
        country: Optional[str] = None,
        year: Optional[str] = None,
        limit: int = 300,
        offset: int = 0,
    ) -> ScraperResult:
        """Get occurrence records with optional filters."""
        records = []
        errors = []
        
        params = {
            "kingdomKey": FUNGI_KINGDOM_KEY,
            "limit": limit,
            "offset": offset,
            "hasCoordinate": True,  # Only georeferenced records
            "hasGeospatialIssue": False,
        }
        
        if taxon_key:
            params["taxonKey"] = taxon_key
        if country:
            params["country"] = country
        if year:
            params["year"] = year
        
        try:
            data = await self._request("occurrence/search", params=params)
            
            if data and "results" in data:
                for occ in data["results"]:
                    normalized = self._normalize_occurrence(occ)
                    if self.validate_record(normalized):
                        records.append(normalized)
                        
        except Exception as e:
            logger.error(f"Error fetching occurrences: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            source=self.source_name,
            data_type="occurrences",
            records=records,
            total_count=data.get("count", 0) if data else 0,
            errors=errors,
            metadata={
                "taxon_key": taxon_key,
                "country": country,
                "offset": offset,
            },
        )
    
    async def get_species_list(
        self,
        rank: str = "SPECIES",
        limit: int = 100,
        offset: int = 0,
    ) -> ScraperResult:
        """Get list of fungal species."""
        records = []
        errors = []
        
        try:
            data = await self._request(
                "species/search",
                params={
                    "kingdom": "Fungi",
                    "rank": rank,
                    "status": "ACCEPTED",
                    "limit": limit,
                    "offset": offset,
                },
            )
            
            if data and "results" in data:
                for species in data["results"]:
                    normalized = self.normalize_record(species)
                    if self.validate_record(normalized):
                        records.append(normalized)
                        
        except Exception as e:
            logger.error(f"Error fetching species list: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            source=self.source_name,
            data_type="species_list",
            records=records,
            total_count=data.get("count", 0) if data else 0,
            errors=errors,
            metadata={"rank": rank, "offset": offset},
        )
    
    async def get_distribution(
        self,
        taxon_key: int,
    ) -> ScraperResult:
        """Get geographic distribution for a taxon."""
        records = []
        errors = []
        
        try:
            data = await self._request(f"species/{taxon_key}/distributions")
            
            if data and "results" in data:
                for dist in data["results"]:
                    records.append({
                        "source": self.source_name,
                        "type": "distribution",
                        "taxon_key": taxon_key,
                        "country": dist.get("country", ""),
                        "locality": dist.get("locality", ""),
                        "status": dist.get("status", ""),
                        "establishment_means": dist.get("establishmentMeans", ""),
                        "scraped_at": datetime.utcnow().isoformat(),
                    })
                    
        except Exception as e:
            logger.error(f"Error getting distribution for {taxon_key}: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            source=self.source_name,
            data_type="distribution",
            records=records,
            total_count=len(records),
            errors=errors,
            metadata={"taxon_key": taxon_key},
        )
    
    async def fetch_all(
        self,
        limit: Optional[int] = None,
    ) -> AsyncIterator[ScraperResult]:
        """Fetch fungal species data in batches."""
        offset = 0
        total_fetched = 0
        max_records = limit or self.config.max_records or 10000
        
        while total_fetched < max_records:
            batch_size = min(self.config.batch_size, max_records - total_fetched)
            result = await self.get_species_list(limit=batch_size, offset=offset)
            
            if not result.records:
                break
            
            yield result
            
            total_fetched += len(result.records)
            offset += batch_size
            
            logger.info(f"Fetched {total_fetched}/{result.total_count} species from GBIF")
            
            # Check if we've fetched all available records
            if total_fetched >= result.total_count:
                break
    
    def validate_record(self, record: dict[str, Any]) -> bool:
        """Validate a GBIF record."""
        if not record:
            return False
        return bool(record.get("scientific_name") or record.get("key"))
    
    def normalize_record(self, species: dict[str, Any]) -> dict[str, Any]:
        """Normalize a species record to MINDEX format."""
        return {
            "source": self.source_name,
            "source_id": str(species.get("key", "")),
            "scientific_name": species.get("scientificName", species.get("canonicalName", "")),
            "canonical_name": species.get("canonicalName", ""),
            "authorship": species.get("authorship", ""),
            "rank": species.get("rank", ""),
            "status": species.get("taxonomicStatus", ""),
            "taxonomy": {
                "kingdom": species.get("kingdom", "Fungi"),
                "phylum": species.get("phylum", ""),
                "class": species.get("class", ""),
                "order": species.get("order", ""),
                "family": species.get("family", ""),
                "genus": species.get("genus", ""),
                "species": species.get("species", ""),
            },
            "taxonomy_keys": {
                "kingdom_key": species.get("kingdomKey"),
                "phylum_key": species.get("phylumKey"),
                "class_key": species.get("classKey"),
                "order_key": species.get("orderKey"),
                "family_key": species.get("familyKey"),
                "genus_key": species.get("genusKey"),
                "species_key": species.get("speciesKey"),
            },
            "parent_key": species.get("parentKey"),
            "accepted_key": species.get("acceptedKey"),
            "num_descendants": species.get("numDescendants", 0),
            "vernacular_names": [
                {"name": v.get("vernacularName", ""), "language": v.get("language", "")}
                for v in species.get("vernacular_names", [])[:10]
            ],
            "scraped_at": datetime.utcnow().isoformat(),
            "raw_data": species,
        }
    
    def _normalize_occurrence(self, occ: dict[str, Any]) -> dict[str, Any]:
        """Normalize an occurrence record."""
        return {
            "source": self.source_name,
            "source_id": str(occ.get("key", "")),
            "type": "occurrence",
            "scientific_name": occ.get("scientificName", ""),
            "taxon_key": occ.get("taxonKey"),
            "species": occ.get("species", ""),
            "location": {
                "latitude": occ.get("decimalLatitude"),
                "longitude": occ.get("decimalLongitude"),
                "country": occ.get("country", ""),
                "country_code": occ.get("countryCode", ""),
                "state_province": occ.get("stateProvince", ""),
                "locality": occ.get("locality", ""),
                "elevation": occ.get("elevation"),
                "depth": occ.get("depth"),
            },
            "event": {
                "date": occ.get("eventDate", ""),
                "year": occ.get("year"),
                "month": occ.get("month"),
                "day": occ.get("day"),
            },
            "record_info": {
                "basis_of_record": occ.get("basisOfRecord", ""),
                "institution_code": occ.get("institutionCode", ""),
                "collection_code": occ.get("collectionCode", ""),
                "catalog_number": occ.get("catalogNumber", ""),
                "dataset_key": occ.get("datasetKey", ""),
            },
            "identifiers": {
                "occurrence_id": occ.get("occurrenceID", ""),
                "gbif_id": occ.get("gbifID"),
            },
            "media": [
                {"type": m.get("type", ""), "identifier": m.get("identifier", "")}
                for m in occ.get("media", [])[:5]
            ],
            "scraped_at": datetime.utcnow().isoformat(),
        }
