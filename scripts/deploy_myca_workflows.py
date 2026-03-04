#!/usr/bin/env python3
"""
MYCA Personal Workflow Deployment — VM 191 n8n (192.168.0.191:5679)

Deploys MYCA's 12 personal workflows to her n8n instance on VM 191.
These are SEPARATE from the 69 MAS workflows on VM 188:5678.

System boundary:
  - MAS workflows (n8n/workflows/)      → VM 188:5678  (use deploy_n8n_workflows.py)
  - MYCA workflows (workflows/n8n/)     → VM 191:5679  (THIS script)

Usage:
    # Deploy via API key (preferred)
    MYCA_N8N_API_KEY=xxx python scripts/deploy_myca_workflows.py

    # Deploy via SSH tunnel (if running from Sandbox/Windows)
    MYCA_N8N_URL=http://localhost:15679 MYCA_N8N_API_KEY=xxx python scripts/deploy_myca_workflows.py

    # List existing workflows
    python scripts/deploy_myca_workflows.py --list

    # Dry run
    python scripts/deploy_myca_workflows.py --dry-run
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from pathlib import Path

import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# MYCA's personal workflows live here
MYCA_WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows" / "n8n"

# MYCA's n8n instance — VM 191, port 5679
DEFAULT_MYCA_N8N_URL = "http://192.168.0.191:5679"


class MYCAWorkflowDeployer:
    """Deploy MYCA personal workflows to VM 191 n8n."""

    def __init__(self, n8n_url: str = None, api_key: str = None):
        self.n8n_url = n8n_url or os.getenv("MYCA_N8N_URL", DEFAULT_MYCA_N8N_URL)
        self.api_key = api_key or os.getenv("MYCA_N8N_API_KEY", "")
        self._session = None

        if not self.api_key:
            raise ValueError(
                "MYCA n8n API key required. Set MYCA_N8N_API_KEY env var.\n"
                "Get it from: http://192.168.0.191:5679/settings/api"
            )

    def _headers(self) -> dict:
        return {
            "X-N8N-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def health_check(self) -> bool:
        """Check n8n connectivity."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.n8n_url}/api/v1/workflows",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    count = len(data.get("data", []))
                    logger.info(f"Connected to MYCA n8n at {self.n8n_url} ({count} workflows)")
                    return True
                else:
                    logger.error(f"n8n returned {resp.status}: {await resp.text()}")
                    return False
        except Exception as e:
            logger.error(f"Cannot connect to MYCA n8n at {self.n8n_url}: {e}")
            return False

    async def get_existing_workflows(self) -> dict:
        """Get existing workflows keyed by name."""
        session = await self._get_session()
        async with session.get(
            f"{self.n8n_url}/api/v1/workflows",
            headers=self._headers(),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {w["name"]: w for w in data.get("data", [])}
            return {}

    def get_workflow_files(self) -> list:
        """Load all MYCA workflow JSON files."""
        if not MYCA_WORKFLOWS_DIR.exists():
            logger.error(f"Workflows directory not found: {MYCA_WORKFLOWS_DIR}")
            return []

        workflows = []
        for fp in sorted(MYCA_WORKFLOWS_DIR.glob("*.json")):
            if fp.name in ("MANIFEST.json",):
                continue
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    wf = json.load(f)
                    wf["_source_file"] = fp.name
                    workflows.append(wf)
            except Exception as e:
                logger.warning(f"Skipping {fp.name}: {e}")
        return workflows

    async def create_workflow(self, workflow: dict) -> bool:
        """Create a new workflow."""
        session = await self._get_session()
        clean = {k: v for k, v in workflow.items() if not k.startswith("_") and k not in ("id", "createdAt", "updatedAt")}
        async with session.post(
            f"{self.n8n_url}/api/v1/workflows",
            headers=self._headers(),
            json=clean,
        ) as resp:
            if resp.status in (200, 201):
                return True
            error = await resp.text()
            logger.error(f"Create failed ({resp.status}): {error[:200]}")
            return False

    async def update_workflow(self, wf_id: str, workflow: dict) -> bool:
        """Update an existing workflow."""
        session = await self._get_session()
        clean = {k: v for k, v in workflow.items() if not k.startswith("_") and k not in ("id", "createdAt", "updatedAt")}
        async with session.patch(
            f"{self.n8n_url}/api/v1/workflows/{wf_id}",
            headers=self._headers(),
            json=clean,
        ) as resp:
            return resp.status == 200

    async def deploy_all(self, dry_run: bool = False) -> dict:
        """Deploy all MYCA workflows."""
        print("=" * 55)
        print("MYCA Personal Workflow Deployment")
        print(f"Target: {self.n8n_url}")
        print(f"Source: {MYCA_WORKFLOWS_DIR}")
        print("=" * 55)

        if not await self.health_check():
            return {"error": "Cannot connect to MYCA n8n"}

        existing = await self.get_existing_workflows()
        files = self.get_workflow_files()
        print(f"\nExisting workflows: {len(existing)}")
        print(f"Local workflow files: {len(files)}")

        if dry_run:
            print("\n[DRY RUN] Would deploy:")
            for wf in files:
                name = wf.get("name", wf.get("_source_file"))
                action = "UPDATE" if name in existing else "CREATE"
                print(f"  [{action}] {name}")
            return {"dry_run": True, "count": len(files)}

        created, updated, errors = 0, 0, 0
        for wf in files:
            name = wf.get("name", wf.get("_source_file", "Unknown"))
            src = wf.get("_source_file", "?")

            if name in existing:
                print(f"  Updating: {name} ({src})")
                if await self.update_workflow(existing[name]["id"], wf):
                    updated += 1
                else:
                    errors += 1
            else:
                print(f"  Creating: {name} ({src})")
                if await self.create_workflow(wf):
                    created += 1
                else:
                    errors += 1

        print(f"\n{'=' * 40}")
        print(f"Created: {created}")
        print(f"Updated: {updated}")
        print(f"Errors:  {errors}")
        print(f"Total:   {created + updated}")
        print(f"{'=' * 40}")

        return {"created": created, "updated": updated, "errors": errors}

    async def list_workflows(self):
        """List all workflows on MYCA n8n."""
        if not await self.health_check():
            return

        existing = await self.get_existing_workflows()
        print(f"\nWorkflows on MYCA n8n ({self.n8n_url}):")
        print("-" * 55)
        for name, wf in sorted(existing.items()):
            status = "ACTIVE" if wf.get("active") else "inactive"
            print(f"  [{status:8}] {name}")
        print("-" * 55)
        print(f"Total: {len(existing)}")


async def main():
    parser = argparse.ArgumentParser(description="Deploy MYCA personal workflows to VM 191 n8n")
    parser.add_argument("--list", action="store_true", help="List workflows on MYCA n8n")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deployed")
    parser.add_argument("--url", type=str, help="Override MYCA n8n URL")
    parser.add_argument("--api-key", type=str, help="Override MYCA n8n API key")
    args = parser.parse_args()

    deployer = MYCAWorkflowDeployer(n8n_url=args.url, api_key=args.api_key)
    try:
        if args.list:
            await deployer.list_workflows()
        else:
            await deployer.deploy_all(dry_run=args.dry_run)
    finally:
        await deployer.close()


if __name__ == "__main__":
    asyncio.run(main())
