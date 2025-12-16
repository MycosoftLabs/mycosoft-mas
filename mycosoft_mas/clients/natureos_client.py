"""
NatureOS Integration Client

Type-safe client for NatureOS (Nature Operating System) platform.
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

from .base_client import BaseClient, ClientResponse


class NatureOSProject(BaseModel):
    """NatureOS project data model."""
    project_id: str
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class NatureOSClient(BaseClient):
    """
    Client for NatureOS API.
    
    NatureOS provides:
    - Project management
    - Sustainability tracking
    - Resource allocation
    - Environmental monitoring
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize NatureOS client.
        
        Args:
            base_url: NatureOS API base URL
            api_key: NatureOS API key
            tenant_id: Tenant/organization identifier
            **kwargs: Additional BaseClient arguments
        """
        base_url = base_url or os.getenv("NATUREOS_API_URL", "https://api.natureos.io")
        api_key = api_key or os.getenv("NATUREOS_API_KEY")
        
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            **kwargs
        )
        
        self.tenant_id = tenant_id or os.getenv("NATUREOS_TENANT_ID")
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Override to add tenant ID header."""
        headers = super()._get_headers(additional_headers)
        if self.tenant_id:
            headers["X-Tenant-ID"] = self.tenant_id
        return headers
    
    async def list_projects(
        self,
        status: Optional[str] = None,
        limit: int = 20
    ) -> ClientResponse:
        """
        List projects in NatureOS.
        
        Args:
            status: Optional status filter
            limit: Maximum results
            
        Returns:
            ClientResponse with projects list
        """
        params = {
            "limit": limit,
            **({"status": status} if status else {})
        }
        
        return await self.get("/api/v1/projects", params=params)
    
    async def get_project(self, project_id: str) -> ClientResponse:
        """
        Get project by ID.
        
        Args:
            project_id: Project identifier
            
        Returns:
            ClientResponse with project data
        """
        return await self.get(f"/api/v1/projects/{project_id}", response_model=NatureOSProject)
    
    async def create_project(
        self,
        name: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ClientResponse:
        """
        Create a new project in NatureOS.
        
        Args:
            name: Project name
            description: Project description
            metadata: Additional metadata
            
        Returns:
            ClientResponse with created project
        """
        data = {
            "name": name,
            "description": description,
            "metadata": metadata or {}
        }
        
        return await self.post("/api/v1/projects", json_data=data)
    
    async def update_project_status(
        self,
        project_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> ClientResponse:
        """
        Update project status.
        
        Args:
            project_id: Project identifier
            status: New status
            notes: Optional notes
            
        Returns:
            ClientResponse with updated project
        """
        data = {
            "status": status,
            **({"notes": notes} if notes else {})
        }
        
        return await self.put(f"/api/v1/projects/{project_id}/status", json_data=data)
    
    async def get_sustainability_metrics(
        self,
        project_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> ClientResponse:
        """
        Get sustainability metrics.
        
        Args:
            project_id: Optional project filter
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)
            
        Returns:
            ClientResponse with metrics data
        """
        params = {
            **({"project_id": project_id} if project_id else {}),
            **({"start_date": start_date} if start_date else {}),
            **({"end_date": end_date} if end_date else {})
        }
        
        return await self.get("/api/v1/metrics/sustainability", params=params)
    
    async def allocate_resources(
        self,
        project_id: str,
        resources: List[Dict[str, Any]]
    ) -> ClientResponse:
        """
        Allocate resources to a project.
        
        Args:
            project_id: Project identifier
            resources: List of resource allocations
            
        Returns:
            ClientResponse with allocation result
        """
        data = {
            "resources": resources
        }
        
        return await self.post(f"/api/v1/projects/{project_id}/resources", json_data=data)
    
    async def health_check(self) -> bool:
        """Check NatureOS service health."""
        response = await self.get("/health")
        return response.success
