"""
MYCA MINDEX Integration Client - Feb 5, 2026

Provides MYCA with direct access to MINDEX data for answering questions
about fungi, species, compounds, genetics, and research.

This is the exclusive data source for MYCA's knowledge about fungi.
No fallback to external APIs - all data comes from MINDEX.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import aiohttp

logger = logging.getLogger(__name__)


# MINDEX API Configuration
MINDEX_URL = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8001")
MINDEX_API_KEY = os.environ.get("MINDEX_API_KEY", "local-dev-key")
MINDEX_TIMEOUT = 8  # seconds


class MINDEXClient:
    """
    MINDEX client for MYCA to query fungal data.
    
    All data queries should go through this client to ensure
    consistent access to the canonical MINDEX database.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = MINDEX_TIMEOUT,
    ):
        self.base_url = base_url or MINDEX_URL
        self.api_key = api_key or MINDEX_API_KEY
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "MYCA/1.0 (Mycosoft AI)",
                }
            )
        return self._session
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Make request to MINDEX API."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with session.request(
                method,
                url,
                params=params,
                json=json,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"MINDEX API error: {response.status} from {endpoint}")
                    return None
        except asyncio.TimeoutError:
            logger.warning(f"MINDEX request timeout: {endpoint}")
            return None
        except aiohttp.ClientError as e:
            logger.warning(f"MINDEX request error: {e}")
            return None
    
    # =========================================================================
    # SPECIES QUERIES
    # =========================================================================
    
    async def search_species(
        self,
        query: str,
        limit: int = 10,
        include_images: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search for fungal species by name.
        
        Returns list of species with basic info and images.
        """
        data = await self._request(
            "GET",
            "/mindex/species/search",
            params={
                "q": query,
                "limit": limit,
                "include_images": str(include_images).lower(),
            },
        )
        
        if data:
            return data if isinstance(data, list) else data.get("results", [])
        return []
    
    async def get_species_by_id(self, species_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed species information by ID."""
        return await self._request("GET", f"/mindex/species/{species_id}")
    
    async def get_species_by_name(self, scientific_name: str) -> Optional[Dict[str, Any]]:
        """Get species information by scientific name."""
        return await self._request("GET", f"/mindex/species/by-name/{scientific_name}")
    
    # =========================================================================
    # IMAGE QUERIES
    # =========================================================================
    
    async def get_species_images(
        self,
        species_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get images for a species."""
        data = await self._request(
            "GET",
            f"/mindex/images/for-species/{species_id}",
            params={"limit": limit},
        )
        
        if data:
            return data if isinstance(data, list) else data.get("images", [])
        return []
    
    # =========================================================================
    # DNA SEQUENCE QUERIES
    # =========================================================================
    
    async def search_sequences(
        self,
        query: str,
        gene_region: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for DNA sequences by species name or accession."""
        params = {"q": query, "limit": limit}
        if gene_region:
            params["gene_region"] = gene_region
        
        data = await self._request("GET", "/mindex/sequences/search", params=params)
        
        if data:
            return data if isinstance(data, list) else data.get("sequences", [])
        return []
    
    async def get_species_sequences(
        self,
        species_id: int,
        gene_region: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get DNA sequences for a species."""
        params = {"limit": limit}
        if gene_region:
            params["gene_region"] = gene_region
        
        data = await self._request(
            "GET",
            f"/mindex/sequences/for-species/{species_id}",
            params=params,
        )
        
        if data:
            return data if isinstance(data, list) else data.get("sequences", [])
        return []
    
    # =========================================================================
    # RESEARCH PAPER QUERIES
    # =========================================================================
    
    async def search_research(
        self,
        query: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for research papers."""
        params = {"q": query, "limit": limit}
        if year_from:
            params["year_from"] = year_from
        if year_to:
            params["year_to"] = year_to
        
        data = await self._request("GET", "/mindex/research/search", params=params)
        
        if data:
            return data if isinstance(data, list) else data.get("papers", [])
        return []
    
    async def get_species_research(
        self,
        species_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get research papers for a species."""
        data = await self._request(
            "GET",
            f"/mindex/research/for-species/{species_id}",
            params={"limit": limit},
        )
        
        if data:
            return data if isinstance(data, list) else data.get("papers", [])
        return []
    
    # =========================================================================
    # COMPOUND QUERIES
    # =========================================================================
    
    async def search_compounds(
        self,
        query: str,
        compound_class: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for chemical compounds."""
        params = {"q": query, "limit": limit}
        if compound_class:
            params["compound_class"] = compound_class
        
        data = await self._request("GET", "/mindex/compounds/search", params=params)
        
        if data:
            return data if isinstance(data, list) else data.get("compounds", [])
        return []
    
    async def get_species_compounds(
        self,
        species_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get compounds produced by a species."""
        data = await self._request(
            "GET",
            f"/mindex/compounds/for-species/{species_id}",
            params={"limit": limit},
        )
        
        if data:
            return data if isinstance(data, list) else data.get("compounds", [])
        return []
    
    # =========================================================================
    # UNIFIED SEARCH
    # =========================================================================
    
    async def unified_search(
        self,
        query: str,
        include_species: bool = True,
        include_images: bool = False,
        include_sequences: bool = False,
        include_research: bool = False,
        include_compounds: bool = False,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Unified search across all MINDEX data types.
        
        Returns combined results from species, compounds, sequences, research.
        """
        data = await self._request(
            "GET",
            "/mindex/unified/search",
            params={
                "q": query,
                "include_species": str(include_species).lower(),
                "include_images": str(include_images).lower(),
                "include_sequences": str(include_sequences).lower(),
                "include_research": str(include_research).lower(),
                "include_compounds": str(include_compounds).lower(),
                "limit": limit,
            },
        )
        
        return data or {
            "query": query,
            "results": {
                "species": [],
                "compounds": [],
                "genetics": [],
                "research": [],
            },
            "totalCount": 0,
        }
    
    # =========================================================================
    # KNOWLEDGE GRAPH QUERIES
    # =========================================================================
    
    async def query_knowledge_graph(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query the MINDEX knowledge graph."""
        data = await self._request(
            "POST",
            "/mindex/knowledge/search",
            json={"query": query, "limit": limit},
        )
        
        if data:
            return data if isinstance(data, list) else data.get("nodes", [])
        return []
    
    async def get_knowledge_node(
        self,
        node_id: str,
        depth: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """Get a knowledge graph node with edges."""
        return await self._request(
            "GET",
            f"/mindex/knowledge/nodes/{node_id}",
            params={"depth": depth},
        )
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get MINDEX database statistics."""
        data = await self._request("GET", "/mindex/stats")
        return data or {
            "species": 0,
            "images": 0,
            "sequences": 0,
            "papers": 0,
            "compounds": 0,
        }


# Global MINDEX client instance
_mindex_client: Optional[MINDEXClient] = None


def get_mindex_client() -> MINDEXClient:
    """Get global MINDEX client instance."""
    global _mindex_client
    if _mindex_client is None:
        _mindex_client = MINDEXClient()
    return _mindex_client


# =========================================================================
# HELPER FUNCTIONS FOR MYCA RESPONSES
# =========================================================================

async def get_species_summary(species_name: str) -> str:
    """
    Get a summary about a fungal species for MYCA to use in responses.
    """
    client = get_mindex_client()
    
    # Search for species
    species_list = await client.search_species(species_name, limit=1)
    
    if not species_list:
        return f"I don't have detailed information about '{species_name}' in my MINDEX database yet."
    
    species = species_list[0]
    
    # Build summary
    parts = []
    
    name = species.get("scientific_name", species_name)
    common_name = species.get("common_name")
    if common_name and common_name != name:
        parts.append(f"{common_name} ({name})")
    else:
        parts.append(name)
    
    # Taxonomy
    taxonomy = species.get("taxonomy", {})
    family = taxonomy.get("family") or species.get("family")
    if family:
        parts.append(f"Family: {family}")
    
    # Description
    description = species.get("description", "")
    if description:
        parts.append(description[:300] + "..." if len(description) > 300 else description)
    
    return " | ".join(parts)


async def get_compound_info(compound_name: str) -> str:
    """
    Get information about a fungal compound for MYCA.
    """
    client = get_mindex_client()
    
    compounds = await client.search_compounds(compound_name, limit=1)
    
    if not compounds:
        return f"I don't have detailed information about '{compound_name}' in MINDEX."
    
    compound = compounds[0]
    
    parts = [compound.get("name", compound_name)]
    
    formula = compound.get("molecular_formula") or compound.get("formula")
    if formula:
        parts.append(f"Formula: {formula}")
    
    compound_class = compound.get("compound_class") or compound.get("chemicalClass")
    if compound_class:
        parts.append(f"Class: {compound_class}")
    
    species = compound.get("producing_species", [])
    if species:
        parts.append(f"Produced by: {', '.join(species[:3])}")
    
    activities = compound.get("biologicalActivity", [])
    if activities:
        parts.append(f"Activity: {', '.join(activities[:3])}")
    
    return " | ".join(parts)


async def search_fungal_knowledge(query: str) -> Dict[str, Any]:
    """
    Search MINDEX for any fungal knowledge.
    Returns structured data for MYCA to format into a response.
    """
    client = get_mindex_client()
    
    return await client.unified_search(
        query=query,
        include_species=True,
        include_compounds=True,
        include_research=True,
        include_sequences=True,
        limit=5,
    )


async def get_mindex_context_for_query(query: str) -> str:
    """
    Get MINDEX context to inject into MYCA's LLM prompt for answering questions.
    """
    result = await search_fungal_knowledge(query)
    
    parts = []
    
    # Species
    species = result.get("results", {}).get("species", [])
    if species:
        species_info = []
        for sp in species[:3]:
            name = sp.get("scientificName", sp.get("scientific_name", ""))
            common = sp.get("commonName", sp.get("common_name", ""))
            desc = sp.get("description", "")[:150]
            species_info.append(f"- {common} ({name}): {desc}")
        parts.append("SPECIES FROM MINDEX:\n" + "\n".join(species_info))
    
    # Compounds
    compounds = result.get("results", {}).get("compounds", [])
    if compounds:
        compound_info = []
        for c in compounds[:3]:
            name = c.get("name", "")
            formula = c.get("formula", c.get("molecular_formula", ""))
            compound_info.append(f"- {name} ({formula})")
        parts.append("COMPOUNDS FROM MINDEX:\n" + "\n".join(compound_info))
    
    # Research
    research = result.get("results", {}).get("research", [])
    if research:
        research_info = []
        for r in research[:2]:
            title = r.get("title", "")
            year = r.get("year", "")
            research_info.append(f"- \"{title}\" ({year})")
        parts.append("RESEARCH FROM MINDEX:\n" + "\n".join(research_info))
    
    if not parts:
        return f"No MINDEX data found for query: {query}"
    
    return "\n\n".join(parts)
