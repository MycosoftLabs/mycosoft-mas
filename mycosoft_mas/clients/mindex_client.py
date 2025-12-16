"""
MINDEX Integration Client

Type-safe client for Mycosoft's MINDEX (Mycological Index) system.
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from .base_client import BaseClient, ClientResponse


class MINDEXSpecies(BaseModel):
    """MINDEX species data model."""
    species_id: str
    scientific_name: str
    common_names: List[str]
    taxonomy: Dict[str, str]
    properties: Dict[str, Any]


class MINDEXClient(BaseClient):
    """
    Client for MINDEX API.
    
    MINDEX provides:
    - Mycological species database
    - Cultivation protocols
    - Research data
    - Growth tracking
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        database_url: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize MINDEX client.
        
        Args:
            base_url: MINDEX API base URL
            api_key: MINDEX API key
            database_url: Direct database connection URL (optional)
            **kwargs: Additional BaseClient arguments
        """
        base_url = base_url or os.getenv("MINDEX_API_URL", "http://mindex-api:8080")
        api_key = api_key or os.getenv("MINDEX_API_KEY")
        
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            **kwargs
        )
        
        self.database_url = database_url or os.getenv("MINDEX_DATABASE_URL")
    
    async def search_species(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> ClientResponse:
        """
        Search for species in MINDEX.
        
        Args:
            query: Search query
            filters: Optional filters (taxonomy, properties, etc.)
            limit: Maximum results to return
            
        Returns:
            ClientResponse with species data
        """
        params = {
            "q": query,
            "limit": limit,
            **(filters or {})
        }
        
        return await self.get("/api/v1/species/search", params=params)
    
    async def get_species(self, species_id: str) -> ClientResponse:
        """
        Get species by ID.
        
        Args:
            species_id: Species identifier
            
        Returns:
            ClientResponse with species data
        """
        return await self.get(f"/api/v1/species/{species_id}", response_model=MINDEXSpecies)
    
    async def get_cultivation_protocol(self, species_id: str) -> ClientResponse:
        """
        Get cultivation protocol for a species.
        
        Args:
            species_id: Species identifier
            
        Returns:
            ClientResponse with cultivation protocol
        """
        return await self.get(f"/api/v1/species/{species_id}/cultivation")
    
    async def log_growth_data(
        self,
        species_id: str,
        data: Dict[str, Any]
    ) -> ClientResponse:
        """
        Log growth data for a species.
        
        Args:
            species_id: Species identifier
            data: Growth observation data
            
        Returns:
            ClientResponse with logged data
        """
        return await self.post(
            f"/api/v1/species/{species_id}/growth",
            json_data=data
        )
    
    async def get_research_papers(
        self,
        species_id: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 10
    ) -> ClientResponse:
        """
        Get research papers from MINDEX.
        
        Args:
            species_id: Optional species filter
            topic: Optional topic filter
            limit: Maximum results
            
        Returns:
            ClientResponse with research papers
        """
        params = {
            "limit": limit,
            **({"species_id": species_id} if species_id else {}),
            **({"topic": topic} if topic else {})
        }
        
        return await self.get("/api/v1/research", params=params)
    
    async def health_check(self) -> bool:
        """Check MINDEX service health."""
        response = await self.get("/health")
        return response.success
