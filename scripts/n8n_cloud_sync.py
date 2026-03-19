"""
n8n Local Sync Service
Sync workflow JSON files to local MAS n8n (192.168.0.188:5678).
All workflows run locally — no cloud instance needed.

Originally: n8n Cloud Sync Service (January 27, 2026)
Migrated to local-only: March 19, 2026
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import base64


class N8NLocalSync:
    """Synchronizes workflow JSON files to local MAS n8n instance."""

    def __init__(
        self,
        local_url: str = None,
        local_username: str = None,
        local_password: str = None,
        api_key: str = None,
        workflows_dir: str = None
    ):
        # Local n8n instance (MAS VM 188)
        self.local_url = local_url or os.getenv("N8N_URL", "http://192.168.0.188:5678")
        self.local_username = local_username or os.getenv("N8N_USERNAME", "")
        self.local_password = local_password or os.getenv("N8N_PASSWORD", "")
        self.api_key = api_key or os.getenv("N8N_API_KEY", "")

        # Local workflows directory
        self.workflows_dir = Path(workflows_dir or os.getenv(
            "N8N_WORKFLOWS_DIR",
            str(Path(__file__).parent.parent / "n8n" / "workflows")
        ))

        self._session: Optional[aiohttp.ClientSession] = None

    def _headers(self) -> Dict[str, str]:
        """Get auth headers — prefer API key, fall back to basic auth."""
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-N8N-API-KEY"] = self.api_key
        elif self.local_username and self.local_password:
            credentials = f"{self.local_username}:{self.local_password}"
            h["Authorization"] = f"Basic {base64.b64encode(credentials.encode()).decode()}"
        return h

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_local_workflows(self) -> List[Dict[str, Any]]:
        """Get all workflows from local n8n instance."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.local_url}/api/v1/workflows",
                headers=self._headers()
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    print(f"Error getting local workflows: {response.status}")
                    return []
        except Exception as e:
            print(f"Error connecting to local n8n: {e}")
            return []

    async def get_local_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific workflow from local n8n."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.local_url}/api/v1/workflows/{workflow_id}",
                headers=self._headers()
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f"Error getting local workflow {workflow_id}: {e}")
            return None

    async def create_local_workflow(self, workflow: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a workflow in local n8n."""
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.local_url}/api/v1/workflows",
                headers=self._headers(),
                json=workflow
            ) as response:
                if response.status in (200, 201):
                    return await response.json()
                else:
                    error = await response.text()
                    print(f"Error creating local workflow: {response.status} - {error}")
                    return None
        except Exception as e:
            print(f"Error creating local workflow: {e}")
            return None

    async def update_local_workflow(self, workflow_id: str, workflow: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a workflow in local n8n."""
        session = await self._get_session()
        try:
            async with session.patch(
                f"{self.local_url}/api/v1/workflows/{workflow_id}",
                headers=self._headers(),
                json=workflow
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    print(f"Error updating local workflow: {response.status} - {error}")
                    return None
        except Exception as e:
            print(f"Error updating local workflow: {e}")
            return None

    def get_file_workflows(self) -> List[Dict[str, Any]]:
        """Get all workflows from local JSON files."""
        workflows = []
        if not self.workflows_dir.exists():
            print(f"Workflows directory not found: {self.workflows_dir}")
            return workflows

        for file_path in self.workflows_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                    workflow['_file_path'] = str(file_path)
                    workflow['_file_name'] = file_path.name
                    workflows.append(workflow)
            except Exception as e:
                print(f"Error reading workflow file {file_path}: {e}")

        return workflows

    async def sync_files_to_local(self) -> Dict[str, Any]:
        """Sync workflow JSON files to local n8n instance."""
        file_workflows = self.get_file_workflows()
        local_workflows = await self.get_local_workflows()

        local_by_name = {w['name']: w for w in local_workflows}

        results = {'created': [], 'updated': [], 'skipped': [], 'errors': []}

        for workflow in file_workflows:
            name = workflow.get('name', 'Unknown')
            try:
                if name in local_by_name:
                    results['skipped'].append(name)
                else:
                    result = await self.create_local_workflow(workflow)
                    if result:
                        results['created'].append(name)
                    else:
                        results['errors'].append(f"Failed to create: {name}")
            except Exception as e:
                results['errors'].append(f"{name}: {str(e)}")

        return results

    async def export_from_local(self) -> Dict[str, Any]:
        """Export all workflows from local n8n to JSON files (backup)."""
        local_workflows = await self.get_local_workflows()
        results = {'exported': [], 'errors': []}

        self.workflows_dir.mkdir(parents=True, exist_ok=True)

        for wf_summary in local_workflows:
            name = wf_summary.get('name', 'Unknown')
            try:
                full_wf = await self.get_local_workflow(wf_summary['id'])
                if not full_wf:
                    results['errors'].append(f"Could not fetch: {name}")
                    continue
                safe_name = "".join(c if c.isalnum() or c in " ._-" else "_" for c in name).strip()
                file_path = self.workflows_dir / f"{safe_name}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(full_wf, f, indent=2)
                results['exported'].append(name)
            except Exception as e:
                results['errors'].append(f"{name}: {str(e)}")

        return results


# Backwards compatibility alias
N8NCloudSync = N8NLocalSync


async def main():
    """Run the sync."""
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env.local"
    load_dotenv(env_path)

    sync = N8NLocalSync()

    print("=== n8n Local Sync Service ===")
    print(f"Local n8n: {sync.local_url}")
    print(f"Workflows dir: {sync.workflows_dir}")
    print()

    # Get local workflows
    print("Fetching local workflows...")
    local_workflows = await sync.get_local_workflows()
    print(f"Found {len(local_workflows)} local workflows")

    # Get file workflows
    print("Checking workflow files...")
    file_workflows = sync.get_file_workflows()
    print(f"Found {len(file_workflows)} workflow files")
    print()

    # Sync files to local n8n
    print("Syncing workflow files to local n8n...")
    results = await sync.sync_files_to_local()
    print(f"Created: {len(results['created'])}")
    print(f"Skipped: {len(results['skipped'])}")
    print(f"Errors: {len(results['errors'])}")
    if results['errors']:
        for err in results['errors'][:5]:
            print(f"  - {err}")

    await sync.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
