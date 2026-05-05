"""Optional Supabase persistence for agent100_* tables."""

from __future__ import annotations

import os
from dataclasses import asdict

from mycosoft_mas.agent100.types import CallRecord

try:
    from supabase import create_client  # type: ignore[import-untyped]
except Exception:  # pragma: no cover
    create_client = None  # type: ignore[misc, assignment]


def supabase_enabled() -> bool:
    return bool(os.environ.get("NEXT_PUBLIC_SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY") and create_client)


_ALLOWED_MODES = frozenset(
    ("singular", "multi", "grouped", "all_bundle", "health", "snapshot", "stream", "tile")
)


def persist_calls(rows: list[CallRecord]) -> int:
    """Upsert agents + insert agent100_calls when Supabase is configured."""
    if not supabase_enabled() or not rows:
        return 0
    url = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(url, key)
    n = 0
    seen_agents: set[str] = set()
    for r in rows:
        d = asdict(r)
        mode = d.get("mode") or "health"
        if mode not in _ALLOWED_MODES:
            mode = "health"
        if r.agent_id not in seen_agents:
            seen_agents.add(r.agent_id)
            try:
                client.table("agent100_agents").upsert(
                    {
                        "id": r.agent_id,
                        "archetype": r.archetype,
                        "framework": r.framework,
                        "status": "active",
                        "meta": {},
                    }
                ).execute()
            except Exception:
                pass
        payload = {
            "agent_id": r.agent_id,
            "archetype": r.archetype,
            "framework": r.framework,
            "dataset_id": d.get("dataset_id"),
            "mode": mode,
            "request_path": r.request_path,
            "status_code": d.get("status_code"),
            "latency_ms": d.get("latency_ms"),
            "cache": d.get("cache"),
            "cost_debited": d.get("cost_debited"),
            "rate_weight": d.get("rate_weight"),
            "bytes": d.get("bytes"),
            "schema_valid": d.get("schema_valid"),
            "freshness_ok": d.get("freshness_ok"),
            "error_class": d.get("error_class"),
            "request_id": d.get("request_id"),
            "envelope_ok": d.get("envelope_ok"),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        try:
            client.table("agent100_calls").insert(payload).execute()
            n += 1
        except Exception:
            continue
    return n
