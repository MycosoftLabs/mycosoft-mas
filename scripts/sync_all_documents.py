#!/usr/bin/env python3
"""
Master Document Sync Script
Orchestrates the complete document management workflow:
1. Scan and inventory all documents
2. Sync to Notion knowledge base
3. Sync to NAS shared drive
4. Generate master index
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def run_script(script_path: str, description: str) -> bool:
    """Run a Python script and return success status."""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=Path(__file__).parent.parent,
            check=True,
            capture_output=False
        )
        print(f"\n✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error running {description}: {e}")
        return False

def main():
    """Main orchestration."""
    print("="*60)
    print("MYCOSOFT MAS - COMPLETE DOCUMENT SYNC")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    scripts_dir = Path(__file__).parent
    root_dir = scripts_dir.parent
    
    results = {}
    
    # Step 1: Scan and inventory documents
    results["inventory"] = run_script(
        str(scripts_dir / "document_inventory.py"),
        "Step 1: Scanning and inventorying all documents"
    )
    
    if not results["inventory"]:
        print("\n❌ Inventory scan failed. Cannot proceed.")
        sys.exit(1)
    
    # Step 2: Sync to Notion (optional, requires API keys)
    notion_api_key = os.getenv("NOTION_API_KEY")
    notion_db_id = os.getenv("NOTION_DATABASE_ID")
    
    if notion_api_key and notion_db_id:
        results["notion"] = run_script(
            str(scripts_dir / "sync_to_notion.py"),
            "Step 2: Syncing documents to Notion knowledge base"
        )
    else:
        print("\n⏭️  Skipping Notion sync (NOTION_API_KEY or NOTION_DATABASE_ID not set)")
        results["notion"] = None
    
    # Step 3: Sync to NAS (optional, requires NAS path)
    nas_path = os.getenv("NAS_DOCS_PATH")
    if not nas_path:
        # Try to detect
        from sync_to_nas import get_nas_path
        nas_path = get_nas_path()
    
    if nas_path:
        results["nas"] = run_script(
            str(scripts_dir / "sync_to_nas.py"),
            "Step 3: Syncing documents to NAS shared drive"
        )
    else:
        print("\n⏭️  Skipping NAS sync (NAS_DOCS_PATH not set or NAS not accessible)")
        results["nas"] = None
    
    # Summary
    print("\n" + "="*60)
    print("SYNC SUMMARY")
    print("="*60)
    print(f"Inventory: {'✓' if results['inventory'] else '❌'}")
    print(f"Notion: {'✓' if results.get('notion') else '⏭️  Skipped' if results.get('notion') is None else '❌'}")
    print(f"NAS: {'✓' if results.get('nas') else '⏭️  Skipped' if results.get('nas') is None else '❌'}")
    print("="*60)
    
    # Check inventory file
    inventory_file = root_dir / "docs" / "document_inventory.json"
    if inventory_file.exists():
        print(f"\n📄 Full inventory available at: {inventory_file}")
    
    index_file = root_dir / "DOCUMENT_INDEX.md"
    if index_file.exists():
        print(f"📄 Document index available at: {index_file}")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

