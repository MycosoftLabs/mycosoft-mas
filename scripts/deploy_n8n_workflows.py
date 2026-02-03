#!/usr/bin/env python3
"""
N8N Workflow Deployment Script - January 25, 2026

This script imports all local n8n workflows to the n8n instance.
Run this after setting up n8n or when workflows need to be synced.

Usage:
    python scripts/deploy_n8n_workflows.py [--activate-all] [--cloud]

Environment Variables:
    N8N_URL: Local n8n URL (default: http://192.168.0.188:5678)
    N8N_API_KEY: n8n API key for authentication
    N8N_CLOUD_URL: Cloud n8n URL (optional)
    N8N_CLOUD_API_KEY: Cloud n8n API key (optional)
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mycosoft_mas.core.n8n_workflow_engine import (
    N8NWorkflowEngine,
    SyncResult,
    WORKFLOWS_DIR,
    BACKUP_DIR
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print script banner"""
    print("=" * 60)
    print("MYCA N8N Workflow Deployment")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def print_result(result: SyncResult):
    """Print sync result summary"""
    print("\n" + "=" * 40)
    print("SYNC RESULT SUMMARY")
    print("=" * 40)
    
    print(f"\nImported: {len(result.imported)}")
    for f in result.imported:
        print(f"  + {f}")
    
    print(f"\nActivated: {len(result.activated)}")
    for f in result.activated:
        print(f"  * {f}")
    
    if result.errors:
        print(f"\nErrors: {len(result.errors)}")
        for e in result.errors:
            print(f"  ! {e['file']}: {e['error']}")
    
    print("\n" + "=" * 40)


def deploy_workflows(
    use_cloud: bool = False,
    activate_all: bool = False,
    dry_run: bool = False
):
    """Deploy all workflows to n8n"""
    
    print_banner()
    
    # Create engine
    engine = N8NWorkflowEngine(use_cloud=use_cloud)
    
    # Health check first
    print("\nChecking n8n connection...")
    health = engine.health_check()
    
    if not health.get("connected"):
        print(f"ERROR: Cannot connect to n8n at {health.get('base_url')}")
        print(f"Error: {health.get('error', 'Unknown error')}")
        return False
    
    print(f"Connected to: {health.get('base_url')}")
    print(f"Current workflows: {health.get('workflow_count')} ({health.get('active_count')} active)")
    
    # List local workflows
    print(f"\nLocal workflows directory: {WORKFLOWS_DIR}")
    workflow_files = list(WORKFLOWS_DIR.glob("**/*.json"))
    print(f"Found {len(workflow_files)} workflow files")
    
    if dry_run:
        print("\n[DRY RUN] Would import:")
        for f in sorted(workflow_files):
            print(f"  - {f.name}")
        return True
    
    # Sync workflows
    print("\nImporting workflows...")
    result = engine.sync_all_local_workflows(activate_core=not activate_all)
    
    # If activate_all, activate all workflows
    if activate_all and result.imported:
        print("\nActivating all workflows...")
        for wf in engine.list_workflows():
            if not wf.active:
                try:
                    engine.activate_workflow(wf.id)
                    result.activated.append(wf.name)
                except Exception as e:
                    logger.warning(f"Could not activate {wf.name}: {e}")
    
    print_result(result)
    
    # Final stats
    final_health = engine.health_check()
    print(f"\nFinal state: {final_health.get('workflow_count')} workflows ({final_health.get('active_count')} active)")
    
    engine.close()
    return len(result.errors) == 0


def backup_workflows(use_cloud: bool = False):
    """Backup all workflows from n8n to local files"""
    
    print_banner()
    print("\nBacking up workflows from n8n...")
    
    engine = N8NWorkflowEngine(use_cloud=use_cloud)
    
    health = engine.health_check()
    if not health.get("connected"):
        print(f"ERROR: Cannot connect to n8n")
        return False
    
    print(f"Connected to: {health.get('base_url')}")
    
    # Export all workflows
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_DIR / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    paths = engine.export_all_workflows(backup_dir)
    
    print(f"\nBackup complete: {len(paths)} workflows exported to {backup_dir}")
    
    engine.close()
    return True


def list_workflows(use_cloud: bool = False):
    """List all workflows in n8n"""
    
    engine = N8NWorkflowEngine(use_cloud=use_cloud)
    
    health = engine.health_check()
    if not health.get("connected"):
        print(f"ERROR: Cannot connect to n8n at {health.get('base_url')}")
        return
    
    workflows = engine.list_workflows()
    
    print(f"\nWorkflows on {health.get('base_url')}:")
    print("-" * 60)
    
    for wf in workflows:
        status = "ACTIVE" if wf.active else "inactive"
        print(f"  [{status:8}] {wf.name} ({wf.category.value})")
    
    print("-" * 60)
    print(f"Total: {len(workflows)} ({len([w for w in workflows if w.active])} active)")
    
    engine.close()


def main():
    parser = argparse.ArgumentParser(
        description="Deploy n8n workflows for MYCA orchestrator"
    )
    parser.add_argument(
        "--cloud",
        action="store_true",
        help="Use cloud n8n instance instead of local"
    )
    parser.add_argument(
        "--activate-all",
        action="store_true",
        help="Activate all workflows after import"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup workflows from n8n instead of deploying"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List workflows in n8n"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_workflows(use_cloud=args.cloud)
    elif args.backup:
        success = backup_workflows(use_cloud=args.cloud)
        sys.exit(0 if success else 1)
    else:
        success = deploy_workflows(
            use_cloud=args.cloud,
            activate_all=args.activate_all,
            dry_run=args.dry_run
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
