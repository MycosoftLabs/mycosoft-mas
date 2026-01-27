"""
n8n Cloud Sync Service
Bidirectional sync between local n8n (192.168.0.188:5678) and cloud (mycosoft.app.n8n.cloud)
Date: January 27, 2026
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import base64


class N8NCloudSync:
    """Synchronizes workflows between local n8n and n8n cloud."""
    
    def __init__(
        self,
        local_url: str = None,
        local_username: str = None,
        local_password: str = None,
        cloud_url: str = None,
        cloud_api_key: str = None,
        workflows_dir: str = None
    ):
        # Local n8n instance
        self.local_url = local_url or os.getenv("N8N_URL", "http://192.168.0.188:5678")
        self.local_username = local_username or os.getenv("N8N_USERNAME", "admin")
        self.local_password = local_password or os.getenv("N8N_PASSWORD", "Mushroom1!")
        
        # Cloud n8n instance
        self.cloud_url = cloud_url or os.getenv("N8N_CLOUD_URL", "https://mycosoft.app.n8n.cloud")
        self.cloud_api_key = cloud_api_key or os.getenv("N8N_CLOUD_API_KEY", "")
        
        # Local workflows directory
        self.workflows_dir = Path(workflows_dir or os.getenv(
            "N8N_WORKFLOWS_DIR",
            str(Path(__file__).parent.parent / "n8n" / "workflows")
        ))
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def local_auth(self) -> str:
        """Get base64 encoded auth for local n8n."""
        credentials = f"{self.local_username}:{self.local_password}"
        return base64.b64encode(credentials.encode()).decode()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    # ==================== Local n8n Operations ====================
    
    async def get_local_workflows(self) -> List[Dict[str, Any]]:
        """Get all workflows from local n8n instance."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.local_url}/api/v1/workflows",
                headers={"Authorization": f"Basic {self.local_auth}"}
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
                headers={"Authorization": f"Basic {self.local_auth}"}
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
                headers={
                    "Authorization": f"Basic {self.local_auth}",
                    "Content-Type": "application/json"
                },
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
                headers={
                    "Authorization": f"Basic {self.local_auth}",
                    "Content-Type": "application/json"
                },
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
    
    # ==================== Cloud n8n Operations ====================
    
    async def get_cloud_workflows(self) -> List[Dict[str, Any]]:
        """Get all workflows from n8n cloud."""
        if not self.cloud_api_key:
            print("No cloud API key configured")
            return []
        
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.cloud_url}/api/v1/workflows",
                headers={"X-N8N-API-KEY": self.cloud_api_key}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    error = await response.text()
                    print(f"Error getting cloud workflows: {response.status} - {error}")
                    return []
        except Exception as e:
            print(f"Error connecting to n8n cloud: {e}")
            return []
    
    async def create_cloud_workflow(self, workflow: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a workflow in n8n cloud."""
        if not self.cloud_api_key:
            print("No cloud API key configured")
            return None
        
        session = await self._get_session()
        try:
            # Remove local-specific fields
            workflow_data = {k: v for k, v in workflow.items() if k not in ['id', 'createdAt', 'updatedAt']}
            
            async with session.post(
                f"{self.cloud_url}/api/v1/workflows",
                headers={
                    "X-N8N-API-KEY": self.cloud_api_key,
                    "Content-Type": "application/json"
                },
                json=workflow_data
            ) as response:
                if response.status in (200, 201):
                    return await response.json()
                else:
                    error = await response.text()
                    print(f"Error creating cloud workflow: {response.status} - {error}")
                    return None
        except Exception as e:
            print(f"Error creating cloud workflow: {e}")
            return None
    
    # ==================== File Operations ====================
    
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
        
        results = {'created': [], 'updated': [], 'errors': []}
        
        for workflow in file_workflows:
            name = workflow.get('name', 'Unknown')
            try:
                if name in local_by_name:
                    local_id = local_by_name[name]['id']
                    result = await self.update_local_workflow(local_id, workflow)
                    if result:
                        results['updated'].append(name)
                    else:
                        results['errors'].append(f"Failed to update: {name}")
                else:
                    result = await self.create_local_workflow(workflow)
                    if result:
                        results['created'].append(name)
                    else:
                        results['errors'].append(f"Failed to create: {name}")
            except Exception as e:
                results['errors'].append(f"{name}: {str(e)}")
        
        return results
    
    async def sync_local_to_cloud(self) -> Dict[str, Any]:
        """Sync local n8n workflows to cloud."""
        local_workflows = await self.get_local_workflows()
        cloud_workflows = await self.get_cloud_workflows()
        
        cloud_by_name = {w['name']: w for w in cloud_workflows}
        
        results = {'created': [], 'skipped': [], 'errors': []}
        
        for workflow in local_workflows:
            name = workflow.get('name', 'Unknown')
            try:
                full_workflow = await self.get_local_workflow(workflow['id'])
                if not full_workflow:
                    results['errors'].append(f"Could not fetch: {name}")
                    continue
                
                if name in cloud_by_name:
                    results['skipped'].append(name)
                else:
                    result = await self.create_cloud_workflow(full_workflow)
                    if result:
                        results['created'].append(name)
                    else:
                        results['errors'].append(f"Failed to create: {name}")
            except Exception as e:
                results['errors'].append(f"{name}: {str(e)}")
        
        return results
    
    async def full_sync(self) -> Dict[str, Any]:
        """Perform a full sync: files -> local -> cloud."""
        results = {
            'files_to_local': {},
            'local_to_cloud': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # First, sync file workflows to local
        print("Syncing workflow files to local n8n...")
        results['files_to_local'] = await self.sync_files_to_local()
        
        # Then sync local to cloud
        print("Syncing local n8n to cloud...")
        results['local_to_cloud'] = await self.sync_local_to_cloud()
        
        return results


async def main():
    """Run the sync."""
    # Load environment variables
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env.local"
    load_dotenv(env_path)
    
    sync = N8NCloudSync()
    
    print("=== n8n Cloud Sync Service ===")
    print(f"Local: {sync.local_url}")
    print(f"Cloud: {sync.cloud_url}")
    print(f"Workflows dir: {sync.workflows_dir}")
    print()
    
    # Get local workflows
    print("Fetching local workflows...")
    local_workflows = await sync.get_local_workflows()
    print(f"Found {len(local_workflows)} local workflows")
    
    # Get cloud workflows
    print("Fetching cloud workflows...")
    cloud_workflows = await sync.get_cloud_workflows()
    print(f"Found {len(cloud_workflows)} cloud workflows")
    
    # Get file workflows
    print("Checking workflow files...")
    file_workflows = sync.get_file_workflows()
    print(f"Found {len(file_workflows)} workflow files")
    print()
    
    if local_workflows and len(cloud_workflows) == 0:
        print("Cloud is empty. Syncing all local workflows to cloud...")
        results = await sync.sync_local_to_cloud()
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
