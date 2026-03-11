#!/usr/bin/env python3
"""
Emit merged role config as JSON from YAML manifests.

Reads proxmox202_csuite.yaml, csuite_role_manifests.yaml, and
csuite_openclaw_defaults.yaml; merges for the given role; outputs JSON to stdout.

Used by apply_role_manifest.ps1, csuite_heartbeat.ps1, and bootstrap.
Date: March 7, 2026
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = REPO_ROOT / "config"


def load_yaml(path: Path) -> dict:
    """Load YAML file. Returns {} if missing or invalid."""
    try:
        import yaml
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def collect_winget_apps(manifest: dict, role_key: str) -> list[str]:
    """Extract winget IDs from base + role apps. Skips web_bookmark and non-winget."""
    apps: list[str] = []
    base = manifest.get("base") or {}
    for entry in base.get("apps") or []:
        wid = entry.get("winget")
        if wid:
            apps.append(wid)
    role_cfg = manifest.get(role_key) or {}
    for entry in role_cfg.get("apps") or []:
        wid = entry.get("winget")
        if wid:
            apps.append(wid)
    return apps


def emit_role_config(role_key: str, out_path: Path | None = None) -> dict:
    """
    Load configs, merge for role, return merged dict.
    If out_path given, also write JSON there.
    """
    # Load credentials so PROXMOX202_*_TOKEN env vars are available when run standalone
    try:
        # Ensure repo root is on path when run as script (python infra/csuite/emit_role_config.py)
        _script_root = Path(__file__).resolve().parent.parent.parent
        if str(_script_root) not in sys.path:
            sys.path.insert(0, str(_script_root))
        from infra.csuite.provision_base import load_credentials
        load_credentials()
    except Exception:
        pass  # Proceed; tokens may already be in env or not needed

    role_key = role_key.lower()
    if role_key not in ("ceo", "cfo", "cto", "coo"):
        raise ValueError(f"Invalid role: {role_key}")

    prox = load_yaml(CONFIG_DIR / "proxmox202_csuite.yaml")
    manifest = load_yaml(CONFIG_DIR / "csuite_role_manifests.yaml")
    defaults = load_yaml(CONFIG_DIR / "csuite_openclaw_defaults.yaml")

    vms = prox.get("vms") or {}
    vm = vms.get(role_key) or {}
    role_manifest = manifest.get(role_key) or {}
    base_manifest = manifest.get("base") or {}
    reporting = defaults.get("reporting") or {}

    mas_url = reporting.get("mas_api_url") or "http://192.168.0.188:8001"
    heartbeat_sec = reporting.get("heartbeat_interval_sec") or 60
    heartbeat_endpoint = reporting.get("heartbeat_endpoint") or f"{mas_url.rstrip('/')}/api/csuite/heartbeat"
    report_endpoint = reporting.get("report_endpoint") or f"{mas_url.rstrip('/')}/api/csuite/report"

    # Proxmox token for this role (from env via proxmox_token_env in manifest)
    prox_host = prox.get("proxmox") or {}
    prox_host_str = (prox_host.get("host") or "192.168.0.202") + ":" + str(prox_host.get("port") or 8006)
    token_env = role_manifest.get("proxmox_token_env") or f"PROXMOX202_{role_key.upper()}_TOKEN"
    proxmox_token = os.environ.get(token_env, "")

    merged = {
        "role": vm.get("role") or role_key.upper(),
        "role_key": role_key,
        "assistant_name": vm.get("assistant_name") or role_manifest.get("assistant_name") or "Unknown",
        "ip": vm.get("ip") or "",
        "primary_tool": vm.get("primary_tool") or role_manifest.get("primary_tool") or "",
        "apps": collect_winget_apps(manifest, role_key),
        "mas_api_url": mas_url,
        "heartbeat_interval_sec": heartbeat_sec,
        "heartbeat_endpoint": heartbeat_endpoint,
        "report_endpoint": report_endpoint,
        "proxmox_host": prox_host_str,
        "proxmox_api_token": proxmox_token,
    }

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)

    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit C-Suite role config as JSON")
    ap.add_argument("--role", "-r", required=True, choices=["ceo", "cfo", "cto", "coo"])
    ap.add_argument("--out", "-o", type=Path, help="Write JSON to file instead of stdout")
    args = ap.parse_args()

    try:
        merged = emit_role_config(args.role, args.out)
        if not args.out:
            print(json.dumps(merged, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
