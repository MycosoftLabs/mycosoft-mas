#!/usr/bin/env python3
"""
Import all n8n workflow JSON files via SSH tunnel.

Usage (from your Windows machine with the tunnel running):
    python scripts/import_workflows_via_tunnel.py

Requires: requests (pip install requests)
The SSH tunnel must be active: localhost:15679 -> VM 191:5679
"""

import json
import os
import sys
import glob
import requests

# Configuration - adjust if your tunnel is on a different port
N8N_URL = os.getenv("N8N_URL", "http://localhost:15679")
API_KEY = os.getenv("N8N_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyMzhhODMzNi03YzRiLTQzNDctYmQwZS00MzIzMTFlOGJhNDgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiY2MzN2M2OGUtYzVkNS00Mjc2LTkzNDgtMzVmNGU4YjQxNTgxIiwiaWF0IjoxNzcyNTkwOTA2fQ.I_jFZVAkLi-Tqzdvf9A2ictI6CPlfyIVdMTT-g06nng")

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Find workflow directories relative to script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
WORKFLOW_DIRS = [
    os.path.join(PROJECT_ROOT, "n8n", "workflows"),
    os.path.join(PROJECT_ROOT, "workflows", "n8n"),
]


def main():
    print(f"=== n8n Workflow Importer ===")
    print(f"Target: {N8N_URL}")
    print()

    # Test connection
    try:
        resp = requests.get(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, timeout=10)
        if resp.status_code == 403:
            print(f"ERROR: 403 Forbidden. Check your API key.")
            print(f"Response: {resp.text[:200]}")
            sys.exit(1)
        resp.raise_for_status()
    except requests.ConnectionError:
        print(f"ERROR: Cannot connect to {N8N_URL}")
        print("Make sure your SSH tunnel is running:")
        print("  ssh -L 15679:localhost:5679 mycosoft@192.168.0.191")
        sys.exit(1)

    existing_data = resp.json()
    existing = {w["name"]: w["id"] for w in existing_data.get("data", [])}
    print(f"Existing workflows in n8n: {len(existing)}")

    # Collect workflow files
    files = []
    for d in WORKFLOW_DIRS:
        if os.path.isdir(d):
            for f in sorted(glob.glob(os.path.join(d, "*.json"))):
                files.append(f)

    print(f"Workflow JSON files found: {len(files)}")
    print()

    created = 0
    updated = 0
    errors = 0

    for filepath in files:
        basename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                wf = json.load(fh)
        except Exception as e:
            print(f"  SKIP {basename}: {e}")
            errors += 1
            continue

        name = wf.get("name", basename.replace(".json", ""))

        # Remove server-managed fields
        for key in ["id", "createdAt", "updatedAt", "versionId"]:
            wf.pop(key, None)

        if not wf.get("name"):
            wf["name"] = name

        try:
            if name in existing:
                wf_id = existing[name]
                resp = requests.patch(
                    f"{N8N_URL}/api/v1/workflows/{wf_id}",
                    headers=HEADERS,
                    json=wf,
                    timeout=30,
                )
                if resp.status_code == 200:
                    updated += 1
                    print(f"  Updated: {name}")
                else:
                    errors += 1
                    print(f"  ERROR updating {name}: {resp.status_code} - {resp.text[:120]}")
            else:
                resp = requests.post(
                    f"{N8N_URL}/api/v1/workflows",
                    headers=HEADERS,
                    json=wf,
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    created += 1
                    new_id = resp.json().get("id", "?")
                    existing[name] = new_id
                    print(f"  Created: {name} (id={new_id})")
                else:
                    errors += 1
                    print(f"  ERROR creating {name}: {resp.status_code} - {resp.text[:120]}")
        except Exception as e:
            errors += 1
            print(f"  ERROR {basename}: {e}")

    print()
    print(f"=== RESULTS ===")
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Errors:  {errors}")
    print(f"Total deployed: {created + updated}")


if __name__ == "__main__":
    main()
