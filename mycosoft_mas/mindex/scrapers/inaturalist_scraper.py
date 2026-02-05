"""
iNaturalist Scraper for MINDEX - Feb 5, 2026

Fetches fungi observations and species data from iNaturalist API.
https://api.inaturalist.org/v1/

Features:
- API token authentication for higher rate limits
- Exponential backoff for rate limiting
- Batch processing with configurable page limits
- Retry logic for failed requests
"""

import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp

logger = logging.getLogger(__name__)


class RateLimiter:
    """Handles rate limiting with exponential backoff."""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, max_retries: int = 5):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.current_delay = base_delay
        self.consecutive_errors = 0
        self.last_request_time = 0.0
    
    async def wait(self):
        """Wait before next request, respecting rate limits."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_request_time
        
        if elapsed < self.current_delay:
            await asyncio.sleep(self.current_delay - elapsed)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    def success(self):
        """Called after successful request - reduce delay."""
        self.consecutive_errors = 0
        self.current_delay = max(self.base_delay, self.current_delay * 0.9)
    
    def failure(self, status_code: int = 0):
        """Called after failed request - increase delay with backoff."""
        self.consecutive_errors += 1
        
        if status_code == 429 or status_code == 403:
            # Rate limited - significant backoff
            self.current_delay = min(
                self.max_delay,
                self.current_delay * (2 ** self.consecutive_errors) + random.uniform(0, 1)
            )
        else:
            # Other error - moderate backoff
            self.current_delay = min(
                self.max_delay,
                self.current_delay * 1.5 + random.uniform(0, 0.5)
            )
        
        logger.warning(f"Rate limiter backoff: {self.current_delay:.2f}s (errors: {self.consecutive_errors})")
    
    def should_retry(self) -> bool:
        """Check if we should retry after an error."""
        return self.consecutive_errors < self.max_retries


class INaturalistScraper:
    """
    Scraper for iNaturalist fungal data.
    
    Fetches:
    - Observations with photos
    - Species/taxon information
    - Images for training data
    
    Features:
    - API token authentication
    - Exponential backoff rate limiting
    - Batch processing with page limits
    """
    
    BASE_URL = "https://api.inaturalist.org/v1"
    
    # Fungi taxon ID in iNaturalist
    FUNGI_TAXON_ID = 47170
    
    # Maximum pages per sync run to avoid rate limits
    MAX_PAGES_PER_RUN = 100
    
    def __init__(self, db=None, api_token: Optional[str] = None):
        self.db = db
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_token = api_token or os.environ.get("INATURALIST_API_TOKEN")
        self.rate_limiter = RateLimiter(base_delay=1.0, max_delay=60.0, max_retries=5)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional API token."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mycosoft-MINDEX/1.0 (https://mycosoft.com; contact@mycosoft.com)",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self._get_headers())
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        session: aiohttp.ClientSession,
    ) -> Optional[Dict[str, Any]]:
        """Make a rate-limited request with retry logic."""
        url = f"{self.BASE_URL}/{endpoint}"
        
        while self.rate_limiter.should_retry():
            await self.rate_limiter.wait()
            
            try:
                async with session.get(url, params=params, headers=self._get_headers()) as response:
                    if response.status == 200:
                        self.rate_limiter.success()
                        return await response.json()
                    
                    elif response.status == 429 or response.status == 403:
                        # Rate limited
                        self.rate_limiter.failure(response.status)
                        logger.warning(f"Rate limited by iNaturalist (status {response.status}), backing off...")
                        continue
                    
                    elif response.status >= 500:
                        # Server error - retry
                        self.rate_limiter.failure(response.status)
                        logger.warning(f"iNaturalist server error: {response.status}")
                        continue
                    
                    else:
                        # Client error - don't retry
                        logger.error(f"iNaturalist API error: {response.status}")
                        return None
                        
            except aiohttp.ClientError as e:
                self.rate_limiter.failure()
                logger.error(f"Network error: {e}")
                continue
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None
        
        logger.error("Max retries exceeded for iNaturalist request")
        return None
    
    async def fetch_observations(
        self,
        limit: int = 1000,
        quality_grade: str = "research",
        per_page: int = 200,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch fungal observations from iNaturalist.
        
        Args:
            limit: Maximum observations to fetch
            quality_grade: 'research', 'needs_id', or 'any'
            per_page: Results per API page (max 200)
            max_pages: Maximum pages to fetch (default: MAX_PAGES_PER_RUN)
        """
        observations = []
        page = 1
        max_pages = max_pages or self.MAX_PAGES_PER_RUN
        
        async with aiohttp.ClientSession() as session:
            while len(observations) < limit and page <= max_pages:
                params = {
                    "taxon_id": self.FUNGI_TAXON_ID,
                    "quality_grade": quality_grade,
                    "photos": "true",
                    "per_page": min(per_page, limit - len(observations)),
                    "page": page,
                    "order": "desc",
                    "order_by": "observed_on",
                }
                
                data = await self._make_request("observations", params, session)
                
                if not data:
                    logger.warning(f"Failed to fetch page {page}, stopping")
                    break
                
                results = data.get("results", [])
                
                if not results:
                    break
                
                for obs in results:
                    parsed = self._parse_observation(obs)
                    if parsed:
                        observations.append(parsed)
                
                logger.info(f"Fetched page {page}: {len(observations)} total observations")
                
                if len(results) < per_page:
                    break
                
                page += 1
        
        return observations
    
    async def fetch_species(
        self,
        limit: int = 10000,
        per_page: int = 500,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch fungal taxa/species from iNaturalist.
        
        Args:
            limit: Maximum species to fetch
            per_page: Results per page (max 500)
            max_pages: Maximum pages to fetch (default: MAX_PAGES_PER_RUN)
        """
        species = []
        page = 1
        max_pages = max_pages or self.MAX_PAGES_PER_RUN
        
        async with aiohttp.ClientSession() as session:
            while len(species) < limit and page <= max_pages:
                params = {
                    "taxon_id": self.FUNGI_TAXON_ID,
                    "rank": "species,subspecies,variety",
                    "per_page": min(per_page, limit - len(species)),
                    "page": page,
                }
                
                data = await self._make_request("taxa", params, session)
                
                if not data:
                    logger.warning(f"Failed to fetch page {page}, stopping")
                    break
                
                results = data.get("results", [])
                
                if not results:
                    break
                
                for taxon in results:
                    parsed = self._parse_taxon(taxon)
                    if parsed:
                        species.append(parsed)
                
                logger.info(f"Fetched page {page}: {len(species)} total species")
                
                if len(results) < per_page:
                    break
                
                page += 1
        
        return species
    
    async def fetch_images(
        self,
        species_name: str = None,
        taxon_id: int = None,
        limit: int = 1000,
        download_to_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch images for a species or all fungi.
        
        Args:
            species_name: Optional species name filter
            taxon_id: Optional taxon ID filter
            limit: Maximum images to fetch
            download_to_path: Optional path to download images to
        """
        images = []
        
        params = {
            "taxon_id": taxon_id or self.FUNGI_TAXON_ID,
            "photos": "true",
            "quality_grade": "research",
            "per_page": 200,
        }
        
        if species_name:
            params["taxon_name"] = species_name
        
        async with aiohttp.ClientSession() as session:
            data = await self._make_request("observations", params, session)
            
            if data:
                for obs in data.get("results", [])[:limit]:
                    taxon = obs.get("taxon", {})
                    for photo in obs.get("photos", []):
                        image_data = {
                            "url": photo.get("url", "").replace("square", "large"),
                            "original_url": photo.get("url", "").replace("square", "original"),
                            "medium_url": photo.get("url", "").replace("square", "medium"),
                            "source": "iNaturalist",
                            "source_id": str(photo.get("id")),
                            "species_name": taxon.get("name"),
                            "taxon_id": taxon.get("id"),
                            "license": photo.get("license_code"),
                            "attribution": photo.get("attribution"),
                            "quality_score": 0.9 if obs.get("quality_grade") == "research" else 0.5,
                            "is_training_data": obs.get("quality_grade") == "research",
                            "observation_id": obs.get("id"),
                        }
                        images.append(image_data)
                        
                        if len(images) >= limit:
                            break
                    
                    if len(images) >= limit:
                        break
        
        return images[:limit]
    
    def _parse_observation(self, obs: Dict) -> Optional[Dict[str, Any]]:
        """Parse an observation from API response."""
        try:
            taxon = obs.get("taxon", {})
            photos = obs.get("photos", [])
            geojson = obs.get("geojson") or {}
            coords = geojson.get("coordinates", [None, None])
            
            return {
                "external_id": f"inat-{obs.get('id')}",
                "inat_id": obs.get("id"),
                "scientific_name": taxon.get("name"),
                "common_name": taxon.get("preferred_common_name"),
                "taxon_id": taxon.get("id"),
                "latitude": coords[1] if len(coords) > 1 else None,
                "longitude": coords[0] if len(coords) > 0 else None,
                "location_name": obs.get("place_guess"),
                "observed_on": obs.get("observed_on"),
                "quality_grade": obs.get("quality_grade"),
                "research_grade": obs.get("quality_grade") == "research",
                "photo_count": len(photos),
                "photos": [
                    {
                        "id": p.get("id"),
                        "url": p.get("url", "").replace("square", "large"),
                        "license": p.get("license_code"),
                        "attribution": p.get("attribution"),
                    }
                    for p in photos[:5]
                ],
                "observer": obs.get("user", {}).get("login"),
                "source": "iNaturalist",
                "source_url": f"https://www.inaturalist.org/observations/{obs.get('id')}",
                "created_at": obs.get("created_at"),
                "updated_at": obs.get("updated_at"),
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
            
            # Get default photo if available
            default_photo = taxon.get("default_photo", {})
            
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
                "rank": taxon.get("rank"),
                "source": "iNaturalist",
                "external_ids": {"inaturalist": taxon.get("id")},
                "inat_id": taxon.get("id"),
                "observation_count": taxon.get("observations_count", 0),
                "wikipedia_url": taxon.get("wikipedia_url"),
                "wikipedia_summary": taxon.get("wikipedia_summary"),
                "default_photo": {
                    "id": default_photo.get("id"),
                    "url": default_photo.get("medium_url") or default_photo.get("url"),
                    "attribution": default_photo.get("attribution"),
                    "license": default_photo.get("license_code"),
                } if default_photo else None,
                "is_active": taxon.get("is_active", True),
                "created_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error parsing taxon: {e}")
            return None
    
    async def sync(
        self,
        limit: int = 1000,
        max_pages: Optional[int] = None,
        include_observations: bool = True,
    ) -> Dict[str, int]:
        """
        Full sync of species and observations with taxonomic reconciliation.
        
        Args:
            limit: Maximum records per type to fetch
            max_pages: Maximum pages per request type
            include_observations: Whether to also sync observations
        """
        try:
            from ..reconciliation_integration import reconcile_scraper_output
            has_reconciliation = True
        except ImportError:
            has_reconciliation = False
            logger.warning("Reconciliation module not available, skipping reconciliation")
        
        stats = {
            "species_fetched": 0,
            "species_inserted": 0,
            "species_reconciled": 0,
            "observations_fetched": 0,
            "observations_inserted": 0,
            "observations_reconciled": 0,
            "images_fetched": 0,
            "errors": 0,
        }
        
        # Fetch species
        logger.info(f"Starting iNaturalist species sync (limit={limit}, max_pages={max_pages})")
        species = await self.fetch_species(limit=limit, max_pages=max_pages)
        stats["species_fetched"] = len(species)
        
        # Reconcile with GBIF backbone and Index Fungorum
        if species and has_reconciliation:
            try:
                reconciled_species = await reconcile_scraper_output(
                    self,
                    species,
                    enforce_license=True,
                )
                stats["species_reconciled"] = len(reconciled_species)
                species = reconciled_species
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
        
        # Fetch observations (optional)
        if include_observations:
            logger.info(f"Starting iNaturalist observations sync (limit={limit})")
            observations = await self.fetch_observations(limit=limit, max_pages=max_pages)
            stats["observations_fetched"] = len(observations)
            
            # Reconcile observations (ensures consistent taxonomy)
            if observations and has_reconciliation:
                try:
                    reconciled_obs = await reconcile_scraper_output(
                        self,
                        observations,
                        enforce_license=True,
                    )
                    stats["observations_reconciled"] = len(reconciled_obs)
                    observations = reconciled_obs
                except Exception as e:
                    logger.error(f"Observation reconciliation failed: {e}")
                    stats["errors"] += 1
            
            if self.db:
                for obs in observations:
                    try:
                        self.db.insert_observation(obs)
                        stats["observations_inserted"] += 1
                    except Exception as e:
                        logger.error(f"Error inserting observation: {e}")
                        stats["errors"] += 1
        
        logger.info(f"iNaturalist sync complete: {stats}")
        return stats


# CLI entry point for testing
if __name__ == "__main__":
    import sys
    
    async def main():
        scraper = INaturalistScraper()
        
        if len(sys.argv) > 1 and sys.argv[1] == "test":
            # Quick test with small limit
            species = await scraper.fetch_species(limit=10, max_pages=1)
            print(f"Fetched {len(species)} species")
            for s in species[:3]:
                print(f"  - {s['scientific_name']} ({s.get('observation_count', 0)} obs)")
        else:
            # Full sync
            stats = await scraper.sync(limit=1000, max_pages=10)
            print(f"Sync stats: {stats}")
    
    asyncio.run(main())
