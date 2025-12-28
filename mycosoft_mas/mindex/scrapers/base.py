"""
Base Scraper Class for MINDEX

Provides common functionality for all data scrapers including:
- Rate limiting
- Retry logic
- Data validation
- Progress tracking
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ScraperResult:
    """Result from a scraper operation."""
    
    source: str
    data_type: str
    records: list[dict[str, Any]]
    total_count: int
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScraperConfig:
    """Configuration for a scraper."""
    
    rate_limit_per_second: float = 1.0
    max_retries: int = 3
    timeout_seconds: int = 30
    batch_size: int = 100
    max_records: Optional[int] = None


class BaseScraper(ABC):
    """Abstract base class for all MINDEX scrapers."""
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_request_time: float = 0
        self._request_count: int = 0
        
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data source."""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the API."""
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            headers=self._get_default_headers(),
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers for requests."""
        return {
            "User-Agent": "MYCOSOFT-MINDEX/1.0 (https://mycosoft.io; mindex@mycosoft.io)",
            "Accept": "application/json",
        }
    
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        import time
        current_time = time.time()
        min_interval = 1.0 / self.config.rate_limit_per_second
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        self._last_request_time = time.time()
    
    async def _request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> Optional[dict[str, Any]]:
        """Make an API request with rate limiting and retry logic."""
        if not self.session:
            raise RuntimeError("Scraper must be used as async context manager")
        
        await self._rate_limit()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.max_retries):
            try:
                async with self.session.request(
                    method,
                    url,
                    params=params,
                    json=data,
                ) as response:
                    self._request_count += 1
                    
                    if response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        return None
    
    @abstractmethod
    async def search_species(
        self,
        query: str,
        limit: int = 100,
    ) -> ScraperResult:
        """Search for species by name or keyword."""
        pass
    
    @abstractmethod
    async def get_species_details(
        self,
        species_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get detailed information about a specific species."""
        pass
    
    @abstractmethod
    async def fetch_all(
        self,
        limit: Optional[int] = None,
    ) -> AsyncIterator[ScraperResult]:
        """Fetch all available data in batches."""
        pass
    
    def validate_record(self, record: dict[str, Any]) -> bool:
        """Validate a scraped record. Override in subclasses for custom validation."""
        return bool(record)
    
    def normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize a record to MINDEX format. Override in subclasses."""
        return {
            "source": self.source_name,
            "raw_data": record,
            "scraped_at": datetime.utcnow().isoformat(),
        }
