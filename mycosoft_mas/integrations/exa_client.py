"""
Exa Client - Feb 11, 2026

Exa (exa.ai) is a semantic search API for finding web content by meaning.
This client provides async methods for searching and finding similar content.

Usage:
    client = ExaClient(api_key="...")
    results = await client.semantic_search("psilocybin research 2024")
"""

import os
import httpx
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

# Exa API base URL
EXA_API_BASE = "https://api.exa.ai"


class ExaResult(BaseModel):
    """A single Exa search result"""
    id: str
    url: str
    title: str
    score: float = 0.0
    published_date: Optional[str] = None
    author: Optional[str] = None
    text: Optional[str] = None  # Snippet or full text
    highlights: List[str] = Field(default_factory=list)
    summary: Optional[str] = None


class ExaSearchResponse(BaseModel):
    """Response from Exa search"""
    results: List[ExaResult]
    autoprompt_string: Optional[str] = None
    request_id: Optional[str] = None


class ExaClient:
    """
    Client for the Exa semantic search API.
    
    Features:
    - Semantic search (find content by meaning)
    - Find similar (find pages similar to a given URL)
    - Auto-prompt (Exa enhances your query)
    - Content retrieval (get full text or summaries)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=EXA_API_BASE,
                timeout=self.timeout,
                headers={
                    "x-api-key": self.api_key or "",
                    "Content-Type": "application/json",
                },
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def semantic_search(
        self,
        query: str,
        num_results: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        use_autoprompt: bool = True,
        category: Optional[str] = None,
        include_text: bool = True,
        include_highlights: bool = True,
    ) -> ExaSearchResponse:
        """
        Perform a semantic search using Exa.
        
        Args:
            query: Natural language search query
            num_results: Number of results to return (1-100)
            include_domains: Only include results from these domains
            exclude_domains: Exclude results from these domains
            start_published_date: Filter by publish date (YYYY-MM-DD)
            end_published_date: Filter by publish date (YYYY-MM-DD)
            use_autoprompt: Let Exa enhance your query
            category: Filter by category (e.g., "research paper", "news")
            include_text: Include page text snippets
            include_highlights: Include highlighted passages
            
        Returns:
            ExaSearchResponse with results
        """
        if not self.api_key:
            logger.warning("Exa API key not configured")
            return ExaSearchResponse(results=[])
        
        try:
            client = await self._get_client()
            
            # Build request payload
            payload: Dict[str, Any] = {
                "query": query,
                "numResults": min(num_results, 100),
                "useAutoprompt": use_autoprompt,
                "type": "neural",  # Use semantic search (vs keyword)
            }
            
            # Optional filters
            if include_domains:
                payload["includeDomains"] = include_domains
            if exclude_domains:
                payload["excludeDomains"] = exclude_domains
            if start_published_date:
                payload["startPublishedDate"] = start_published_date
            if end_published_date:
                payload["endPublishedDate"] = end_published_date
            if category:
                payload["category"] = category
            
            # Content options
            contents: Dict[str, Any] = {}
            if include_text:
                contents["text"] = {"maxCharacters": 1000}
            if include_highlights:
                contents["highlights"] = {"numSentences": 3, "highlightsPerUrl": 2}
            if contents:
                payload["contents"] = contents
            
            response = await client.post("/search", json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Parse results
            results = []
            for item in data.get("results", []):
                results.append(ExaResult(
                    id=item.get("id", ""),
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    score=item.get("score", 0.0),
                    published_date=item.get("publishedDate"),
                    author=item.get("author"),
                    text=item.get("text"),
                    highlights=item.get("highlights", []),
                    summary=item.get("summary"),
                ))
            
            return ExaSearchResponse(
                results=results,
                autoprompt_string=data.get("autopromptString"),
                request_id=data.get("requestId"),
            )
            
        except httpx.HTTPError as e:
            logger.error(f"Exa API error: {e}")
            return ExaSearchResponse(results=[])
        except Exception as e:
            logger.error(f"Exa search failed: {e}")
            return ExaSearchResponse(results=[])
    
    async def find_similar(
        self,
        url: str,
        num_results: int = 10,
        include_text: bool = True,
    ) -> ExaSearchResponse:
        """
        Find pages similar to a given URL.
        
        Args:
            url: URL to find similar pages for
            num_results: Number of results to return
            include_text: Include page text snippets
            
        Returns:
            ExaSearchResponse with similar pages
        """
        if not self.api_key:
            logger.warning("Exa API key not configured")
            return ExaSearchResponse(results=[])
        
        try:
            client = await self._get_client()
            
            payload: Dict[str, Any] = {
                "url": url,
                "numResults": min(num_results, 100),
            }
            
            if include_text:
                payload["contents"] = {"text": {"maxCharacters": 1000}}
            
            response = await client.post("/findSimilar", json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append(ExaResult(
                    id=item.get("id", ""),
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    score=item.get("score", 0.0),
                    published_date=item.get("publishedDate"),
                    text=item.get("text"),
                ))
            
            return ExaSearchResponse(results=results, request_id=data.get("requestId"))
            
        except Exception as e:
            logger.error(f"Exa find similar failed: {e}")
            return ExaSearchResponse(results=[])
    
    async def get_contents(
        self,
        ids: List[str],
        include_text: bool = True,
        include_highlights: bool = False,
    ) -> List[ExaResult]:
        """
        Get full content for specific result IDs.
        
        Args:
            ids: List of Exa result IDs to retrieve
            include_text: Include full page text
            include_highlights: Include highlighted passages
            
        Returns:
            List of ExaResult with content
        """
        if not self.api_key:
            return []
        
        try:
            client = await self._get_client()
            
            payload: Dict[str, Any] = {"ids": ids}
            contents: Dict[str, Any] = {}
            if include_text:
                contents["text"] = {"maxCharacters": 5000}
            if include_highlights:
                contents["highlights"] = {"numSentences": 5}
            if contents:
                payload["contents"] = contents
            
            response = await client.post("/contents", json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append(ExaResult(
                    id=item.get("id", ""),
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    text=item.get("text"),
                    highlights=item.get("highlights", []),
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Exa get contents failed: {e}")
            return []


# Singleton instance
_exa_client: Optional[ExaClient] = None


def get_exa_client() -> ExaClient:
    """Get the singleton Exa client"""
    global _exa_client
    if _exa_client is None:
        _exa_client = ExaClient()
    return _exa_client
