#!/usr/bin/env python3
"""
Auto-Index New Documents
Scans for new or modified markdown/README files and indexes them.
Can be run manually or as a scheduled task.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.services.document_watcher import DocumentWatcher
from mycosoft_mas.services.document_knowledge_base import DocumentKnowledgeBase


async def main():
    """Main function."""
    print("="*60)
    print("MYCOSOFT MAS - AUTO-INDEX NEW DOCUMENTS")
    print("="*60)
    print()
    
    # Initialize knowledge base
    print("Initializing knowledge base...")
    kb = DocumentKnowledgeBase()
    
    if not await kb.initialize():
        print("❌ Failed to initialize knowledge base")
        print("   Make sure Qdrant and Redis are available")
        sys.exit(1)
    
    print("✓ Knowledge base initialized")
    print()
    
    # Create watcher
    print("Scanning for new/modified documents...")
    watcher = DocumentWatcher(knowledge_base=kb)
    
    # Force scan
    stats = await watcher.force_scan()
    
    print()
    print("="*60)
    print("SCAN COMPLETE")
    print("="*60)
    print(f"Documents Scanned: {stats['scanned']}")
    print(f"Indexed: {stats['indexed']}")
    print(f"Failed: {stats['failed']}")
    print("="*60)
    
    if stats['indexed'] > 0:
        print(f"\n✓ {stats['indexed']} new/modified documents indexed!")
    
    if stats['failed'] > 0:
        print(f"\n⚠️  {stats['failed']} documents failed to index")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

