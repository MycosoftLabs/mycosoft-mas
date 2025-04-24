from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
import httpx
import os

auth_scheme = HTTPBearer()
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")

async def get_current_user(token=Depends(auth_scheme)):
    try:
        jwks = httpx.get(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json").json()
        payload = jwt.decode(token.credentials, jwks, audience=API_AUDIENCE, algorithms=["RS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") 