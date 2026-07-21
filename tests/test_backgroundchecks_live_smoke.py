"""Opt-in, non-destructive BackgroundChecks production connectivity smoke test."""

from __future__ import annotations

import os

import pytest

from mycosoft_mas.integrations.backgroundchecks_client import BackgroundChecksClient


@pytest.mark.asyncio
async def test_backgroundchecks_account_smoke() -> None:
    if os.getenv("BACKGROUNDCHECKS_LIVE_SMOKE", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        pytest.skip("set BACKGROUNDCHECKS_LIVE_SMOKE=1 to run the provider account smoke test")

    account = await BackgroundChecksClient().get_account()

    assert isinstance(account, dict)
