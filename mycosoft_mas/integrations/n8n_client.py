"""
N8N Workflow Automation Integration Client

This module provides integration with N8N (https://n8n.io/) for workflow automation.
N8N is used for:
- Workflow orchestration
- Task automation
- Data pipelines
- Event-driven actions
- Integration between systems

Environment Variables:
    N8N_WEBHOOK_URL: N8N webhook base URL (default: http://localhost:5678)
    N8N_API_KEY: N8N API key for authenticated requests (optional)

Usage:
    from mycosoft_mas.integrations.n8n_client import N8NClient
    
    client = N8NClient()
    result = await client.trigger_workflow(workflow_id="abc123", data={"key": "value"})
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class N8NClient:
    """
    Client for interacting with N8N workflow automation platform.
    
    N8N provides:
    - Webhook triggers for workflows
    - Workflow execution
    - Workflow management
    - Execution history
    - Node operations
    
    This client handles both webhook triggers and API operations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the N8N client.
        
        Args:
            config: Optional configuration dictionary. If not provided, reads from environment variables.
                   Expected keys:
                   - webhook_url: N8N webhook base URL
                   - api_url: N8N API base URL (if different from webhook)
                   - api_key: N8N API key for authenticated requests
                   - timeout: Request timeout in seconds (default: 30)
        
        Note:
            N8N can be accessed via:
            1. Webhooks (public URLs for triggering workflows)
            2. API (for management and execution control)
        """
        self.config = config or {}
        
        # Webhook URL (for triggering workflows)
        self.webhook_url = self.config.get(
            "webhook_url",
            os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678")
        ).rstrip('/')
        
        # API URL (for management operations)
        self.api_url = self.config.get(
            "api_url",
            os.getenv("N8N_API_URL", self.webhook_url.replace("/webhook", ""))
        ).rstrip('/')
        
        # Authentication
        self.api_key = self.config.get(
            "api_key",
            os.getenv("N8N_API_KEY", "")
        )
        
        # Connection settings
        self.timeout = self.config.get("timeout", 30)
        
        # HTTP clients (lazy loading)
        self._webhook_client = None
        self._api_client = None
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"N8N client initialized - Webhook: {self.webhook_url}, API: {self.api_url}")
    
    async def _get_webhook_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client for webhook triggers.
        
        Returns:
            httpx.AsyncClient: HTTP client for webhook requests
        """
        if self._webhook_client is None:
            self._webhook_client = httpx.AsyncClient(
                base_url=self.webhook_url,
                timeout=self.timeout,
                follow_redirects=True
            )
        
        return self._webhook_client
    
    async def _get_api_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client for API operations.
        
        Returns:
            httpx.AsyncClient: HTTP client with API authentication
        """
        if self._api_client is None:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            if self.api_key:
                headers["X-N8N-API-KEY"] = self.api_key
            
            self._api_client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True
            )
        
        return self._api_client
    
    async def trigger_workflow(
        self,
        workflow_id: str,
        data: Dict[str, Any],
        method: str = "POST"
    ) -> Dict[str, Any]:
        """
        Trigger an N8N workflow via webhook.
        
        Args:
            workflow_id: Workflow ID or webhook path
            data: Data to send to workflow
            method: HTTP method (POST or GET)
        
        Returns:
            Workflow execution result
        
        Example:
            result = await client.trigger_workflow(
                workflow_id="webhook/my-workflow",
                data={"event": "agent_completed", "agent_id": "agent_1"}
            )
        
        Note:
            Workflow ID can be:
            - Webhook path: "webhook/my-workflow"
            - Workflow ID: "abc123" (requires API access)
            - Full webhook URL path
        """
        try:
            client = await self._get_webhook_client()
            
            # Determine webhook path
            if workflow_id.startswith("webhook/"):
                path = workflow_id
            elif workflow_id.startswith("/"):
                path = workflow_id
            else:
                # Assume it's a workflow ID, try webhook path
                path = f"/webhook/{workflow_id}"
            
            if method.upper() == "GET":
                response = await client.get(path, params=data)
            else:
                response = await client.post(path, json=data)
            
            response.raise_for_status()
            
            self.logger.info(f"Triggered workflow {workflow_id}")
            return response.json() if response.content else {"status": "success"}
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error triggering workflow {workflow_id}: {e}")
            raise
    
    async def get_workflows(self) -> List[Dict[str, Any]]:
        """
        Get list of all workflows (requires API access).
        
        Returns:
            List of workflow dictionaries
        
        Note:
            Requires N8N API key and API access.
            Used for workflow discovery and management.
        """
        try:
            client = await self._get_api_client()
            response = await client.get("/api/v1/workflows")
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"Retrieved {len(data.get('data', []))} workflows")
            return data.get("data", [])
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error getting workflows: {e}")
            raise
    
    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get workflow details (requires API access).
        
        Args:
            workflow_id: Workflow ID
        
        Returns:
            Workflow object with nodes and configuration
        """
        try:
            client = await self._get_api_client()
            response = await client.get(f"/api/v1/workflows/{workflow_id}")
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error getting workflow {workflow_id}: {e}")
            raise
    
    async def execute_workflow(
        self,
        workflow_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow via API (requires API access).
        
        Args:
            workflow_id: Workflow ID
            data: Optional input data
        
        Returns:
            Execution result
        
        Note:
            API execution provides more control than webhook triggers.
            Can pass data directly to workflow input nodes.
        """
        try:
            client = await self._get_api_client()
            payload = {}
            if data:
                payload["data"] = data
            
            response = await client.post(f"/api/v1/workflows/{workflow_id}/execute", json=payload)
            response.raise_for_status()
            
            self.logger.info(f"Executed workflow {workflow_id} via API")
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error executing workflow {workflow_id}: {e}")
            raise
    
    async def get_executions(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get workflow execution history (requires API access).
        
        Args:
            workflow_id: Optional workflow ID filter
            limit: Maximum number of executions
        
        Returns:
            List of execution records
        
        Note:
            Execution history includes:
            - Execution status (success, error, running)
            - Start/end times
            - Input/output data
            - Error messages
        """
        try:
            client = await self._get_api_client()
            params = {"limit": limit}
            if workflow_id:
                params["workflowId"] = workflow_id
            
            response = await client.get("/api/v1/executions", params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error getting executions: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check N8N system health.
        
        Returns:
            Health status dictionary
        
        Note:
            Checks both webhook and API availability.
            Used for monitoring N8N integration status.
        """
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_status": "unknown",
            "api_status": "unknown"
        }
        
        # Check webhook
        try:
            client = await self._get_webhook_client()
            # Try to access webhook root (may return 404, but confirms server is up)
            response = await client.get("/", timeout=5)
            health["webhook_status"] = "ok" if response.status_code < 500 else "error"
        except Exception as e:
            health["webhook_status"] = "error"
            health["webhook_error"] = str(e)
        
        # Check API (if API key configured)
        if self.api_key:
            try:
                api_client = await self._get_api_client()
                response = await api_client.get("/healthz", timeout=5)
                health["api_status"] = "ok" if response.status_code == 200 else "error"
            except Exception as e:
                health["api_status"] = "error"
                health["api_error"] = str(e)
        else:
            health["api_status"] = "not_configured"
        
        return health
    
    async def close(self):
        """Close HTTP clients and clean up resources."""
        if self._webhook_client:
            await self._webhook_client.aclose()
            self._webhook_client = None
        
        if self._api_client:
            await self._api_client.aclose()
            self._api_client = None
        
        self.logger.info("N8N client connections closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes connections."""
        await self.close()

