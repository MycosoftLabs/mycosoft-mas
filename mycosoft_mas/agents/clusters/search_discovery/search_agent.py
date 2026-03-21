"""
Search Agent for Mycology BioAgent System

This agent handles search and discovery operations for mycology research data.
It provides functionality for searching across various data sources and discovering
relevant information.
"""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus


class SearchType(Enum):
    """Types of search operations"""

    KEYWORD = auto()
    SEMANTIC = auto()
    FUZZY = auto()
    REGEX = auto()
    STRUCTURED = auto()


@dataclass
class SearchQuery:
    """Search query configuration"""

    query_type: SearchType
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: Optional[int] = None
    offset: int = 0
    sort_by: Optional[str] = None
    sort_order: str = "desc"


@dataclass
class SearchResult:
    """Results of a search operation"""

    result_id: str
    query: SearchQuery
    matches: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class SearchAgent(BaseAgent):
    """Agent for performing search and discovery operations"""

    def __init__(
        self, agent_id: str, name: str = "SearchAgent", config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.search_results: Dict[str, SearchResult] = {}
        self.search_queue: asyncio.Queue = asyncio.Queue()
        self.index_queue: asyncio.Queue = asyncio.Queue()

        # Create necessary directories
        self.data_dir = Path("data/search")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metrics
        self.metrics.update(
            {"searches_performed": 0, "results_found": 0, "index_updates": 0, "search_errors": 0}
        )

        self.mindex_api_url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
        self.mindex_api_key = os.getenv("MINDEX_API_KEY")

    async def initialize(self) -> None:
        """Initialize the agent"""
        await super().initialize()
        self.status = AgentStatus.READY
        self.logger.info("Search Agent initialized")

    async def stop(self) -> None:
        """Stop the agent"""
        self.status = AgentStatus.STOPPING
        self.logger.info("Stopping Search Agent")
        await super().stop()

    async def search(self, query: SearchQuery) -> str:
        """Perform a search operation"""
        result_id = f"search_{len(self.search_results)}"

        try:
            # Add to search queue
            await self.search_queue.put({"result_id": result_id, "query": query})

            # Wait for result
            while result_id not in self.search_results:
                await asyncio.sleep(0.1)

            return result_id

        except Exception as e:
            self.logger.error(f"Error performing search: {str(e)}")
            self.metrics["search_errors"] += 1
            raise

    async def get_search_result(self, result_id: str) -> Optional[SearchResult]:
        """Get the results of a specific search"""
        return self.search_results.get(result_id)

    async def update_index(self, data: Dict[str, Any]) -> None:
        """Update the search index with new data"""
        try:
            await self.index_queue.put(data)
        except Exception as e:
            self.logger.error(f"Error updating index: {str(e)}")
            raise

    async def _process_search_queue(self) -> None:
        """Process the search queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next search task
                task = await self.search_queue.get()

                # Perform search
                result = await self._perform_search(task["result_id"], task["query"])

                # Store result
                self.search_results[task["result_id"]] = result

                # Update metrics
                self.metrics["searches_performed"] += 1
                self.metrics["results_found"] += len(result.matches)

                # Mark task as complete
                self.search_queue.task_done()

            except Exception as e:
                self.logger.error(f"Error processing search: {str(e)}")
                self.metrics["search_errors"] += 1
                continue

    async def _process_index_queue(self) -> None:
        """Process the index queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next index update
                data = await self.index_queue.get()

                # Update index
                await self._update_search_index(data)

                # Update metrics
                self.metrics["index_updates"] += 1

                # Mark task as complete
                self.index_queue.task_done()

            except Exception as e:
                self.logger.error(f"Error processing index update: {str(e)}")
                continue

    async def _perform_search(self, result_id: str, query: SearchQuery) -> SearchResult:
        """Perform the actual search operation"""
        try:
            matches = []

            if query.query_type == SearchType.KEYWORD:
                matches = await self._keyword_search(query)
            elif query.query_type == SearchType.SEMANTIC:
                matches = await self._semantic_search(query)
            elif query.query_type == SearchType.FUZZY:
                matches = await self._fuzzy_search(query)
            elif query.query_type == SearchType.REGEX:
                matches = await self._regex_search(query)
            elif query.query_type == SearchType.STRUCTURED:
                matches = await self._structured_search(query)

            return SearchResult(result_id=result_id, query=query, matches=matches)

        except Exception as e:
            self.logger.error(f"Error performing search: {str(e)}")
            raise

    async def _keyword_search(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """Perform keyword-based search"""
        limit = query.limit or 10
        types = query.filters.get("types") if isinstance(query.filters, dict) else None
        if not types:
            types = ["taxa", "compounds", "genetics"]
        params: Dict[str, Any] = {
            "q": query.query,
            "types": ",".join(types),
            "limit": limit,
        }
        for key in ("toxicity", "lat", "lng", "radius"):
            if key in query.filters:
                params[key] = query.filters[key]

        data = await self._call_mindex("/api/mindex/unified-search", params)
        results = data.get("results", {}) if isinstance(data, dict) else {}
        matches: List[Dict[str, Any]] = []
        for result_type, items in results.items():
            for item in items:
                matches.append({"type": result_type, "data": item, "source": "mindex"})
        return matches

    async def _semantic_search(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """Perform semantic search"""
        limit = query.limit or 10
        results: List[Dict[str, Any]] = []

        mindex_data = await self._call_mindex(
            "/api/mindex/unified-search",
            {"q": query.query, "types": "taxa,compounds,genetics", "limit": limit},
        )
        mindex_results = mindex_data.get("results", {}) if isinstance(mindex_data, dict) else {}
        for result_type, items in mindex_results.items():
            for item in items:
                results.append({"type": result_type, "data": item, "source": "mindex"})

        from mycosoft_mas.integrations.exa_client import get_exa_client

        exa = get_exa_client()
        if exa.is_configured:
            exa_response = await exa.semantic_search(
                query=query.query,
                num_results=min(limit, 10),
                include_text=True,
                include_highlights=True,
                category=query.filters.get("category") if isinstance(query.filters, dict) else None,
            )
            for item in exa_response.results or []:
                results.append({"type": "web", "data": item.model_dump(), "source": "exa"})

        return results

    async def _fuzzy_search(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """Perform fuzzy search"""
        limit = query.limit or 20
        data = await self._call_mindex("/api/mindex/taxa", {"q": query.query, "limit": limit})
        taxa = data.get("data", []) if isinstance(data, dict) else []
        matches: List[Dict[str, Any]] = []
        for item in taxa:
            candidates = [item.get("canonical_name", ""), item.get("common_name", "")]
            best_score = 0.0
            for candidate in candidates:
                if not candidate:
                    continue
                score = SequenceMatcher(None, query.query.lower(), candidate.lower()).ratio()
                best_score = max(best_score, score)
            if best_score >= 0.65:
                matches.append(
                    {
                        "type": "taxa",
                        "data": item,
                        "source": "mindex",
                        "score": round(best_score, 3),
                    }
                )
        matches.sort(key=lambda m: m.get("score", 0), reverse=True)
        return matches[:limit]

    async def _regex_search(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """Perform regex-based search"""
        try:
            pattern = re.compile(query.query, re.IGNORECASE)
        except re.error:
            return []
        limit = query.limit or 50
        data = await self._call_mindex("/api/mindex/taxa", {"q": query.query, "limit": limit})
        taxa = data.get("data", []) if isinstance(data, dict) else []
        matches = [
            {"type": "taxa", "data": item, "source": "mindex"}
            for item in taxa
            if pattern.search(item.get("canonical_name", ""))
            or pattern.search(item.get("common_name", ""))
        ]
        return matches[:limit]

    async def _structured_search(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """Perform structured search"""
        limit = query.limit or 10
        filters = query.filters or {}
        params: Dict[str, Any] = {
            "q": query.query,
            "types": ",".join(filters.get("types", ["taxa", "compounds", "genetics"])),
            "limit": limit,
        }
        if "toxicity" in filters:
            params["toxicity"] = filters["toxicity"]
        if "lat" in filters and "lng" in filters:
            params["lat"] = filters["lat"]
            params["lng"] = filters["lng"]
            params["radius"] = filters.get("radius", 100)
            params["types"] = params["types"] + ",observations"

        data = await self._call_mindex("/api/mindex/unified-search", params)
        results = data.get("results", {}) if isinstance(data, dict) else {}
        matches: List[Dict[str, Any]] = []
        for result_type, items in results.items():
            for item in items:
                matches.append({"type": result_type, "data": item, "source": "mindex"})
        return matches

    async def _update_search_index(self, data: Dict[str, Any]) -> None:
        """Update the search index with new data"""
        try:
            index_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
            }
            file_path = self.data_dir / f"index_update_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
            with file_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(index_entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to update index: {e}")

    async def _call_mindex(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        headers = {}
        if self.mindex_api_key:
            headers["X-API-Key"] = self.mindex_api_key
        url = f"{self.mindex_api_url}{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code != 200:
                return {}
            return response.json()
