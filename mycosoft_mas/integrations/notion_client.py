"""
Notion Integration Client

This module provides integration with Notion API for knowledge management and documentation.
Notion is used for:
- Project documentation
- Task management
- Knowledge base
- Meeting notes
- Agent logs and reports

Environment Variables:
    NOTION_API_KEY: Notion API integration token
    NOTION_DATABASE_ID: Default database ID for operations

Usage:
    from mycosoft_mas.integrations.notion_client import NotionClient
    
    client = NotionClient()
    pages = await client.query_database(database_id="abc123")
    page = await client.create_page(database_id="abc123", properties={"Title": "New Page"})
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class NotionClient:
    """
    Client for interacting with Notion API.
    
    Notion provides:
    - Database management
    - Page creation and editing
    - Block manipulation
    - Search functionality
    - User and workspace management
    
    This client handles Notion API v1 authentication and operations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Notion client.
        
        Args:
            config: Optional configuration dictionary. If not provided, reads from environment variables.
                   Expected keys:
                   - api_key: Notion API integration token
                   - database_id: Default database ID
                   - timeout: Request timeout in seconds (default: 30)
        
        Note:
            API key is obtained from Notion integration settings.
            Integration must be added to the workspace and granted appropriate permissions.
        """
        self.config = config or {}
        
        # API endpoint
        self.api_url = "https://api.notion.com/v1"
        
        # Authentication
        self.api_key = self.config.get(
            "api_key",
            os.getenv("NOTION_API_KEY", "")
        )
        
        self.default_database_id = self.config.get(
            "database_id",
            os.getenv("NOTION_DATABASE_ID", "")
        )
        
        # Connection settings
        self.timeout = self.config.get("timeout", 30)
        
        # HTTP client (lazy loading)
        self._http_client = None
        
        self.logger = logging.getLogger(__name__)
        if self.api_key:
            self.logger.info("Notion client initialized")
        else:
            self.logger.warning("Notion client initialized without API key")
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client for Notion API access.
        
        Returns:
            httpx.AsyncClient: HTTP client with Notion API headers
            
        Note:
            Notion API requires specific headers:
            - Authorization: Bearer token
            - Notion-Version: API version (2022-06-28)
            - Content-Type: application/json
        """
        if self._http_client is None:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            self._http_client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True
            )
        
        return self._http_client
    
    async def query_database(
        self,
        database_id: Optional[str] = None,
        filter_properties: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        start_cursor: Optional[str] = None,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Query a Notion database.
        
        Args:
            database_id: Database ID (uses default if not provided)
            filter_properties: Filter conditions
            sorts: Sort order
            start_cursor: Pagination cursor
            page_size: Number of results per page (max 100)
        
        Returns:
            Query results with pages and next_cursor for pagination
        
        Example:
            results = await client.query_database(
                database_id="abc123",
                filter_properties={"Status": {"equals": "Active"}},
                sorts=[{"property": "Created", "direction": "descending"}]
            )
            for page in results['results']:
                print(page['properties']['Title']['title'][0]['plain_text'])
        """
        if not database_id:
            database_id = self.default_database_id
        
        if not database_id:
            raise ValueError("database_id is required")
        
        try:
            client = await self._get_http_client()
            payload = {"page_size": min(page_size, 100)}
            
            if filter_properties:
                payload["filter"] = filter_properties
            if sorts:
                payload["sorts"] = sorts
            if start_cursor:
                payload["start_cursor"] = start_cursor
            
            response = await client.post(f"/databases/{database_id}/query", json=payload)
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"Queried database {database_id}, got {len(data.get('results', []))} results")
            return data
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error querying database: {e}")
            raise
    
    async def create_page(
        self,
        database_id: Optional[str] = None,
        properties: Dict[str, Any] = None,
        children: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create a new page in a Notion database.
        
        Args:
            database_id: Database ID (uses default if not provided)
            properties: Page properties (title, status, etc.)
            children: Optional page content blocks
        
        Returns:
            Created page object
        
        Example:
            page = await client.create_page(
                database_id="abc123",
                properties={
                    "Title": {"title": [{"text": {"content": "New Page"}}]},
                    "Status": {"select": {"name": "Active"}}
                }
            )
        """
        if not database_id:
            database_id = self.default_database_id
        
        if not database_id:
            raise ValueError("database_id is required")
        
        if properties is None:
            properties = {}
        
        try:
            client = await self._get_http_client()
            payload = {
                "parent": {"database_id": database_id},
                "properties": properties
            }
            if children:
                payload["children"] = children
            
            response = await client.post("/pages", json=payload)
            response.raise_for_status()
            
            page = response.json()
            self.logger.info(f"Created page {page['id']} in database {database_id}")
            return page
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error creating page: {e}")
            raise
    
    async def update_page(
        self,
        page_id: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a Notion page.
        
        Args:
            page_id: Page ID to update
            properties: Properties to update
        
        Returns:
            Updated page object
        
        Example:
            page = await client.update_page(
                page_id="abc123",
                properties={"Status": {"select": {"name": "Completed"}}}
            )
        """
        try:
            client = await self._get_http_client()
            payload = {"properties": properties}
            
            response = await client.patch(f"/pages/{page_id}", json=payload)
            response.raise_for_status()
            
            self.logger.info(f"Updated page {page_id}")
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error updating page: {e}")
            raise
    
    async def append_blocks(
        self,
        page_id: str,
        children: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Append blocks to a Notion page.
        
        Args:
            page_id: Page ID
            children: List of block objects to append
        
        Returns:
            Block creation response
        
        Example:
            await client.append_blocks(
                page_id="abc123",
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": "Hello!"}}]
                        }
                    }
                ]
            )
        """
        try:
            client = await self._get_http_client()
            payload = {"children": children}
            
            response = await client.patch(f"/blocks/{page_id}/children", json=payload)
            response.raise_for_status()
            
            self.logger.info(f"Appended blocks to page {page_id}")
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error appending blocks: {e}")
            raise
    
    async def search(
        self,
        query: Optional[str] = None,
        filter_properties: Optional[Dict[str, Any]] = None,
        sort_properties: Optional[Dict[str, Any]] = None,
        start_cursor: Optional[str] = None,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Search across Notion workspace.
        
        Args:
            query: Search query string
            filter_properties: Filter by object type (page, database, etc.)
            sort_properties: Sort order
            start_cursor: Pagination cursor
            page_size: Results per page
        
        Returns:
            Search results
        
        Example:
            results = await client.search(query="project status", filter_properties={"property": "object", "value": "page"})
        """
        try:
            client = await self._get_http_client()
            payload = {"page_size": min(page_size, 100)}
            
            if query:
                payload["query"] = query
            if filter_properties:
                payload["filter"] = filter_properties
            if sort_properties:
                payload["sort"] = sort_properties
            if start_cursor:
                payload["start_cursor"] = start_cursor
            
            response = await client.post("/search", json=payload)
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"Search returned {len(data.get('results', []))} results")
            return data
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error searching Notion: {e}")
            raise
    
    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """
        Get a Notion page by ID.
        
        Args:
            page_id: Page ID
        
        Returns:
            Page object with properties and content
        """
        try:
            client = await self._get_http_client()
            response = await client.get(f"/pages/{page_id}")
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error getting page {page_id}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Notion API health.
        
        Returns:
            Health status dictionary
        
        Note:
            Performs API connectivity check.
            Used for monitoring Notion integration availability.
        """
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unknown"
        }
        
        if not self.api_key:
            health["status"] = "error"
            health["error"] = "API key not configured"
            return health
        
        try:
            client = await self._get_http_client()
            # Use search endpoint as health check (lightweight)
            response = await client.post("/search", json={"page_size": 1}, timeout=5)
            if response.status_code == 200:
                health["status"] = "ok"
            else:
                health["status"] = "error"
                health["error"] = f"HTTP {response.status_code}"
        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)
        
        return health
    
    async def close(self):
        """Close HTTP client and clean up resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        
        self.logger.info("Notion client connections closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes connections."""
        await self.close()

