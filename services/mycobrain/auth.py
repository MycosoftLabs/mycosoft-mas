"""MycoBrain API Authentication Module"""
import os
from typing import Optional
from fastapi import HTTPException, Security, Header, status
from fastapi.security import APIKeyHeader

# API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_valid_api_keys() -> list[str]:
    """Get list of valid API keys from environment variable."""
    keys_str = os.environ.get("MYCOBRAIN_API_KEYS", "")
    if not keys_str:
        single_key = os.environ.get("MYCOBRAIN_API_KEY", "")
        if single_key:
            return [single_key]
        if os.environ.get("MYCOBRAIN_DEV_MODE", "false").lower() == "true":
            return ["dev-key-mycobrain"]
        return []
    return [k.strip() for k in keys_str.split(",") if k.strip()]

def verify_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """Verify the API key from header."""
    key = api_key or x_api_key
    valid_keys = get_valid_api_keys()
    
    if not valid_keys:
        return "no-auth-configured"
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return key
