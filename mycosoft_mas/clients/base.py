"""
Base Client Module

Provides a base class for HTTP API clients with:
- Consistent configuration
- Retry logic with exponential backoff
- Error handling
- Request/response logging
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, TypeVar
from uuid import UUID

import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ClientError(Exception):
    """Base exception for client errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.retryable = retryable


class AuthenticationError(ClientError):
    """Authentication failed."""
    pass


class RateLimitError(ClientError):
    """Rate limit exceeded."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(message, retryable=True, **kwargs)
        self.retry_after = retry_after


class NotFoundError(ClientError):
    """Resource not found."""
    pass


class ServerError(ClientError):
    """Server error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=True, **kwargs)


@dataclass
class ClientConfig:
    """Configuration for an API client."""
    base_url: str
    api_key: str = ""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_max_delay: float = 60.0
    retry_multiplier: float = 2.0
    
    # Headers
    default_headers: dict[str, str] = field(default_factory=dict)
    
    # Authentication
    auth_header_name: str = "Authorization"
    auth_header_prefix: str = "Bearer"
    
    @classmethod
    def from_env(
        cls,
        base_url_env: str,
        api_key_env: str,
        default_base_url: str = "",
    ) -> "ClientConfig":
        """Create config from environment variables."""
        return cls(
            base_url=os.getenv(base_url_env, default_base_url),
            api_key=os.getenv(api_key_env, ""),
        )


class BaseClient:
    """
    Base class for HTTP API clients.
    
    Provides common functionality for making HTTP requests with:
    - Automatic retry with exponential backoff
    - Error handling and classification
    - Request/response logging
    - Correlation ID propagation
    
    Subclasses should implement specific API methods.
    """
    
    def __init__(self, config: ClientConfig):
        self.config = config
        self.logger = logging.getLogger(f"client.{self.__class__.__name__}")
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None or self._session.closed:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                **self.config.default_headers,
            }
            
            if self.config.api_key:
                auth_value = f"{self.config.auth_header_prefix} {self.config.api_key}".strip()
                headers[self.config.auth_header_name] = auth_value
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
            )
        
        return self._session
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        correlation_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """
        Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method
            path: URL path (relative to base_url)
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers
            correlation_id: Correlation ID for tracing
            
        Returns:
            Response JSON as dict
            
        Raises:
            ClientError: On request failure
        """
        session = await self._get_session()
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        
        # Build headers
        request_headers = dict(headers or {})
        if correlation_id:
            request_headers["X-Correlation-ID"] = str(correlation_id)
        
        # Retry loop
        last_error: Optional[Exception] = None
        delay = self.config.retry_delay
        
        for attempt in range(self.config.max_retries + 1):
            try:
                self.logger.debug(
                    f"Request: {method} {url}",
                    extra={"attempt": attempt + 1, "params": params},
                )
                
                start_time = datetime.now()
                
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=request_headers,
                ) as response:
                    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                    
                    self.logger.debug(
                        f"Response: {response.status}",
                        extra={"duration_ms": duration_ms},
                    )
                    
                    # Handle response
                    if response.status == 200:
                        return await response.json()
                    
                    elif response.status == 401:
                        raise AuthenticationError(
                            "Authentication failed",
                            status_code=401,
                        )
                    
                    elif response.status == 404:
                        raise NotFoundError(
                            f"Resource not found: {path}",
                            status_code=404,
                        )
                    
                    elif response.status == 429:
                        retry_after = float(
                            response.headers.get("Retry-After", 60)
                        )
                        raise RateLimitError(
                            "Rate limit exceeded",
                            status_code=429,
                            retry_after=retry_after,
                        )
                    
                    elif response.status >= 500:
                        body = await response.text()
                        raise ServerError(
                            f"Server error: {response.status}",
                            status_code=response.status,
                            response_body=body,
                        )
                    
                    else:
                        body = await response.text()
                        raise ClientError(
                            f"Request failed: {response.status}",
                            status_code=response.status,
                            response_body=body,
                        )
                        
            except (RateLimitError, ServerError) as e:
                last_error = e
                
                if attempt < self.config.max_retries:
                    # Calculate delay
                    if isinstance(e, RateLimitError) and e.retry_after:
                        wait_time = e.retry_after
                    else:
                        wait_time = min(delay, self.config.retry_max_delay)
                    
                    self.logger.warning(
                        f"Retrying after {wait_time}s (attempt {attempt + 1})",
                        extra={"error": str(e)},
                    )
                    
                    await asyncio.sleep(wait_time)
                    delay *= self.config.retry_multiplier
                else:
                    raise
                    
            except aiohttp.ClientError as e:
                last_error = ClientError(
                    f"Connection error: {str(e)}",
                    retryable=True,
                )
                
                if attempt < self.config.max_retries:
                    self.logger.warning(
                        f"Connection error, retrying in {delay}s",
                        extra={"error": str(e)},
                    )
                    await asyncio.sleep(delay)
                    delay *= self.config.retry_multiplier
                else:
                    raise last_error
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise ClientError("Request failed after retries")
    
    async def get(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make a GET request."""
        return await self._request("GET", path, params=params, **kwargs)
    
    async def post(
        self,
        path: str,
        data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make a POST request."""
        return await self._request("POST", path, json_data=data, **kwargs)
    
    async def put(
        self,
        path: str,
        data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make a PUT request."""
        return await self._request("PUT", path, json_data=data, **kwargs)
    
    async def delete(
        self,
        path: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Make a DELETE request."""
        return await self._request("DELETE", path, **kwargs)
    
    async def health_check(self) -> bool:
        """Check if the service is healthy."""
        try:
            await self.get("/health")
            return True
        except Exception:
            return False
