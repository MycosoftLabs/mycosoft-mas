"""
LLM Usage Ledger — persist token/cost usage to Supabase llm_usage_ledger.

Fire-and-forget: failures are logged but never raise. Used by router.py
and frontier_router.py to track LLM spend.

Env:
  NEXT_PUBLIC_SUPABASE_URL or SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY or NEXT_PUBLIC_SUPABASE_ANON_KEY
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def persist_to_supabase_ledger(
    provider: str,
    model: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    estimated_cost: float = 0.0,
    *,
    tool_or_workflow_owner: Optional[str] = None,
    requesting_agent: Optional[str] = None,
    requesting_app: Optional[str] = None,
    user_scope: Optional[str] = None,
    workspace_scope: Optional[str] = None,
    related_business_object_id: Optional[str] = None,
    related_run_id: Optional[str] = None,
) -> None:
    """Insert a row into Supabase llm_usage_ledger. Best-effort; never raises."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
        "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY"
    ) or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        return
    row: dict[str, Any] = {
        "provider": provider or "unknown",
        "model": model or "unknown",
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "estimated_cost": float(estimated_cost),
    }
    if tool_or_workflow_owner:
        row["tool_or_workflow_owner"] = tool_or_workflow_owner
    if requesting_agent:
        row["requesting_agent"] = requesting_agent
    if requesting_app:
        row["requesting_app"] = requesting_app
    if user_scope:
        row["user_scope"] = user_scope
    if workspace_scope:
        row["workspace_scope"] = workspace_scope
    if related_business_object_id:
        row["related_business_object_id"] = related_business_object_id
    if related_run_id:
        row["related_run_id"] = related_run_id
    try:
        import requests
        rest_url = f"{url.rstrip('/')}/rest/v1/llm_usage_ledger"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        resp = requests.post(rest_url, headers=headers, json=row, timeout=5)
        if resp.status_code not in (200, 201, 204):
            logger.debug("llm_ledger persist %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.debug("llm_ledger persist failed: %s", e)
