"""
Mushroom.World Scraper for MINDEX

Fetches fungal species data from Mushroom.World database.
This is a comprehensive mushroom database with detailed information.

Focus areas:
- Species identification
- Edibility information
- Habitat and distribution
- Photos and descriptions
"""

import logging
import re
from datetime import datetime
from typing import Any, AsyncIterator, Optional
from bs4 import BeautifulSoup

from .base import BaseScraper, ScraperConfig, ScraperResult

logger = logging.getLogger(__name__)


class MushroomWorldScraper(BaseScraper):
    """Scraper for Mushroom.World fungal data."""
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        # Be respectful with rate limiting
        if config is None:
            config = ScraperConfig(rate_limit_per_second=0.5, batch_size=50)
        super().__init__(config)
    
    @property
    def source_name(self) -> str:
        return "MushroomWorld"
    
    @property
    def base_url(self) -> str:
        return "https://www.mushroom.world"
    
    def _get_default_headers(self) -> dict[str, str]:
        headers = super()._get_default_headers()
        headers["User-Agent"] = "MYCOSOFT-MINDEX/1.0 (Research Bot; https://mycosoft.io)"
        return headers
    
    async def search_species(
        self,
        query: str,
        limit: int = 100,
    ) -> ScraperResult:
        """Search for species by name."""
        records = []
        errors = []
        
        try:
            # Search endpoint
            params = {"search": query}
            data = await self._request("search", params=params)
            
            if data:
                # Parse HTML response for species
                soup = BeautifulSoup(data, "html.parser")
                species_links = soup.find_all("a", class_="species-link")[:limit]
                
                for link in species_links:
                    species_name = link.text.strip()
                    species_url = link.get("href", "")
                    
                    records.append({
                        "source": self.source_name,
                        "source_id": species_url,
                        "scientific_name": species_name,
                        "url": f"{self.base_url}{species_url}",
                        "scraped_at": datetime.utcnow().isoformat(),
                    })
                        
        except Exception as e:
            logger.error(f"Error searching MushroomWorld: {e}")
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
        species_url: str,
    ) -> Optional[dict[str, Any]]:
        """Get detailed information about a species."""
        try:
            response = await self._request(species_url.lstrip("/"))
            
            if response:
                soup = BeautifulSoup(response, "html.parser")
                
                # Extract species info
                name_elem = soup.find("h1", class_="species-name")
                scientific_name = name_elem.text.strip() if name_elem else ""
                
                common_name_elem = soup.find("span", class_="common-name")
                common_name = common_name_elem.text.strip() if common_name_elem else None
                
                description_elem = soup.find("div", class_="description")
                description = description_elem.text.strip() if description_elem else None
                
                edibility_elem = soup.find("span", class_="edibility")
                edibility = edibility_elem.text.strip() if edibility_elem else None
                
                habitat_elem = soup.find("div", class_="habitat")
                habitat = habitat_elem.text.strip() if habitat_elem else None
                
                image_elem = soup.find("img", class_="species-image")
                image_url = image_elem.get("src") if image_elem else None
                
                # Extract taxonomy
                taxonomy = {}
                tax_table = soup.find("table", class_="taxonomy")
                if tax_table:
                    for row in tax_table.find_all("tr"):
                        cells = row.find_all("td")
                        if len(cells) == 2:
                            key = cells[0].text.strip().lower()
                            value = cells[1].text.strip()
                            taxonomy[key] = value
                
                return self.normalize_record({
                    "scientific_name": scientific_name,
                    "common_name": common_name,
                    "description": description,
                    "edibility": edibility,
                    "habitat": habitat,
                    "image_url": image_url,
                    "taxonomy": taxonomy,
                    "url": f"{self.base_url}{species_url}",
                })
                
        except Exception as e:
            logger.error(f"Error getting species {species_url}: {e}")
        return None
    
    async def fetch_species_list(
        self,
        page: int = 1,
        per_page: int = 100,
    ) -> ScraperResult:
        """Fetch a page of species from the index."""
        records = []
        errors = []
        
        try:
            params = {"page": page, "per_page": per_page}
            response = await self._request("species/index", params=params)
            
            if response:
                soup = BeautifulSoup(response, "html.parser")
                species_items = soup.find_all("div", class_="species-item")
                
                for item in species_items:
                    name_elem = item.find("a", class_="species-name")
                    if name_elem:
                        records.append({
                            "source": self.source_name,
                            "source_id": name_elem.get("href", ""),
                            "scientific_name": name_elem.text.strip(),
                            "common_name": item.find("span", class_="common-name").text.strip() 
                                if item.find("span", class_="common-name") else None,
                            "scraped_at": datetime.utcnow().isoformat(),
                        })
                        
        except Exception as e:
            logger.error(f"Error fetching species list: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            source=self.source_name,
            data_type="species_list",
            records=records,
            total_count=len(records),
            errors=errors,
            metadata={"page": page},
        )
    
    async def fetch_all(
        self,
        limit: Optional[int] = None,
    ) -> AsyncIterator[ScraperResult]:
        """Fetch all species in batches."""
        page = 1
        max_records = limit or self.config.max_records or 10000
        total_fetched = 0
        
        while total_fetched < max_records:
            result = await self.fetch_species_list(page=page, per_page=self.config.batch_size)
            
            if not result.records:
                break
            
            yield result
            
            total_fetched += len(result.records)
            page += 1
            
            logger.info(f"Fetched {total_fetched} species from MushroomWorld")
    
    def validate_record(self, record: dict[str, Any]) -> bool:
        """Validate a record."""
        if not record:
            return False
        return bool(record.get("scientific_name"))
    
    def normalize_record(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize a record to MINDEX format."""
        taxonomy = data.get("taxonomy", {})
        
        return {
            "source": self.source_name,
            "source_id": data.get("url", ""),
            "scientific_name": data.get("scientific_name", ""),
            "common_name": data.get("common_name"),
            "rank": "species",
            "taxonomy": {
                "kingdom": taxonomy.get("kingdom", "Fungi"),
                "phylum": taxonomy.get("phylum", ""),
                "class": taxonomy.get("class", ""),
                "order": taxonomy.get("order", ""),
                "family": taxonomy.get("family", ""),
                "genus": taxonomy.get("genus", ""),
            },
            "description": data.get("description"),
            "edibility": data.get("edibility"),
            "habitat": data.get("habitat"),
            "image_url": data.get("image_url"),
            "wikipedia_url": None,
            "scraped_at": datetime.utcnow().isoformat(),
            "raw_data": data,
        }
