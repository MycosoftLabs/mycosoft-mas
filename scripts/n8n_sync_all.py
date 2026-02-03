#!/usr/bin/env python3
"""
N8N Workflow Sync Script - February 2, 2026

Syncs all local n8n workflows to the n8n instance and activates core workflows.

Usage:
    python scripts/n8n_sync_all.py                    # Sync all, activate core
    python scripts/n8n_sync_all.py --list             # List all workflows
    python scripts/n8n_sync_all.py --health           # Health check
    python scripts/n8n_sync_all.py --activate-all     # Activate all workflows
    python scripts/n8n_sync_all.py --stats            # Show stats
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YTYxMTEyYS00YWViLTQwYTItYTUwNC1iZDY3YWZhOGU1NWIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY5NTM4NzM0LCJleHAiOjE3NzIwOTI4MDB9.I1mgswouNspryGfJfIiVz-tOhW0iBQg5f0OfJbwxWvw")
WORKFLOWS_DIR = Path(__file__).parent.parent / "n8n" / "workflows"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class N8NClient:
    def __init__(self):
        self.base_url = N8N_URL.rstrip("/")
        self.headers = {"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"}
        self.client = httpx.Client(timeout=30.0)
    
    def request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.base_url}/api/v1{endpoint}"
        response = self.client.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json() if response.text else {}
    
    def list_workflows(self) -> list:
        data = self.request("GET", "/workflows")
        return data.get("data", [])
    
    def get_workflow(self, wid: str) -> dict:
        return self.request("GET", f"/workflows/{wid}")
    
    def create_workflow(self, data: dict) -> dict:
        clean = {k: v for k, v in data.items() if k != "id"}
        return self.request("POST", "/workflows", json=clean)
    
    def update_workflow(self, wid: str, data: dict) -> dict:
        return self.request("PUT", f"/workflows/{wid}", json=data)
    
    def activate(self, wid: str) -> dict:
        return self.request("POST", f"/workflows/{wid}/activate")
    
    def deactivate(self, wid: str) -> dict:
        return self.request("POST", f"/workflows/{wid}/deactivate")
    
    def find_by_name(self, name: str) -> dict | None:
        for w in self.list_workflows():
            if w["name"] == name:
                return w
        return None
    
    def close(self):
        self.client.close()


def health_check():
    """Check n8n connectivity"""
    client = N8NClient()
    try:
        workflows = client.list_workflows()
        active = len([w for w in workflows if w.get("active")])
        print(f"✅ N8N connected: {N8N_URL}")
        print(f"   Total workflows: {len(workflows)}")
        print(f"   Active workflows: {active}")
        return True
    except Exception as e:
        print(f"❌ N8N connection failed: {e}")
        return False
    finally:
        client.close()


def list_workflows():
    """List all workflows"""
    client = N8NClient()
    try:
        workflows = client.list_workflows()
        print(f"\n{'Status':<8} {'Name':<50} {'ID':<10}")
        print("-" * 70)
        for w in sorted(workflows, key=lambda x: x["name"]):
            status = "✅" if w.get("active") else "⭕"
            print(f"{status:<8} {w['name'][:48]:<50} {w['id']:<10}")
        print(f"\nTotal: {len(workflows)}")
    finally:
        client.close()


def sync_all(activate_core: bool = True):
    """Sync all local workflows to n8n"""
    client = N8NClient()
    
    if not WORKFLOWS_DIR.exists():
        print(f"❌ Workflows directory not found: {WORKFLOWS_DIR}")
        return
    
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.json"))
    print(f"📁 Found {len(workflow_files)} workflow files\n")
    
    imported = 0
    activated = 0
    errors = 0
    
    for filepath in workflow_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            name = data.get("name", filepath.stem)
            existing = client.find_by_name(name)
            
            if existing:
                client.update_workflow(existing["id"], data)
                result_id = existing["id"]
                action = "Updated"
            else:
                result = client.create_workflow(data)
                result_id = result.get("id")
                action = "Created"
            
            # Activate core workflows
            is_core = filepath.name.startswith(("01_", "02_", "myca-"))
            if activate_core and is_core and result_id:
                try:
                    client.activate(result_id)
                    print(f"✅ {action} & Activated: {name}")
                    activated += 1
                except:
                    print(f"⚠️  {action}: {name} (activation failed)")
            else:
                print(f"📥 {action}: {name}")
            
            imported += 1
            
        except Exception as e:
            print(f"❌ Failed: {filepath.name} - {e}")
            errors += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Imported: {imported}")
    print(f"🔄 Activated: {activated}")
    print(f"❌ Errors: {errors}")
    
    client.close()


def activate_all():
    """Activate all workflows"""
    client = N8NClient()
    try:
        workflows = client.list_workflows()
        inactive = [w for w in workflows if not w.get("active")]
        
        print(f"Activating {len(inactive)} inactive workflows...\n")
        
        for w in inactive:
            try:
                client.activate(w["id"])
                print(f"✅ Activated: {w['name']}")
            except Exception as e:
                print(f"❌ Failed: {w['name']} - {e}")
        
        print(f"\n✅ Done!")
    finally:
        client.close()


def show_stats():
    """Show workflow statistics"""
    client = N8NClient()
    try:
        workflows = client.list_workflows()
        active = [w for w in workflows if w.get("active")]
        inactive = [w for w in workflows if not w.get("active")]
        
        # Count by prefix
        prefixes = {}
        for w in workflows:
            name = w["name"]
            if "_" in name[:3]:
                prefix = name.split("_")[0]
            elif name.startswith("myca"):
                prefix = "myca"
            else:
                prefix = "other"
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
        
        print("\n📊 N8N Workflow Statistics")
        print("=" * 40)
        print(f"Total workflows:    {len(workflows)}")
        print(f"Active workflows:   {len(active)}")
        print(f"Inactive workflows: {len(inactive)}")
        print("\nBy prefix:")
        for prefix, count in sorted(prefixes.items()):
            print(f"  {prefix}: {count}")
    finally:
        client.close()


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "--health":
            health_check()
        elif cmd == "--list":
            list_workflows()
        elif cmd == "--activate-all":
            activate_all()
        elif cmd == "--stats":
            show_stats()
        elif cmd == "--no-activate":
            sync_all(activate_core=False)
        else:
            print(f"Unknown option: {cmd}")
            print(__doc__)
    else:
        # Default: sync all and activate core
        if health_check():
            print()
            sync_all(activate_core=True)


if __name__ == "__main__":
    main()
