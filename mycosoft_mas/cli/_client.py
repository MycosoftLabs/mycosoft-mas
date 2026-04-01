"""Shared HTTP client for the myca CLI.

Thin wrapper around httpx for calling MAS, MINDEX, and Gateway APIs.
All CLI commands use this module — it handles retries, timeouts, and auth.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]


@dataclass
class APIConfig:
    """API connection configuration resolved from env vars or flags."""

    mas_url: str = ""
    mindex_url: str = ""
    gateway_url: str = ""
    api_key: str = ""
    timeout: float = 30.0
    retries: int = 2

    def __post_init__(self) -> None:
        self.mas_url = self.mas_url or os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        self.mindex_url = self.mindex_url or os.getenv(
            "MINDEX_API_URL", "http://192.168.0.189:8000"
        )
        self.gateway_url = self.gateway_url or os.getenv(
            "MYCA_GATEWAY_URL", "http://192.168.0.191:8100"
        )
        self.api_key = self.api_key or os.getenv("MYCA_API_KEY", "")


@dataclass
class APIResult:
    """Typed result from an API call."""

    ok: bool
    status_code: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    hint: str = ""


def _ensure_httpx() -> None:
    if httpx is None:
        print("Error: httpx is required. Install with: pip install httpx", file=sys.stderr)
        sys.exit(1)


def request(
    method: str,
    url: str,
    *,
    config: Optional[APIConfig] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> APIResult:
    """Synchronous HTTP request with retry logic.

    Uses httpx sync client so CLI commands stay simple (no async).
    Retries on connection errors with exponential backoff.
    """
    _ensure_httpx()
    cfg = config or APIConfig()

    req_headers = {}
    if cfg.api_key:
        req_headers["X-API-Key"] = cfg.api_key
    if headers:
        req_headers.update(headers)

    last_error = ""
    for attempt in range(cfg.retries + 1):
        try:
            with httpx.Client(timeout=cfg.timeout) as client:
                resp = client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=req_headers,
                )
                if resp.status_code >= 400:
                    try:
                        body = resp.json()
                    except Exception:
                        body = {"detail": resp.text[:500]}
                    return APIResult(
                        ok=False,
                        status_code=resp.status_code,
                        data=body,
                        error=f"HTTP {resp.status_code}: {body.get('detail', resp.text[:200])}",
                    )
                try:
                    data = resp.json()
                except Exception:
                    data = {"raw": resp.text}
                return APIResult(ok=True, status_code=resp.status_code, data=data)

        except httpx.ConnectError:
            last_error = f"Cannot connect to {url}"
        except httpx.TimeoutException:
            last_error = f"Request to {url} timed out after {cfg.timeout}s"
        except Exception as e:
            last_error = str(e)

        if attempt < cfg.retries:
            time.sleep(2 ** (attempt + 1))

    return APIResult(ok=False, error=last_error)


def get(url: str, *, config: Optional[APIConfig] = None, **kwargs: Any) -> APIResult:
    """Shorthand for GET request."""
    return request("GET", url, config=config, **kwargs)


def post(
    url: str, *, config: Optional[APIConfig] = None, json_body: Optional[Dict[str, Any]] = None, **kwargs: Any
) -> APIResult:
    """Shorthand for POST request."""
    return request("POST", url, config=config, json_body=json_body, **kwargs)


def delete(url: str, *, config: Optional[APIConfig] = None, **kwargs: Any) -> APIResult:
    """Shorthand for DELETE request."""
    return request("DELETE", url, config=config, **kwargs)


def read_stdin_json() -> Dict[str, Any]:
    """Read JSON from stdin. Fails fast with actionable error."""
    if sys.stdin.isatty():
        print("Error: --stdin requires piped input", file=sys.stderr)
        print("  echo '{\"key\": \"value\"}' | myca ... --stdin", file=sys.stderr)
        sys.exit(1)
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON on stdin: {e}", file=sys.stderr)
        sys.exit(1)
