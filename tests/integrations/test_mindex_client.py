from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mycosoft_mas.integrations.mindex_client import MINDEXClient


@pytest.mark.asyncio
async def test_database_pool_uses_raw_dsn_for_encoded_credentials() -> None:
    database_url = "postgresql://mindex:password%3Awith%40symbols@db.example:5432/mindex"
    client = MINDEXClient(config={"database_url": database_url})
    pool = object()

    with patch(
        "mycosoft_mas.integrations.mindex_client.asyncpg.create_pool",
        AsyncMock(return_value=pool),
    ) as create_pool:
        result = await client._get_db_pool()

    assert result is pool
    create_pool.assert_awaited_once_with(
        dsn=database_url,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
