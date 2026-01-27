"""
Import n8n Workflows from JSON files to local n8n instance
Date: January 27, 2026
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
import base64


class N8NWorkflowImporter:
    def __init__(self):
        self.n8n_url = os.getenv("N8N_URL", "http://192.168.0.188:5678")
        self.username = os.getenv("N8N_USERNAME", "admin")
        self.password = os.getenv("N8N_PASSWORD", "Mushroom1!")
        self.workflows_dir = Path(__file__).parent.parent / "n8n" / "workflows"
        self._session = None
    
    @property
    def auth_header(self) -> str:
        credentials = f"{self.username}:{self.password}"
        return base64.b64encode(credentials.encode()).decode()
    
    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_existing_workflows(self):
        """Get list of existing workflows."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.n8n_url}/api/v1/workflows",
                headers={"Authorization": f"Basic {self.auth_header}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {w['name']: w for w in data.get('data', [])}
                else:
                    print(f"Error getting workflows: {response.status}")
                    return {}
        except Exception as e:
            print(f"Error: {e}")
            return {}
    
    async def create_workflow(self, workflow: dict) -> bool:
        """Create a workflow in n8n."""
        session = await self._get_session()
        try:
            # Clean up workflow data
            workflow_data = {k: v for k, v in workflow.items() 
                          if k not in ['id', 'createdAt', 'updatedAt', '_file_path', '_file_name']}
            
            async with session.post(
                f"{self.n8n_url}/api/v1/workflows",
                headers={
                    "Authorization": f"Basic {self.auth_header}",
                    "Content-Type": "application/json"
                },
                json=workflow_data
            ) as response:
                if response.status in (200, 201):
                    return True
                else:
                    error = await response.text()
                    print(f"  Error creating: {response.status} - {error[:100]}")
                    return False
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    async def update_workflow(self, workflow_id: str, workflow: dict) -> bool:
        """Update a workflow in n8n."""
        session = await self._get_session()
        try:
            workflow_data = {k: v for k, v in workflow.items() 
                          if k not in ['id', 'createdAt', 'updatedAt', '_file_path', '_file_name']}
            
            async with session.patch(
                f"{self.n8n_url}/api/v1/workflows/{workflow_id}",
                headers={
                    "Authorization": f"Basic {self.auth_header}",
                    "Content-Type": "application/json"
                },
                json=workflow_data
            ) as response:
                return response.status == 200
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def get_workflow_files(self):
        """Get all workflow JSON files."""
        if not self.workflows_dir.exists():
            print(f"Workflows directory not found: {self.workflows_dir}")
            return []
        
        files = []
        for file_path in sorted(self.workflows_dir.glob("*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                    workflow['_file_name'] = file_path.name
                    files.append(workflow)
            except Exception as e:
                print(f"Error reading {file_path.name}: {e}")
        
        return files
    
    async def import_all(self):
        """Import all workflow files to n8n."""
        print(f"=== n8n Workflow Importer ===")
        print(f"n8n URL: {self.n8n_url}")
        print(f"Workflows dir: {self.workflows_dir}")
        print()
        
        # Get existing workflows
        existing = await self.get_existing_workflows()
        print(f"Existing workflows in n8n: {len(existing)}")
        
        # Get workflow files
        files = self.get_workflow_files()
        print(f"Workflow files found: {len(files)}")
        print()
        
        if not files:
            print("No workflow files to import.")
            return
        
        created = 0
        updated = 0
        errors = 0
        
        for workflow in files:
            name = workflow.get('name', 'Unknown')
            file_name = workflow.get('_file_name', 'unknown.json')
            
            if name in existing:
                print(f"Updating: {name} ({file_name})")
                if await self.update_workflow(existing[name]['id'], workflow):
                    updated += 1
                else:
                    errors += 1
            else:
                print(f"Creating: {name} ({file_name})")
                if await self.create_workflow(workflow):
                    created += 1
                else:
                    errors += 1
        
        print()
        print(f"=== Import Complete ===")
        print(f"Created: {created}")
        print(f"Updated: {updated}")
        print(f"Errors: {errors}")
        print(f"Total: {created + updated}")


async def main():
    importer = N8NWorkflowImporter()
    await importer.import_all()
    await importer.close()


if __name__ == "__main__":
    asyncio.run(main())
