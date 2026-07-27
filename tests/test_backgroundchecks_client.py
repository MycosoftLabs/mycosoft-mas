from __future__ import annotations

import httpx
import pytest

from mycosoft_mas.integrations.backgroundchecks_client import (
    BackgroundChecksClient,
    BackgroundChecksError,
)


@pytest.mark.asyncio
async def test_get_account_sends_api_token_as_query_parameter() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/accounts"
        assert request.url.params["api_token"] == "test-token"
        return httpx.Response(200, json={"company_name": "Mycosoft"})

    client = BackgroundChecksClient(
        api_token="test-token",
        base_url="https://provider.test/api",
        transport=httpx.MockTransport(handler),
    )

    assert await client.get_account() == {"company_name": "Mycosoft"}


@pytest.mark.asyncio
async def test_list_reports_rejects_invalid_state() -> None:
    client = BackgroundChecksClient(api_token="test-token")

    with pytest.raises(ValueError, match="invalid report state"):
        await client.list_reports("unknown")


@pytest.mark.asyncio
async def test_upstream_error_does_not_expose_response_body() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "provider-specific detail"})

    client = BackgroundChecksClient(
        api_token="test-token",
        base_url="https://provider.test/api",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(BackgroundChecksError) as error:
        await client.get_account()

    assert error.value.status_code == 401
    assert "provider-specific detail" not in str(error.value)
