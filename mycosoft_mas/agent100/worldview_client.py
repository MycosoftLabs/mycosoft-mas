"""HTTP client for Worldview v1 on mycosoft.com — Agent100 harness."""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urljoin

import httpx

from mycosoft_mas.agent100.constants import AGENT100_DEFAULT_WORLDBASE


class WorldviewClient:
    """Signed Worldview requests using x-worldview-key (server-side harness only)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self.base_url = (base_url or AGENT100_DEFAULT_WORLDBASE).rstrip("/")
        self.api_key = api_key or os.environ.get("AGENT100_WORLDBASE_API_KEY", "")
        self._client = httpx.Client(timeout=timeout_s, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            h["x-worldview-key"] = self.api_key
        return h

    def health(self) -> tuple[int, dict[str, Any] | None, float]:
        path = "/api/worldview/v1/health"
        t0 = time.perf_counter()
        r = self._client.get(urljoin(self.base_url + "/", path.lstrip("/")), headers=self._headers())
        elapsed_ms = (time.perf_counter() - t0) * 1000
        body: dict[str, Any] | None = None
        try:
            if r.headers.get("content-type", "").startswith("application/json"):
                body = r.json()
        except Exception:
            body = None
        return r.status_code, body, elapsed_ms

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any] | list[Any] | str | None, float]:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        t0 = time.perf_counter()
        r = self._client.get(url, headers=self._headers(), params=params or {})
        elapsed_ms = (time.perf_counter() - t0) * 1000
        data: dict[str, Any] | list[Any] | str | None = None
        ct = r.headers.get("content-type", "")
        if "json" in ct:
            try:
                data = r.json()
            except Exception:
                data = None
        else:
            data = r.text[:5000] if r.text else None
        return r.status_code, data, elapsed_ms
