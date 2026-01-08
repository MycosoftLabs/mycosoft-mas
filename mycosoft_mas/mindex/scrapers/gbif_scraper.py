"""
GBIF Scraper for MINDEX

Fetches global biodiversity data from GBIF (Global Biodiversity Information Facility).
https://www.gbif.org/developer/species
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp

logger = logging.getLogger(__name__)


class GBIFScraper:
    """
    Scraper for GBIF fungal biodiversity data.
    
    Fetches:
    - Species occurrences (observations)
    - Taxonomic backbone data
    - Media (images)
    """
    
    BASE_URL = "https://api.gbif.org/v1"
    
    # Fungi kingdom key in GBIF
    FUNGI_KINGDOM_KEY = 5
    
    def __init__(self, db=None):
        self.db = db
    
    async def fetch_species(
        self,
        limit: int = 10000,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch fungal species from GBIF backbone taxonomy.
        """
        species = []
        
        async with aiohttp.ClientSession() as session:
            while len(species) < limit:
                try:
                    params = {
                        "kingdomKey": self.FUNGI_KINGDOM_KEY,
                        "rank": "SPECIES",
                        "status": "ACCEPTED",
                        "limit": min(1000, limit - len(species)),
                        "offset": offset + len(species),
                    }
                    
                    async with session.get(
                        f"{self.BASE_URL}/species/search",
                        params=params,
                    ) as response:
                        if response.status != 200:
                            logger.error(f"GBIF API error: {response.status}")
                            break
                        
                        data = await response.json()
                        results = data.get("results", [])
                        
                        if not results:
                            break
                        
                        for taxon in results:
                            parsed = self._parse_species(taxon)
                            if parsed:
                                species.append(parsed)
                        
                        if data.get("endOfRecords"):
                            break
                        
                        logger.info(f"Fetched {len(species)} species from GBIF")
                        await asyncio.sleep(0.2)
                        
                except Exception as e:
                    logger.error(f"Error fetching from GBIF: {e}")
                    break
        
        return species
    
    async def fetch_occurrences(
        self,
        species_key: int = None,
        limit: int = 1000,
        has_coordinate: bool = True,
        has_media: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Fetch occurrence records (observations).
        """
        occurrences = []
        
        async with aiohttp.ClientSession() as session:
            params = {
                "kingdomKey": self.FUNGI_KINGDOM_KEY,
                "limit": min(300, limit),
                "offset": 0,
            }
            
            if species_key:
                params["taxonKey"] = species_key
            if has_coordinate:
                params["hasCoordinate"] = "true"
            if has_media:
                params["mediaType"] = "StillImage"
            
            while len(occurrences) < limit:
                try:
                    async with session.get(
                        f"{self.BASE_URL}/occurrence/search",
                        params=params,
                    ) as response:
                        if response.status != 200:
                            break
                        
                        data = await response.json()
                        results = data.get("results", [])
                        
                        if not results:
                            break
                        
                        for occ in results:
                            parsed = self._parse_occurrence(occ)
                            if parsed:
                                occurrences.append(parsed)
                        
                        if data.get("endOfRecords"):
                            break
                        
                        params["offset"] = params.get("offset", 0) + len(results)
                        await asyncio.sleep(0.2)
                        
                except Exception as e:
                    logger.error(f"Error fetching occurrences: {e}")
                    break
        
        logger.info(f"Fetched {len(occurrences)} occurrences from GBIF")
        return occurrences
    
    async def fetch_images(
        self,
        species_key: int = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch images from occurrence media.
        """
        images = []
        
        occurrences = await self.fetch_occurrences(
            species_key=species_key,
            limit=limit,
            has_media=True,
        )
        
        for occ in occurrences:
            for media in occ.get("media", []):
                if media.get("type") == "StillImage":
                    images.append({
                        "url": media.get("identifier"),
                        "source": "GBIF",
                        "source_id": occ.get("external_id"),
                        "species_name": occ.get("scientific_name"),
                        "license": media.get("license"),
                        "attribution": media.get("rightsHolder"),
                        "quality_score": 0.7,
                        "is_training_data": True,
                    })
        
        return images[:limit]
    
    def _parse_species(self, taxon: Dict) -> Optional[Dict[str, Any]]:
        """Parse GBIF species record."""
        try:
            return {
                "scientific_name": taxon.get("scientificName") or taxon.get("canonicalName"),
                "canonical_name": taxon.get("canonicalName"),
                "author": taxon.get("authorship"),
                "kingdom": taxon.get("kingdom", "Fungi"),
                "phylum": taxon.get("phylum"),
                "class_name": taxon.get("class"),
                "order_name": taxon.get("order"),
                "family": taxon.get("family"),
                "genus": taxon.get("genus"),
                "species_epithet": taxon.get("specificEpithet"),
                "source": "GBIF",
                "external_ids": {"gbif": taxon.get("key")},
            }
        except Exception as e:
            logger.error(f"Error parsing GBIF species: {e}")
            return None
    
    def _parse_occurrence(self, occ: Dict) -> Optional[Dict[str, Any]]:
        """Parse GBIF occurrence record."""
        try:
            return {
                "external_id": f"gbif-{occ.get('key')}",
                "scientific_name": occ.get("scientificName"),
                "latitude": occ.get("decimalLatitude"),
                "longitude": occ.get("decimalLongitude"),
                "country": occ.get("country"),
                "location_name": occ.get("locality"),
                "observed_on": occ.get("eventDate"),
                "quality_grade": "research" if occ.get("issues", []) == [] else "needs_id",
                "research_grade": len(occ.get("issues", [])) == 0,
                "photo_count": len([m for m in occ.get("media", []) if m.get("type") == "StillImage"]),
                "observer": occ.get("recordedBy"),
                "source": "GBIF",
                "source_url": f"https://www.gbif.org/occurrence/{occ.get('key')}",
                "media": occ.get("media", []),
            }
        except Exception as e:
            logger.error(f"Error parsing GBIF occurrence: {e}")
            return None
    
    async def sync(self, limit: int = 1000) -> Dict[str, int]:
        """
        Full sync from GBIF with taxonomic reconciliation.
        """
        from ..reconciliation_integration import reconcile_scraper_output
        
        stats = {
            "species_fetched": 0,
            "species_inserted": 0,
            "species_reconciled": 0,
            "occurrences_fetched": 0,
            "occurrences_inserted": 0,
            "images_fetched": 0,
        }
        
        # Fetch species
        species = await self.fetch_species(limit=limit)
        stats["species_fetched"] = len(species)
        
        # Reconcile taxonomy with GBIF backbone (already from GBIF, but ensures consistency)
        if species:
            reconciled_species = await reconcile_scraper_output(
                self,
                species,
                enforce_license=True,
            )
            stats["species_reconciled"] = len(reconciled_species)
            species = reconciled_species
        
        if self.db:
            for s in species:
                try:
                    self.db.insert_species(s)
                    stats["species_inserted"] += 1
                except Exception as e:
                    logger.error(f"Error inserting species: {e}")
        
        # Fetch occurrences
        occurrences = await self.fetch_occurrences(limit=limit)
        stats["occurrences_fetched"] = len(occurrences)
        
        if self.db:
            for occ in occurrences:
                try:
                    # Remove media before insert
                    occ_copy = {k: v for k, v in occ.items() if k != "media"}
                    self.db.insert_observation(occ_copy)
                    stats["occurrences_inserted"] += 1
                except Exception as e:
                    logger.error(f"Error inserting occurrence: {e}")
        
        # Fetch images
        images = await self.fetch_images(limit=limit)
        stats["images_fetched"] = len(images)
        
        if self.db:
            for img in images:
                try:
                    self.db.insert_image(img)
                except Exception as e:
                    logger.error(f"Error inserting image: {e}")
        
        return stats











