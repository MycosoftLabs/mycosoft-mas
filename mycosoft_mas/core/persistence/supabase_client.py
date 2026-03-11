"""
Supabase REST client for MAS persistence.
Best-effort; failures are logged, never raised.
Follows llm_ledger pattern.

Created: March 10, 2026
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_supabase_config() -> tuple[str | None, str | None]:
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    )
    return (url or None, key or None)


def supabase_available() -> bool:
    """Return True if Supabase is configured."""
    url, key = _get_supabase_config()
    return bool(url and key)


def supabase_insert(table: str, row: Dict[str, Any]) -> bool:
    """Insert a row into a Supabase table. Best-effort; returns False on failure."""
    url, key = _get_supabase_config()
    if not url or not key:
        return False
    try:
        import requests
        rest_url = f"{url.rstrip('/')}/rest/v1/{table}"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        # Serialize non-JSON types
        payload = {}
        for k, v in row.items():
            if v is None:
                payload[k] = None
            elif hasattr(v, "isoformat"):
                payload[k] = v.isoformat()
            else:
                payload[k] = v
        resp = requests.post(rest_url, headers=headers, json=payload, timeout=5)
        if resp.status_code not in (200, 201, 204):
            logger.debug("supabase_insert %s %s: %s", table, resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as e:
        logger.debug("supabase_insert %s failed: %s", table, e)
        return False


def supabase_upsert(table: str, row: Dict[str, Any], on_conflict: str = "id") -> bool:
    """Upsert a row. Uses Prefer: resolution=merge-duplicates."""
    url, key = _get_supabase_config()
    if not url or not key:
        return False
    try:
        import requests
        rest_url = f"{url.rstrip('/')}/rest/v1/{table}"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }
        payload = {}
        for k, v in row.items():
            if v is None:
                payload[k] = None
            elif hasattr(v, "isoformat"):
                payload[k] = v.isoformat()
            else:
                payload[k] = v
        resp = requests.post(rest_url, headers=headers, json=payload, timeout=5)
        if resp.status_code not in (200, 201, 204):
            logger.debug("supabase_upsert %s %s: %s", table, resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as e:
        logger.debug("supabase_upsert %s failed: %s", table, e)
        return False


def supabase_select(
    table: str,
    columns: str = "*",
    filters: Optional[Dict[str, Any]] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Select rows from a Supabase table. Returns empty list on failure."""
    url, key = _get_supabase_config()
    if not url or not key:
        return []
    try:
        import requests
        rest_url = f"{url.rstrip('/')}/rest/v1/{table}"
        params = {"select": columns}
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        # Build filter query string
        if filters:
            for k, v in filters.items():
                if v is None:
                    params[k] = "is.null"
                else:
                    params[k] = f"eq.{v}"
        resp = requests.get(rest_url, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            logger.debug("supabase_select %s %s: %s", table, resp.status_code, resp.text[:200])
            return []
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.debug("supabase_select %s failed: %s", table, e)
        return []


def supabase_update(
    table: str,
    updates: Dict[str, Any],
    filters: Dict[str, Any],
) -> bool:
    """Update rows matching filters. Best-effort."""
    url, key = _get_supabase_config()
    if not url or not key:
        return False
    try:
        import requests
        rest_url = f"{url.rstrip('/')}/rest/v1/{table}"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        # Build filter as query params
        params = {}
        for k, v in filters.items():
            if v is None:
                params[k] = "is.null"
            else:
                params[k] = f"eq.{v}"
        payload = {}
        for k, v in updates.items():
            if hasattr(v, "isoformat"):
                payload[k] = v.isoformat()
            else:
                payload[k] = v
        resp = requests.patch(rest_url, headers=headers, params=params, json=payload, timeout=5)
        if resp.status_code not in (200, 204):
            logger.debug("supabase_update %s %s: %s", table, resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as e:
        logger.debug("supabase_update %s failed: %s", table, e)
        return False
