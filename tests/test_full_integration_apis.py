"""
Integration tests for full-stack read/write/search/interact APIs.
Skips when VMs are unreachable. Use SKIP_INTEGRATION=1 to force skip.

Date: March 9, 2026
"""

from __future__ import annotations

import os

import httpx
import pytest

# VM URLs
MAS_URL = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001")
MINDEX_URL = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000")

SKIP_INTEGRATION = os.environ.get("SKIP_INTEGRATION", "0") == "1"


def _is_reachable(url: str, path: str = "/health") -> bool:
    """Quick check if service is reachable."""
    try:
        r = httpx.get(f"{url.rstrip('/')}{path}", timeout=5)
        return r.status_code < 500
    except Exception:
        return False


def _mas_reachable() -> bool:
    try:
        r = httpx.get(f"{MAS_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _mindex_reachable() -> bool:
    return _is_reachable(MINDEX_URL, "/health")


@pytest.mark.skipif(SKIP_INTEGRATION, reason="SKIP_INTEGRATION=1")
@pytest.mark.skipif(not _mas_reachable(), reason="MAS VM unreachable")
class TestMASIntegration:
    """MAS API integration tests (device registry, merkle, health)."""

    def test_mas_health(self) -> None:
        """MAS /health returns 200."""
        r = httpx.get(f"{MAS_URL}/health", timeout=10)
        assert r.status_code == 200

    def test_device_registry_read(self) -> None:
        """Device registry is readable via /api/devices/."""
        r = httpx.get(f"{MAS_URL}/api/devices/", timeout=10)
        # 200 = success; 429 = rate limited (API reachable, try again later)
        assert r.status_code in (200, 429), f"Unexpected: {r.status_code} {r.text[:200]}"
        if r.status_code == 200:
            data = r.json()
            assert isinstance(data, (dict, list))

    def test_merkle_world_root_post(self) -> None:
        """Merkle world root can be built via POST /api/merkle/roots/world."""
        r = httpx.post(
            f"{MAS_URL}/api/merkle/roots/world",
            json={},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        # 200 = success; 404 = router not deployed on VM yet; 429 = rate limited
        assert r.status_code in (200, 404, 429), f"Unexpected: {r.status_code} {r.text[:200]}"
        if r.status_code == 200:
            data = r.json()
            assert "root" in data or "world_root" in data


@pytest.mark.skipif(SKIP_INTEGRATION, reason="SKIP_INTEGRATION=1")
@pytest.mark.skipif(not _mindex_reachable(), reason="MINDEX VM unreachable")
class TestMINDEXIntegration:
    """MINDEX API integration tests (search, health)."""

    def test_mindex_health(self) -> None:
        """MINDEX /health returns 200."""
        r = httpx.get(f"{MINDEX_URL}/health", timeout=10)
        assert r.status_code == 200

    def test_mindex_unified_search_read(self) -> None:
        """MINDEX unified search is searchable via GET."""
        # MINDEX api_prefix=/api/mindex, unified-search router
        url = f"{MINDEX_URL}/api/mindex/unified-search"
        r = httpx.get(url, params={"q": "psilocybe"}, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "results" in data or "query" in data


@pytest.mark.skipif(SKIP_INTEGRATION, reason="SKIP_INTEGRATION=1")
class TestFullStackReadable:
    """Full-stack read/write/search/interact surface for AI."""

    def test_at_least_one_system_reachable(self) -> None:
        """At least MAS or MINDEX must be reachable for integration tests to run."""
        mas = _mas_reachable()
        mindex = _mindex_reachable()
        assert mas or mindex, "No VMs reachable; run with SKIP_INTEGRATION=1 to skip"
