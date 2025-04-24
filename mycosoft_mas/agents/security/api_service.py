from typing import Dict, Any, Optional
import time
import redis
from functools import wraps
from config.api_config import api_config

class APIService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0
        )
        self.rate_limits: Dict[str, Dict[str, int]] = {
            "stripe": {"requests": 100, "period": 60},  # 100 requests per minute
            "mercury": {"requests": 50, "period": 60},  # 50 requests per minute
            "openai": {"requests": 60, "period": 60},  # 60 requests per minute
            "anthropic": {"requests": 30, "period": 60},  # 30 requests per minute
            "azure": {"requests": 100, "period": 60},  # 100 requests per minute
            "google": {"requests": 100, "period": 60}  # 100 requests per minute
        }

    def rate_limit(self, service: str):
        """Decorator to enforce rate limiting for API calls"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                key = f"rate_limit:{service}:{int(time.time() // self.rate_limits[service]['period'])}"
                current = self.redis_client.incr(key)
                
                if current == 1:
                    self.redis_client.expire(key, self.rate_limits[service]['period'])
                
                if current > self.rate_limits[service]['requests']:
                    raise Exception(f"Rate limit exceeded for {service}")
                
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def cache_response(self, service: str, key: str, value: Any, ttl: int = 300):
        """Cache API response with a time-to-live"""
        cache_key = f"cache:{service}:{key}"
        self.redis_client.setex(cache_key, ttl, str(value))

    def get_cached_response(self, service: str, key: str) -> Optional[Any]:
        """Get cached API response"""
        cache_key = f"cache:{service}:{key}"
        value = self.redis_client.get(cache_key)
        return value.decode() if value else None

    def clear_cache(self, service: str, key: Optional[str] = None):
        """Clear cache for a service or specific key"""
        if key:
            cache_key = f"cache:{service}:{key}"
            self.redis_client.delete(cache_key)
        else:
            pattern = f"cache:{service}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)

    def get_api_key(self, service: str) -> str:
        """Get API key for a specific service"""
        return api_config.get_api_key(service)

    def get_endpoint(self, service: str, endpoint: str) -> str:
        """Get endpoint URL for a specific service and endpoint"""
        return api_config.get_endpoint(service, endpoint)

# Create a singleton instance
api_service = APIService() 