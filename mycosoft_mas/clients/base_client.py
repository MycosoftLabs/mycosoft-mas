"""
Base Client for External Integrations

Provides common functionality:
- Retry logic with exponential backoff
- Authentication handling
- Error handling and logging
- Request/response typing
- Timeout management
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Type, TypeVar
from dataclasses import dataclass
from datetime import datetime
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class ClientError(Exception):
    """Base exception for client errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data
        self.original_error = original_error
        self.timestamp = datetime.utcnow()


@dataclass
class ClientResponse:
    """Standardized client response."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    response_time_ms: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class BaseClient:
    """
    Base client for external service integrations.
    
    Provides:
    - Automatic retries with exponential backoff
    - Authentication (API key, Bearer token, etc.)
    - Timeout management
    - Error handling and logging
    - Request/response validation
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the base client.
        
        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Initial retry delay (doubles each retry)
            headers: Additional headers to include in requests
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.default_headers = headers or {}
        
        self.client_name = self.__class__.__name__
        self.logger = logging.getLogger(f"client.{self.client_name}")
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Build request headers.
        
        Args:
            additional_headers: Additional headers for this request
            
        Returns:
            Complete headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"MYCA-MAS/{self.client_name}",
            **self.default_headers
        }
        
        # Add API key if present
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Merge additional headers
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL from endpoint.
        
        Args:
            endpoint: API endpoint (e.g., "/users/123")
            
        Returns:
            Full URL
        """
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> ClientResponse:
        """
        Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON request body
            headers: Additional headers
            response_model: Pydantic model to parse response
            
        Returns:
            ClientResponse object
        """
        url = self._build_url(endpoint)
        request_headers = self._get_headers(headers)
        
        import time
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json_data,
                        headers=request_headers
                    )
                    
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    # Handle non-2xx responses
                    if not response.is_success:
                        error_data = None
                        try:
                            error_data = response.json()
                        except:
                            error_data = {"text": response.text}
                        
                        if response.status_code >= 500 and attempt < self.max_retries - 1:
                            # Server error, retry
                            delay = self.retry_delay * (2 ** attempt)
                            self.logger.warning(
                                f"{self.client_name} server error (attempt {attempt + 1}/{self.max_retries}). "
                                f"Retrying in {delay}s..."
                            )
                            await asyncio.sleep(delay)
                            continue
                        
                        return ClientResponse(
                            success=False,
                            error=f"HTTP {response.status_code}: {response.text[:200]}",
                            status_code=response.status_code,
                            response_time_ms=response_time_ms,
                            data=error_data
                        )
                    
                    # Parse successful response
                    data = response.json()
                    
                    # Validate with Pydantic model if provided
                    if response_model:
                        try:
                            data = response_model(**data)
                        except Exception as e:
                            self.logger.error(f"Response validation failed: {e}")
                            return ClientResponse(
                                success=False,
                                error=f"Response validation failed: {e}",
                                status_code=response.status_code,
                                response_time_ms=response_time_ms,
                                data=data
                            )
                    
                    return ClientResponse(
                        success=True,
                        data=data,
                        status_code=response.status_code,
                        response_time_ms=response_time_ms
                    )
            
            except httpx.TimeoutException as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    self.logger.warning(
                        f"{self.client_name} request timeout (attempt {attempt + 1}/{self.max_retries}). "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                
                return ClientResponse(
                    success=False,
                    error=f"Request timeout after {self.timeout}s",
                    response_time_ms=(time.time() - start_time) * 1000
                )
            
            except Exception as e:
                self.logger.error(f"{self.client_name} request failed: {e}")
                return ClientResponse(
                    success=False,
                    error=str(e),
                    response_time_ms=(time.time() - start_time) * 1000
                )
        
        return ClientResponse(
            success=False,
            error=f"Request failed after {self.max_retries} attempts",
            response_time_ms=(time.time() - start_time) * 1000
        )
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> ClientResponse:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params, headers=headers, response_model=response_model)
    
    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> ClientResponse:
        """Make a POST request."""
        return await self._request("POST", endpoint, json_data=json_data, headers=headers, response_model=response_model)
    
    async def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> ClientResponse:
        """Make a PUT request."""
        return await self._request("PUT", endpoint, json_data=json_data, headers=headers, response_model=response_model)
    
    async def delete(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> ClientResponse:
        """Make a DELETE request."""
        return await self._request("DELETE", endpoint, headers=headers, response_model=response_model)
    
    async def health_check(self) -> bool:
        """
        Check if the service is reachable.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Try a simple GET request to a common health endpoint
            # Override this method in subclasses for service-specific health checks
            response = await self.get("/health")
            return response.success
        except:
            return False
