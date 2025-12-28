"""
iNaturalist Scraper for MINDEX

Fetches fungal observation and species data from iNaturalist.
API Documentation: https://api.inaturalist.org/v1/docs/

Focus areas:
- Fungal observations with photos
- Species taxonomy and classification
- Geographic distribution data
- Phenology (fruiting times)
"""

import logging
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from .base import BaseScraper, ScraperConfig, ScraperResult

logger = logging.getLogger(__name__)

# iNaturalist taxon IDs for fungi
FUNGI_TAXON_ID = 47170  # Kingdom Fungi


class INaturalistScraper(BaseScraper):
    """Scraper for iNaturalist fungal data."""
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        # iNaturalist allows 60 requests per minute
        if config is None:
            config = ScraperConfig(rate_limit_per_second=1.0)
        super().__init__(config)
    
    @property
    def source_name(self) -> str:
        return "iNaturalist"
    
    @property
    def base_url(self) -> str:
        return "https://api.inaturalist.org/v1"
    
    async def search_species(
        self,
        query: str,
        limit: int = 100,
    ) -> ScraperResult:
        """Search for fungal species by name."""
        records = []
        errors = []
        
        try:
            data = await self._request(
                "taxa/autocomplete",
                params={
                    "q": query,
                    "per_page": min(limit, 30),
                    "taxon_id": FUNGI_TAXON_ID,  # Limit to fungi
                },
            )
            
            if data and "results" in data:
                for taxon in data["results"]:
                    normalized = self.normalize_record(taxon)
                    if self.validate_record(normalized):
                        records.append(normalized)
                        
        except Exception as e:
            logger.error(f"Error searching iNaturalist: {e}")
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
        """Get detailed information about a species."""
        try:
            data = await self._request(f"taxa/{species_id}")
            if data and "results" in data and data["results"]:
                return self.normalize_record(data["results"][0])
        except Exception as e:
            logger.error(f"Error getting species {species_id}: {e}")
        return None
    
    async def get_observations(
        self,
        taxon_id: Optional[int] = None,
        place_id: Optional[int] = None,
        quality_grade: str = "research",
        per_page: int = 100,
        page: int = 1,
    ) -> ScraperResult:
        """Get fungal observations with optional filters."""
        records = []
        errors = []
        
        params = {
            "taxon_id": taxon_id or FUNGI_TAXON_ID,
            "quality_grade": quality_grade,
            "per_page": per_page,
            "page": page,
            "photos": True,  # Only observations with photos
            "order_by": "created_at",
            "order": "desc",
        }
        
        if place_id:
            params["place_id"] = place_id
        
        try:
            data = await self._request("observations", params=params)
            
            if data and "results" in data:
                for obs in data["results"]:
                    normalized = self._normalize_observation(obs)
                    if self.validate_record(normalized):
                        records.append(normalized)
                        
        except Exception as e:
            logger.error(f"Error fetching observations: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            source=self.source_name,
            data_type="observations",
            records=records,
            total_count=data.get("total_results", 0) if data else 0,
            errors=errors,
            metadata={
                "taxon_id": taxon_id,
                "quality_grade": quality_grade,
                "page": page,
            },
        )
    
    async def fetch_all(
        self,
        limit: Optional[int] = None,
    ) -> AsyncIterator[ScraperResult]:
        """Fetch all fungal observations in batches."""
        page = 1
        total_fetched = 0
        max_records = limit or self.config.max_records or 10000
        
        while total_fetched < max_records:
            batch_size = min(self.config.batch_size, max_records - total_fetched)
            result = await self.get_observations(per_page=batch_size, page=page)
            
            if not result.records:
                break
            
            yield result
            
            total_fetched += len(result.records)
            page += 1
            
            logger.info(f"Fetched {total_fetched} observations from iNaturalist")
    
    def validate_record(self, record: dict[str, Any]) -> bool:
        """Validate an iNaturalist record."""
        if not record:
            return False
        # Must have at least a name or ID
        return bool(record.get("scientific_name") or record.get("id"))
    
    def normalize_record(self, taxon: dict[str, Any]) -> dict[str, Any]:
        """Normalize a taxon record to MINDEX format."""
        return {
            "source": self.source_name,
            "source_id": str(taxon.get("id", "")),
            "scientific_name": taxon.get("name", ""),
            "common_name": taxon.get("preferred_common_name", ""),
            "rank": taxon.get("rank", ""),
            "taxonomy": {
                "kingdom": taxon.get("kingdom", "Fungi"),
                "phylum": taxon.get("phylum", ""),
                "class": taxon.get("class", ""),
                "order": taxon.get("order", ""),
                "family": taxon.get("family", ""),
                "genus": taxon.get("genus", ""),
                "species": taxon.get("name", ""),
            },
            "observations_count": taxon.get("observations_count", 0),
            "photos": [
                {
                    "url": photo.get("url", "").replace("square", "medium"),
                    "attribution": photo.get("attribution", ""),
                }
                for photo in taxon.get("default_photo", {}).get("square_url", [])[:5]
            ] if taxon.get("default_photo") else [],
            "wikipedia_url": taxon.get("wikipedia_url", ""),
            "is_active": taxon.get("is_active", True),
            "scraped_at": datetime.utcnow().isoformat(),
            "raw_data": taxon,
        }
    
    def _normalize_observation(self, obs: dict[str, Any]) -> dict[str, Any]:
        """Normalize an observation record."""
        taxon = obs.get("taxon", {})
        location = obs.get("location", "").split(",") if obs.get("location") else [None, None]
        
        return {
            "source": self.source_name,
            "source_id": str(obs.get("id", "")),
            "type": "observation",
            "scientific_name": taxon.get("name", ""),
            "common_name": taxon.get("preferred_common_name", ""),
            "taxon_id": taxon.get("id"),
            "observer": obs.get("user", {}).get("login", ""),
            "observed_on": obs.get("observed_on", ""),
            "location": {
                "latitude": float(location[0]) if location[0] else None,
                "longitude": float(location[1]) if location[1] else None,
                "place_guess": obs.get("place_guess", ""),
            },
            "quality_grade": obs.get("quality_grade", ""),
            "photos": [
                {
                    "url": photo.get("url", "").replace("square", "medium"),
                    "attribution": photo.get("attribution", ""),
                }
                for photo in obs.get("photos", [])[:5]
            ],
            "identifications_count": obs.get("identifications_count", 0),
            "scraped_at": datetime.utcnow().isoformat(),
        }
