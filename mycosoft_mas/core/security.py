import json
import os
import time

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

auth_scheme = HTTPBearer()
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")
JWKS_TTL_SECONDS = 600
_jwks_cache = {"keys": None, "expires_at": 0.0}


async def _get_jwks() -> dict:
    if not AUTH0_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AUTH0_DOMAIN is not configured",
        )
    now = time.time()
    if _jwks_cache["keys"] and _jwks_cache["expires_at"] > now:
        return _jwks_cache["keys"]
    url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            jwks = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch JWKS: {exc}",
        ) from exc
    _jwks_cache["keys"] = jwks
    _jwks_cache["expires_at"] = now + JWKS_TTL_SECONDS
    return jwks


async def get_current_user(token=Depends(auth_scheme)):
    if not API_AUDIENCE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AUTH0_API_AUDIENCE is not configured",
        )
    try:
        unverified_header = jwt.get_unverified_header(token.credentials)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token header",
            )
        jwks = await _get_jwks()
        keys = jwks.get("keys", [])
        key_data = next((key for key in keys if key.get("kid") == kid), None)
        if not key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signing key not found",
            )
        public_key = jwk.construct(key_data)
        message, encoded_sig = token.credentials.rsplit(".", 1)
        decoded_sig = base64url_decode(encoded_sig.encode("utf-8"))
        if not public_key.verify(message.encode("utf-8"), decoded_sig):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature",
            )
        payload = jwt.decode(
            token.credentials,
            json.dumps(key_data),
            algorithms=["RS256"],
            audience=API_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
        )
        return payload
    except HTTPException:
        raise
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
