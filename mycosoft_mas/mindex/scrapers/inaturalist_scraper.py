"""
iNaturalist Scraper for MINDEX

Fetches fungi observations and species data from iNaturalist API.
https://api.inaturalist.org/v1/
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp

logger = logging.getLogger(__name__)


class INaturalistScraper:
    """
    Scraper for iNaturalist fungal data.
    
    Fetches:
    - Observations with photos
    - Species/taxon information
    - Images for training data
    """
    
    BASE_URL = "https://api.inaturalist.org/v1"
    
    # Fungi taxon ID in iNaturalist
    FUNGI_TAXON_ID = 47170
    
    def __init__(self, db=None):
        self.db = db
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def fetch_observations(
        self,
        limit: int = 1000,
        quality_grade: str = "research",
        per_page: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Fetch fungal observations from iNaturalist.
        
        Args:
            limit: Maximum observations to fetch
            quality_grade: 'research', 'needs_id', or 'any'
            per_page: Results per API page (max 200)
        """
        observations = []
        page = 1
        
        async with aiohttp.ClientSession() as session:
            while len(observations) < limit:
                params = {
                    "taxon_id": self.FUNGI_TAXON_ID,
                    "quality_grade": quality_grade,
                    "photos": "true",
                    "per_page": min(per_page, limit - len(observations)),
                    "page": page,
                    "order": "desc",
                    "order_by": "observed_on",
                }
                
                try:
                    async with session.get(
                        f"{self.BASE_URL}/observations",
                        params=params,
                    ) as response:
                        if response.status != 200:
                            logger.error(f"iNaturalist API error: {response.status}")
                            break
                        
                        data = await response.json()
                        results = data.get("results", [])
                        
                        if not results:
                            break
                        
                        for obs in results:
                            parsed = self._parse_observation(obs)
                            if parsed:
                                observations.append(parsed)
                        
                        logger.info(f"Fetched {len(observations)} observations from iNaturalist")
                        
                        if len(results) < per_page:
                            break
                        
                        page += 1
                        await asyncio.sleep(0.5)  # Rate limiting
                        
                except Exception as e:
                    logger.error(f"Error fetching observations: {e}")
                    break
        
        return observations
    
    async def fetch_species(
        self,
        limit: int = 10000,
        per_page: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Fetch fungal taxa/species from iNaturalist.
        """
        species = []
        page = 1
        
        async with aiohttp.ClientSession() as session:
            while len(species) < limit:
                params = {
                    "taxon_id": self.FUNGI_TAXON_ID,
                    "rank": "species,subspecies,variety",
                    "per_page": min(per_page, limit - len(species)),
                    "page": page,
                }
                
                try:
                    async with session.get(
                        f"{self.BASE_URL}/taxa",
                        params=params,
                    ) as response:
                        if response.status != 200:
                            logger.error(f"iNaturalist API error: {response.status}")
                            break
                        
                        data = await response.json()
                        results = data.get("results", [])
                        
                        if not results:
                            break
                        
                        for taxon in results:
                            parsed = self._parse_taxon(taxon)
                            if parsed:
                                species.append(parsed)
                        
                        logger.info(f"Fetched {len(species)} species from iNaturalist")
                        
                        if len(results) < per_page:
                            break
                        
                        page += 1
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Error fetching species: {e}")
                    break
        
        return species
    
    async def fetch_images(
        self,
        species_name: str = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch images for a species or all fungi.
        """
        images = []
        
        params = {
            "taxon_id": self.FUNGI_TAXON_ID,
            "photos": "true",
            "quality_grade": "research",
            "per_page": 200,
        }
        
        if species_name:
            params["taxon_name"] = species_name
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE_URL}/observations",
                params=params,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    for obs in data.get("results", [])[:limit]:
                        for photo in obs.get("photos", []):
                            images.append({
                                "url": photo.get("url", "").replace("square", "large"),
                                "source": "iNaturalist",
                                "source_id": str(photo.get("id")),
                                "species_name": obs.get("taxon", {}).get("name"),
                                "license": photo.get("license_code"),
                                "attribution": photo.get("attribution"),
                                "quality_score": 0.8 if obs.get("quality_grade") == "research" else 0.5,
                                "is_training_data": obs.get("quality_grade") == "research",
                            })
        
        return images[:limit]
    
    def _parse_observation(self, obs: Dict) -> Optional[Dict[str, Any]]:
        """Parse an observation from API response."""
        try:
            taxon = obs.get("taxon", {})
            photos = obs.get("photos", [])
            
            return {
                "external_id": f"inat-{obs.get('id')}",
                "scientific_name": taxon.get("name"),
                "common_name": taxon.get("preferred_common_name"),
                "latitude": obs.get("geojson", {}).get("coordinates", [None, None])[1],
                "longitude": obs.get("geojson", {}).get("coordinates", [None, None])[0],
                "location_name": obs.get("place_guess"),
                "observed_on": obs.get("observed_on"),
                "quality_grade": obs.get("quality_grade"),
                "research_grade": obs.get("quality_grade") == "research",
                "photo_count": len(photos),
                "photos": ",".join([p.get("url", "") for p in photos[:5]]),
                "observer": obs.get("user", {}).get("login"),
                "source": "iNaturalist",
                "source_url": f"https://www.inaturalist.org/observations/{obs.get('id')}",
            }
        except Exception as e:
            logger.error(f"Error parsing observation: {e}")
            return None
    
    def _parse_taxon(self, taxon: Dict) -> Optional[Dict[str, Any]]:
        """Parse a taxon from API response."""
        try:
            ancestors = taxon.get("ancestors", [])
            
            # Extract taxonomy from ancestors
            taxonomy = {}
            for a in ancestors:
                rank = a.get("rank")
                if rank in ["kingdom", "phylum", "class", "order", "family", "genus"]:
                    taxonomy[rank] = a.get("name")
            
            return {
                "scientific_name": taxon.get("name"),
                "common_names": taxon.get("preferred_common_name"),
                "kingdom": taxonomy.get("kingdom", "Fungi"),
                "phylum": taxonomy.get("phylum"),
                "class_name": taxonomy.get("class"),
                "order_name": taxonomy.get("order"),
                "family": taxonomy.get("family"),
                "genus": taxonomy.get("genus"),
                "species_epithet": taxon.get("name", "").split()[-1] if " " in taxon.get("name", "") else None,
                "source": "iNaturalist",
                "external_ids": {"inaturalist": taxon.get("id")},
                "observation_count": taxon.get("observations_count", 0),
            }
        except Exception as e:
            logger.error(f"Error parsing taxon: {e}")
            return None
    
    async def sync(self, limit: int = 1000) -> Dict[str, int]:
        """
        Full sync of species and observations.
        """
        stats = {
            "species_fetched": 0,
            "species_inserted": 0,
            "observations_fetched": 0,
            "observations_inserted": 0,
            "images_fetched": 0,
        }
        
        # Fetch species
        species = await self.fetch_species(limit=limit)
        stats["species_fetched"] = len(species)
        
        if self.db:
            for s in species:
                try:
                    self.db.insert_species(s)
                    stats["species_inserted"] += 1
                except Exception as e:
                    logger.error(f"Error inserting species: {e}")
        
        # Fetch observations
        observations = await self.fetch_observations(limit=limit)
        stats["observations_fetched"] = len(observations)
        
        if self.db:
            for obs in observations:
                try:
                    self.db.insert_observation(obs)
                    stats["observations_inserted"] += 1
                except Exception as e:
                    logger.error(f"Error inserting observation: {e}")
        
        return stats

