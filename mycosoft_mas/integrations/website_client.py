"""
Mycosoft Website Integration Client

This module provides integration with the Mycosoft website (https://mycosoft.vercel.app/).
The website is built with Next.js and deployed on Vercel.

The client connects to the website API for:
- Content management
- User interactions
- Form submissions
- Analytics data
- Public API endpoints

Environment Variables:
    WEBSITE_API_URL: Website API endpoint (default: https://mycosoft.vercel.app/api)
    WEBSITE_API_KEY: API key for authenticated requests (optional)

Usage:
    from mycosoft_mas.integrations.website_client import WebsiteClient
    
    client = WebsiteClient()
    content = await client.get_content(page="about")
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class WebsiteClient:
    """
    Client for interacting with the Mycosoft website API.
    
    The website provides:
    - Public content pages
    - Contact forms
    - Newsletter subscriptions
    - API endpoints for integrations
    - Analytics and tracking
    
    This client handles API communication with the Next.js/Vercel deployment.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the website client.
        
        Args:
            config: Optional configuration dictionary. If not provided, reads from environment variables.
                   Expected keys:
                   - api_url: Website API base URL
                   - api_key: API key for authenticated requests
                   - timeout: Request timeout in seconds (default: 30)
        """
        self.config = config or {}
        
        # API endpoint
        self.api_url = self.config.get(
            "api_url",
            os.getenv("WEBSITE_API_URL", "https://mycosoft.vercel.app/api")
        ).rstrip('/')
        
        # Authentication
        self.api_key = self.config.get(
            "api_key",
            os.getenv("WEBSITE_API_KEY", "")
        )
        
        # Connection settings
        self.timeout = self.config.get("timeout", 30)
        
        # HTTP client (lazy loading)
        self._http_client = None
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Website client initialized - API: {self.api_url}")
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client for REST API access.
        
        Returns:
            httpx.AsyncClient: HTTP client with configured headers
        """
        if self._http_client is None:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            
            self._http_client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True
            )
        
        return self._http_client
    
    async def get_content(self, page: str) -> Dict[str, Any]:
        """
        Get website content for a specific page.
        
        Args:
            page: Page identifier (e.g., "about", "home", "products")
        
        Returns:
            Content dictionary with page data
        
        Example:
            content = await client.get_content(page="about")
            print(content['title'])
        """
        try:
            client = await self._get_http_client()
            response = await client.get(f"/content/{page}")
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error getting content for page {page}: {e}")
            raise
    
    async def submit_contact_form(
        self,
        name: str,
        email: str,
        message: str,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a contact form to the website.
        
        Args:
            name: Contact name
            email: Contact email
            message: Message content
            subject: Optional subject line
        
        Returns:
            Submission confirmation
        
        Note:
            Form submissions are typically forwarded to email or CRM system.
            Used for customer inquiries and support requests.
        """
        try:
            client = await self._get_http_client()
            payload = {
                "name": name,
                "email": email,
                "message": message
            }
            if subject:
                payload["subject"] = subject
            
            response = await client.post("/contact", json=payload)
            response.raise_for_status()
            
            self.logger.info(f"Contact form submitted from {email}")
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error submitting contact form: {e}")
            raise
    
    async def subscribe_newsletter(self, email: str) -> Dict[str, Any]:
        """
        Subscribe an email to the newsletter.
        
        Args:
            email: Email address to subscribe
        
        Returns:
            Subscription confirmation
        
        Note:
            Newsletter subscriptions are managed through email service provider.
            Used for marketing and updates.
        """
        try:
            client = await self._get_http_client()
            payload = {"email": email}
            
            response = await client.post("/newsletter/subscribe", json=payload)
            response.raise_for_status()
            
            self.logger.info(f"Newsletter subscription: {email}")
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error subscribing to newsletter: {e}")
            raise
    
    async def get_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get website analytics data.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
        
        Returns:
            Analytics data including page views, visitors, etc.
        
        Note:
            Requires API key authentication.
            Used for monitoring website performance and user engagement.
        """
        try:
            client = await self._get_http_client()
            params = {}
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
            
            response = await client.get("/analytics", params=params)
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error getting analytics: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check website API health.
        
        Returns:
            Health status dictionary
        
        Note:
            Performs API connectivity check.
            Used for monitoring website availability.
        """
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unknown"
        }
        
        try:
            client = await self._get_http_client()
            response = await client.get("/health", timeout=5)
            if response.status_code == 200:
                health["status"] = "ok"
                health.update(response.json())
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
        
        self.logger.info("Website client connections closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes connections."""
        await self.close()

