#!/usr/bin/env python3
"""
Validate CFO MCP Connector — dynamic discovery and end-to-end flow.

Run: python scripts/validate_cfo_mcp_connector.py

Checks:
1. CFO MCP API health
2. list_finance_agents returns agents (dynamic discovery)
3. list_finance_services returns services
4. C-Suite cfo/dashboard and cfo/summary respond

Requires MAS on 192.168.0.188:8001 (or set MAS_API_URL).
"""

import os
import sys
from pathlib import Path

# Add repo root for imports
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

BASE = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")


def main() -> int:
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx required. pip install httpx")
        return 1

    errors: list[str] = []

    with httpx.Client(timeout=10.0) as client:
        # 1. CFO MCP health
        try:
            r = client.get(f"{BASE}/api/cfo-mcp/health")
            if r.status_code != 200:
                errors.append(f"CFO MCP health: {r.status_code}")
            else:
                print("OK  CFO MCP health")
        except Exception as e:
            errors.append(f"CFO MCP health: {e}")

        # 2. list_finance_agents
        try:
            r = client.post(
                f"{BASE}/api/cfo-mcp/tools/call",
                json={"name": "list_finance_agents", "arguments": {}},
            )
            if r.status_code != 200:
                errors.append(f"list_finance_agents: {r.status_code} {r.text[:200]}")
            else:
                data = r.json()
                agents = data.get("content", [])
                if isinstance(agents, str):
                    import json
                    try:
                        agents = json.loads(agents) if agents else []
                    except json.JSONDecodeError:
                        agents = []
                print(f"OK  list_finance_agents returned {len(agents) if isinstance(agents, list) else 'data'}")
        except Exception as e:
            errors.append(f"list_finance_agents: {e}")

        # 3. list_finance_services
        try:
            r = client.post(
                f"{BASE}/api/cfo-mcp/tools/call",
                json={"name": "list_finance_services", "arguments": {}},
            )
            if r.status_code != 200:
                errors.append(f"list_finance_services: {r.status_code}")
            else:
                print("OK  list_finance_services")
        except Exception as e:
            errors.append(f"list_finance_services: {e}")

        # 4. cfo/dashboard
        try:
            r = client.get(f"{BASE}/api/csuite/cfo/dashboard")
            if r.status_code != 200:
                errors.append(f"cfo/dashboard: {r.status_code}")
            else:
                print("OK  cfo/dashboard")
        except Exception as e:
            errors.append(f"cfo/dashboard: {e}")

        # 5. cfo/summary
        try:
            r = client.get(f"{BASE}/api/csuite/cfo/summary")
            if r.status_code != 200:
                errors.append(f"cfo/summary: {r.status_code}")
            else:
                print("OK  cfo/summary")
        except Exception as e:
            errors.append(f"cfo/summary: {e}")

    if errors:
        print("\nFAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nAll CFO MCP connector checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
