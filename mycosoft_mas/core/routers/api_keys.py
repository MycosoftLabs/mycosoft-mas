"""API key management for MYCA services."""

from datetime import datetime, timezone
import hashlib
import secrets
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from mycosoft_mas.core.security import get_current_user
from mycosoft_mas.integrations.mindex_client import MINDEXClient


router = APIRouter(prefix="/api/keys", tags=["api-keys"])
_mindex_client = MINDEXClient()
_rate_windows: dict[str, list[float]] = {}
_rate_window_seconds = 60


class ApiKeyCreateRequest(BaseModel):
    user_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    rate_limit: int = Field(default=1000, ge=1)
    expires_at: Optional[datetime] = None


class ApiKeyRecord(BaseModel):
    id: str
    user_id: str
    scopes: List[str]
    rate_limit: int
    created_at: datetime
    expires_at: Optional[datetime]


class ApiKeyCreateResponse(BaseModel):
    status: str
    api_key: str
    record: ApiKeyRecord


class ApiKeyListResponse(BaseModel):
    status: str
    items: List[ApiKeyRecord]
    total: int


class ApiKeyDeleteResponse(BaseModel):
    status: str
    deleted_id: str


async def _ensure_api_keys_table() -> None:
    pool = await _mindex_client._get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY,
                user_id TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
                rate_limit INT DEFAULT 1000,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP
            );
            """
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);"
        )


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _check_rate_limit(key_id: str, limit: int) -> None:
    now = time.time()
    window = _rate_windows.get(key_id, [])
    cutoff = now - _rate_window_seconds
    window = [ts for ts in window if ts > cutoff]
    if len(window) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API key rate limit exceeded",
            headers={"Retry-After": str(_rate_window_seconds)},
        )
    window.append(now)
    _rate_windows[key_id] = window


async def require_api_key(request: Request) -> Dict[str, Any]:
    raw_key = request.headers.get("X-API-Key")
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header missing",
        )
    await _ensure_api_keys_table()
    key_hash = _hash_key(raw_key)
    pool = await _mindex_client._get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, scopes, rate_limit, created_at, expires_at
            FROM api_keys
            WHERE key_hash = $1
            """,
            key_hash,
        )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    if row["expires_at"] and row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(
        timezone.utc
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired",
        )
    _check_rate_limit(str(row["id"]), int(row["rate_limit"]))
    return dict(row)


def _resolve_user_id(user: Dict[str, Any], requested_id: Optional[str]) -> str:
    if requested_id:
        return requested_id
    sub = user.get("sub") or user.get("user_id")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User id not available in token",
        )
    return str(sub)


@router.get("/health")
async def health():
    await _ensure_api_keys_table()
    return {"status": "healthy", "service": "api-keys"}


@router.post("", response_model=ApiKeyCreateResponse)
async def create_key(
    request: ApiKeyCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    await _ensure_api_keys_table()
    user_id = _resolve_user_id(user, request.user_id)
    raw_key = f"myca_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    key_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)
    pool = await _mindex_client._get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO api_keys (id, user_id, key_hash, scopes, rate_limit, created_at, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            key_id,
            user_id,
            key_hash,
            request.scopes,
            request.rate_limit,
            created_at.replace(tzinfo=None),
            request.expires_at.replace(tzinfo=None) if request.expires_at else None,
        )
    record = ApiKeyRecord(
        id=str(key_id),
        user_id=user_id,
        scopes=request.scopes,
        rate_limit=request.rate_limit,
        created_at=created_at,
        expires_at=request.expires_at,
    )
    return ApiKeyCreateResponse(status="success", api_key=raw_key, record=record)


@router.get("", response_model=ApiKeyListResponse)
async def list_keys(
    user_id: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user),
):
    await _ensure_api_keys_table()
    resolved_user_id = _resolve_user_id(user, user_id)
    pool = await _mindex_client._get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_id, scopes, rate_limit, created_at, expires_at
            FROM api_keys
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            resolved_user_id,
        )
    items = [
        ApiKeyRecord(
            id=str(row["id"]),
            user_id=row["user_id"],
            scopes=row["scopes"] or [],
            rate_limit=int(row["rate_limit"]),
            created_at=row["created_at"].replace(tzinfo=timezone.utc),
            expires_at=row["expires_at"].replace(tzinfo=timezone.utc)
            if row["expires_at"]
            else None,
        )
        for row in rows
    ]
    return ApiKeyListResponse(status="success", items=items, total=len(items))


@router.delete("/{key_id}", response_model=ApiKeyDeleteResponse)
async def delete_key(
    key_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    await _ensure_api_keys_table()
    resolved_user_id = _resolve_user_id(user, None)
    pool = await _mindex_client._get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM api_keys
            WHERE id = $1 AND user_id = $2
            """,
            uuid.UUID(key_id),
            resolved_user_id,
        )
    if result.split(" ")[-1] == "0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    return ApiKeyDeleteResponse(status="success", deleted_id=key_id)


@router.post("/verify")
async def verify_key(record: Dict[str, Any] = Depends(require_api_key)):
    return {
        "status": "valid",
        "user_id": record["user_id"],
        "scopes": record["scopes"] or [],
        "rate_limit": int(record["rate_limit"]),
    }


def require_api_key_scoped(scope: str):
    """Dependency that requires API key with a specific scope."""

    async def _dep(request: Request) -> Dict[str, Any]:
        record = await require_api_key(request)
        scopes = record.get("scopes") or []
        if scope not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{scope}' required",
            )
        return record

    return Depends(_dep)
