"""Rate limiting and security middleware for MAS API."""

import time
import os
from typing import Callable, Optional
from collections import defaultdict
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """In-memory rate limiter with sliding window algorithm."""
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_windows: dict[str, list[float]] = defaultdict(list)
        self.hour_windows: dict[str, list[float]] = defaultdict(list)
    
    def _clean_old_requests(self, key: str, window_seconds: int, window_dict: dict):
        """Remove requests older than the window."""
        cutoff = time.time() - window_seconds
        window_dict[key] = [t for t in window_dict[key] if t > cutoff]
    
    def is_rate_limited(self, client_id: str) -> tuple[bool, Optional[str]]:
        """Check if a client is rate limited."""
        now = time.time()
        
        # Check minute limit
        self._clean_old_requests(client_id, 60, self.minute_windows)
        if len(self.minute_windows[client_id]) >= self.requests_per_minute:
            return True, "Rate limit exceeded: too many requests per minute"
        
        # Check hour limit
        self._clean_old_requests(client_id, 3600, self.hour_windows)
        if len(self.hour_windows[client_id]) >= self.requests_per_hour:
            return True, "Rate limit exceeded: too many requests per hour"
        
        # Record this request
        self.minute_windows[client_id].append(now)
        self.hour_windows[client_id].append(now)
        
        return False, None
    
    def get_remaining(self, client_id: str) -> dict:
        """Get remaining requests for a client."""
        self._clean_old_requests(client_id, 60, self.minute_windows)
        self._clean_old_requests(client_id, 3600, self.hour_windows)
        
        return {
            "minute_remaining": max(0, self.requests_per_minute - len(self.minute_windows[client_id])),
            "hour_remaining": max(0, self.requests_per_hour - len(self.hour_windows[client_id])),
        }


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
    requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    
    # Endpoints exempt from rate limiting
    EXEMPT_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip if rate limiting is disabled
        if os.getenv("DISABLE_RATE_LIMIT", "false").lower() == "true":
            return await call_next(request)
        
        # Get client identifier (IP address or API key)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        is_limited, message = rate_limiter.is_rate_limited(client_id)
        
        if is_limited:
            remaining = rate_limiter.get_remaining(client_id)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": message,
                    "remaining": remaining,
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Remaining-Minute": str(remaining["minute_remaining"]),
                    "X-RateLimit-Remaining-Hour": str(remaining["hour_remaining"]),
                },
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        remaining = rate_limiter.get_remaining(client_id)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["minute_remaining"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hour_remaining"])
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Prefer API key if present
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:8]}..."
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"


def validate_input_length(max_length: int = 10000):
    """Decorator to validate input body length."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if request and hasattr(request, "body"):
                body = await request.body()
                if len(body) > max_length:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request body too large. Maximum size: {max_length} bytes",
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
