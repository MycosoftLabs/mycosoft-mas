from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from mycosoft_mas.core.routers import api_keys


def _request(api_key: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if api_key:
        headers.append((b"x-api-key", api_key.encode("utf-8")))
    return Request({"type": "http", "headers": headers})


def _pool_with_row(row: dict[str, object] | None) -> MagicMock:
    connection = AsyncMock()
    connection.fetchrow.return_value = row
    acquired_connection = MagicMock()
    acquired_connection.__aenter__ = AsyncMock(return_value=connection)
    acquired_connection.__aexit__ = AsyncMock(return_value=None)
    pool = MagicMock()
    pool.acquire.return_value = acquired_connection
    return pool


@pytest.mark.asyncio
async def test_require_api_key_rejects_missing_header() -> None:
    with pytest.raises(HTTPException) as exception_info:
        await api_keys.require_api_key(_request())

    assert exception_info.value.status_code == 401
    assert exception_info.value.detail == "X-API-Key header missing"


@pytest.mark.asyncio
async def test_require_api_key_fails_closed_when_store_rejects_credentials() -> None:
    with patch.object(
        api_keys,
        "_ensure_api_keys_table",
        AsyncMock(side_effect=asyncpg.InvalidPasswordError("redacted")),
    ):
        with pytest.raises(HTTPException) as exception_info:
            await api_keys.require_api_key(_request("test-key"))

    assert exception_info.value.status_code == 503
    assert exception_info.value.detail == "API key authentication is temporarily unavailable"
    assert "redacted" not in exception_info.value.detail


@pytest.mark.asyncio
async def test_require_api_key_rejects_unknown_key() -> None:
    pool = _pool_with_row(None)

    with (
        patch.object(api_keys, "_ensure_api_keys_table", AsyncMock()),
        patch.object(api_keys._mindex_client, "_get_db_pool", AsyncMock(return_value=pool)),
    ):
        with pytest.raises(HTTPException) as exception_info:
            await api_keys.require_api_key(_request("unknown-key"))

    assert exception_info.value.status_code == 401
    assert exception_info.value.detail == "Invalid API key"


@pytest.mark.asyncio
async def test_require_api_key_accepts_valid_key() -> None:
    record = {
        "id": uuid.uuid4(),
        "user_id": "guardian-operator",
        "scopes": ["guardian:admin"],
        "rate_limit": 10,
        "created_at": None,
        "expires_at": None,
    }
    pool = _pool_with_row(record)

    with (
        patch.object(api_keys, "_ensure_api_keys_table", AsyncMock()),
        patch.object(api_keys._mindex_client, "_get_db_pool", AsyncMock(return_value=pool)),
    ):
        authenticated_record = await api_keys.require_api_key(_request("valid-key"))

    assert authenticated_record == record


@pytest.mark.asyncio
async def test_scoped_key_rejects_missing_scope() -> None:
    dependency = api_keys.require_api_key_scoped("guardian:admin").dependency
    assert dependency is not None

    with patch.object(
        api_keys,
        "require_api_key",
        AsyncMock(return_value={"scopes": ["guardian:read"]}),
    ):
        with pytest.raises(HTTPException) as exception_info:
            await dependency(_request("test-key"))

    assert exception_info.value.status_code == 403
    assert exception_info.value.detail == "Scope 'guardian:admin' required"


@pytest.mark.asyncio
async def test_scoped_key_accepts_required_scope() -> None:
    dependency = api_keys.require_api_key_scoped("guardian:admin").dependency
    assert dependency is not None
    record = {"id": "key-id", "scopes": ["guardian:admin"]}

    with patch.object(
        api_keys,
        "require_api_key",
        AsyncMock(return_value=record),
    ):
        result = await dependency(_request("test-key"))

    assert result == record
