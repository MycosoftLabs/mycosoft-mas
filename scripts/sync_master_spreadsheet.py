#!/usr/bin/env python3
"""
Multi-tab sync for the master Google Sheet.

Reads config/master_spreadsheet_automation.yaml and syncs each enabled tab
from its configured source (Supabase, MAS API, CSV).

Usage:
  python scripts/sync_master_spreadsheet.py              # CSV only (per tab)
  python scripts/sync_master_spreadsheet.py --push       # Push to Google Sheets
  python scripts/sync_master_spreadsheet.py --tabs inventory,hardware  # Specific tabs

Env:
  NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  MAS_API_URL (default http://192.168.0.188:8001) for mas_api tabs
  GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SHEETS_CREDENTIALS_JSON
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

# Paths
MAS_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = MAS_ROOT / "config" / "master_spreadsheet_automation.yaml"
DATA_ROOT = MAS_ROOT / "data"


def load_env() -> None:
    """Load env from .env and credentials files."""
    code_root = MAS_ROOT.parent.parent
    for p in [
        code_root / "WEBSITE" / "website" / ".env.local",
        code_root / "website" / "website" / ".env.local",
        MAS_ROOT.parent / "website" / ".env.local",
        MAS_ROOT / ".env",
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


def load_config() -> dict[str, Any]:
    """Load master spreadsheet automation config."""
    if not CONFIG_PATH.exists():
        print(f"Config not found: {CONFIG_PATH}")
        sys.exit(1)
    if not yaml:
        print("Install: pip install pyyaml")
        sys.exit(1)
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

def _supabase_rest(table: str, method: str = "GET", data: dict | None = None, params: dict | None = None) -> Any:
    """Call Supabase REST API."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    import requests
    url = url.rstrip("/")
    rest_url = f"{url}/rest/v1/{table}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if method == "GET":
        resp = requests.get(rest_url, headers=headers, params=params or {}, timeout=60)
    elif method == "POST":
        resp = requests.post(rest_url, headers=headers, json=data or {}, params=params or {}, timeout=30)
    elif method == "PATCH":
        resp = requests.patch(rest_url, headers=headers, json=data or {}, params=params or {}, timeout=30)
    else:
        raise ValueError(f"Unsupported method: {method}")
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text[:500]}")
    if resp.text:
        return resp.json()
    return None


def fetch_supabase_table(table: str, columns: list[str]) -> list[dict]:
    """Fetch rows from any Supabase table."""
    sel = ",".join(columns)
    data = _supabase_rest(table, method="GET", params={"select": sel})
    if not isinstance(data, list):
        return []
    return data


def persist_sheet_sync_status(
    spreadsheet_id: str,
    tab_name: str,
    rows_synced: int,
    sync_status: str,
    error_message: str | None = None,
) -> None:
    """Upsert sync status to Supabase sheet_sync_status (schema: last_sync_at, sync_status, rows_synced)."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "spreadsheet_id": spreadsheet_id,
        "tab_name": tab_name,
        "last_sync_at": now,
        "sync_status": sync_status,
        "rows_synced": rows_synced,
        "error_message": error_message or "",
    }
    try:
        import requests

        url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        if not url or not key:
            return
        url = url.rstrip("/")
        rest_url = f"{url}/rest/v1/sheet_sync_status"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
        resp = requests.post(
            rest_url,
            headers=headers,
            json=row,
            params={"on_conflict": "spreadsheet_id,tab_name"},
            timeout=10,
        )
        if resp.status_code not in (200, 201, 204):
            pass  # Best-effort
    except Exception:
        pass  # Best-effort persist


def persist_sync_run(
    tab_name: str,
    source_system: str,
    started_at: str,
    completed_at: str,
    records_synced: int,
    status: str,
    error_message: str | None = None,
) -> None:
    """Insert sync run audit into Supabase sync_runs (schema: sync_type, source_system, target_system, status, records_processed, records_synced, completed_at)."""
    row = {
        "sync_type": "sheet_tab",
        "source_system": source_system,
        "target_system": tab_name,
        "status": status,
        "records_processed": records_synced,
        "records_synced": records_synced,
        "error_message": error_message or "",
        "started_at": started_at,
        "completed_at": completed_at,
    }
    try:
        _supabase_rest("sync_runs", method="POST", data=row)
    except Exception:
        pass  # Best-effort audit


def row_for_inventory(c: dict) -> dict:
    """Convert Supabase component row to master-sheet format."""
    return {
        "id": str(c.get("id") or "").strip(),
        "name": str(c.get("name") or "").strip() or "Unknown",
        "sku": str(c.get("sku") or c.get("id") or "").strip(),
        "category": str(c.get("category") or "misc").strip(),
        "quantity": int(float(c.get("quantity") or 0)),
        "unit_cost": round(float(c.get("unit_cost") or 0), 2),
        "supplier_name": str(c.get("supplier_name") or "Amazon").strip(),
        "location": str(c.get("location") or "").strip(),
        "reorder_threshold": int(float(c.get("reorder_threshold") or 0)),
        "supplier_lead_time_days": int(float(c.get("supplier_lead_time_days") or 7)),
    }


def fetch_mas_devices(columns: list[str], mas_base: str) -> list[dict]:
    """Fetch devices from MAS /api/devices (include_offline for full list)."""
    import requests
    url = f"{mas_base.rstrip('/')}/api/devices?include_offline=true"
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"MAS API error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    devices = data.get("devices", data) if isinstance(data, dict) else data
    if not isinstance(devices, list):
        return []

    rows = []
    for d in devices:
        last_seen = d.get("last_seen", "") or ""
        if isinstance(last_seen, str) and len(last_seen) > 19:
            last_seen = last_seen[:19]
        row = {
            "device_id": str(d.get("device_id", "")),
            "device_name": str(d.get("device_name", "")),
            "host": str(d.get("host", "")),
            "port": str(d.get("port", 0)),
            "connection_type": str(d.get("connection_type", "")),
            "last_seen": last_seen,
            "status": str(d.get("status", "")),
        }
        rows.append({k: row.get(k, "") for k in columns})
    return rows


def fetch_csv(path: Path, columns: list[str]) -> list[dict]:
    """Read rows from CSV file."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        rows = []
        for row in r:
            rows.append({k: str(row.get(k, "")).strip() for k in columns})
        return rows


# ---------------------------------------------------------------------------
# Sync logic
# ---------------------------------------------------------------------------


def _row_from_columns(raw: dict, columns: list[str]) -> dict:
    """Map raw row to sheet columns (string values)."""
    return {k: str(raw.get(k, "")).strip() for k in columns}


def fetch_tab_data(tab_name: str, tab_cfg: dict, mas_base: str) -> tuple[list[dict], list[str]]:
    """Fetch data for a tab based on its source. Returns (rows, columns)."""
    columns = tab_cfg.get("columns", [])
    source = tab_cfg.get("source", "manual")
    enabled = tab_cfg.get("enabled", True)

    if not enabled:
        return [], columns

    if source == "supabase":
        table = tab_cfg.get("supabase_table", "components")
        raw = fetch_supabase_table(table, columns)
        if tab_name == "inventory":
            rows = [row_for_inventory(c) for c in raw]
        else:
            rows = [_row_from_columns(c, columns) for c in raw]
        # mas_api_fallback: when Supabase returns 0 rows, try MAS endpoint (e.g. hardware)
        if len(rows) == 0 and tab_cfg.get("mas_api_fallback"):
            endpoint = tab_cfg["mas_api_fallback"]
            if "devices" in endpoint or endpoint in ("/api/devices", "/api/devices/network"):
                rows = fetch_mas_devices(columns, mas_base)
            else:
                import requests
                url = f"{mas_base.rstrip('/')}{endpoint}"
                resp = requests.get(url, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    arr = data if isinstance(data, list) else data.get("devices", data.get("data", data.get("items", [])))
                    rows = [_row_from_columns(x, columns) for x in (arr or [])]
        return rows, columns

    if source == "mas_api":
        endpoint = tab_cfg.get("mas_endpoint", "/api/devices")
        # MAS device list is at /api/devices (website /api/devices/network proxies here)
        if "devices" in endpoint or endpoint in ("/api/devices", "/api/devices/network"):
            rows = fetch_mas_devices(columns, mas_base)
        else:
            import requests
            url = f"{mas_base.rstrip('/')}{endpoint}"
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                raise RuntimeError(f"MAS API error {resp.status_code}: {resp.text[:500]}")
            data = resp.json()
            arr = data if isinstance(data, list) else data.get("data", data.get("items", []))
            rows = [{k: str(x.get(k, "")).strip() for k in columns} for x in (arr or [])]
        return rows, columns

    if source == "csv" or source == "manual":
        csv_path = tab_cfg.get("csv_path")
        if csv_path:
            full = MAS_ROOT / csv_path if not Path(csv_path).is_absolute() else Path(csv_path)
            return fetch_csv(full, columns), columns
        return [], columns

    return [], columns


def push_to_google_sheets(
    spreadsheet_id: str,
    tab_gid: str,
    tab_name: str,
    rows: list[dict],
    columns: list[str],
) -> bool:
    """Replace sheet tab content. Returns True on success.

    When tab_gid is empty, uses tab_name to find or create the worksheet.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("Install: pip install gspread google-auth")
        return False

    creds_path = (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("GOOGLE_SERVICE_ACCOUNT_PATH")
        or os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY")
    )
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON", "").strip()
    if not creds_path and not creds_json:
        print("Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SHEETS_CREDENTIALS_JSON")
        return False

    if creds_json:
        try:
            import base64
            raw = creds_json
            if raw.startswith("eyJ"):  # base64 of '{"'
                raw = base64.b64decode(raw).decode("utf-8")
            info = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as e:
            print("GOOGLE_SHEETS_CREDENTIALS_JSON must be valid JSON or base64: %s" % e)
            return False
        creds = Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    else:
        creds = Credentials.from_service_account_file(
            creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)

    # Resolve worksheet: by gid first, else by tab name; create if missing
    ws = None
    if tab_gid and tab_gid.strip().isdigit():
        try:
            ws = sh.get_worksheet_by_id(int(tab_gid))
        except gspread.exceptions.APIError:
            ws = None
    if ws is None:
        sheet_title = tab_name or tab_gid
        if not sheet_title:
            print("Need gid or tab_name to identify worksheet")
            return False
        try:
            ws = sh.worksheet(sheet_title)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=sheet_title, rows=1000, cols=26)
            print(f"Created worksheet '{sheet_title}' (gid={ws.id})")

    vals = [columns] + [[str(r.get(k, "")) for k in columns] for r in rows]
    ws.clear()
    ws.update(vals, "A1", value_input_option="USER_ENTERED")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true", help="Push to Google Sheets")
    ap.add_argument("--tabs", default=None, help="Comma-separated tab names (default: all enabled)")
    args = ap.parse_args()

    load_env()
    cfg = load_config()
    spreadsheet_id = cfg.get("spreadsheet_id", "")
    tabs_cfg = cfg.get("tabs", {})
    mas_base = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001")

    tab_filter = [t.strip() for t in args.tabs.split(",")] if args.tabs else None

    results: list[dict] = []
    for tab_name, tab_cfg in tabs_cfg.items():
        if not isinstance(tab_cfg, dict):
            continue
        if tab_filter and tab_name not in tab_filter:
            continue
        if not tab_cfg.get("enabled", True):
            continue
        gid = str(tab_cfg.get("gid", "")).strip()
        # Process even without gid: fetch, write CSV, persist status. Push only when gid set.

        started_at = datetime.now(timezone.utc).isoformat()
        source_system = tab_cfg.get("supabase_table") or tab_cfg.get("source", "unknown")

        try:
            rows, columns = fetch_tab_data(tab_name, tab_cfg, mas_base)
        except Exception as e:
            completed_at = datetime.now(timezone.utc).isoformat()
            persist_sheet_sync_status(
                spreadsheet_id, tab_name, 0, "failed", error_message=str(e)
            )
            persist_sync_run(
                tab_name, source_system, started_at, completed_at, 0, "failed", str(e)
            )
            results.append({"tab": tab_name, "status": "error", "error": str(e), "rows": 0})
            continue

        csv_dir = DATA_ROOT / "master_sheet"
        csv_dir.mkdir(parents=True, exist_ok=True)
        csv_path = csv_dir / f"{tab_name}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"[{tab_name}] Wrote {len(rows)} rows to {csv_path}")

        push_ok = False
        if args.push and rows:
            push_ok = push_to_google_sheets(spreadsheet_id, gid, tab_name, rows, columns)
            if push_ok:
                results.append({"tab": tab_name, "status": "pushed", "rows": len(rows)})
                print(f"[{tab_name}] Pushed to Google Sheets")
            else:
                results.append({"tab": tab_name, "status": "push_failed", "rows": len(rows)})
        else:
            results.append({"tab": tab_name, "status": "csv_only", "rows": len(rows)})

        completed_at = datetime.now(timezone.utc).isoformat()
        sync_status = "success" if (not args.push) or push_ok else "partial"
        persist_sheet_sync_status(
            spreadsheet_id, tab_name, len(rows), sync_status, error_message=None
        )
        persist_sync_run(
            tab_name, source_system, started_at, completed_at, len(rows), sync_status, None
        )

    # Print summary
    for r in results:
        print(f"  {r['tab']}: {r['status']} ({r.get('rows', 0)} rows)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
