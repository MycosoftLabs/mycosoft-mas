#!/usr/bin/env python3
"""
Ingest external system data into Supabase backbone tables.

Asana tasks -> commitments
Notion databases -> customer_vendors, commitments, liabilities, recruitment_roles
GitHub issues -> commitments

Usage:
  python scripts/ingest_external_to_supabase.py
  python scripts/ingest_external_to_supabase.py --sources asana,notion,github

Env:
  NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  ASANA_API_KEY / ASANA_PAT / MYCA_ASANA_TOKEN, ASANA_WORKSPACE_ID
  NOTION_API_KEY, NOTION_DATABASE_COMMITMENTS, NOTION_DATABASE_VENDORS, etc.
  GITHUB_TOKEN, GITHUB_OWNER (or GITHUB_REPO=owner/repo)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ingest_external")

MAS_ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    """Load env from .env files."""
    for p in [
        MAS_ROOT / ".env",
        MAS_ROOT.parent / "website" / ".env.local",
        MAS_ROOT.parent.parent / "WEBSITE" / "website" / ".env.local",
        Path.home() / ".mycosoft-credentials",
    ]:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ[key] = value


def _supabase_rest(
    table: str,
    method: str = "GET",
    data: Optional[dict] = None,
    params: Optional[dict] = None,
) -> Any:
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
        "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY"
    ) or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    import requests
    rest_url = f"{url.rstrip('/')}/rest/v1/{table}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if method == "GET":
        resp = requests.get(rest_url, headers=headers, params=params or {}, timeout=60)
    elif method == "POST":
        resp = requests.post(rest_url, headers=headers, json=data or {}, timeout=30)
    elif method == "PATCH":
        resp = requests.patch(rest_url, headers=headers, json=data or {}, params=params or {}, timeout=30)
    else:
        raise ValueError(f"Unsupported: {method}")
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Supabase {table} {method} {resp.status_code}: {resp.text[:500]}")
    if resp.text:
        return resp.json()
    return None


def _upsert_by_source(
    table: str,
    row: dict,
    source_system: str,
    source_record_id: str,
) -> bool:
    """Find existing by source_system+source_record_id; PATCH if found, else POST."""
    try:
        existing = _supabase_rest(
            table,
            method="GET",
            params={
                "source_system": f"eq.{source_system}",
                "source_record_id": f"eq.{source_record_id}",
                "select": "id",
            },
        )
        if isinstance(existing, list) and existing:
            uid = existing[0].get("id")
            if uid:
                _supabase_rest(
                    table,
                    method="PATCH",
                    data=row,
                    params={"id": f"eq.{uid}"},
                )
                return True
        _supabase_rest(table, method="POST", data=row)
        return True
    except Exception as e:
        logger.warning("Upsert %s %s/%s: %s", table, source_system, source_record_id, e)
        return False


def _content_hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:32]


def _asana_status(s: str) -> str:
    s = (s or "").lower()
    if s in ("completed", "done"):
        return "completed"
    if "progress" in s or "doing" in s:
        return "in_progress"
    return "open"


async def ingest_asana() -> int:
    """Asana tasks -> commitments."""
    from mycosoft_mas.integrations.asana_client import AsanaClient
    client = AsanaClient()
    if not client.api_key:
        logger.info("Asana: no token, skip")
        return 0
    tasks = await client.list_tasks(limit=100)
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    for t in tasks:
        gid = t.get("gid", "")
        name = (t.get("name") or "Untitled").strip()
        if not name:
            continue
        due = t.get("due_on")
        if due:
            try:
                due = due[:10]
            except Exception:
                due = None
        completed = t.get("completed", False)
        status = "completed" if completed else _asana_status(t.get("status", ""))
        notes = (t.get("notes") or "")[:4096]
        assignee = t.get("assignee")
        owner = ""
        if assignee and isinstance(assignee, dict):
            owner = assignee.get("name") or ""
        payload = {
            "title": name[:500],
            "due_date": due,
            "owner": owner[:200] or None,
            "status": status,
            "notes": notes or None,
            "source_system": "asana",
            "source_record_id": gid,
            "last_synced_at": now,
            "sync_status": "synced",
            "content_hash": _content_hash({"name": name, "due": due, "completed": completed}),
            "updated_at": now,
        }
        if _upsert_by_source("commitments", payload, "asana", gid):
            count += 1
    await client.close()
    logger.info("Asana: upserted %d commitments", count)
    return count


def _notion_title(props: dict) -> str:
    for key in ("title", "Title", "Name", "name"):
        if key in props:
            val = props[key]
            if isinstance(val, dict) and "title" in val:
                arr = val.get("title", [])
                if arr and isinstance(arr, list):
                    first = arr[0] if arr else {}
                    if isinstance(first, dict) and "plain_text" in first:
                        return (first["plain_text"] or "").strip()
            elif isinstance(val, dict) and "rich_text" in val:
                arr = val.get("rich_text", [])
                if arr:
                    first = arr[0] if isinstance(arr[0], dict) else {}
                    return (first.get("plain_text") or "").strip()
    return ""


def _notion_select(props: dict, key: str) -> str:
    val = props.get(key, {})
    if isinstance(val, dict) and "select" in val:
        sel = val["select"]
        if isinstance(sel, dict) and "name" in sel:
            return (sel["name"] or "").strip()
    return ""


def _notion_date(props: dict, key: str) -> Optional[str]:
    val = props.get(key, {})
    if isinstance(val, dict) and "date" in val:
        d = val["date"]
        if isinstance(d, dict) and d.get("start"):
            return d["start"][:10]
    return None


def _notion_number(props: dict, key: str) -> Optional[float]:
    val = props.get(key, {})
    if isinstance(val, dict) and "number" in val:
        n = val["number"]
        if n is not None:
            try:
                return float(n)
            except Exception:
                pass
    return None


async def ingest_notion() -> int:
    """Notion databases -> commitments, customer_vendors, liabilities, recruitment_roles."""
    from mycosoft_mas.integrations.notion_client import NotionClient
    api_key = os.environ.get("NOTION_API_KEY", "").strip()
    if not api_key:
        logger.info("Notion: no API key, skip")
        return 0
    client = NotionClient(api_key=api_key)
    now = datetime.now(timezone.utc).isoformat()
    count = 0

    # Commitments
    db_id = os.environ.get("NOTION_DATABASE_COMMITMENTS", "").strip()
    if db_id:
        try:
            result = await client.query_database(database_id=db_id, page_size=100)
            for page in result.get("results", []):
                pid = page.get("id", "")
                props = page.get("properties", {})
                title = _notion_title(props)
                if not title:
                    continue
                status = _notion_select(props, "Status") or "open"
                status = status.lower().replace(" ", "_")
                if status not in ("open", "in_progress", "completed", "cancelled"):
                    status = "open"
                payload = {
                    "title": title[:500],
                    "due_date": _notion_date(props, "Due") or _notion_date(props, "Due Date"),
                    "owner": _notion_title(props.get("Owner") or props.get("Assignee") or {}),
                    "status": status,
                    "notes": None,
                    "source_system": "notion",
                    "source_record_id": pid,
                    "last_synced_at": now,
                    "sync_status": "synced",
                    "content_hash": _content_hash({"title": title, "status": status}),
                    "updated_at": now,
                }
                if _upsert_by_source("commitments", payload, "notion", pid):
                    count += 1
        except Exception as e:
            logger.warning("Notion commitments: %s", e)

    # Customer/vendors
    db_id = os.environ.get("NOTION_DATABASE_VENDORS", "").strip() or os.environ.get("NOTION_DATABASE_CUSTOMER_VENDORS", "").strip()
    if db_id:
        try:
            result = await client.query_database(database_id=db_id, page_size=100)
            for page in result.get("results", []):
                pid = page.get("id", "")
                props = page.get("properties", {})
                name = _notion_title(props)
                if not name:
                    continue
                t = (_notion_select(props, "Type") or "vendor").lower()
                if t not in ("customer", "vendor", "partner"):
                    t = "vendor"
                row = {
                    "name": name[:200],
                    "type": t,
                    "contact": _notion_title(props.get("Contact") or {}),
                    "terms": _notion_title(props.get("Terms") or {}),
                    "notes": _notion_title(props.get("Notes") or {}),
                    "source_system": "notion",
                    "source_record_id": pid,
                    "last_synced_at": now,
                    "sync_status": "synced",
                    "content_hash": _content_hash({"name": name}),
                    "updated_at": now,
                }
                if _upsert_by_source("customer_vendors", row, "notion", pid):
                    count += 1
        except Exception as e:
            logger.warning("Notion customer_vendors: %s", e)

    # Liabilities
    db_id = os.environ.get("NOTION_DATABASE_LIABILITIES", "").strip()
    if db_id:
        try:
            result = await client.query_database(database_id=db_id, page_size=100)
            for page in result.get("results", []):
                pid = page.get("id", "")
                props = page.get("properties", {})
                title = _notion_title(props)
                if not title:
                    continue
                amount = _notion_number(props, "Amount") or _notion_number(props, "amount")
                status = _notion_select(props, "Status") or "open"
                status = status.lower().replace(" ", "_")
                if status not in ("open", "paid", "overdue", "cancelled"):
                    status = "open"
                payload = {
                    "title": title[:500],
                    "amount": amount,
                    "due_date": _notion_date(props, "Due") or _notion_date(props, "Due Date"),
                    "status": status,
                    "notes": _notion_title(props.get("Notes") or {}),
                    "source_system": "notion",
                    "source_record_id": pid,
                    "last_synced_at": now,
                    "sync_status": "synced",
                    "content_hash": _content_hash({"title": title, "amount": amount}),
                    "updated_at": now,
                }
                if _upsert_by_source("liabilities", payload, "notion", pid):
                    count += 1
        except Exception as e:
            logger.warning("Notion liabilities: %s", e)

    # Recruitment roles
    db_id = os.environ.get("NOTION_DATABASE_RECRUITMENT", "").strip()
    if db_id:
        try:
            result = await client.query_database(database_id=db_id, page_size=100)
            for page in result.get("results", []):
                pid = page.get("id", "")
                props = page.get("properties", {})
                role = _notion_title(props) or _notion_title(props.get("Role") or {})
                if not role:
                    continue
                status = _notion_select(props, "Status") or "open"
                status = status.lower().replace(" ", "_")
                if status not in ("open", "in_progress", "filled", "cancelled"):
                    status = "open"
                payload = {
                    "role": role[:200],
                    "status": status,
                    "owner": _notion_title(props.get("Owner") or {}),
                    "notes": _notion_title(props.get("Notes") or {}),
                    "source_system": "notion",
                    "source_record_id": pid,
                    "last_synced_at": now,
                    "sync_status": "synced",
                    "content_hash": _content_hash({"role": role}),
                    "updated_at": now,
                }
                if _upsert_by_source("recruitment_roles", payload, "notion", pid):
                    count += 1
        except Exception as e:
            logger.warning("Notion recruitment_roles: %s", e)

    logger.info("Notion: upserted %d records", count)
    return count


async def ingest_github() -> int:
    """GitHub issues -> commitments."""
    from mycosoft_mas.integrations.github_client import GitHubClient
    client = GitHubClient()
    if not client.token:
        logger.info("GitHub: no token, skip")
        return 0
    owner = os.environ.get("GITHUB_OWNER", "").strip() or client.owner
    repo = os.environ.get("GITHUB_REPO", "").strip()
    if not repo and owner:
        repo = f"{owner}/mycosoft-mas"
    if "/" not in repo:
        logger.info("GitHub: set GITHUB_REPO=owner/repo")
        return 0
    o, r = repo.split("/", 1)
    try:
        issues = await client.list_issues(owner=o, repo=r, state="all", limit=50)
    except Exception as e:
        logger.warning("GitHub list_issues: %s", e)
        return 0
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    for issue in issues:
        iid = str(issue.get("id", ""))
        title = (issue.get("title") or "Untitled").strip()
        state = (issue.get("state") or "open").lower()
        status = "completed" if state == "closed" else "open"
        due = None
        if issue.get("milestone") and isinstance(issue["milestone"], dict):
            due = issue["milestone"].get("due_on")
            if due:
                due = due[:10]
        assignee = issue.get("assignee")
        owner_name = (assignee.get("login", "") if isinstance(assignee, dict) else "") or ""
        body = (issue.get("body") or "")[:4096]
        payload = {
            "title": f"[{repo}] {title}"[:500],
            "due_date": due,
            "owner": owner_name[:200] or None,
            "status": status,
            "notes": body or None,
            "source_system": "github",
            "source_record_id": iid,
            "last_synced_at": now,
            "sync_status": "synced",
            "content_hash": _content_hash({"title": title, "state": state}),
            "updated_at": now,
        }
        if _upsert_by_source("commitments", payload, "github", iid):
            count += 1
    await client.close()
    logger.info("GitHub: upserted %d commitments", count)
    return count


async def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(description="Ingest external data to Supabase")
    parser.add_argument("--sources", default="asana,notion,github", help="Comma-separated: asana,notion,github")
    args = parser.parse_args()
    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    total = 0
    if "asana" in sources:
        total += await ingest_asana()
    if "notion" in sources:
        total += await ingest_notion()
    if "github" in sources:
        total += await ingest_github()
    logger.info("Total upserted: %d", total)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
