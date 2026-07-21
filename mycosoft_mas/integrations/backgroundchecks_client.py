"""Async client for the BackgroundChecks.com v1 API.

The provider authenticates with an ``api_token`` query parameter.  This module
only reads configuration from environment variables and deliberately avoids
logging request parameters or response bodies because they can contain
sensitive applicant data.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

DEFAULT_BASE_URL = "https://app.backgroundchecks.com/api"


@dataclass
class BackgroundChecksError(Exception):
    """A safe representation of an upstream BackgroundChecks API failure."""

    message: str
    status_code: int | None = None

    def __str__(self) -> str:
        return self.message


class BackgroundChecksClient:
    """Typed, rate-limit-aware client for non-adverse BackgroundChecks actions."""

    def __init__(
        self,
        *,
        api_token: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 15.0,
        max_retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_token = api_token if api_token is not None else os.getenv("BACKGROUNDCHECKS_API_TOKEN", "")
        self._base_url = (
            base_url if base_url is not None else os.getenv("BACKGROUNDCHECKS_API_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._transport = transport

    @property
    def is_configured(self) -> bool:
        return bool(self._api_token)

    async def get_account(self) -> dict[str, Any]:
        """Read account metadata. Suitable for an explicitly enabled smoke test."""
        return await self._request_json("GET", "/accounts")

    async def list_reports(self, state: str = "all") -> list[dict[str, Any]]:
        """List provider reports in a documented state without fetching report detail."""
        if state not in {"all", "pending", "complete", "adverse", "archived"}:
            raise ValueError("invalid report state")
        payload = await self._request_json("GET", f"/reports/{state}")
        records = payload.get("data", [])
        if not isinstance(records, list):
            raise BackgroundChecksError("BackgroundChecks returned an invalid reports response")
        return [record for record in records if isinstance(record, dict)]

    async def get_report_status(self, report_key: str) -> dict[str, Any]:
        """Get the narrow provider status resource for an existing report."""
        return await self._request_json("GET", f"/reports/{report_key}/status")

    async def create_order(
        self,
        *,
        applicant_email: str,
        report_sku: str,
        terms_agree: bool,
        add_ons: Mapping[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Create one applicant invitation/order using provider-supported fields."""
        if report_sku not in {"HIRE1", "HIRE2", "HIRE3"}:
            raise ValueError("unsupported report SKU")
        if not terms_agree:
            raise ValueError("provider terms agreement is required")

        body: dict[str, Any] = {
            "report_sku": report_sku,
            "order_quantity": 1,
            "applicant_emails": [applicant_email],
            "terms_agree": "Y",
        }
        for provider_field, enabled in (add_ons or {}).items():
            if provider_field in {
                "drug_test",
                "mvr",
                "employment",
                "education",
                "blj",
                "federal_criminal",
            }:
                body[provider_field] = "Y" if enabled else "N"
        return await self._request_json("POST", "/orders/new", json=body, expected_statuses={201})

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        expected_statuses: set[int] | None = None,
    ) -> dict[str, Any]:
        if not self._api_token:
            raise BackgroundChecksError("BACKGROUNDCHECKS_API_TOKEN is not configured")

        successful_statuses = expected_statuses or {200}
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            transport=self._transport,
        ) as client:
            for attempt in range(self._max_retries + 1):
                try:
                    response = await client.request(
                        method,
                        path,
                        params={"api_token": self._api_token},
                        json=json,
                    )
                except httpx.HTTPError as exc:
                    if attempt == self._max_retries:
                        raise BackgroundChecksError("BackgroundChecks request failed") from exc
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue

                if response.status_code in successful_statuses:
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise BackgroundChecksError("BackgroundChecks returned an invalid response")
                    return payload

                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt < self._max_retries:
                        retry_after = response.headers.get("Retry-After")
                        try:
                            wait_seconds = min(float(retry_after), 5.0) if retry_after else 0.25 * (2**attempt)
                        except ValueError:
                            wait_seconds = 0.25 * (2**attempt)
                        await asyncio.sleep(wait_seconds)
                        continue

                raise BackgroundChecksError(
                    "BackgroundChecks request was rejected",
                    status_code=response.status_code,
                )

        raise BackgroundChecksError("BackgroundChecks request retry budget exhausted")
