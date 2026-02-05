"""
GBIF Scraper for MINDEX - Feb 5, 2026

Fetches global biodiversity data from GBIF (Global Biodiversity Information Facility).
https://www.gbif.org/developer/species

Features:
- Rate limiting (3 req/sec max)
- Full backbone taxonomy support
- Occurrence data with images
- Media download support
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
import aiohttp

logger = logging.getLogger(__name__)


class GBIFScraper:
    """
    Scraper for GBIF fungal biodiversity data.
    
    Fetches:
    - Species from backbone taxonomy
    - Occurrences (observations) with coordinates
    - Media (images) for species
    - Taxonomic matching for reconciliation
    """
    
    BASE_URL = "https://api.gbif.org/v1"
    
    # Fungi kingdom key in GBIF
    FUNGI_KINGDOM_KEY = 5
    
    # Rate limit: 3 requests per second
    REQUEST_INTERVAL = 0.35  # Slightly higher than 1/3 for safety
    
    def __init__(
        self,
        db=None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.db = db
        self.username = username or os.environ.get("GBIF_USERNAME")
        self.password = password or os.environ.get("GBIF_PASSWORD")
        self.last_request_time = 0.0
        self.seen_keys: Set[int] = set()
    
    def _get_auth(self) -> Optional[aiohttp.BasicAuth]:
        """Get authentication if credentials provided."""
        if self.username and self.password:
            return aiohttp.BasicAuth(self.username, self.password)
        return None
    
    async def _rate_limit(self):
        """Enforce rate limiting."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            await asyncio.sleep(self.REQUEST_INTERVAL - elapsed)
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        params: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Make a rate-limited request to GBIF API."""
        await self._rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with session.get(
                url,
                params=params,
                auth=self._get_auth(),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.warning("GBIF rate limited, waiting 5s")
                    await asyncio.sleep(5)
                    return await self._make_request(session, endpoint, params)
                else:
                    logger.warning(f"GBIF API returned {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"GBIF request error: {e}")
            return None
    
    async def fetch_species(
        self,
        limit: int = 50000,
        offset: int = 0,
        rank: str = "SPECIES",
        status: str = "ACCEPTED",
    ) -> List[Dict[str, Any]]:
        """
        Fetch fungal species from GBIF backbone taxonomy.
        
        Args:
            limit: Maximum species to fetch
            offset: Starting offset
            rank: Taxonomic rank to fetch (SPECIES, GENUS, FAMILY, etc.)
            status: Taxonomic status (ACCEPTED, SYNONYM, etc.)
        """
        species = []
        current_offset = offset
        
        async with aiohttp.ClientSession() as session:
            while len(species) < limit:
                params = {
                    "kingdomKey": self.FUNGI_KINGDOM_KEY,
                    "rank": rank,
                    "status": status,
                    "limit": min(1000, limit - len(species)),
                    "offset": current_offset,
                }
                
                data = await self._make_request(session, "species/search", params)
                
                if not data:
                    break
                
                results = data.get("results", [])
                
                if not results:
                    break
                
                for taxon in results:
                    key = taxon.get("key")
                    if key and key not in self.seen_keys:
                        self.seen_keys.add(key)
                        parsed = self._parse_species(taxon)
                        if parsed:
                            species.append(parsed)
                
                if data.get("endOfRecords"):
                    logger.info(f"GBIF: Reached end of records at {len(species)} species")
                    break
                
                current_offset += len(results)
                logger.info(f"GBIF: Fetched {len(species)} species (offset: {current_offset})")
        
        return species
    
    async def fetch_occurrences(
        self,
        taxon_key: Optional[int] = None,
        limit: int = 10000,
        has_coordinate: bool = True,
        has_media: bool = False,
        country: Optional[str] = None,
        year_range: Optional[tuple] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch occurrence records (observations).
        
        Args:
            taxon_key: Specific taxon to fetch occurrences for
            limit: Maximum occurrences to fetch
            has_coordinate: Only fetch georeferenced occurrences
            has_media: Only fetch occurrences with media
            country: Filter by country code (e.g., "US", "GB")
            year_range: Tuple of (start_year, end_year)
        """
        occurrences = []
        offset = 0
        
        async with aiohttp.ClientSession() as session:
            while len(occurrences) < limit:
                params = {
                    "kingdomKey": self.FUNGI_KINGDOM_KEY,
                    "limit": min(300, limit - len(occurrences)),
                    "offset": offset,
                }
                
                if taxon_key:
                    params["taxonKey"] = taxon_key
                if has_coordinate:
                    params["hasCoordinate"] = "true"
                if has_media:
                    params["mediaType"] = "StillImage"
                if country:
                    params["country"] = country
                if year_range:
                    params["year"] = f"{year_range[0]},{year_range[1]}"
                
                data = await self._make_request(session, "occurrence/search", params)
                
                if not data:
                    break
                
                results = data.get("results", [])
                
                if not results:
                    break
                
                for occ in results:
                    parsed = self._parse_occurrence(occ)
                    if parsed:
                        occurrences.append(parsed)
                
                if data.get("endOfRecords"):
                    break
                
                offset += len(results)
                logger.info(f"GBIF: Fetched {len(occurrences)} occurrences")
        
        return occurrences
    
    async def fetch_images(
        self,
        taxon_key: Optional[int] = None,
        limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch images from GBIF occurrence media.
        
        Args:
            taxon_key: Specific taxon to fetch images for
            limit: Maximum images to fetch
        """
        images = []
        
        # Fetch occurrences with media
        occurrences = await self.fetch_occurrences(
            taxon_key=taxon_key,
            limit=limit * 2,  # Fetch more occurrences to get enough images
            has_media=True,
        )
        
        for occ in occurrences:
            for media in occ.get("media", []):
                if media.get("type") == "StillImage" and len(images) < limit:
                    image_url = media.get("identifier")
                    if image_url:
                        images.append({
                            "url": image_url,
                            "source": "GBIF",
                            "source_id": f"gbif-{occ.get('gbif_key')}",
                            "species_name": occ.get("scientific_name"),
                            "taxon_key": occ.get("taxon_key"),
                            "license": media.get("license") or "unknown",
                            "attribution": media.get("rightsHolder") or media.get("creator") or "",
                            "format": media.get("format"),
                            "quality_score": 0.7,
                            "is_training_data": True,
                            "occurrence_key": occ.get("gbif_key"),
                        })
        
        logger.info(f"GBIF: Collected {len(images)} images")
        return images
    
    async def match_name(
        self,
        name: str,
        strict: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Match a species name against GBIF backbone taxonomy.
        
        Args:
            name: Scientific name to match
            strict: If True, only exact matches are returned
        """
        async with aiohttp.ClientSession() as session:
            params = {
                "name": name,
                "strict": str(strict).lower(),
                "kingdom": "Fungi",
            }
            
            data = await self._make_request(session, "species/match", params)
            
            if data and data.get("matchType") != "NONE":
                return {
                    "matched_name": data.get("scientificName"),
                    "canonical_name": data.get("canonicalName"),
                    "gbif_key": data.get("usageKey"),
                    "match_type": data.get("matchType"),
                    "confidence": data.get("confidence", 0),
                    "rank": data.get("rank"),
                    "status": data.get("status"),
                    "kingdom": data.get("kingdom"),
                    "phylum": data.get("phylum"),
                    "class_name": data.get("class"),
                    "order_name": data.get("order"),
                    "family": data.get("family"),
                    "genus": data.get("genus"),
                }
            
            return None
    
    async def get_species_details(
        self,
        gbif_key: int,
    ) -> Optional[Dict[str, Any]]:
        """Get detailed species information by GBIF key."""
        async with aiohttp.ClientSession() as session:
            data = await self._make_request(session, f"species/{gbif_key}")
            
            if data:
                return self._parse_species(data)
            
            return None
    
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
                "rank": taxon.get("rank"),
                "taxonomic_status": taxon.get("taxonomicStatus"),
                "source": "GBIF",
                "external_ids": {"gbif": taxon.get("key")},
                "gbif_key": taxon.get("key"),
                "parent_key": taxon.get("parentKey"),
                "accepted_key": taxon.get("acceptedKey"),
                "basionym_key": taxon.get("basionymKey"),
                "num_descendants": taxon.get("numDescendants", 0),
                "references": taxon.get("references"),
                "created_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error parsing GBIF species: {e}")
            return None
    
    def _parse_occurrence(self, occ: Dict) -> Optional[Dict[str, Any]]:
        """Parse GBIF occurrence record."""
        try:
            return {
                "external_id": f"gbif-{occ.get('key')}",
                "gbif_key": occ.get("key"),
                "scientific_name": occ.get("scientificName"),
                "taxon_key": occ.get("taxonKey"),
                "latitude": occ.get("decimalLatitude"),
                "longitude": occ.get("decimalLongitude"),
                "coordinate_uncertainty": occ.get("coordinateUncertaintyInMeters"),
                "country": occ.get("country"),
                "country_code": occ.get("countryCode"),
                "state_province": occ.get("stateProvince"),
                "location_name": occ.get("locality"),
                "observed_on": occ.get("eventDate"),
                "year": occ.get("year"),
                "month": occ.get("month"),
                "day": occ.get("day"),
                "basis_of_record": occ.get("basisOfRecord"),
                "quality_grade": "research" if not occ.get("issues") else "needs_id",
                "research_grade": len(occ.get("issues", [])) == 0,
                "issues": occ.get("issues", []),
                "photo_count": len([m for m in occ.get("media", []) if m.get("type") == "StillImage"]),
                "observer": occ.get("recordedBy"),
                "institution": occ.get("institutionCode"),
                "collection": occ.get("collectionCode"),
                "catalog_number": occ.get("catalogNumber"),
                "source": "GBIF",
                "source_url": f"https://www.gbif.org/occurrence/{occ.get('key')}",
                "media": occ.get("media", []),
                "dataset_key": occ.get("datasetKey"),
            }
        except Exception as e:
            logger.error(f"Error parsing GBIF occurrence: {e}")
            return None
    
    async def sync(
        self,
        species_limit: int = 50000,
        occurrence_limit: int = 10000,
        include_occurrences: bool = True,
        include_images: bool = True,
    ) -> Dict[str, int]:
        """
        Full sync from GBIF.
        
        Args:
            species_limit: Maximum species to fetch
            occurrence_limit: Maximum occurrences to fetch
            include_occurrences: Whether to fetch occurrence data
            include_images: Whether to fetch image data
        """
        try:
            from ..reconciliation_integration import reconcile_scraper_output
            has_reconciliation = True
        except ImportError:
            has_reconciliation = False
            logger.warning("Reconciliation module not available")
        
        stats = {
            "species_fetched": 0,
            "species_inserted": 0,
            "species_reconciled": 0,
            "occurrences_fetched": 0,
            "occurrences_inserted": 0,
            "images_fetched": 0,
            "errors": 0,
        }
        
        # Fetch species from backbone
        logger.info(f"Starting GBIF species sync (limit={species_limit})")
        species = await self.fetch_species(limit=species_limit)
        stats["species_fetched"] = len(species)
        
        # Reconcile taxonomy
        if species and has_reconciliation:
            try:
                reconciled = await reconcile_scraper_output(self, species, enforce_license=True)
                stats["species_reconciled"] = len(reconciled)
                species = reconciled
            except Exception as e:
                logger.error(f"Reconciliation failed: {e}")
                stats["errors"] += 1
        
        if self.db:
            for s in species:
                try:
                    self.db.insert_species(s)
                    stats["species_inserted"] += 1
                except Exception as e:
                    logger.error(f"Error inserting species: {e}")
                    stats["errors"] += 1
        
        # Fetch occurrences
        if include_occurrences:
            logger.info(f"Starting GBIF occurrence sync (limit={occurrence_limit})")
            occurrences = await self.fetch_occurrences(limit=occurrence_limit)
            stats["occurrences_fetched"] = len(occurrences)
            
            if self.db:
                for occ in occurrences:
                    try:
                        occ_copy = {k: v for k, v in occ.items() if k != "media"}
                        self.db.insert_observation(occ_copy)
                        stats["occurrences_inserted"] += 1
                    except Exception as e:
                        logger.error(f"Error inserting occurrence: {e}")
                        stats["errors"] += 1
        
        # Fetch images
        if include_images:
            logger.info("Fetching GBIF images")
            images = await self.fetch_images(limit=5000)
            stats["images_fetched"] = len(images)
            
            if self.db:
                for img in images:
                    try:
                        self.db.insert_image(img)
                    except Exception as e:
                        logger.debug(f"Error inserting image: {e}")
        
        logger.info(f"GBIF sync complete: {stats}")
        return stats


# CLI entry point
if __name__ == "__main__":
    import sys
    
    async def main():
        scraper = GBIFScraper()
        
        if len(sys.argv) > 1 and sys.argv[1] == "match":
            name = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Amanita muscaria"
            result = await scraper.match_name(name)
            print(f"Match result for '{name}': {result}")
        elif len(sys.argv) > 1 and sys.argv[1] == "test":
            species = await scraper.fetch_species(limit=20)
            print(f"Fetched {len(species)} species")
            for s in species[:5]:
                print(f"  - {s['scientific_name']} (GBIF: {s.get('gbif_key')})")
        else:
            stats = await scraper.sync(species_limit=100, occurrence_limit=50, include_images=False)
            print(f"Sync stats: {stats}")
    
    asyncio.run(main())
