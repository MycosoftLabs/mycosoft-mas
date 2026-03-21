"""
iNaturalist API Integration Client.

Mass data ingestion client for pulling taxonomy, observations, images,
locations, species descriptions, and live events from iNaturalist into MINDEX.
Covers ALL kingdoms of life: Fungi, Plantae, Animalia, Bacteria, Protista, etc.

Used by: TaxonomyIngestionAgent, MycologyBioAgent, ETLAgent, MINDEX sync pipelines.

iNaturalist API docs: https://api.inaturalist.org/v1/docs/
Rate limit: 100 requests per minute (unauthenticated), 200 with token.

Environment Variables:
    INATURALIST_API_URL: Base URL (default https://api.inaturalist.org/v1)
    INATURALIST_JWT_TOKEN: JWT token for authenticated requests (optional)
    INATURALIST_APP_ID: Application ID for OAuth (optional)
    INATURALIST_APP_SECRET: Application secret for OAuth (optional)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_INATURALIST_URL = "https://api.inaturalist.org/v1"

# iNaturalist kingdom-level taxon IDs
KINGDOM_TAXON_IDS = {
    "fungi": 47170,
    "plantae": 47126,
    "animalia": 1,
    "bacteria": 67333,
    "protista": 48222,
    "chromista": 48222,
    "archaea": 151817,
}


@dataclass
class INaturalistConfig:
    """Configuration for the iNaturalist API client."""

    base_url: str = DEFAULT_INATURALIST_URL
    jwt_token: str = ""
    app_id: str = ""
    app_secret: str = ""
    requests_per_minute: int = 100
    batch_size: int = 200
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    timeout_seconds: int = 30
    # Minimum interval between requests to stay within rate limit
    min_request_interval: float = field(init=False)

    def __post_init__(self) -> None:
        self.min_request_interval = 60.0 / self.requests_per_minute


class INaturalistClient:
    """
    Async client for the iNaturalist v1 API.

    Provides paginated access to taxa, observations, places, and species counts.
    Built-in rate limiting ensures compliance with iNaturalist's 100 req/min cap.
    Designed for mass ingestion pipelines that pull millions of records.

    Usage:
        async with INaturalistClient() as client:
            taxa = await client.search_taxa("Amanita", rank="genus")
            observations = await client.search_observations(taxon_id=47170, per_page=200)
    """

    def __init__(self, config: Optional[INaturalistConfig] = None) -> None:
        self.config = config or INaturalistConfig(
            base_url=os.getenv("INATURALIST_API_URL", DEFAULT_INATURALIST_URL),
            jwt_token=os.getenv("INATURALIST_JWT_TOKEN", ""),
            app_id=os.getenv("INATURALIST_APP_ID", ""),
            app_secret=os.getenv("INATURALIST_APP_SECRET", ""),
        )
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0.0
        self._request_count: int = 0
        self._window_start: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        """Build request headers, including JWT auth if configured."""
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "Mycosoft-MAS/1.0 (taxonomy-ingestion)",
        }
        if self.config.jwt_token:
            headers["Authorization"] = f"Bearer {self.config.jwt_token}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize the shared httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url.rstrip("/"),
                headers=self._headers(),
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def __aenter__(self) -> "INaturalistClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Rate Limiting
    # ------------------------------------------------------------------

    async def _rate_limit(self) -> None:
        """
        Enforce iNaturalist rate limits using a sliding window.

        Sleeps if necessary so that no more than ``requests_per_minute``
        requests are issued within any 60-second window.
        """
        now = time.monotonic()

        # Reset the window if 60 seconds have passed
        if now - self._window_start >= 60.0:
            self._window_start = now
            self._request_count = 0

        self._request_count += 1

        if self._request_count >= self.config.requests_per_minute:
            sleep_for = 60.0 - (now - self._window_start)
            if sleep_for > 0:
                logger.debug("Rate limit reached, sleeping %.1f seconds", sleep_for)
                await asyncio.sleep(sleep_for)
                self._window_start = time.monotonic()
                self._request_count = 1

        # Also enforce minimum interval between individual requests
        elapsed = now - self._last_request_time
        if elapsed < self.config.min_request_interval:
            await asyncio.sleep(self.config.min_request_interval - elapsed)

        self._last_request_time = time.monotonic()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Issue an API request with rate limiting and retry logic.

        Retries on transient 5xx errors and httpx transport failures.
        """
        await self._rate_limit()
        client = await self._get_client()

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                resp = await client.request(method, path, params=params)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", "60"))
                    logger.warning(
                        "iNaturalist 429 Too Many Requests, sleeping %s seconds",
                        retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code >= 500:
                    wait = self.config.retry_backoff_seconds * attempt
                    logger.warning(
                        "iNaturalist %s on %s (attempt %d/%d), retrying in %.1fs",
                        exc.response.status_code,
                        path,
                        attempt,
                        self.config.max_retries,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                wait = self.config.retry_backoff_seconds * attempt
                logger.warning(
                    "iNaturalist transport error on %s (attempt %d/%d): %s",
                    path,
                    attempt,
                    self.config.max_retries,
                    exc,
                )
                await asyncio.sleep(wait)

        raise RuntimeError(
            f"iNaturalist request to {path} failed after {self.config.max_retries} retries"
        ) from last_exc

    # ------------------------------------------------------------------
    # Observations
    # ------------------------------------------------------------------

    async def search_observations(
        self,
        query: Optional[str] = None,
        per_page: int = 200,
        page: int = 1,
        taxon_id: Optional[int] = None,
        place_id: Optional[int] = None,
        quality_grade: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search observations with optional filters.

        Args:
            query: Free-text search string.
            per_page: Results per page (max 200 per iNaturalist docs).
            page: Page number (1-indexed).
            taxon_id: Filter by taxon ID (e.g. 47170 for Fungi).
            place_id: Filter by iNaturalist place ID.
            quality_grade: One of 'research', 'needs_id', 'casual'.

        Returns:
            API response dict with ``total_results``, ``page``, ``per_page``,
            and ``results`` list of observation objects.
        """
        params: Dict[str, Any] = {
            "per_page": min(per_page, 200),
            "page": page,
            "order_by": "id",
            "order": "asc",
        }
        if query:
            params["q"] = query
        if taxon_id is not None:
            params["taxon_id"] = taxon_id
        if place_id is not None:
            params["place_id"] = place_id
        if quality_grade:
            params["quality_grade"] = quality_grade

        return await self._request("GET", "/observations", params=params)

    async def get_observation(self, observation_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single observation by ID.

        Returns the full observation record including photos, identifications,
        comments, geolocation, quality metrics, and taxon details.
        """
        data = await self._request("GET", f"/observations/{observation_id}")
        results = data.get("results", [])
        return results[0] if results else None

    async def get_observations_batch(
        self,
        params: Optional[Dict[str, Any]] = None,
        per_page: int = 200,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Fetch a batch of observations with arbitrary query parameters.

        Designed for mass ingestion pipelines. Supports all iNaturalist
        observation query parameters passed through ``params``.

        Args:
            params: Dict of iNaturalist observation query parameters.
            per_page: Results per page (max 200).
            page: Page number.

        Returns:
            Full API response including pagination metadata.
        """
        merged: Dict[str, Any] = {
            "per_page": min(per_page, 200),
            "page": page,
            "order_by": "id",
            "order": "asc",
        }
        if params:
            merged.update(params)
        return await self._request("GET", "/observations", params=merged)

    # ------------------------------------------------------------------
    # Taxa
    # ------------------------------------------------------------------

    async def get_taxa(self, taxon_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single taxon by ID.

        Returns taxon details including ancestry chain, rank, common names,
        Wikipedia summary, conservation status, default photo, and children IDs.
        """
        data = await self._request("GET", f"/taxa/{taxon_id}")
        results = data.get("results", [])
        return results[0] if results else None

    async def search_taxa(
        self,
        query: str,
        rank: Optional[str] = None,
        is_active: Optional[bool] = None,
        per_page: int = 30,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Search taxa by name or keyword.

        Args:
            query: Taxon name or search term.
            rank: Taxonomic rank filter (e.g. 'species', 'genus', 'family').
            is_active: If True, only return currently accepted taxa.
            per_page: Results per page (max 200).
            page: Page number.

        Returns:
            API response with ``results`` list of taxon objects.
        """
        params: Dict[str, Any] = {
            "q": query,
            "per_page": min(per_page, 200),
            "page": page,
        }
        if rank:
            params["rank"] = rank
        if is_active is not None:
            params["is_active"] = str(is_active).lower()

        return await self._request("GET", "/taxa", params=params)

    async def get_taxon_children(
        self,
        taxon_id: int,
        per_page: int = 200,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Get direct child taxa of a parent taxon.

        Used for recursive tree traversal during full kingdom ingestion.
        """
        params: Dict[str, Any] = {
            "taxon_id": taxon_id,
            "per_page": min(per_page, 200),
            "page": page,
            "order_by": "id",
            "order": "asc",
        }
        return await self._request("GET", "/taxa", params=params)

    async def get_taxon_photos(
        self,
        taxon_id: int,
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve photos associated with a taxon.

        Pulls from iNaturalist taxon photos endpoint. Returns a list of
        photo objects with URLs for square, small, medium, large, and
        original sizes.

        Args:
            taxon_id: iNaturalist taxon ID.
            per_page: Max number of photos to return.

        Returns:
            List of photo dicts with ``id``, ``url``, ``attribution``,
            ``license_code``, and sized URL variants.
        """
        taxon = await self.get_taxa(taxon_id)
        if not taxon:
            return []

        photos: List[Dict[str, Any]] = []
        # Default photo is always first
        default_photo = taxon.get("default_photo")
        if default_photo:
            photos.append(default_photo)

        # Taxon photos array
        for tp in taxon.get("taxon_photos", []):
            photo = tp.get("photo")
            if photo and photo.get("id") != (default_photo or {}).get("id"):
                photos.append(photo)

        return photos[:per_page]

    # ------------------------------------------------------------------
    # Places & Species Counts
    # ------------------------------------------------------------------

    async def get_places(
        self,
        query: str,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Search iNaturalist places by name.

        Returns place records with bounding boxes and admin levels.
        Useful for scoping observations to geographic regions.
        """
        params: Dict[str, Any] = {
            "q": query,
            "per_page": min(per_page, 200),
        }
        return await self._request("GET", "/places/autocomplete", params=params)

    async def get_species_counts(
        self,
        taxon_id: Optional[int] = None,
        place_id: Optional[int] = None,
        quality_grade: str = "research",
        per_page: int = 200,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Get species observation counts, optionally filtered by taxon and place.

        Returns ranked list of species with observation counts. Essential
        for understanding biodiversity density per region.

        Args:
            taxon_id: Parent taxon ID to scope counts.
            place_id: iNaturalist place ID.
            quality_grade: Quality filter ('research', 'needs_id', 'casual').
            per_page: Results per page.
            page: Page number.

        Returns:
            API response with ``results`` list of species count objects.
        """
        params: Dict[str, Any] = {
            "quality_grade": quality_grade,
            "per_page": min(per_page, 200),
            "page": page,
        }
        if taxon_id is not None:
            params["taxon_id"] = taxon_id
        if place_id is not None:
            params["place_id"] = place_id

        return await self._request("GET", "/observations/species_counts", params=params)

    # ------------------------------------------------------------------
    # Streaming / Bulk Helpers
    # ------------------------------------------------------------------

    async def stream_recent_observations(
        self,
        since_date: str,
        taxon_id: Optional[int] = None,
        per_page: int = 200,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream observations created or updated since a given date.

        Paginates through all matching records, yielding individual
        observation objects. Designed for incremental sync pipelines.

        Args:
            since_date: ISO-8601 date string (e.g. '2026-03-01').
            taxon_id: Optional taxon filter.
            per_page: Page size for each API call.

        Yields:
            Individual observation dicts.
        """
        page = 1
        while True:
            params: Dict[str, Any] = {
                "updated_since": since_date,
                "per_page": min(per_page, 200),
                "page": page,
                "order_by": "id",
                "order": "asc",
            }
            if taxon_id is not None:
                params["taxon_id"] = taxon_id

            data = await self._request("GET", "/observations", params=params)
            results = data.get("results", [])

            if not results:
                break

            for obs in results:
                yield obs

            total = data.get("total_results", 0)
            if page * per_page >= total:
                break

            page += 1

    async def paginate_all_taxa(
        self,
        root_taxon_id: int,
        rank: Optional[str] = None,
        per_page: int = 200,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Paginate through all taxa under a root taxon ID.

        Yields individual taxon objects. Handles pagination automatically.

        Args:
            root_taxon_id: Root taxon ID to start from.
            rank: Optional rank filter.
            per_page: Page size.

        Yields:
            Individual taxon dicts.
        """
        page = 1
        while True:
            params: Dict[str, Any] = {
                "taxon_id": root_taxon_id,
                "per_page": min(per_page, 200),
                "page": page,
                "order_by": "id",
                "order": "asc",
            }
            if rank:
                params["rank"] = rank

            data = await self._request("GET", "/taxa", params=params)
            results = data.get("results", [])

            if not results:
                break

            for taxon in results:
                yield taxon

            total = data.get("total_results", 0)
            if page * per_page >= total:
                break

            page += 1

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_kingdom_taxon_id(self, kingdom: str) -> Optional[int]:
        """
        Resolve a kingdom name to its iNaturalist taxon ID.

        Supported kingdoms: fungi, plantae, animalia, bacteria, protista,
        chromista, archaea.
        """
        return KINGDOM_TAXON_IDS.get(kingdom.lower())

    async def health_check(self) -> Dict[str, Any]:
        """
        Verify connectivity to the iNaturalist API.

        Returns a status dict with API reachability and response time.
        """
        start = time.monotonic()
        try:
            # Fetch a well-known taxon (Fungi) as a connectivity test
            data = await self._request("GET", "/taxa/47170")
            elapsed_ms = (time.monotonic() - start) * 1000
            results = data.get("results", [])
            return {
                "status": "healthy",
                "api_url": self.config.base_url,
                "response_time_ms": round(elapsed_ms, 1),
                "test_taxon": results[0].get("name") if results else None,
                "authenticated": bool(self.config.jwt_token),
            }
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            return {
                "status": "error",
                "api_url": self.config.base_url,
                "response_time_ms": round(elapsed_ms, 1),
                "error": str(exc),
            }
